import csv
import io

from chainbench.checks import CHECKS, run_all
from chainbench.cli import main
from chainbench.reporting import render_csv, render_markdown


def test_markdown_report_contains_every_registered_check():
    report = render_markdown(run_all())
    for slug in CHECKS:
        assert slug in report


def test_csv_report_is_machine_readable():
    rows = list(csv.DictReader(io.StringIO(render_csv(run_all()))))
    assert [row["slug"] for row in rows] == list(CHECKS)
    assert all(row["status"] == "CONSISTENT" for row in rows)


def test_cli_report_writes_markdown(tmp_path):
    destination = tmp_path / "report.md"
    code = main(["report", "--format", "markdown", "--output", str(destination)])
    assert code == 0
    text = destination.read_text(encoding="utf-8")
    assert text.startswith("# ChainBench benchmark report")
    assert "nesterov-1983" in text
