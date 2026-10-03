"""Offline UI and pixel-to-record verification of the FISTA image experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    evidence = {"viewports": [], "network_requests": [], "javascript_errors": []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        evidence["browser"] = browser.version
        for width in (1440, 390):
            context = browser.new_context(viewport={"width": width, "height": 1000}, offline=True)
            page = context.new_page()
            page.on("pageerror", lambda e: evidence["javascript_errors"].append(str(e)))
            page.on(
                "request",
                lambda r: (
                    evidence["network_requests"].append(r.url)
                    if r.url.startswith(("http:", "https:"))
                    else None
                ),
            )
            page.goto(args.html.resolve().as_uri())
            record = json.loads(page.locator("#chainbench-evidence").text_content())
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            select = page.locator("[data-deblur-select]")
            for k in record["parameters"]["snapshot_iterations"]:
                select.select_option(str(k))
                for method in ("ista", "fista"):
                    assert page.locator('[data-deblur-image="' + method + '"]').get_attribute(
                        "src"
                    ) == page.locator(f'[data-snapshot="{method}-{k}"]').get_attribute("src")
                    expect(
                        page.locator('[data-deblur-metrics="' + method + '"]').locator(
                            "visible=true"
                        )
                    ).to_contain_text(f"k={k} · F=")
            # Decode every stored image: all grayscale pixels must match the raw float64 record.
            assert page.evaluate("""()=>{
                const r=JSON.parse(document.getElementById('chainbench-evidence').textContent);
                const canvas=document.createElement('canvas');canvas.width=canvas.height=64;
                const ctx=canvas.getContext('2d');
                for(const method of ['ista','fista'])for(const s of r.runs[method].snapshots){
                    const img=document.querySelector('[data-snapshot="'+method+'-'+s.iteration+'"]');
                    if(!img.complete||img.naturalWidth!==64||img.naturalHeight!==64)return false;
                    ctx.drawImage(img,0,0);const pixels=ctx.getImageData(0,0,64,64).data;
                    for(let i=0;i<4096;i++){
                        const expected=Math.floor(Math.max(0,Math.min(1,s.image[Math.floor(i/64)][i%64]))*255+.5);
                        if(pixels[4*i]!==expected||pixels[4*i+1]!==expected||pixels[4*i+2]!==expected||pixels[4*i+3]!==255)return false;
                    }
                }return true;
            }""")
            select.focus()
            select.press("Home")
            select.press("ArrowDown")
            expect(select).to_have_value("1")
            select.select_option(str(record["parameters"]["steps"]))
            slider = page.locator('[data-deblur-slider]')
            slider.focus()
            slider.press('Home')
            slider.press('ArrowRight')
            expect(select).to_have_value('1')
            expect(page.locator('[data-deblur-label]')).to_have_text('k = 1')
            slider.scroll_into_view_if_needed()
            bounds = slider.bounding_box()
            y = bounds['y'] + bounds['height'] / 2
            page.mouse.move(bounds['x'] + 8, y)
            page.mouse.down()
            page.mouse.move(bounds['x'] + bounds['width'] - 8, y, steps=12)
            page.mouse.up()
            expect(select).to_have_value(str(record['parameters']['steps']))
            page.locator('[data-deblur-play]').click()
            page.wait_for_timeout(1050)
            expect(select).to_have_value('1')
            page.locator('[data-deblur-play]').click()
            page.wait_for_timeout(1000)
            expect(select).to_have_value('1')
            select.select_option(str(record['parameters']['steps']))
            for i, field in enumerate(("objective", "image_rmse")):
                svg = page.locator(".plot svg").nth(i)
                chart = json.loads(svg.locator("metadata").text_content())
                for series, method in zip(chart["series"], ("ista", "fista")):
                    assert series["y"] == [row[field] for row in record["runs"][method]["rows"]]
                    assert len(series["x"]) == record["parameters"]["steps"] + 1
                assert svg.evaluate("""svg=>{const v=svg.getBoundingClientRect();return [...svg.querySelectorAll('text')].every(t=>{
                    const b=t.getBoundingClientRect();return b.left>=v.left-.5&&b.top>=v.top-.5&&b.right<=v.right+.5&&b.bottom<=v.bottom+.5;});}""")
            for part in ("inputs", "outputs"):
                page.locator(".deblur-" + part).screenshot(
                    path=str(args.output / f"{part}-{width}.png")
                )
            page.locator(".plot").first.screenshot(path=str(args.output / f"curve-{width}.png"))
            old = page.locator("html").get_attribute("lang")
            page.locator('[data-action="language"]').click()
            assert page.locator("html").get_attribute("lang") != old
            page.locator('[data-action="language"]').click()
            appendix = page.locator("#chainbench-evidence").locator("..")
            appendix.locator(":scope > summary").click()
            with page.expect_download() as info:
                page.locator('[data-download="chainbench-evidence"]').click()
            dest = args.output / f"download-{width}.json"
            info.value.save_as(dest)
            assert json.loads(dest.read_text(encoding="utf8")) == record
            appendix.locator(":scope > summary").click()
            page.screenshot(path=str(args.output / f"page-{width}.png"), full_page=True)
            evidence["viewports"].append(
                {
                    "width": width,
                    "snapshots": len(record["parameters"]["snapshot_iterations"]),
                    "all_pixels": "matched to raw arrays",
                    "all_curves": "matched",
                    "keyboard": "passed",
                    "labels": "inside SVG bounds",
                    "download": "matched",
                    "overflow": False,
                }
            )
            context.close()
        context = browser.new_context(
            java_script_enabled=False, offline=True, viewport={"width": 390, "height": 1000}
        )
        page = context.new_page()
        page.goto(args.html.resolve().as_uri())
        assert page.locator("[data-deblur-select]").is_hidden()
        page.locator(".deblur-gallery > summary").click()
        assert page.locator("[data-snapshot]").count() == 2 * len(
            record["parameters"]["snapshot_iterations"]
        )
        assert all(img.is_visible() for img in page.locator("[data-snapshot]").all())
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(args.output / "no-script.png"), full_page=True)
        context.close()
        browser.close()
    evidence["no_script"] = "full curves and every stored image remain available"
    assert not evidence["network_requests"], evidence["network_requests"]
    assert not evidence["javascript_errors"], evidence["javascript_errors"]
    (args.output / "browser-verification.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf8"
    )
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
