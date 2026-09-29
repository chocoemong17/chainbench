from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from . import __version__
from .checks import CHECKS, CheckResult, run_all, run_check
from .experiment_reporting import render_experiment
from .experiments import (
    MAX_CONFIG_BYTES,
    PRESETS,
    load_config,
    normalize_config,
    preset_config,
    run_experiment,
)
from .reporting import render_json, render_report, result_status
from .visuals import render_check_svg


def _render(result: CheckResult) -> str:
    threshold = "n/a" if result.threshold is None else f"{result.threshold:.6g}"
    return "\n".join([
        f"[{result_status(result)}] {result.title}",
        f"Reference : {result.reference}",
        f"Check     : {result.statement}",
        f"Metric    : {result.metric}",
        f"Observed  : {result.observed:.6g}",
        f"Threshold : {threshold}",
        f"Note      : {result.note}",
    ])


def _exit_code(results: list[CheckResult]) -> int:
    if not results:
        raise ValueError("an empty suite has no evidence of success")
    return 1 if any(result.consistent is False for result in results) else 0


def _write(path: Path | None, text: str, force: bool = False) -> None:
    if path is None:
        print(text, end="" if text.endswith("\n") else "\n")
        return
    with path.open("w" if force else "x", encoding="utf-8", newline="") as stream:
        stream.write(text)


def _welcome() -> str:
    return f"""ChainBench {__version__}

See what classic optimization results are saying, not just their raw numbers.

Start here:
  chainbench report --format html --output report.html
      Visual paper-by-paper dashboard: claim -> plot -> limitation.

  chainbench plot nesterov-1983 --output nesterov.svg
      One standalone paper/check plot.

  chainbench experiment --preset quadratic --format html --output experiment.html
      Visual comparison on a configurable synthetic problem.

Choose a supported instance directly:
  chainbench experiment --preset quadratic --dimension 20 --condition-number 100 \
      --steps 50 --methods gd smooth-fista cg --format html --output custom.html

Use 'chainbench --help' for all commands. JSON/CSV remain available for auditing.
"""


_OVERRIDE_NAMES = (
    "dimension",
    "steps",
    "methods",
    "condition_number",
    "smoothness",
    "rotation",
    "lam",
    "include_iterates",
    "random_seed",
)


def _add_overrides(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dimension", type=int, help="override the preset problem dimension")
    parser.add_argument("--steps", type=int, help="override the update budget")
    parser.add_argument(
        "--methods",
        nargs="+",
        help="replace the preset method list; compatibility is validated by the problem family",
    )
    parser.add_argument("--condition-number", type=float, help="quadratic only")
    parser.add_argument("--L", "--smoothness", dest="smoothness", type=float, help="quadratic only")
    parser.add_argument("--rotation", choices=["householder", "none"], help="quadratic only")
    parser.add_argument("--lam", type=float, help="diagonal-LASSO only")
    parser.add_argument(
        "--include-iterates",
        action="store_true",
        default=None,
        help="retain coordinate vectors in the experiment result",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        help=(
            "sample supported preset parameters deterministically; the resolved config, not the "
            "seed alone, is the reproducibility record"
        ),
    )


def _has_overrides(args: argparse.Namespace) -> bool:
    return any(getattr(args, name, None) is not None for name in _OVERRIDE_NAMES)


def _randomized_preset(name: str, seed: int) -> dict:
    rng = random.Random(seed)
    config = preset_config(name)
    config["problem"]["dimension"] = rng.choice([4, 6, 8, 12, 20, 32, 48])
    config["steps"] = rng.choice([12, 20, 30, 50, 80, 120])
    if name == "quadratic":
        config["problem"]["condition_number"] = 10 ** rng.uniform(0.0, 4.0)
        config["problem"]["L"] = 10 ** rng.uniform(-1.0, 1.0)
        config["problem"]["rotation"] = rng.choice(["householder", "none"])
    elif name == "diagonal-lasso":
        config["problem"]["lam"] = 10 ** rng.uniform(-2.0, 0.5)
    return normalize_config(config)


def _configured_preset(name: str, args: argparse.Namespace) -> dict:
    config = (
        _randomized_preset(name, args.random_seed)
        if getattr(args, "random_seed", None) is not None
        else preset_config(name)
    )
    problem = config["problem"]

    if getattr(args, "dimension", None) is not None:
        problem["dimension"] = args.dimension
    if getattr(args, "steps", None) is not None:
        config["steps"] = args.steps
    if getattr(args, "methods", None) is not None:
        config["methods"] = list(args.methods)
        config["method_options"] = {
            method: options
            for method, options in config.get("method_options", {}).items()
            if method in config["methods"]
        }
    if getattr(args, "include_iterates", None) is True:
        config["include_iterates"] = True

    quadratic = {
        "condition_number": getattr(args, "condition_number", None),
        "L": getattr(args, "smoothness", None),
        "rotation": getattr(args, "rotation", None),
    }
    if any(value is not None for value in quadratic.values()):
        if name != "quadratic":
            raise ValueError("condition-number, L and rotation options require the quadratic preset")
        for key, value in quadratic.items():
            if value is not None:
                problem[key] = value

    if getattr(args, "lam", None) is not None:
        if name != "diagonal-lasso":
            raise ValueError("--lam requires the diagonal-lasso preset")
        problem["lam"] = args.lam

    return normalize_config(config)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chainbench",
        description="Auditable visual and numerical experiments for published optimization methods.",
    )
    parser.add_argument("--version", action="version", version=f"ChainBench {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="list bundled literature checks")

    check = sub.add_parser("check", help="run one fixed literature check or the full suite")
    check.add_argument("name", choices=[*CHECKS, "all"])
    check.add_argument("--json", action="store_true")

    report = sub.add_parser("report", help="render the fixed paper/check suite")
    report.add_argument("--format", choices=["html", "markdown", "csv", "json"], default="html")
    report.add_argument("--output", type=Path)
    report.add_argument("--force", action="store_true", help="overwrite an existing output file")

    plot = sub.add_parser("plot", help="render one paper/check as a standalone SVG")
    plot.add_argument("name", choices=CHECKS)
    plot.add_argument("--output", type=Path)
    plot.add_argument("--force", action="store_true")

    preset = sub.add_parser("preset", help="print or save an installed experiment configuration")
    preset.add_argument("name", choices=PRESETS)
    _add_overrides(preset)
    preset.add_argument("--output", type=Path)
    preset.add_argument("--force", action="store_true")

    experiment = sub.add_parser("experiment", help="run a configurable local-only experiment")
    source = experiment.add_mutually_exclusive_group(required=True)
    source.add_argument("--preset", choices=PRESETS)
    source.add_argument("--config", type=Path)
    _add_overrides(experiment)
    experiment.add_argument("--format", choices=["html", "markdown", "csv", "json"], default="json")
    experiment.add_argument("--output", type=Path)
    experiment.add_argument("--force", action="store_true")

    args = parser.parse_args(argv)
    if args.command is None:
        print(_welcome())
        return 0
    if args.command == "list":
        print("\n".join(CHECKS))
        return 0

    try:
        if args.command == "plot":
            _write(args.output, render_check_svg(args.name), args.force)
            return 0

        if args.command in ("preset", "experiment"):
            if args.command == "preset":
                config = _configured_preset(args.name, args)
                text = json.dumps(config, indent=2) + "\n"
            else:
                if args.config is None:
                    config = _configured_preset(args.preset, args)
                else:
                    if _has_overrides(args):
                        raise ValueError(
                            "preset overrides and --random-seed cannot be combined with --config; "
                            "edit or regenerate the config instead"
                        )
                    with args.config.open("rb") as stream:
                        raw = stream.read(MAX_CONFIG_BYTES + 1)
                    if len(raw) > MAX_CONFIG_BYTES:
                        raise ValueError("config exceeds the byte limit")
                    config = load_config(raw.decode("utf-8"))
                    if args.output is not None and (
                        args.output.resolve() == args.config.resolve()
                        or (args.output.exists() and args.output.samefile(args.config))
                    ):
                        raise ValueError("output must not replace the input configuration")
                text = render_experiment(run_experiment(config), args.format)
            _write(args.output, text, args.force)
            return 0

        if args.command == "report":
            results = run_all()
            exit_code = _exit_code(results)
            _write(args.output, render_report(results, args.format), args.force)
        else:
            results = run_all() if args.name == "all" else [run_check(args.name)]
            exit_code = _exit_code(results)
            print(
                render_json(results)
                if args.json
                else "\n\n".join(_render(result) for result in results)
            )
    except (OSError, UnicodeError, ValueError, FloatingPointError) as exc:
        parser.exit(2, f"chainbench: {exc}\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
