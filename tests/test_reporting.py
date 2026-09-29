import csv
import io
import json
import re
from pathlib import Path

import pytest

from chainbench.checks import CHECKS, CheckResult, run_all
from chainbench.cli import _exit_code, main
from chainbench.reporting import render_csv, render_json, render_markdown, render_report


def test_markdown_report_contains_every_registered_check():
    report = render_markdown(run_all())
    assert all(slug in report for slug in CHECKS)


def test_csv_and_json_round_trip():
    results = run_all()
    rows = list(csv.DictReader(io.StringIO(render_csv(results))))
    assert [r["slug"] for r in rows] == list(CHECKS)
    assert rows[-1]["status"] == "INFO"
    assert all(r["status"] == "CONSISTENT" for r in rows[:-1])
    assert len(json.loads(render_json(results))) == len(CHECKS)


def test_cli_report_writes_and_protects_existing_file(tmp_path):
    dest = tmp_path / "report.md"
    args = ["report", "--format", "markdown", "--output", str(dest)]
    assert main(args) == 0
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    assert main(args + ["--force"]) == 0
    assert dest.read_text(encoding="utf-8").startswith("# ChainBench benchmark report")


def test_cli_output_error_is_clean(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["report", "--output", str(tmp_path / "missing" / "x.md")])
    assert exc.value.code == 2
    assert "chainbench:" in capsys.readouterr().err


def test_failed_check_has_nonzero_exit_code():
    failed = CheckResult("x", "x", "x", "x", "x", 2, 1, False, "x")
    assert _exit_code([failed]) == 1


def test_snapshot_preserves_structure_and_numbers_with_tolerance():
    path = Path(__file__).resolve().parents[1] / "benchmarks" / "latest.md"
    old_lines = path.read_text(encoding="utf-8").splitlines()
    new_lines = render_markdown(run_all()).splitlines()
    assert len(old_lines) == len(new_lines)
    for old, new in zip(old_lines, new_lines):
        if not any(old.startswith(f"| {slug} |") for slug in CHECKS):
            assert old == new
            continue
        a = [cell.strip() for cell in re.split(r"(?<!\\)\|", old)[1:-1]]
        b = [cell.strip() for cell in re.split(r"(?<!\\)\|", new)[1:-1]]
        assert len(a) == len(b) == 5
        assert a[:2] == b[:2] and a[3:] == b[3:]
        assert float(a[2]) == pytest.approx(float(b[2]), rel=1e-6, abs=1e-12)


def test_unknown_format_rejected():
    with pytest.raises(ValueError):
        render_report([], "unknown")
