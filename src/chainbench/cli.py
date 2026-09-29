from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .checks import CHECKS, CheckResult, run_all, run_check
from .reporting import render_json, render_report, result_status


def _render(r: CheckResult) -> str:
    threshold = "n/a" if r.threshold is None else f"{r.threshold:.6g}"
    return "\n".join([
        f"[{result_status(r)}] {r.title}", f"Reference : {r.reference}",
        f"Check     : {r.statement}", f"Metric    : {r.metric}",
        f"Observed  : {r.observed:.6g}", f"Threshold : {threshold}", f"Note      : {r.note}",
    ])


def _exit_code(results: list[CheckResult]) -> int:
    if not results:
        raise ValueError("an empty suite has no evidence of success")
    return 1 if any(r.consistent is False for r in results) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chainbench")
    parser.add_argument("--version", action="version", version=f"ChainBench {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    check = sub.add_parser("check")
    check.add_argument("name", choices=[*CHECKS, "all"])
    check.add_argument("--json", action="store_true")
    report = sub.add_parser("report")
    report.add_argument("--format", choices=["markdown", "csv", "json"], default="markdown")
    report.add_argument("--output", type=Path)
    report.add_argument("--force", action="store_true", help="overwrite an existing output file")
    args = parser.parse_args(argv)
    if args.command == "list":
        print("\n".join(CHECKS))
        return 0
    try:
        if args.command == "report":
            results = run_all()
            exit_code = _exit_code(results)
            text = render_report(results, args.format)
            if args.output is None:
                print(text)
            else:
                with args.output.open("w" if args.force else "x", encoding="utf-8", newline="") as f:
                    f.write(text)
        else:
            results = run_all() if args.name == "all" else [run_check(args.name)]
            exit_code = _exit_code(results)
            print(render_json(results) if args.json else "\n\n".join(_render(r) for r in results))
    except (OSError, ValueError, FloatingPointError) as exc:
        parser.exit(2, f"chainbench: {exc}\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
