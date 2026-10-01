"""Offline UI and pixel-to-record verification of the noisy wavelet image experiment."""

from __future__ import annotations

import argparse
import json
import re
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
            select = page.locator("[data-wavelet-select]")
            for k in record["parameters"]["snapshot_iterations"]:
                select.select_option(str(k))
                if "duality" in record:
                    panels = page.locator("[data-dual-snapshot]:visible")
                    assert panels.count() == 1
                    assert panels.get_attribute("data-dual-snapshot") == str(k)
                for method in ("ista", "fista"):
                    assert page.locator('[data-wavelet-image="' + method + '"]').get_attribute(
                        "src"
                    ) == page.locator(f'[data-snapshot="{method}-{k}"]').get_attribute("src")
                    assert page.locator(f'[data-wavelet-coeff="{method}"]').get_attribute(
                        "src"
                    ) == page.locator(f'[data-coeff-snapshot="{method}-{k}"]').get_attribute("src")
                    row = record["runs"][method]["rows"][k]
                    caption = page.locator(f'[data-wavelet-metrics="{method}"]').text_content()
                    assert f"zero coefficients={row['zero_coefficients']}/65536" in caption
                    assert float(re.search(r"F=([0-9.e+-]+)", caption)[1]) == float(
                        f"{row['objective']:.6e}"
                    )
                    expect(
                        page.locator('[data-wavelet-metrics="' + method + '"]').locator(
                            "visible=true"
                        )
                    ).to_contain_text(f"k={k} · F=")
                    if "duality" in record:
                        d = next(
                            s["dual_bound"]
                            for s in record["runs"][method]["snapshots"]
                            if s["iteration"] == k
                        )
                        group = panels.locator(f'[data-dual-method="{method}"]')
                        lo = float(group.get_attribute("data-axis-min"))
                        span = float(group.get_attribute("data-axis-span"))
                        interval = group.locator("[data-dual-interval]")
                        for attr, key in (("x1", "lower_bound"), ("x2", "primal_objective")):
                            assert (
                                abs(
                                    float(interval.get_attribute(attr))
                                    - (90 + 450 * (d[key] - lo) / span)
                                )
                                < 1e-8
                            )
                        caption = panels.locator(f'[data-dual-readout="{method}"]').text_content()
                        assert f"F−D={d['suboptimality_upper_bound']:.9e}" in caption
                        assert f"‖Aᵀν‖∞={d['dual_adjoint_inf']:.12e}" in caption
            # Decode every stored image: all grayscale pixels must match the raw float64 record.
            assert page.evaluate("""()=>{
                const r=JSON.parse(document.getElementById('chainbench-evidence').textContent);
                const canvas=document.createElement('canvas');canvas.width=canvas.height=256;
                const ctx=canvas.getContext('2d');
                const maximum=Math.max(...Object.values(r.runs).flatMap(run=>run.snapshots.map(s=>Math.max(...s.coefficients.flat().map(Math.abs)))));
                for(const method of ['ista','fista'])for(const s of r.runs[method].snapshots){
                    const img=document.querySelector('[data-snapshot="'+method+'-'+s.iteration+'"]');
                    if(!img.complete||img.naturalWidth!==256||img.naturalHeight!==256)return false;
                    ctx.drawImage(img,0,0);const pixels=ctx.getImageData(0,0,256,256).data;
                    for(let i=0;i<65536;i++){
                        const expected=Math.floor(Math.max(0,Math.min(1,s.image[Math.floor(i/256)][i%256]))*255+.5);
                        if(pixels[4*i]!==expected||pixels[4*i+1]!==expected||pixels[4*i+2]!==expected||pixels[4*i+3]!==255)return false;
                    }
                    const coeff=document.querySelector('[data-coeff-snapshot="'+method+'-'+s.iteration+'"]');
                    if(!coeff.complete||coeff.naturalWidth!==256||coeff.naturalHeight!==256)return false;
                    ctx.drawImage(coeff,0,0);const values=ctx.getImageData(0,0,256,256).data;
                    for(let i=0;i<65536;i++){
                        const v=Math.abs(s.coefficients[Math.floor(i/256)][i%256]);
                        const expected=Math.floor(Math.log1p(v)/Math.log1p(maximum)*255+.5);
                        if(values[4*i]!==expected||values[4*i+1]!==expected||values[4*i+2]!==expected||values[4*i+3]!==255)return false;
                    }
                }return true;
            }""")
            select.focus()
            select.press("Home")
            select.press("ArrowDown")
            expect(select).to_have_value("1")
            select.select_option(str(record["parameters"]["steps"]))
            if "duality" in record:
                page.locator("[data-wavelet-duality]").screenshot(
                    path=str(args.output / f"duality-{width}.png")
                )
                assert page.locator(
                    "[data-dual-snapshot]:visible svg"
                ).evaluate("""svg=>{const v=svg.getBoundingClientRect();return [...svg.querySelectorAll('text')].every(t=>{
                    const b=t.getBoundingClientRect();return b.left>=v.left-.5&&b.top>=v.top-.5&&b.right<=v.right+.5&&b.bottom<=v.bottom+.5;});}""")
            for i, field in enumerate(("objective", "squared_residual", "penalty", "image_rmse")):
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
            page.locator(".wavelet-layout").screenshot(path=str(args.output / f"haar-{width}.png"))
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
        assert page.locator("[data-wavelet-select]").is_hidden()
        page.locator(".deblur-gallery > summary").click()
        assert page.locator("[data-snapshot]").count() == 2 * len(
            record["parameters"]["snapshot_iterations"]
        )
        assert all(img.is_visible() for img in page.locator("[data-snapshot]").all())
        if "duality" in record:
            page.locator("[data-dual-table] > summary").click()
            rows = page.locator("[data-dual-table-row]")
            assert rows.count() == 2 * len(record["parameters"]["snapshot_iterations"])
            assert all(row.is_visible() for row in rows.all())
            for row, (method, s) in zip(
                rows.all(), [(m, s) for m, run in record["runs"].items() for s in run["snapshots"]]
            ):
                cells = row.locator("td").all_text_contents()
                assert cells[:2] == [method.upper(), str(s["iteration"])]
                for value, key in zip(
                    cells[2:],
                    (
                        "lower_bound",
                        "primal_objective",
                        "suboptimality_upper_bound",
                        "dual_adjoint_inf",
                        "feasibility_margin",
                        "scale",
                    ),
                ):
                    assert float(value) == float(f"{s['dual_bound'][key]:.12e}")
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
