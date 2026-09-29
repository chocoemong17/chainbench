import xml.etree.ElementTree as ET

from chainbench.checks import CHECKS, run_all
from chainbench.cli import main
from chainbench.experiment_reporting import render_experiment
from chainbench.experiments import preset_config, run_experiment
from chainbench.reporting import render_html, render_report
from chainbench.stories import STORIES
from chainbench.visuals import build_check_chart, render_check_svg, render_line_chart


def test_every_check_has_plain_language_story_and_finite_chart():
    assert set(STORIES) == set(CHECKS)
    for slug in CHECKS:
        story = STORIES[slug]
        assert all((story.claim, story.evidence, story.takeaway, story.caveat))
        chart = build_check_chart(slug)
        assert chart.series
        assert "<svg" in render_line_chart(chart)


def test_standalone_svg_is_valid_xml():
    svg = render_check_svg("nesterov-1983")
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "O(1/k^2)" in svg


def test_visual_html_report_is_claim_centered_and_has_raw_appendix():
    html = render_html(run_all())
    assert html.startswith("<!doctype html>")
    assert html.count("<svg") == len(CHECKS)
    assert "What the result says" in html
    assert "What ChainBench shows" in html
    assert "What to notice" in html
    assert "Raw numerical appendix" in html
    for slug in CHECKS:
        assert f'id="{slug}"' in html


def test_report_dispatch_supports_html():
    assert "<svg" in render_report(run_all(), "html")


def test_configurable_experiment_html_is_visual():
    result = run_experiment(preset_config("quadratic"))
    html = render_experiment(result, "html")
    assert html.count("<svg") == 2
    assert "Objective-gap trajectories" in html
    assert "Stationarity trajectories" in html
    for run in result["runs"]:
        assert run["method"] in html


def test_cli_without_command_teaches_visual_first_run(capsys):
    assert main([]) == 0
    text = capsys.readouterr().out
    assert "report --format html" in text
    assert "plot nesterov-1983" in text
    assert "experiment --preset quadratic --format html" in text


def test_cli_writes_visual_report_plot_and_experiment(tmp_path):
    report = tmp_path / "report.html"
    plot = tmp_path / "nesterov.svg"
    experiment = tmp_path / "experiment.html"
    assert main(["report", "--format", "html", "--output", str(report)]) == 0
    assert main(["plot", "nesterov-1983", "--output", str(plot)]) == 0
    assert main([
        "experiment", "--preset", "quadratic", "--format", "html", "--output", str(experiment)
    ]) == 0
    assert "<svg" in report.read_text(encoding="utf-8")
    assert ET.fromstring(plot.read_text(encoding="utf-8")).tag.endswith("svg")
    assert experiment.read_text(encoding="utf-8").count("<svg") == 2
