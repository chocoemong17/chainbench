"""Optional offline browser check of every recorded ISTA/FISTA proximal case."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def capture_frame(panel, k):
    """Dispatch the real slider handler and read its DOM in one browser roundtrip.

    The report's input handler is synchronous. This only collects raw attributes;
    expected coordinates are calculated independently in Python below.
    """
    return panel.evaluate("""(panel,k)=>{
      const slider=panel.querySelector('input[type=range]');
      slider.value=String(k);
      slider.dispatchEvent(new Event('input',{bubbles:true}));
      const all=(root,selector)=>[...root.querySelectorAll(selector)];
      const text=selector=>panel.querySelector(selector)?.textContent ?? null;
      const marker=(el,key)=>({key:el.getAttribute(key),cx:el.getAttribute('cx'),cy:el.getAttribute('cy')});
      return {
        step:text('[data-model-step]'), values:text('[data-model-values]'),
        curves:all(panel,'[data-model-points]').map(el=>({key:el.dataset.modelPoints,points:el.getAttribute('points')})),
        markers:all(panel,'[data-model-marker]').map(el=>marker(el,'data-model-marker')),
        dual_values:text('[data-dual-values]'),
        dual_spaces:all(panel,'[data-dual-space]').map(svg=>({
          key:svg.dataset.dualSpace,
          markers:all(svg,'[data-dual-marker]').map(el=>marker(el,'data-dual-marker')),
          paths:all(svg,'[data-dual-path]').map(el=>({key:el.dataset.dualPath,points:el.getAttribute('points')}))
        }))
      };
    }""", k)


def keyed(items, names):
    """Reject absent, unexpected or duplicate elements before comparing values."""
    result = {item["key"]: item for item in items}
    assert len(items) == len(result) and set(result) == set(names), (list(result), names)
    return result


def points(raw):
    result = [[float(v) for v in xy.split(",")] for xy in raw.split()]
    assert result and all(len(xy) == 2 and all(math.isfinite(v) for v in xy) for xy in result)
    return result


def check_points(actual, expected, tolerance):
    assert len(actual) == len(expected), (len(actual), len(expected))
    assert all(
        len(xy) == 2 and all(
            math.isfinite(a) and math.isclose(a, b, rel_tol=0, abs_tol=tolerance)
            for a, b in zip(xy, uv)
        )
        for xy, uv in zip(actual, expected)
    ), "SVG coordinates differ from the recorded numerical state"
    return len(actual)


def check_dual_frame(frame, case, method, k):
    geometry = case["dual_geometry"]
    count = 0
    for space, svg in keyed(frame["dual_spaces"], ("plane", "surface")).items():
        surface = space == "surface"

        def project(d):
            u, v = d["normalized"]
            if surface:
                z = (d["lower_bound"] - geometry["surface_minimum"]) / (
                    geometry["surface_maximum"] - geometry["surface_minimum"]
                )
                return [310 + 145 * u + 70 * v, 320 - 35 * u + 65 * v - 150 * z]
            return [310 + 155 * u, 245 - 155 * v]

        markers = keyed(svg["markers"], ("previous", "next"))
        for name, index in [("previous", k), ("next", k + 1)]:
            marker = markers[name]
            xy = project(geometry["runs"][method][index])
            count += check_points(
                [[float(marker[attr]) for attr in ("cx", "cy")]], [xy], 5.1e-6
            )
        paths = keyed(svg["paths"], ("ista", "fista"))
        for m in ("ista", "fista"):
            actual = points(paths[m]["points"])
            expected = [project(d) for d in geometry["runs"][m][: k + 2]]
            count += check_points(actual, expected, 5.1e-6)
    caption = frame["dual_values"]
    assert f"{method.upper()} · completed k={k + 1}" in caption
    d = geometry["runs"][method][k + 1]
    for label, key in [
        ("D=", "lower_bound"),
        ("F−F*=", "primal_gap"),
        ("D*−D=", "dual_deficit"),
        ("F−D=", "suboptimality_upper_bound"),
    ]:
        value = float(caption.split(" · " + label)[1].split(" · ")[0])
        assert value == float(f"{d[key]:.6g}")
    return count


def check_frame(frame, case, method, k):
    assert frame["step"] == f"{method.upper()} · k={k} → {k + 1} · actual update line"
    model = case["runs"][method]["stages"][k]["upper_model"]
    maximum = max(model["model_gap"] + [model["previous_gap"]])
    top = 1.1 * maximum if maximum else 1.0
    count = 0
    for key, curve in keyed(frame["curves"], ("model_gap", "objective_gap")).items():
        expected = [
            (86 + (t + 0.25) * 460 / 1.5, 292 - 210 * g / top)
            for t, g in zip(model["parameter"], model[key])
        ]
        count += check_points(points(curve["points"]), expected, 0.00051)
    markers = keyed(frame["markers"], ("anchor_gap", "model_next_gap", "next_gap"))
    for key, marker in markers.items():
        t = 0 if key == "anchor_gap" else 1
        count += check_points(
            [[float(marker[attr]) for attr in ("cx", "cy")]],
            [(86 + (t + 0.25) * 460 / 1.5, 292 - 210 * model[key] / top)],
            0.00051,
        )
    assert "y=next: " + str(model["zero_step"]).lower() in frame["values"]
    dual = check_dual_frame(frame, case, method, k) if "dual_geometry" in case else 0
    if "dual_geometry" not in case:
        assert frame["dual_spaces"] == [] and frame["dual_values"] is None
    return count, dual


def main():
    from playwright.sync_api import expect, sync_playwright

    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    url = args.html.resolve().as_uri()
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
            page.goto(url)
            record = json.loads(page.locator("#chainbench-evidence").text_content())
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert page.locator("[data-prox-case]").count() == 9
            model_frames = 0
            model_points = dual_points = dual_frames = 0
            for case in record["cases"]:
                primary = case["id"] == "lambda-2-opposite"
                if not primary:
                    page.locator(f"#{case['id']} > summary").click()
                panel = page.locator(f'[data-prox-case="{case["id"]}"]')
                slider, select = panel.locator("input[type=range]"), panel.locator("select")
                for method in ("ista", "fista"):
                    select.select_option(method)
                    slider.focus()
                    slider.press("Home")
                    expect(panel.locator("[data-step]")).to_have_text(
                        f"{method.upper()} · k = 0 → 1"
                    )
                    slider.press("ArrowRight")
                    slider.press("ArrowRight")
                    k = min(2, record["parameters"]["steps"] - 1)
                    expect(panel.locator("[data-step]")).to_have_text(
                        f"{method.upper()} · k = {k} → {k + 1}"
                    )
                    for marker in panel.locator("[data-point]").all():
                        expected = marker.get_attribute("data-" + method).split("|")[k].split(",")
                        assert [marker.get_attribute(a) for a in ("cx", "cy")] == expected
                    assert panel.locator("[data-prox-path]").evaluate_all(
                        '(els,n)=>els.every(el=>el.getAttribute("points").split(" ").length===n)',
                        k + 1,
                    )
                    for k in range(len(case["runs"][method]["stages"])):
                        frame = capture_frame(panel, k)
                        n_model, n_dual = check_frame(frame, case, method, k)
                        model_points += n_model
                        dual_points += n_dual
                        dual_frames += int("dual_geometry" in case)
                        model_frames += 1
                if primary:
                    button = panel.locator("[data-model-increase]")
                    increases = [
                        k
                        for k, s in enumerate(case["runs"]["fista"]["stages"])
                        if s["upper_model"]["next_gap"] > s["upper_model"]["previous_gap"] + 1e-12
                    ]
                    if increases:
                        button.click()
                        assert (
                            select.input_value() == "fista"
                            and int(slider.input_value()) == increases[0]
                        )
                    else:
                        assert button.count() == 0
                    panel.locator(".prox-model").screenshot(
                        path=str(args.output / f"model-explanation-{width}.png")
                    )
                    panel.locator(".prox-model-figure").screenshot(
                        path=str(args.output / f"model-slice-{width}.png")
                    )
                    panel.locator(".visual-grid").screenshot(
                        path=str(args.output / f"geometry-{width}.png")
                    )
                    panel.locator(".prox-stages").screenshot(
                        path=str(args.output / f"stages-{width}.png")
                    )
                    panel.locator(".plot").first.screenshot(
                        path=str(args.output / f"gaps-{width}.png")
                    )
                    if "dual_geometry" in case:
                        panel.locator(".prox-dual").screenshot(
                            path=str(args.output / f"dual-explanation-{width}.png")
                        )
                        panel.locator(".dual-visual-grid").screenshot(
                            path=str(args.output / f"dual-geometry-{width}.png")
                        )
                        for svg in panel.locator("[data-dual-space]").all():
                            assert svg.evaluate("""svg=>{const r=svg.getBoundingClientRect();return [...svg.querySelectorAll('text')].every(t=>{
                              const b=t.getBoundingClientRect();return b.left>=r.left-.5&&b.right<=r.right+.5&&b.top>=r.top-.5&&b.bottom<=r.bottom+.5;});}""")
                if case["id"] == "lambda-3-zero":
                    expect(panel.locator("[data-zero]")).to_contain_text(
                        "coordinate 1: |z|=0.15556 ≤ τ → 0"
                    )
                slider.press("End")
                if not primary:
                    page.locator(f"#{case['id']} > summary").click()
            panel = page.locator('[data-prox-case="lambda-2-opposite"]')
            panel.locator("[data-play]").click()
            expect(panel.locator("[data-step]")).not_to_have_text("FISTA · k = 0 → 1")
            panel.locator("[data-play]").click()
            assert panel.locator("[data-play]").get_attribute("aria-pressed") == "false"
            old = page.locator("html").get_attribute("lang")
            page.locator('[data-action="language"]').click()
            assert page.locator("html").get_attribute("lang") != old
            page.locator('[data-action="language"]').click()
            appendix = page.locator("#chainbench-evidence").locator("..")
            appendix.locator(":scope > summary").click()
            with page.expect_download() as download_info:
                page.locator('[data-download="chainbench-evidence"]').click()
            dest = args.output / f"download-{width}.json"
            download_info.value.save_as(dest)
            assert json.loads(dest.read_text(encoding="utf8")) == record
            appendix.locator(":scope > summary").click()
            page.screenshot(path=str(args.output / f"page-{width}.png"), full_page=True)
            evidence["viewports"].append(
                {
                    "width": width,
                    "all_cases": 9,
                    "both_methods": "passed",
                    "markers": "matched",
                    "keyboard": "passed",
                    "playback": "passed",
                    "zero_coordinate": "verified",
                    "download": "matched",
                    "overflow": False,
                    "upper_model_frames": model_frames,
                    "upper_model_points": model_points,
                    "dual_frames": dual_frames,
                    "dual_points": dual_points,
                    "first_increase": "verified",
                }
            )
            context.close()
        context = browser.new_context(
            java_script_enabled=False, offline=True, viewport={"width": 390, "height": 1000}
        )
        page = context.new_page()
        page.goto(url)
        panel = page.locator('[data-prox-case="lambda-2-opposite"]')
        assert panel.locator("input[type=range]").is_hidden()
        assert panel.locator(".prox-model-figure").is_visible()
        if panel.locator("[data-model-increase]").count():
            assert panel.locator("[data-model-increase]").is_hidden()
        panel.locator(".prox-model details > summary").click()
        assert (
            panel.locator(".prox-model table tr").count() == 2 * record["parameters"]["steps"] + 1
        )
        for path in panel.locator("[data-prox-path]").all():
            assert len(path.get_attribute("points").split()) == record["parameters"]["steps"] + 1
        if "duality" in record:
            panel.locator(".prox-dual details > summary").click()
            rows = panel.locator("[data-dual-row]")
            assert rows.count() == 2 * (record["parameters"]["steps"] + 1)
            assert all(row.is_visible() for row in rows.all())
            for path in panel.locator("[data-dual-path]").all():
                assert (
                    len(path.get_attribute("points").split()) == record["parameters"]["steps"] + 1
                )
        page.locator("#lambda-3-zero > summary").click()
        assert page.locator("#lambda-3-zero svg").first.is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(args.output / "no-script.png"), full_page=True)
        evidence["no_script"] = "full paths, stage tables and every case remain readable"
        context.close()
        browser.close()
    assert not evidence["network_requests"], evidence["network_requests"]
    assert not evidence["javascript_errors"], evidence["javascript_errors"]
    (args.output / "browser-verification.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf8"
    )
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
