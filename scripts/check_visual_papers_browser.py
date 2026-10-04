"""Decode both localized films; exercise every control and audit SVG quantities."""

from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import io
import json
import threading
from pathlib import Path

from check_adam_lesson_browser import QuietHandler
from PIL import Image, ImageChops
from playwright.sync_api import expect, sync_playwright


def audit_diagrams(page, record):
    state = page.evaluate("window.paperLesson")
    if record["slug"] == "attention":
        row = record["cases"][state["selected"]][state["parameter"]]
        for i in range(3):
            actual = float(page.locator(f"#weight-{i}").get_attribute("data-value"))
            assert abs(actual - row["weights"][i]) < 1e-12
            width = float(page.locator(f"#weight-bar-{i}").get_attribute("width"))
            assert abs(width - 432 * row["weights"][i]) < 1e-9
            width = float(page.locator(f"#output-bar-{i}").get_attribute("width"))
            assert abs(width - 516 * row["output"][i]) < 1e-9
    else:
        row = record["blocks"][state["parameter"]]
        if state["direction"] == "forward":
            assert (
                abs(float(page.locator("#prediction").get_attribute("data-value")) - row["y"])
                < 1e-12
            )
        else:
            assert (
                abs(float(page.locator("#input-gradient").get_attribute("data-value")) - row["dx"])
                < 1e-12
            )
        for key in ("plain", "residual"):
            magnitude = abs(record[key][state["depth"]])
            actual = float(page.locator("#" + key + "-signal").get_attribute("data-value"))
            assert abs(actual - 100 * magnitude) < 1e-12
            assert (
                abs(
                    float(page.locator("#" + key + "-bar").get_attribute("width")) - 516 * magnitude
                )
                < 1e-9
            )


def seek(page, seconds):
    movie = page.locator("video")
    t = seconds + 1 / 48
    movie.evaluate("(v,t)=>{v.pause();v.currentTime=t;}", t)
    page.wait_for_function(
        '(t)=>{const v=document.querySelector("video");return !v.seeking&&v.readyState>=2&&Math.abs(v.currentTime-t)<.03;}',
        arg=t,
    )
    page.wait_for_timeout(150)


def decode(page, xy):
    return page.locator("video").evaluate(
        """(v,p)=>{
        const c=document.createElement('canvas');c.width=1280;c.height=720;
        const g=c.getContext('2d');g.drawImage(v,0,0);
        return {pixel:[...g.getImageData(p[0],p[1],1,1).data].slice(0,3),image:c.toDataURL()};
    }""",
        xy,
    )


def drag(page, selector, fraction):
    e = page.locator(selector)
    e.scroll_into_view_if_needed()
    box = e.bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.1, box["y"] + box["height"] * 0.5)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * fraction, box["y"] + box["height"] * 0.5, steps=8)
    page.mouse.up()


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
                        assert (
                            page.goto(origin + f"/papers/{slug}/", wait_until="networkidle").status
                            == 200
                        )
                        expect(page.locator("html")).to_have_attribute("lang", "en")
                        expect(page.locator("#parameter")).to_be_enabled()
                        assert not page.locator(".details").evaluate("e=>e.open")
                        assert (
                            page.locator("video").count() == 1
                            and page.locator(".chart-svg").count() == 2
                        )
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
                        page.wait_for_function('()=>document.querySelector("video").currentTime>.3')
                        movie.evaluate("v=>v.pause()")
                        # Compare the actual film/captions without transient native player
                        # controls or a buffering spinner entering the image-difference mask.
                        # Native controls were exercised above and are restored below.
                        movie.evaluate("v=>v.controls=false")
                        for lang in ("en", "ko"):
                            if lang == "ko":
                                old = movie.evaluate("v=>v.currentTime")
                                page.locator("#language").click()
                                page.wait_for_function(
                                    '()=>document.querySelector("video").readyState>=3&&document.querySelector("video").currentSrc.includes("film.ko.")'
                                )
                                assert abs(movie.evaluate("v=>v.currentTime") - old) < 0.1
                                expect(page.locator("html")).to_have_attribute("lang", "ko")
                            hashes = []
                            for seconds in (9, 21, 33, 45):
                                seek(page, seconds)
                                scene = seconds // 12
                                expect(page.locator(f'[data-chapter="{scene}"]')).to_have_attribute(
                                    "aria-current", "true"
                                )
                                assert page.locator(f'[data-note="{scene}"]').is_visible()
                                # Independent colors at actual numeric locations: selected attention
                                # bar and changed grid cell, then the .9**8 depth bar boundary.
                                points = []
                                if slug == "attention" and seconds == 21:
                                    points = [
                                        ([300, 495], [139, 185, 255]),
                                        ([683, 495], [58, 73, 78]),
                                    ]
                                if slug == "resnet" and seconds == 9:
                                    points = [
                                        ([977 + 3 * 24 + 10, 275 + 5 * 24 + 10], [237, 240, 229]),
                                        ([977 + 4 * 24 + 10, 275 + 6 * 24 + 10], [34, 49, 56]),
                                    ]
                                if slug == "resnet" and seconds == 45:
                                    end = 42 + 1010 * (0.9**8)
                                    points = [
                                        ([int(end - 8), 465], [139, 185, 255]),
                                        ([int(end + 8), 465], [58, 73, 78]),
                                    ]
                                for xy, expected in points:
                                    decoded = decode(page, xy)
                                    assert (
                                        max(abs(a - b) for a, b in zip(decoded["pixel"], expected))
                                        <= 9
                                    ), (slug, lang, seconds, xy, decoded["pixel"], expected)
                                decoded = decode(page, [50, 600])
                                hashes.append(hashlib.sha256(decoded["image"].encode()).hexdigest())
                                movie.screenshot(
                                    path=str(
                                        args.output
                                        / f"{slug}-{engine}-{width}-{lang}-scene-{scene + 1}.png"
                                    )
                                )
                            assert len(set(hashes)) == 4
                            # Distinct frames within a scene prove genuine motion, not a four-still cut.
                            seek(page, 14)
                            one = decode(page, [50, 600])["image"]
                            seek(page, 15)
                            two = decode(page, [50, 600])["image"]
                            assert one != two
                            # Captions remain in the reserved header at both sizes/languages.
                            seek(page, 9)
                            shown = movie.screenshot()
                            movie.evaluate("v=>[...v.textTracks].forEach(t=>t.mode='hidden')")
                            page.wait_for_timeout(150)
                            hidden = movie.screenshot()
                            movie.evaluate(
                                '(v,lang)=>[...v.textTracks].forEach(t=>t.mode=t.language===lang?"showing":"disabled")',
                                lang,
                            )
                            diff = ImageChops.difference(
                                Image.open(io.BytesIO(shown)).convert("RGB"),
                                Image.open(io.BytesIO(hidden)).convert("RGB"),
                            )
                            w, h = diff.size
                            assert diff.crop((0, 0, w, round(106 * h / 720))).getbbox() is not None
                            overlap = diff.crop(
                                (0, round(115 * h / 720), w, round(580 * h / 720))
                            ).getbbox()
                            if overlap:
                                (
                                    args.output
                                    / f"{slug}-{engine}-{width}-{lang}-caption-shown.png"
                                ).write_bytes(shown)
                                (
                                    args.output
                                    / f"{slug}-{engine}-{width}-{lang}-caption-hidden.png"
                                ).write_bytes(hidden)
                                diff.save(
                                    args.output / f"{slug}-{engine}-{width}-{lang}-caption-diff.png"
                                )
                            assert overlap is None, ("Caption overlaps diagram", overlap)
                            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
                            audit_diagrams(page, record)
                        movie.evaluate("v=>v.controls=true")
                        # Real pointer/keyboard control; independent toy does not seek the film.
                        old = movie.evaluate("v=>v.currentTime")
                        drag(page, "#first-chart", 0.37)
                        assert abs(page.evaluate("window.paperLesson.parameter") - 37) <= 1
                        audit_diagrams(page, record)
                        assert movie.evaluate("v=>v.currentTime") == old
                        parameter = page.locator("#parameter")
                        parameter.focus()
                        parameter.press("Home")
                        assert page.evaluate("window.paperLesson.parameter") == 0
                        audit_diagrams(page, record)
                        parameter.press("End")
                        assert page.evaluate("window.paperLesson.parameter") == 100
                        if slug == "attention":
                            for i in range(3):
                                page.locator(f'[data-query="{i}"]').click()
                                audit_diagrams(page, record)
                            drag(page, "#second-chart", 0.1)
                            assert page.evaluate("window.paperLesson.selected") == 0
                        else:
                            page.locator('[data-direction="backward"]').click()
                            audit_diagrams(page, record)
                            drag(page, "#second-chart", 0.75)
                            assert page.evaluate("window.paperLesson.depth") == 12
                            control = page.locator("#depth")
                            control.focus()
                            control.press("Home")
                            audit_diagrams(page, record)
                            control.press("End")
                            assert page.evaluate("window.paperLesson.depth") == 16
                            audit_diagrams(page, record)
                        page.locator('[data-chapter="2"]').click()
                        page.wait_for_function(
                            '()=>Math.abs(document.querySelector("video").currentTime-24)<.1'
                        )
                        slider = page.locator("#iteration")
                        slider.focus()
                        slider.press("Home")
                        page.wait_for_function('()=>document.querySelector("video").currentTime<.1')
                        slider.press("End")
                        page.wait_for_function('()=>document.querySelector("video").currentTime>47')
                        drag(page, "#iteration", 0.5)
                        assert 22 < movie.evaluate("v=>v.currentTime") < 26
                        page.locator(".details summary").click()
                        expect(page.locator("math")).to_be_visible()
                        assert "\\(" not in page.locator(".details").inner_text()
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
                        page.goto(origin + f"/papers/{slug}/?lang=en")
                        expect(page.locator("html")).to_have_attribute("lang", "en")
                        context.close()
                        proof["checks"].append(
                            dict(
                                paper=slug,
                                engine=engine,
                                width=width,
                                languages=["en", "ko"],
                                decoded_numerics="passed",
                                motion="passed",
                                captions="passed",
                                pointer_keyboard="passed",
                                diagram_quantities="passed",
                            )
                        )
                for slug in ("attention", "resnet"):
                    context = browser.new_context(java_script_enabled=False)
                    page = context.new_page()
                    page.goto(origin + f"/papers/{slug}/")
                    expect(page.locator(".noscript")).to_be_visible()
                    context.close()
                    for malformed in (False, True):
                        context = browser.new_context()
                        page = context.new_page()
                        page.route(
                            "**/experiment.json",
                            lambda r: (
                                r.fulfill(
                                    status=200,
                                    content_type="application/json",
                                    body='{"kind":"chainbench.visual-paper.v2"}',
                                )
                                if malformed
                                else r.abort()
                            ),
                        )
                        page.goto(origin + f"/papers/{slug}/")
                        expect(page.locator("#load-status")).to_have_attribute("role", "alert")
                        expect(page.locator("#parameter")).to_be_disabled()
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
