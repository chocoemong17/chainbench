from __future__ import annotations

import argparse
import json

from .checks import CHECKS, CheckResult, run_all, run_check


def _status(result: CheckResult) -> str:
    if result.consistent is None:
        return "INFO"
    return "CONSISTENT" if result.consistent else "NOT CONSISTENT"


def _as_dict(result: CheckResult) -> dict[str, object]:
    return {
        "slug": result.slug,
        "title": result.title,
        "reference": result.reference,
        "statement": result.statement,
        "metric": result.metric,
        "observed": result.observed,
        "threshold": result.threshold,
        "status": _status(result),
        "note": result.note,
    }


def _render(result: CheckResult) -> str:
    threshold = "n/a" if result.threshold is None else f"{result.threshold:.6g}"
    return "\n".join([
        f"[{_status(result)}] {result.title}",
        f"Reference : {result.reference}",
        f"Check     : {result.statement}",
        f"Metric    : {result.metric}",
        f"Observed  : {result.observed:.6g}",
        f"Threshold : {threshold}",
        f"Note      : {result.note}",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chainbench")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    check = sub.add_parser("check")
    check.add_argument("name", choices=[*CHECKS, "all"])
    check.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "list":
        for slug in CHECKS:
            print(slug)
        return 0

    results = run_all() if args.name == "all" else [run_check(args.name)]
    if args.json:
        print(json.dumps([_as_dict(r) for r in results], indent=2))
    else:
        print("\n\n".join(_render(r) for r in results))
    return 0 if all(r.consistent is not False for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
