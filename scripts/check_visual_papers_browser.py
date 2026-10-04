"""Real decoded movies, independent pixel checks and draggable paper diagrams."""

from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import io
import json
import re
import threading
from pathlib import Path

from check_adam_lesson_browser import QuietHandler
from PIL import Image, ImageChops
from playwright.sync_api import expect, sync_playwright


def check_readouts(page, record):
    state = page.evaluate("window.paperLesson")
    k, pixel = state["k"], state["pixel"]
    row = record["rows"][k]
    if record["slug"] == "attention":
        values = {
            **{f"weight-{i}": v for i, v in enumerate(row["weights"])},
            **{f"channel-{i}": v for i, v in enumerate(row["output"])},
        }
    else:
        r = record["row_index"]
        values = {
            "input": record["input"][r][pixel],
            "change": row["delta"][r][pixel],
            "output": row["output"][r][pixel],
            "rmse": row["rmse"],
        }
    for name, value in values.items():
        actual = float(page.locator("#" + name).text_content())
        assert abs(actual - value) <= 0.000501, (name, actual, value)
    # Audit every displayed path coordinate against the record, not just text labels.
    if record["slug"] == "attention":
        sets = [
            ("first", [r["weights"][i] for r in record["rows"]], 0, 1, 180, i) for i in range(4)
        ]
        sets += [
            ("second", [r["output"][i] for r in record["rows"]], 0, 1, 180, i) for i in range(3)
        ]
    else:
        r = record["row_index"]
        sets = [
            ("first", ys, -0.25, 1.05, 31, i)
            for i, ys in enumerate([record["input"][r], row["delta"][r], row["output"][r]])
        ]
        sets += [("second", [r["rmse"] for r in record["rows"]], 0, 0.21, 100, 0)]
    for chart, ys, lo, hi, end, index in sets:
        path = page.locator("#" + chart + "-chart .curve").nth(index).get_attribute("d")
        points = re.findall(r"[ML]([\d.-]+),([\d.-]+)", path)
        assert len(points) == len(ys)
        for x, ((px, py), y) in enumerate(zip(points, ys)):
            assert abs(float(px) - (54 + 480 * x / end)) < 0.006
            assert abs(float(py) - (18 + 228 * (hi - y) / (hi - lo))) < 0.006


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(args.site.resolve()))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    proof = {"checks": [], "errors": [], "external_requests": []}
    try:
        with sync_playwright() as pw:
            for engine in ("chromium", "webkit"):
                browser = getattr(pw, engine).launch()
                for width in (1440, 390):
                    for slug in ("attention", "resnet"):
                        record = json.loads(
                            (args.site / f"papers/{slug}/experiment.json").read_text()
                        )
                        proof["source"] = record["source"]
                        context = browser.new_context(
                            viewport={"width": width, "height": 1000}, reduced_motion="reduce"
                        )
                        page = context.new_page()
                        page.on("pageerror", lambda e: proof["errors"].append(str(e)))
                        page.on(
                            "request",
                            lambda r: (
                                proof["external_requests"].append(r.url)
                                if r.url.startswith(("http:", "https:"))
                                and not r.url.startswith(origin + "/")
                                else None
                            ),
                        )
                        print("Checking", slug, engine, width, flush=True)
                        response = page.goto(origin + f"/papers/{slug}/", wait_until="networkidle")
                        assert response.status == 200
                        expect(page.locator("html")).to_have_attribute("lang", "en")
                        expect(page.locator("#iteration")).to_be_enabled()
                        assert not page.locator(".details").evaluate("e=>e.open")
                        assert page.locator("video").count() == 1
                        assert page.locator(".chart-svg").count() == 2
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
                        movie = page.locator("video")
                        page.wait_for_function('()=>document.querySelector("video").readyState>=3')
                        expect(movie).to_have_js_property("paused", True)
                        assert abs(movie.evaluate("v=>v.duration") - 48) < 0.1
                        page.screenshot(
                            path=str(args.output / f"{slug}-{engine}-{width}-en.png"),
                            full_page=True,
                        )
                        page.locator("#film-start").click()
                        page.wait_for_function(
                            '()=>document.querySelector("video").currentTime>.25'
                        )
                        movie.evaluate("v=>v.pause()")
                        hashes = []
                        for seconds in (7, 20, 36):
                            t = seconds + 1 / 48
                            movie.evaluate("(v,t)=>{v.currentTime=t;}", t)
                            page.wait_for_function(
                                '(t)=>{const v=document.querySelector("video");return !v.seeking&&Math.abs(v.currentTime-t)<.02;}',
                                arg=t,
                            )
                            page.wait_for_timeout(200)
                            k = record["frame_steps"][int(t * 24)]
                            assert page.evaluate("window.paperLesson.k") == k
                            check_readouts(page, record)
                            # Check actual decoded color/brightness against arithmetic.
                            if slug == "attention":
                                xy = [1050, 350]
                                expected = [round(255 * v) for v in record["rows"][k]["output"]]
                            else:
                                xy = [int(910 + 10.5 * 248 / 32), int(263 + 10.5 * 248 / 32)]
                                expected = [round(255 * record["rows"][k]["output"][10][10])] * 3
                            decoded = movie.evaluate(
                                """(v,p)=>{const c=document.createElement('canvas');c.width=1280;c.height=720;const g=c.getContext('2d');g.drawImage(v,0,0);return {pixel:[...g.getImageData(p[0],p[1],1,1).data].slice(0,3),image:c.toDataURL()};}""",
                                xy,
                            )
                            assert (
                                max(abs(a - b) for a, b in zip(decoded["pixel"], expected)) <= 8
                            ), (slug, k, decoded["pixel"], expected)
                            hashes.append(hashlib.sha256(decoded["image"].encode()).hexdigest())
                            png = movie.screenshot(
                                path=str(
                                    args.output / f"{slug}-{engine}-{width}-frame-{seconds}.png"
                                )
                            )
                            if seconds == 7:
                                movie.evaluate("v=>[...v.textTracks].forEach(t=>t.mode='hidden')")
                                page.wait_for_timeout(120)
                                hidden = movie.screenshot()
                                movie.evaluate(
                                    "v=>[...v.textTracks].forEach(t=>t.mode=t.language==='en'?'showing':'disabled')"
                                )
                                page.wait_for_timeout(120)
                                diff = ImageChops.difference(
                                    Image.open(io.BytesIO(png)).convert("RGB"),
                                    Image.open(io.BytesIO(hidden)).convert("RGB"),
                                )
                                w, h = diff.size
                                assert (
                                    diff.crop((0, 0, w, round(130 * h / 720))).getbbox() is not None
                                )
                                assert (
                                    diff.crop(
                                        (0, round(130 * h / 720), w, round(600 * h / 720))
                                    ).getbbox()
                                    is None
                                ), "Caption covers diagram"
                        assert len(set(hashes)) == 3
                        slider = page.locator("#iteration")
                        slider.scroll_into_view_if_needed()
                        b = slider.bounding_box()
                        page.mouse.move(b["x"] + 8, b["y"] + b["height"] / 2)
                        page.mouse.down()
                        page.mouse.move(
                            b["x"] + b["width"] * 0.7, b["y"] + b["height"] / 2, steps=12
                        )
                        page.mouse.up()
                        assert (
                            record["steps"] * 0.6
                            < page.evaluate("window.paperLesson.k")
                            < record["steps"] * 0.95
                        )
                        check_readouts(page, record)
                        slider.focus()
                        slider.press("Home")
                        expect(page.locator("#parameter-value")).to_have_text(
                            "0°" if slug == "attention" else "0.00"
                        )
                        slider.press("End")
                        page.wait_for_timeout(150)
                        assert page.evaluate("window.paperLesson.k") == record["steps"]
                        graph = page.locator("#second-chart")
                        graph.scroll_into_view_if_needed()
                        b = graph.bounding_box()
                        page.mouse.click(b["x"] + b["width"] * 0.55, b["y"] + b["height"] * 0.5)
                        assert (
                            abs(page.evaluate("window.paperLesson.k") - record["steps"] * 0.53) < 4
                        )
                        if slug == "resnet":
                            old = page.evaluate("window.paperLesson.k")
                            graph = page.locator("#first-chart")
                            graph.scroll_into_view_if_needed()
                            b = graph.bounding_box()
                            page.mouse.click(b["x"] + b["width"] * 0.3, b["y"] + b["height"] * 0.5)
                            assert page.evaluate("window.paperLesson.k") == old
                            assert page.evaluate("window.paperLesson.pixel") == 7
                        check_readouts(page, record)
                        page.locator("#language").click()
                        expect(page.locator("html")).to_have_attribute("lang", "ko")
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
                        assert (
                            movie.evaluate("v=>[...v.textTracks].find(t=>t.language==='ko').mode")
                            == "showing"
                        )
                        page.locator(".details summary").click()
                        assert page.locator("math").is_visible()
                        assert not page.locator(".details").inner_text().count("\\(")
                        page.locator(".details summary").click()
                        page.screenshot(
                            path=str(args.output / f"{slug}-{engine}-{width}-ko.png"),
                            full_page=True,
                        )
                        page.goto(origin + "/papers/")
                        expect(page.locator("html")).to_have_attribute("lang", "ko")
                        assert page.locator(".paper-card").count() == 3
                        for img in page.locator(".paper-card img").all():
                            expect(img).to_have_js_property("complete", True)
                            assert img.evaluate("i=>i.naturalWidth>0")
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
                        page.screenshot(
                            path=str(args.output / f"library-{engine}-{width}.png"), full_page=True
                        )
                        page.goto(origin + f"/papers/{slug}/?lang=en")
                        expect(page.locator("html")).to_have_attribute("lang", "en")
                        context.close()
                        proof["checks"].append(
                            {
                                "paper": slug,
                                "engine": engine,
                                "width": width,
                                "decoded_pixels": "passed",
                                "numeric_graph_paths": "passed",
                                "pointer_keyboard": "passed",
                                "captions_clear": "passed",
                                "language_gallery": "passed",
                            }
                        )
                for slug in ("attention", "resnet"):
                    context = browser.new_context(java_script_enabled=False)
                    page = context.new_page()
                    page.goto(origin + f"/papers/{slug}/")
                    expect(page.locator(".noscript")).to_be_visible()
                    context.close()
                    context = browser.new_context()
                    page = context.new_page()
                    page.route("**/experiment.json", lambda r: r.abort())
                    page.goto(origin + f"/papers/{slug}/")
                    expect(page.locator("#load-status")).to_have_attribute("role", "alert")
                    expect(page.locator("#iteration")).to_be_disabled()
                    context.close()
                browser.close()
        assert not proof["errors"], proof["errors"]
        assert not proof["external_requests"], proof["external_requests"]
        (args.output / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
        print(json.dumps(proof), flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
