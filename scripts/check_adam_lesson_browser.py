"""Verify decoded video, synchronized charts, accessibility and the single-paper layout."""

from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    record = json.loads((args.site / "papers/adam/experiment.json").read_text())
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(args.site.resolve()))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    proof = {"source": record["source"], "checks": [], "errors": [], "external_requests": []}
    try:
        with sync_playwright() as pw:
            for engine in ["chromium", "webkit"]:
                browser = getattr(pw, engine).launch()
                for width in [1440, 390]:
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
                    page.wait_for_function('document.querySelector("video").readyState>=2')
                    assert abs(movie.evaluate("e=>e.duration") - 48) < 0.1
                    # Decode actual frames. Different timestamps must produce different pixels.
                    decoded = []
                    for seconds in [7, 20, 36]:
                        movie.evaluate("(v,t)=>{v.currentTime=t;}", seconds)
                        page.wait_for_function(
                            '(t)=>{const v=document.querySelector("video");return !v.seeking&&Math.abs(v.currentTime-t)<.1;}',
                            arg=seconds,
                        )
                        page.wait_for_timeout(180)
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
                        for m in ["gd", "momentum", "adam"]:
                            displayed = page.locator("#loss-" + m).text_content()
                            want = record["traces"][m]["rows"][k]["loss"]
                            assert abs(float(displayed) - want) <= abs(want) * 0.006 + 1e-15
                    assert len(set(decoded)) == 3
                    # Actual playback, not just setting a timestamp.
                    movie.evaluate("v=>v.play()")
                    start = movie.evaluate("v=>v.currentTime")
                    page.wait_for_timeout(1000)
                    assert movie.evaluate("v=>v.currentTime") > start + 0.4
                    movie.evaluate("v=>v.pause()")
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
                    assert int(slider.input_value()) == 1
                    # A graph itself is a second natural way to scrub.
                    chart = page.locator("#loss-chart")
                    chart.scroll_into_view_if_needed()
                    b = chart.bounding_box()
                    page.mouse.click(b["x"] + 0.6 * b["width"], b["y"] + 0.5 * b["height"])
                    assert 1100 < page.evaluate("window.adamLesson.k") < 1600
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
