"""Verify decoded video, synchronized charts, accessibility and the single-paper layout."""

from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import json
import re
import threading
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        if self.path.split("?")[0].endswith((".mp4", ".webm")):
            self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        self.range_left = None
        path = Path(self.translate_path(self.path))
        requested = self.headers.get("Range")
        if not requested or path.suffix not in (".mp4", ".webm") or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested)
        if not match or not any(match.groups()):
            self.send_error(416)
            return None
        a, b = match.groups()
        start = int(a) if a else max(0, size - int(b))
        end = min(size - 1, int(b)) if a and b else size - 1
        if not 0 <= start <= end < size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        file = path.open("rb")
        file.seek(start)
        self.range_left = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(self.range_left))
        self.end_headers()
        return file

    def copyfile(self, source, outputfile):
        if self.range_left is None:
            return super().copyfile(source, outputfile)
        while self.range_left:
            data = source.read(min(65536, self.range_left))
            if not data:
                break
            outputfile.write(data)
            self.range_left -= len(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    record = json.loads((args.site / "papers/adam/experiment.json").read_text())
    assert record["fixture"] == "unequal-scale-quartic-v1"
    assert record["target_test"]["settled"] == {"gd": None, "momentum": 611, "adam": 66}
    assert record["render"]["near_wall"] == "wireframe cutaway"
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(args.site.resolve()))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    for name in ["adam.mp4", "adam.webm"]:
        req = urllib.request.Request(
            origin + "/papers/adam/" + name, headers={"Range": "bytes=0-31"}
        )
        with urllib.request.urlopen(req) as response:
            assert response.status == 206
            assert response.read() == (args.site / "papers/adam" / name).read_bytes()[:32]
    proof = {"source": record["source"], "checks": [], "errors": [], "external_requests": []}
    try:
        with sync_playwright() as pw:
            for engine in ["chromium", "webkit"]:
                browser = getattr(pw, engine).launch()
                for width in [1440, 390]:
                    print(f"Checking Adam film: {engine}, {width}px", flush=True)
                    context = browser.new_context(
                        viewport={"width": width, "height": 1000}, reduced_motion="reduce"
                    )
                    page = context.new_page()
                    page.on("pageerror", lambda error: proof["errors"].append(str(error)))
                    page.on(
                        "request",
                        lambda req: (
                            proof["external_requests"].append(req.url)
                            if req.url.startswith(("http:", "https:"))
                            and not req.url.startswith(origin + "/")
                            else None
                        ),
                    )
                    response = page.goto(origin + "/papers/adam/", wait_until="networkidle")
                    assert response.status == 200
                    expect(page.locator("html")).to_have_attribute("lang", "en")
                    expect(page.locator("#iteration")).to_be_enabled()
                    assert page.locator("video").count() == 1
                    assert page.locator(".chart-svg").count() == 2
                    assert not page.locator(".details").evaluate("e=>e.open")
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
                    movie = page.locator("#movie")
                    expect(movie).to_have_js_property("paused", True)
                    page.wait_for_function('()=>document.querySelector("video").readyState>=3')
                    page.wait_for_timeout(180)
                    assert abs(movie.evaluate("e=>e.duration") - 48) < 0.1
                    # Decode actual frames. Different timestamps must produce different pixels.
                    page.screenshot(
                        path=str(args.output / f"{engine}-initial-{width}.png"), full_page=True
                    )
                    # Use the visible play affordance, not only programmatic playback.
                    page.locator("#film-start").click()
                    expect(page.locator("#film-start")).to_be_hidden()
                    page.wait_for_function('()=>document.querySelector("video").currentTime>.3')
                    movie.evaluate("v=>v.pause()")
                    decoded = []
                    for seconds in [7, 20, 36]:
                        movie.evaluate("(v,t)=>{v.currentTime=t;}", seconds)
                        try:
                            page.wait_for_function(
                                '(t)=>{const v=document.querySelector("video");return !v.seeking&&Math.abs(v.currentTime-t)<.1;}',
                                arg=seconds,
                            )
                        except Exception:
                            print(
                                engine,
                                width,
                                seconds,
                                movie.evaluate(
                                    "v=>({time:v.currentTime,ready:v.readyState,seeking:v.seeking,error:v.error?.message,source:v.currentSrc})"
                                ),
                            )
                            raise
                        page.wait_for_timeout(180)
                        assert movie.evaluate("""v=>{
                            const cue=[...v.textTracks].find(t=>t.language==='en').activeCues[0];
                            return cue.line===18&&cue.position===40&&cue.size===74;
                        }"""), "Captions must leave the lower trajectory unobstructed"
                        png = movie.screenshot(
                            path=str(args.output / f"{engine}-{width}-frame-{seconds}.png")
                        )
                        assert png
                        pixels = movie.evaluate("""v=>{
                            const c=document.createElement('canvas');c.width=320;c.height=180;
                            const g=c.getContext('2d');g.drawImage(v,0,0,320,180);
                            const p=g.getImageData(0,0,320,180).data;
                            if(Math.max(...p.filter((_,i)=>i%4===0))-Math.min(...p.filter((_,i)=>i%4===0))<60)throw Error('Blank decoded frame');
                            return c.toDataURL();
                        }""")
                        decoded.append(hashlib.sha256(pixels.encode()).hexdigest())
                        k = record["frame_iterations"][int(seconds * record["fps"])]
                        assert page.evaluate("window.adamLesson.k") == k
                        for metric in ("loss", "distance"):
                            for m in ["gd", "momentum", "adam"]:
                                displayed = page.locator("#" + metric + "-" + m).text_content()
                                want = record["traces"][m]["rows"][k][metric]
                                assert abs(float(displayed) - want) <= abs(want) * 0.006 + 1e-300
                    assert len(set(decoded)) == 3
                    # The shared JSON clock includes a deliberate hold at k=66.
                    movie.evaluate("v=>{v.currentTime=25;}")
                    page.wait_for_function('()=>!document.querySelector("video").seeking&&window.adamLesson.k===66')
                    for k0 in (0, 10, 60, 66, 100, 611, 1200):
                        got = page.evaluate("k=>window.adamLesson.iterationAt(window.adamLesson.timeAt(k))", k0)
                        assert abs(got - k0) <= 1
                    movie.evaluate("v=>{v.currentTime=36;}")
                    page.wait_for_function('()=>!document.querySelector("video").seeking')
                    # Actual playback, not just setting a timestamp.
                    start = movie.evaluate("v=>v.currentTime")
                    print({"resume_from": start, "engine": engine, "width": width}, flush=True)
                    movie.evaluate("v=>v.play()")
                    print(
                        movie.evaluate(
                            "v=>({afterPlay:v.currentTime,paused:v.paused,ended:v.ended,ready:v.readyState})"
                        ),
                        flush=True,
                    )
                    page.wait_for_function(
                        '(start)=>{const v=document.querySelector("video");return (!v.paused||v.ended)&&v.currentTime>start+.4;}',
                        arg=start,
                        timeout=10000,
                    )
                    movie.evaluate("v=>v.pause()")
                    expect(movie).to_have_js_property("paused", True)
                    # Pointer dragging is bound to encoded frames, never invented optimizer states.
                    slider = page.locator("#iteration")
                    slider.scroll_into_view_if_needed()
                    b = slider.bounding_box()
                    y = b["y"] + b["height"] / 2
                    page.mouse.move(b["x"] + 8, y)
                    page.mouse.down()
                    page.mouse.move(b["x"] + 0.62 * b["width"], y, steps=12)
                    page.mouse.up()
                    page.wait_for_timeout(200)
                    f = int(slider.input_value())
                    assert 500 < f < 900
                    assert page.evaluate("window.adamLesson.k") == record["frame_iterations"][f]
                    slider.press("Home")
                    slider.press("ArrowRight")
                    expect(slider).to_have_value("1")
                    page.wait_for_function('()=>!document.querySelector("video").seeking')
                    expect(slider).to_have_value("1")
                    assert (
                        1 / record["fps"] <= movie.evaluate("v=>v.currentTime") < 2 / record["fps"]
                    )
                    slider.press("ArrowRight")
                    expect(slider).to_have_value("2")
                    slider.press("End")
                    page.wait_for_function('()=>!document.querySelector("video").seeking')
                    expect(slider).to_have_value(str(len(record["frame_iterations"]) - 1))
                    assert page.evaluate("window.adamLesson.k") == record["steps"]
                    # A graph itself is a second natural way to scrub.
                    chart = page.locator("#loss-chart")
                    chart.scroll_into_view_if_needed()
                    b = chart.bounding_box()
                    page.mouse.click(b["x"] + 0.6 * b["width"], b["y"] + 0.5 * b["height"])
                    assert abs(page.evaluate("window.adamLesson.k") - 7*record["steps"]/12) <= 6
                    page.locator("#language").click()
                    expect(page.locator("html")).to_have_attribute("lang", "ko")
                    assert (
                        movie.evaluate('v=>[...v.textTracks].find(t=>t.language==="ko").mode')
                        == "showing"
                    )
                    page.screenshot(
                        path=str(args.output / f"{engine}-ko-{width}.png"), full_page=True
                    )
                    page.reload(wait_until="networkidle")
                    expect(page.locator("html")).to_have_attribute("lang", "ko")
                    page.goto(origin + "/papers/adam/?lang=en", wait_until="networkidle")
                    expect(page.locator("html")).to_have_attribute("lang", "en")
                    page.wait_for_function('()=>document.querySelector("video").readyState>=3')
                    page.wait_for_timeout(180)
                    page.screenshot(
                        path=str(args.output / f"{engine}-en-{width}.png"), full_page=True
                    )
                    proof["checks"].append(
                        {
                            "engine": engine,
                            "width": width,
                            "decoded_video": "passed",
                            "pointer_keyboard_chart_scrub": "passed",
                            "captions_language": "passed",
                            "overflow": False,
                        }
                    )
                    context.close()
                # Media-only reading still works without JS; broken data cannot claim ready controls.
                context = browser.new_context(java_script_enabled=False)
                page = context.new_page()
                page.goto(origin + "/papers/adam/")
                expect(page.locator("video")).to_be_visible()
                expect(page.locator(".noscript")).to_be_visible()
                context.close()
                context = browser.new_context()
                page = context.new_page()
                page.route("**/experiment.json", lambda route: route.abort())
                page.goto(origin + "/papers/adam/")
                expect(page.locator("#load-status")).to_have_attribute("role", "alert")
                expect(page.locator("#iteration")).to_be_disabled()
                context.close()
                browser.close()
        assert not proof["errors"], proof["errors"]
        assert not proof["external_requests"], proof["external_requests"]
        (args.output / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
        print(json.dumps(proof, indent=2))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
