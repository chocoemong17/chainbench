from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from . import __version__
from .adam_counterexample import run_adam_counterexample
from .adam_counterexample_views import adam_counterexample_html
from .admm_geometry import run_admm_geometry
from .admm_views import admm_html
from .case_studies import case_html, gd_tight_case
from .cg_spectrum import run_cg_spectrum
from .cg_spectrum_views import cg_spectrum_html
from .checks import CHECKS, CheckResult, run_all, run_check
from .comparison import METRICS, compare_experiments, read_comparison_inputs
from .comparison_views import comparison_html
from .deblur_views import deblur_html
from .deblurring import run_deblurring
from .experiment_reporting import render_experiment
from .experiments import (
    MAX_CONFIG_BYTES,
    PRESETS,
    load_config,
    normalize_config,
    preset_config,
    run_experiment,
)
from .fista_backtracking import run_fista_backtracking
from .fista_backtracking_views import fista_backtracking_html
from .fw_sparsity import run_fw_sparsity
from .fw_sparsity_views import fw_sparsity_html
from .heavy_ball_cycle import run_heavy_ball_cycle
from .heavy_ball_views import heavy_ball_cycle_html
from .instance_cli import add_instance_parser, execute_instance
from .kaczmarz import run_kaczmarz
from .kaczmarz_views import kaczmarz_html
from .landscape import METHODS as LANDSCAPE_METHODS
from .landscape import landscape_html, run_landscape
from .learning import learning_html
from .nonuniform_sampling import run_nonuniform_sampling
from .nonuniform_views import nonuniform_html
from .proximal_geometry import run_proximal_geometry
from .proximal_views import proximal_html
from .reporting import render_json, render_report, result_status
from .reproduction_views import reproduction_html
from .reproductions import run_reproduction
from .simplex_geometry import run_simplex_geometry, simplex_html
from .stress import TOPICS as STRESS_TOPICS
from .stress import run_stress, run_stress_case, stress_case_html, stress_html
from .studio import add_studio_parser, execute_studio
from .tour import build_tour
from .visuals import render_check_svg
from .wavelet_deblurring import run_wavelet_deblurring
from .wavelet_views import wavelet_html
from .workflows import (
    MAX_REPORT_BYTES,
    PARAMETERS,
    load_report,
    replay_experiment,
    replay_html,
    run_sweep,
    sweep_html,
)


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
  chainbench tour --lang ko --output tour
      Generate a guided offline folder; open tour/index.html in a browser.

  chainbench learn --lang ko --output learn.html
      Read each method's question, assumptions, recurrence and plot.

  chainbench report --format html --output report.html
      Visual paper-by-paper dashboard: claim -> plot -> limitation.

  chainbench plot nesterov-1983 --output nesterov.svg
      One standalone paper/check plot.

  chainbench experiment --preset quadratic --format html --output experiment.html
      Visual comparison on a configurable synthetic problem.

Choose a supported instance directly:
  chainbench experiment --preset quadratic --dimension 20 --condition-number 100 \
      --steps 50 --methods gd smooth-fista cg --format html --output custom.html

Also try 'stress', 'landscape', 'sweep', 'replay' and 'case-study gd-tight'.\nUse 'chainbench --help' for all commands. JSON/CSV remain available for auditing.
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

    add_instance_parser(sub)
    add_studio_parser(sub)

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

    learn = sub.add_parser("learn", help="open a bilingual paper-to-plot reading guide")
    learn.add_argument("--focus", choices=CHECKS)
    learn.add_argument("--lang", choices=["en", "ko"], default="en")
    learn.add_argument("--output", type=Path)
    learn.add_argument("--force", action="store_true")

    tour = sub.add_parser('tour', help='export a guided offline folder using all existing evidence layers')
    tour.add_argument('--output', type=Path, required=True)
    tour.add_argument('--lang', choices=['en', 'ko'], default='en')
    tour.add_argument('--extended', action='store_true', help='include noisy images, sparsity, randomized sampling, CG spectra and the Adam counterexample; index reports generated size')

    sweep = sub.add_parser("sweep", help="vary one supported setting with a shared work budget")
    sweep.add_argument("--preset", choices=PRESETS, required=True)
    sweep.add_argument("--parameter", choices=PARAMETERS, required=True)
    sweep.add_argument("--values", type=float, nargs="+", required=True)
    sweep.add_argument("--dimension", type=int)
    sweep.add_argument("--steps", type=int)
    sweep.add_argument("--methods", nargs="+")
    sweep.add_argument("--lang", choices=["en", "ko"], default="en")
    sweep.add_argument("--format", choices=["html", "json"], default="html")
    sweep.add_argument("--output", type=Path)
    sweep.add_argument("--force", action="store_true")

    replay = sub.add_parser("replay", help="rerun and compare a saved experiment JSON")
    replay.add_argument("input", type=Path)
    replay.add_argument("--rtol", type=float, default=1e-7)
    replay.add_argument("--atol", type=float, default=1e-12)
    replay.add_argument("--lang", choices=["en", "ko"], default="en")
    replay.add_argument("--format", choices=["html", "json"], default="html")
    replay.add_argument("--output", type=Path)
    replay.add_argument("--force", action="store_true")

    compare = sub.add_parser("compare", help="inspect two to four saved experiment reports without rerunning")
    compare.add_argument("inputs", type=Path, nargs="+")
    compare.add_argument("--metric", choices=METRICS, default="gap")
    compare.add_argument("--lang", choices=["en", "ko"], default="en")
    compare.add_argument("--format", choices=["html", "json"], default="html")
    compare.add_argument("--output", type=Path)
    compare.add_argument("--force", action="store_true")

    stress = sub.add_parser(
        "stress", help="run the same paper-linked measurement on many seeded instances"
    )
    stress.add_argument("topic", choices=STRESS_TOPICS)
    stress.add_argument("--trials", type=int, default=24)
    stress.add_argument("--seed", type=int, default=0)
    stress.add_argument("--lang", choices=["en", "ko"], default="en")
    stress.add_argument("--format", choices=["html", "json"], default="html")
    stress.add_argument("--output", type=Path)
    stress.add_argument("--force", action="store_true")

    stress_case = sub.add_parser("stress-case", help="inspect one versioned seeded stress instance")
    stress_case.add_argument("topic", choices=STRESS_TOPICS)
    stress_case.add_argument("--seed", type=int, default=0)
    stress_case.add_argument("--lang", choices=["en", "ko"], default="en")
    stress_case.add_argument("--format", choices=["html", "json"], default="html")
    stress_case.add_argument("--output", type=Path)
    stress_case.add_argument("--force", action="store_true")

    landscape = sub.add_parser(
        "landscape", help="compare quadratic methods on contour and 3D surface views"
    )
    landscape.add_argument("--condition-number", type=float, default=20.0)
    landscape.add_argument("--angle", type=float, default=32.0)
    landscape.add_argument("--steps", type=int, default=18)
    landscape.add_argument(
        "--methods", nargs="+", choices=LANDSCAPE_METHODS, default=list(LANDSCAPE_METHODS)
    )
    landscape.add_argument("--lang", choices=["en", "ko"], default="en")
    landscape.add_argument("--format", choices=["html", "json"], default="html")
    landscape.add_argument("--output", type=Path)
    landscape.add_argument("--force", action="store_true")

    reproduce = sub.add_parser("reproduce", help="recompute a published example or declared experiment protocol")
    reproduce.add_argument("name", choices=["shewchuk-1994", "fista-deblurring", "fista-wavelet", "lessard-2016", "kaczmarz-sampling", "reddi-2018"])
    reproduce.add_argument("--steps", type=int, help="default: Shewchuk 12, noiseless FISTA 10000, noisy wavelet 200, Lessard 50, Kaczmarz sampling 15000, Reddi 3000")
    reproduce.add_argument("--seed", type=int, help="fista-wavelet only: declared PCG64 noise seed (default 0)")
    reproduce.add_argument("--lang", choices=["en", "ko"], default="en")
    reproduce.add_argument("--format", choices=["html", "json"], default="html")
    reproduce.add_argument("--output", type=Path)
    reproduce.add_argument("--force", action="store_true")

    geometry = sub.add_parser("geometry", help="inspect recorded oracle, proximal and splitting updates")
    geometry.add_argument("name", choices=["frank-wolfe", "ista-fista", "admm-lasso", "fista-backtracking"])
    geometry.add_argument("--steps", type=int, help="default: Frank–Wolfe and FISTA variants 18, ADMM 60")
    geometry.add_argument("--lang", choices=["en", "ko"], default="en")
    geometry.add_argument("--format", choices=["html", "json"], default="html")
    geometry.add_argument("--output", type=Path)
    geometry.add_argument("--force", action="store_true")

    case = sub.add_parser("case-study", help="compute a public construction or controlled illustration")
    case.add_argument("name", choices=["gd-tight", "fw-sparsity", "kaczmarz-expectation", "cg-spectrum"])
    case.add_argument("--horizon", type=int, help="gd-tight only (default 20)")
    case.add_argument("--L", type=float, help="gd-tight only (default 1)")
    case.add_argument("--R", type=float, help="gd-tight only (default 1)")
    case.add_argument("--h", type=float, help="gd-tight only (default 1)")
    case.add_argument("--steps", type=int, help="cg-spectrum (default 32), fw-sparsity or kaczmarz-expectation (default 40)")
    case.add_argument("--trials", type=int, help="kaczmarz-expectation only (default 64)")
    case.add_argument("--lang", choices=["en", "ko"], default="en")
    case.add_argument("--format", choices=["html", "json"], default="html")
    case.add_argument("--output", type=Path)
    case.add_argument("--force", action="store_true")

    args = parser.parse_args(argv)
    if args.command is None:
        print(_welcome())
        return 0
    if args.command == "list":
        print("\n".join(CHECKS))
        return 0

    try:
        if args.command == 'studio':
            return execute_studio(args)
        if args.command == 'instance':
            return execute_instance(args, _write)
        if args.command == 'tour':
            manifest = build_tour(args.output, args.lang, extended=args.extended)
            print(f'Created {len(manifest["artifacts"])} HTML files. Open {args.output / "index.html"}')
            return 0
        if args.command == "learn":
            _write(args.output, learning_html(args.focus, args.lang), args.force)
            return 0
        if args.command == "sweep":
            config = _configured_preset(args.preset, args)
            if (args.parameter == "dimension" and args.dimension is not None
                    or args.parameter == "steps" and args.steps is not None):
                raise ValueError("the swept field cannot also have a fixed override")
            result = run_sweep(config, args.parameter, args.values)
            text = sweep_html(result, args.lang) if args.format == "html" else json.dumps(result, indent=2, allow_nan=False)
            _write(args.output, text, args.force)
            return 0
        if args.command == "compare":
            if args.output is not None and any(
                    args.output.resolve() == path.resolve()
                    or (args.output.exists() and path.exists() and args.output.samefile(path))
                    for path in args.inputs):
                raise ValueError("comparison output must not replace any input")
            result = compare_experiments(read_comparison_inputs(args.inputs), metric=args.metric)
            text = comparison_html(result, args.lang) if args.format == "html" else json.dumps(result, indent=2, allow_nan=False)
            _write(args.output, text, args.force)
            return 0
        if args.command == "replay":
            if args.output is not None and (args.input.resolve() == args.output.resolve()
                    or (args.output.exists() and args.output.samefile(args.input))):
                raise ValueError("replay output must not replace its input")
            with args.input.open("rb") as stream:
                raw = stream.read(MAX_REPORT_BYTES + 1)
            if len(raw) > MAX_REPORT_BYTES:
                raise ValueError("saved report exceeds the byte limit")
            result = replay_experiment(load_report(raw.decode("utf-8")), rtol=args.rtol, atol=args.atol)
            text = replay_html(result, args.lang) if args.format == "html" else json.dumps(result, indent=2, allow_nan=False)
            _write(args.output, text, args.force)
            return 0 if result["status"] == "MATCH" else 1
        if args.command == "stress-case":
            result = run_stress_case(args.topic, args.seed)
            text = (stress_case_html(result, args.lang) if args.format == "html"
                    else json.dumps(result, indent=2, allow_nan=False))
            _write(args.output, text, args.force)
            return 0
        if args.command == "stress":
            result = run_stress(args.topic, args.trials, args.seed)
            text = (
                stress_html(result, args.lang)
                if args.format == "html"
                else json.dumps(result, indent=2, allow_nan=False)
            )
            _write(args.output, text, args.force)
            return 0
        if args.command == "landscape":
            result = run_landscape(
                args.condition_number, args.angle, args.steps, tuple(args.methods)
            )
            text = (
                landscape_html(result, args.lang)
                if args.format == "html"
                else json.dumps(result, indent=2, allow_nan=False)
            )
            _write(args.output, text, args.force)
            return 0
        if args.command == "geometry":
            compute, renderer, default_steps = {
                'frank-wolfe': (run_simplex_geometry, simplex_html, 18),
                'ista-fista': (run_proximal_geometry, proximal_html, 18),
                'admm-lasso': (run_admm_geometry, admm_html, 60),
                'fista-backtracking': (run_fista_backtracking, fista_backtracking_html, 18),
            }[args.name]
            result = compute(args.steps if args.steps is not None else default_steps)
            text = (renderer(result, args.lang) if args.format == "html"
                    else json.dumps(result, indent=2, allow_nan=False))
            _write(args.output, text, args.force)
            return 0
        if args.command == "reproduce":
            if args.seed is not None and args.name != 'fista-wavelet':
                raise ValueError('--seed is only supported for fista-wavelet')
            compute, renderer, default_steps = {
                'shewchuk-1994': (run_reproduction, reproduction_html, 12),
                'fista-deblurring': (run_deblurring, deblur_html, 10000),
                'lessard-2016': (run_heavy_ball_cycle, heavy_ball_cycle_html, 50),
                'fista-wavelet': (run_wavelet_deblurring, wavelet_html, 200),
                'kaczmarz-sampling': (run_nonuniform_sampling, nonuniform_html, 15000),
                'reddi-2018': (run_adam_counterexample, adam_counterexample_html, 3000),
            }[args.name]
            steps = args.steps if args.steps is not None else default_steps
            result = (compute(steps, seed=args.seed if args.seed is not None else 0)
                      if args.name == 'fista-wavelet' else compute(steps))
            text = (renderer(result, args.lang) if args.format == "html"
                    else json.dumps(result, indent=2, allow_nan=False))
            _write(args.output, text, args.force)
            return 0
        if args.command == "case-study":
            if args.trials is not None and args.name != 'kaczmarz-expectation':
                raise ValueError('--trials is only supported for kaczmarz-expectation')
            if args.name in ('fw-sparsity', 'kaczmarz-expectation', 'cg-spectrum'):
                if any(v is not None for v in (args.horizon, args.L, args.R, args.h)):
                    raise ValueError('--horizon, --L, --R and --h are only supported for gd-tight')
                steps = args.steps if args.steps is not None else (32 if args.name == 'cg-spectrum' else 40)
                if args.name == 'fw-sparsity':
                    result, renderer = run_fw_sparsity(steps), fw_sparsity_html
                elif args.name == 'cg-spectrum':
                    result, renderer = run_cg_spectrum(steps), cg_spectrum_html
                else:
                    result = run_kaczmarz(steps, args.trials if args.trials is not None else 64)
                    renderer = kaczmarz_html
            else:
                if args.steps is not None:
                    raise ValueError('--steps is only supported for fw-sparsity, kaczmarz-expectation or cg-spectrum')
                result = gd_tight_case(args.horizon if args.horizon is not None else 20,
                                       args.L if args.L is not None else 1.,
                                       args.R if args.R is not None else 1.,
                                       args.h if args.h is not None else 1.)
                renderer = case_html
            text = renderer(result, args.lang) if args.format == "html" else json.dumps(result, indent=2, allow_nan=False)
            _write(args.output, text, args.force)
            return 0 if args.name != 'gd-tight' or result["matches_target"] else 1

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
    except (OSError, UnicodeError, ValueError, FloatingPointError, OverflowError) as exc:
        parser.exit(2, f"chainbench: {exc}\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
