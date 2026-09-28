from __future__ import annotations

import argparse
from pathlib import Path

from .checks import CHECKS, CheckResult, run_all, run_check
from .reporting import render_json, render_report, result_status


def _render(result: CheckResult) -> str:
    threshold = "n/a" if result.threshold is None else f"{result.threshold:.6g}"
    return "\n".join(
        [
            f"[{result_status(result)}] {result.title}",
            f"Reference : {result.reference}",
            f"Check     : {result.statement}",
            f"Metric    : {result.metric}",
            f"Observed  : {result.observed:.6g}",
            f"Threshold : {threshold}",
            f"Note      : {result.note}",
        ]
    )


def _exit_code(results: list[CheckResult]) -> int:
    return 0 if all(result.consistent is not False for result in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chainbench")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")

    check = sub.add_parser("check")
    check.add_argument("name", choices=[*CHECKS, "all"])
    check.add_argument("--json", action="store_true")

    report = sub.add_parser("report")
    report.add_argument("--format", choices=["markdown", "csv", "json"], default="markdown")
    report.add_argument("--output", type=Path)

    args = parser.parse_args(argv)

    if args.command == "list":
        for slug in CHECKS:
            print(slug)
        return 0

    if args.command == "report":
        results = run_all()
        output = render_report(results, args.format)
        if args.output is None:
            print(output)
        else:
            args.output.write_text(output, encoding="utf-8")
        return _exit_code(results)

    results = run_all() if args.name == "all" else [run_check(args.name)]
    if args.json:
        print(render_json(results))
    else:
        print("\n\n".join(_render(result) for result in results))
    return _exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
