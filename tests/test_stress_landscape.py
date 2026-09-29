import json
from html.parser import HTMLParser

import numpy as np
import pytest

from chainbench.cli import main
from chainbench.landscape import METHODS, contour_svg, landscape_html, run_landscape, surface_svg
from chainbench.learning import DEEP_CONTEXT, LESSONS, learning_html
from chainbench.stress import TOPICS, run_stress, stress_html


class Evidence(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.reading = False
        self.text = ""
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == "pre" and dict(attrs).get("id") == "chainbench-evidence":
            self.reading = True

    def handle_endtag(self, tag):
        if tag == "pre":
            self.reading = False

    def handle_data(self, data):
        if self.reading:
            self.text += data


def test_every_lesson_has_deep_context_and_evidence_label():
    assert set(DEEP_CONTEXT) == set(LESSONS)
    for slug, item in DEEP_CONTEXT.items():
        assert slug in TOPICS
        assert item["evidence"]
        for key in ("why", "strength", "tradeoff", "compare"):
            assert len(item[key]) == 2
            assert all(item[key])
    html = learning_html(lang="ko")
    assert "CANONICAL ILLUSTRATION" in html
    assert "Seeded stress" in html
    assert "Why it mattered" in html
    assert "Trade-off" in html


@pytest.mark.parametrize("topic", TOPICS)
def test_seeded_stress_is_reproducible_and_finite(topic):
    a = run_stress(topic, trials=3, seed=11)
    b = run_stress(topic, trials=3, seed=11)
    assert a == b
    assert a["trials"] == 3
    assert len(a["rows"]) == 3
    assert all(np.isfinite(row["metric"]) and row["metric"] >= 0 for row in a["rows"])
    assert a["summary"]["unique_instances"] == 3
    assert all(len(row["instance_sha256"]) == 64 for row in a["rows"])
    if a["threshold"] == 1.0:
        assert a["summary"]["within_threshold"] == 3
    html = stress_html(a, "ko")
    restored = json.loads(Evidence(html).text)
    assert restored == json.loads(json.dumps(a))
    assert "MULTI-INSTANCE STRESS" in html


def test_heavy_ball_stress_is_labelled_empirical_not_theorem():
    result = run_stress("polyak-1964", trials=4, seed=2)
    assert result["threshold"] == .08
    assert all(row["evidence_kind"] == "empirical" for row in result["rows"])
    assert "empirical regression threshold" in stress_html(result)


def test_info_stress_has_no_pass_fail_threshold():
    result = run_stress("ista-vs-fista", trials=3, seed=1)
    assert result["threshold"] is None
    assert "within_threshold" not in result["summary"]
    assert "descriptive" in stress_html(result)


@pytest.mark.parametrize("kwargs", [
    {"topic": "unknown"},
    {"topic": "gd-baseline", "trials": 1},
    {"topic": "gd-baseline", "trials": 65},
    {"topic": "gd-baseline", "seed": True},
])
def test_bad_stress_requests_are_rejected(kwargs):
    with pytest.raises(ValueError):
        run_stress(**kwargs)


def test_landscape_preserves_same_trajectory_across_three_views():
    result = run_landscape(
        80, 32, 12, ("gd", "smooth-fista", "heavy-ball", "cg", "proximal-point")
    )
    assert result["methods"] == list(METHODS)
    assert all(len(result["traces"][m]) >= 2 for m in METHODS)
    assert all(len(result["gaps"][m]) == len(result["traces"][m]) for m in METHODS)
    contour = contour_svg(result)
    surface = surface_svg(result)
    html = landscape_html(result, "ko")
    assert "Contour trajectories" in contour
    assert "3D objective surface" in surface
    assert "GEOMETRIC ILLUSTRATION" in html
    assert "Objective gap along the same geometric run" in html
    assert "data-trajectory-player" in html
    assert "data-trajectory-line" in html
    assert "data-trajectory-marker" in html
    restored = json.loads(Evidence(html).text)
    assert restored == json.loads(json.dumps(result))


def test_cg_finishes_two_dimensional_spd_problem_quickly():
    result = run_landscape(50, 25, 18, ("cg",))
    assert len(result["traces"]["cg"]) <= 3
    assert result["gaps"]["cg"][-1] < 1e-20


@pytest.mark.parametrize("args", [
    (1.0, 30, 10, ("gd",)),
    (80, 90, 10, ("gd",)),
    (80, 30, 1, ("gd",)),
    (80, 30, 10, ("unknown",)),
    (80, 30, 10, ("gd", "gd")),
])
def test_bad_landscape_requests_are_rejected(args):
    with pytest.raises(ValueError):
        run_landscape(*args)


def test_new_cli_workflows_write_html_and_json(tmp_path):
    stress = tmp_path / "stress.html"
    landscape = tmp_path / "landscape.html"
    raw = tmp_path / "stress.json"
    assert main([
        "stress", "gd-baseline", "--trials", "3", "--seed", "8", "--lang", "ko",
        "--output", str(stress),
    ]) == 0
    assert main([
        "stress", "gd-baseline", "--trials", "3", "--seed", "8", "--format", "json",
        "--output", str(raw),
    ]) == 0
    assert main([
        "landscape", "--condition-number", "60", "--steps", "8", "--lang", "ko",
        "--methods", "gd", "smooth-fista", "cg", "--output", str(landscape),
    ]) == 0
    assert stress.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert json.loads(raw.read_text(encoding="utf-8"))["kind"] == "chainbench.stress"
    assert landscape.read_text(encoding="utf-8").count("<svg") >= 3
