"""Install BOTH distributions into separate clean environments outside the checkout."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import re
import struct
import subprocess
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_canonical_plot(figure):
    """Check retained inputs, constants, first update and reference curves without package imports."""
    c = figure.get('instance')
    if not c or c.get('kind') != 'canonical-fixed-instance' or c.get('seed') is not None:
        raise RuntimeError('Missing canonical instance context')
    arrays, n, constants = c['inputs'], c['dimension'], c['constants']
    digest = hashlib.sha256()
    for name, value in sorted(arrays.items()):
        matrix = bool(value) and isinstance(value[0], list)
        shape = [len(value), len(value[0])] if matrix else [len(value)]
        flat = [v for row in value for v in row] if matrix else value
        if any(not math.isfinite(v) for v in flat) or (matrix and any(len(row) != shape[1] for row in value)):
            raise RuntimeError('Invalid canonical input array')
        digest.update(name.encode('ascii')+b'\0'+json.dumps(shape, separators=(',', ':')).encode('ascii')+b'\0')
        digest.update(struct.pack('<'+str(len(flat))+'d', *flat))
    if digest.hexdigest() != c['input_sha256'] or len(arrays['x0']) != n:
        raise RuntimeError('Canonical input fingerprint or dimension differs')
    def close(a, b):
        if not math.isfinite(a) or not math.isfinite(b) or not math.isclose(a, b, rel_tol=2e-9, abs_tol=1e-12):
            raise RuntimeError('Canonical calculation disagrees with inputs or plotted samples')
    def dot(a, b):
        return sum(x*y for x, y in zip(a, b))
    def soft(z, threshold):
        return math.copysign(max(abs(z)-threshold, 0.), z)
    x0, star = arrays['x0'], c['optimizer']
    if c['family'] == 'quadratic':
        Q, b = arrays['Q'], arrays['b']
        if len(Q) != n or len(b) != n or any(len(row) != n for row in Q):
            raise RuntimeError('Canonical matrix dimensions differ')
        if any(Q[i][j] != 0 for i in range(n) for j in range(n) if i != j):
            raise RuntimeError('Fixed canonical quadratics are diagonal')
        eigenvalues = [Q[i][i] for i in range(n)]
        L, mu = max(eigenvalues), min(eigenvalues)
        close(constants['L'], L)
        close(constants['mu'], mu)
        if mu == 0:
            if constants['condition_number'] is not None:
                raise RuntimeError('Singular canonical conditioning must remain undefined')
        else:
            close(constants['condition_number'], L/mu)
        for i in range(n):
            close(b[i], eigenvalues[i]*star[i])
        def grad(x):
            return [eigenvalues[i]*x[i]-b[i] for i in range(n)]
        def gap(x):
            return .5*sum(eigenvalues[i]*(x[i]-star[i])**2 for i in range(n))
    elif c['family'] == 'diagonal-lasso':
        a, b, lam = arrays['a'], arrays['b'], arrays['lam'][0]
        if len(a) != n or len(b) != n:
            raise RuntimeError('Canonical LASSO dimensions differ')
        L = max(v*v for v in a)
        close(constants['L'], L)
        close(constants['lambda'], lam)
        for i in range(n):
            close(star[i], soft(a[i]*b[i], lam)/a[i]**2)
        def grad(x):
            return [a[i]*(a[i]*x[i]-b[i]) for i in range(n)]
        def gap(x):
            return (.5*sum((a[i]*(x[i]-star[i]))**2 for i in range(n))
                    + lam*sum(abs(x[i])-max(-1, min(1, a[i]*b[i]/lam))*x[i] for i in range(n)))
    elif c['family'] == 'simplex-quadratic':
        target = arrays['target']
        if len(target) != n or min(x0) < 0:
            raise RuntimeError('Invalid canonical simplex')
        close(sum(x0), 1.)
        close(constants['curvature'], 2.)
        def grad(x):
            return [x[i]-target[i] for i in range(n)]
        def gap(x):
            return .5*sum((x[i]-target[i])**2 for i in range(n))
    else:
        raise RuntimeError('Unknown canonical family')
    radius2 = sum((x0[i]-star[i])**2 for i in range(n))
    close(constants['radius_squared'], radius2)
    slug, options = c['topic'], c['method_parameters']
    for method, state in c['runs'].items():
        if not 1 <= state['updates'] <= c['budget'] or (method != 'cg' and state['updates'] != c['budget']):
            raise RuntimeError('Canonical update count exceeds its budget')
        g = grad(x0)
        if method in ('gd', 'smooth-fista', 'ista', 'fista'):
            step = options[method]['step']
            close(step, 1/L)
            xn = [x0[i]-step*g[i] for i in range(n)]
            if method in ('ista', 'fista'):
                xn = [soft(x, arrays['lam'][0]*step) for x in xn]
        elif method == 'heavy-ball':
            xn = [x0[i]-options[method]['alpha']*g[i] for i in range(n)]
        elif method == 'cg':
            residual = [-v for v in g]
            alpha = dot(residual, residual)/sum(eigenvalues[i]*residual[i]**2 for i in range(n))
            xn = [x0[i]+alpha*residual[i] for i in range(n)]
        elif method == 'proximal-point':
            parameter = options[method]['c']
            xn = [(x0[i]+parameter*b[i])/(1+parameter*eigenvalues[i]) for i in range(n)]
        elif method == 'frank-wolfe':
            chosen = min(range(n), key=lambda i: g[i])
            xn = [float(i == chosen) for i in range(n)]  # gamma[0]=1
        else:
            raise RuntimeError('Unknown canonical method')
        observed = figure['series'][1 if slug == 'ista-vs-fista' and method == 'fista' else 0]
        expected = gap(xn)
        if method == 'cg':
            expected = math.sqrt(2*expected)
        elif method in ('heavy-ball', 'proximal-point'):
            expected = math.sqrt(sum((xn[i]-star[i])**2 for i in range(n)))
            if method == 'heavy-ball':
                expected /= math.sqrt(radius2)
        close(observed['y'][observed['x'].index(1)], expected)
    if slug != 'ista-vs-fista':
        for k, value in zip(figure['series'][1]['x'], figure['series'][1]['y']):
            if slug == 'gd-baseline':
                expected = L*radius2/(2*k)
            elif slug in ('nesterov-1983', 'beck-teboulle-2009'):
                expected = 2*L*radius2/(k+1)**2
            elif slug == 'jaggi-2013':
                expected = 4/(k+2)
            elif slug == 'rockafellar-1976':
                expected = math.sqrt(radius2)/(1+options['proximal-point']['c']*mu)**k
            else:
                rho = (math.sqrt(L)-math.sqrt(mu))/(math.sqrt(L)+math.sqrt(mu))
                expected = rho if slug == 'polyak-1964' else 2*rho**k*math.sqrt(2*gap(x0))
            close(value, expected)


def run(args: list[str], cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def validate_rows(rows: list[dict], listing: list[str]) -> None:
    """Validate evidence, not just the absence of a recognized failure label."""
    if not listing or len(set(listing)) != len(listing):
        raise RuntimeError("Empty or duplicate check registry")
    if not isinstance(rows, list) or len(rows) != len(listing):
        raise RuntimeError("CLI registry and report disagree")
    if [r.get("slug") for r in rows] != listing:
        raise RuntimeError("CLI registry and report disagree")
    quantitative = 0
    for row in rows:
        value = row.get("observed")
        if type(value) not in (float, int) or not math.isfinite(value):
            raise RuntimeError("Missing or non-finite installed check observation")
        status, threshold = row.get("status"), row.get("threshold")
        if status == "CONSISTENT":
            if type(threshold) not in (float, int) or not math.isfinite(threshold):
                raise RuntimeError("Missing quantitative threshold")
            if value > threshold + 1e-10:
                raise RuntimeError("Quantitative check exceeds its threshold")
            quantitative += 1
        elif status != "INFO" or threshold is not None:
            raise RuntimeError("Failed or unrecognized installed check status")
    if not quantitative:
        raise RuntimeError("No quantitative evidence in installed suite")


def validate_html(text: str, expected, *, experiment: bool = False) -> None:
    """Read the exported evidence independently; a '<svg' substring is insufficient."""
    from html.parser import HTMLParser

    class Parser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.active = None
            self.record = ''
            self.figures = []
            self.svg_count = 0
        def handle_starttag(self, tag, attrs):
            if tag == 'script':
                raise RuntimeError('Unexpected script in offline visual export')
            if tag == 'svg':
                self.svg_count += 1
            if tag == 'metadata':
                self.active = 'figure'
                self.figures.append('')
            if tag == 'pre' and dict(attrs).get('id') == 'chainbench-evidence':
                self.active = 'record'
        def handle_endtag(self, tag):
            if tag in ('metadata', 'pre'):
                self.active = None
        def handle_data(self, data):
            if self.active == 'record':
                self.record += data
            elif self.active == 'figure':
                self.figures[-1] += data

    p = Parser()
    p.feed(text)
    try:
        record = json.loads(p.record)
        figures = [json.loads(raw) for raw in p.figures]
    except (ValueError, TypeError) as exc:
        raise RuntimeError('Missing visual evidence record') from exc
    if experiment:
        if record != expected or p.svg_count != 2 or len(figures) != 2:
            raise RuntimeError('Experiment HTML differs from the actual run')
        for figure, field in zip(figures, ('gap', 'stationarity')):
            actual = [(s['label'], s['x'], s['y']) for s in figure['series']]
            wanted = [(r['method'], [v['iteration'] for v in r['rows']],
                       [v[field] for v in r['rows']]) for r in expected['runs']]
            if actual != wanted:
                raise RuntimeError('Experiment figure lost or changed trajectory samples')
    else:
        results = record.get('results', [])
        normalized = []
        for result in results:
            result = dict(result)
            consistent = result.pop('consistent')
            result['status'] = ('INFO' if consistent is None else
                                'CONSISTENT' if consistent else 'NOT CONSISTENT')
            normalized.append(result)
        if normalized != expected or p.svg_count != len(expected) or len(figures) != len(expected):
            raise RuntimeError('Fixed HTML differs from the actual check suite')
        for result, figure in zip(expected, figures):
            if figure != record['charts'][result['slug']]:
                raise RuntimeError('Fixed SVG samples differ from exported evidence')
            validate_canonical_plot(figure)



PRESET_METHODS = {
    "quadratic": ["gd", "smooth-fista", "heavy-ball", "cg", "proximal-point"],
    "diagonal-lasso": ["ista", "fista"],
    "simplex": ["frank-wolfe"],
}


def validate_experiment(result: dict, config: dict, version: str) -> None:
    """Validate installed experiment evidence independently of the package serializer."""
    if not isinstance(result, dict) or result.get("kind") != "chainbench.experiment":
        raise RuntimeError("Missing experiment envelope")
    if type(result.get("schema_version")) is not int or result["schema_version"] != 1:
        raise RuntimeError("Unexpected experiment schema")
    if result.get("config") != config:
        raise RuntimeError("Experiment did not run the supplied configuration")
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False)
    expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if result.get("config_sha256") != expected_hash:
        raise RuntimeError("Experiment configuration hash mismatch")
    environment = result.get("environment")
    if not isinstance(environment, dict) or environment.get("chainbench") != version:
        raise RuntimeError("Experiment version mismatch")
    if any(not isinstance(environment.get(k), str) or not environment[k]
           for k in ("numpy", "python", "os")):
        raise RuntimeError("Missing experiment environment")
    fixture = result.get("fixture")
    if (not isinstance(fixture, dict)
            or not re.fullmatch(r"[0-9a-f]{64}", str(fixture.get("input_sha256", "")))
            or fixture.get("kind") != config["problem"]["kind"]
            or fixture.get("dimension") != config["problem"]["dimension"]):
        raise RuntimeError("Missing experiment input provenance")
    runs = result.get("runs")
    if (not isinstance(runs, list) or not runs
            or [r.get("method") for r in runs] != config["methods"]):
        raise RuntimeError("Experiment method set mismatch")
    for run in runs:
        rows, updates = run.get("rows"), run.get("updates")
        if (type(updates) is not int or not 0 <= updates <= config["steps"]
                or not isinstance(rows, list) or len(rows) != updates + 1):
            raise RuntimeError("Missing experiment trajectory")
        expected_states = ("converged", "max_steps") if run["method"] == "cg" else ("budget_complete",)
        if run.get("termination") not in expected_states:
            raise RuntimeError("Unexpected experiment termination")
        if run["termination"] != "converged" and updates != config["steps"]:
            raise RuntimeError("Experiment stopped before its budget without convergence")
        for k, row in enumerate(rows):
            if type(row.get("iteration")) is not int or row["iteration"] != k:
                raise RuntimeError("Experiment trajectory indices are inconsistent")
            for field in ("objective", "gap", "stationarity", "distance_to_reference"):
                value = row.get(field)
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise RuntimeError("Missing or non-finite experiment observation")
                if field != "objective" and value < 0:
                    raise RuntimeError("Negative experiment error metric")


def exercise_experiments(cli: str, work: Path, env: dict[str, str], version: str) -> list[dict]:
    records = []
    for name, methods in PRESET_METHODS.items():
        path = work / f"{name}-config.json"
        run([cli, "preset", name, "--output", str(path)], work, env)
        config = json.loads(path.read_text(encoding="utf-8"))
        if config.get("methods") != methods:
            raise RuntimeError("Installed preset lost or changed expected methods")
        result = json.loads(run([cli, "experiment", "--preset", name], work, env))
        validate_experiment(result, config, version)
        rerun = json.loads(run([cli, "experiment", "--config", str(path)], work, env))
        if rerun != result:
            raise RuntimeError("Saved configuration rerun differs from the preset")
        for format_name in ("json", "csv", "markdown", "html"):
            target = work / f"{name}-experiment.{format_name}"
            run([cli, "experiment", "--config", str(path), "--format", format_name,
                 "--output", str(target)], work, env)
            text = target.read_text(encoding="utf-8")
            if not text:
                raise RuntimeError("Empty installed experiment export")
            if format_name == "json":
                if json.loads(text) != result:
                    raise RuntimeError("Experiment JSON differs from the actual run")
            elif format_name == "csv":
                with target.open(newline="", encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                flattened = [(t["method"], r) for t in result["runs"] for r in t["rows"]]
                if len(rows) != len(flattened):
                    raise RuntimeError("Experiment CSV lost trajectory rows")
                for row, (method, expected) in zip(rows, flattened):
                    if (row["method"] != method or int(row["iteration"]) != expected["iteration"]
                            or float(row["gap"]) != expected["gap"]
                            or json.loads(row["config_json"]) != config
                            or row["config_sha256"] != result["config_sha256"]):
                        raise RuntimeError("Experiment CSV differs from the actual run")
            elif format_name == "html":
                validate_html(text, result, experiment=True)
            elif result["config_sha256"] not in text or result["fixture"]["input_sha256"] not in text:
                raise RuntimeError("Experiment Markdown lost its provenance")
        records.append({"preset": name, "config_sha256": result["config_sha256"],
                        "methods": methods, "rows": sum(len(r["rows"]) for r in result["runs"]),
                        "exports": ["json", "csv", "markdown", "html"],
                        "saved_config_rerun": "matched"})
    return records



def exercise_instance_controls(cli: str, work: Path, env: dict[str, str]) -> dict:
    first = run([cli, "preset", "quadratic", "--random-seed", "17"], work, env)
    second = run([cli, "preset", "quadratic", "--random-seed", "17"], work, env)
    if first != second:
        raise RuntimeError("Seeded config generation is not deterministic in one environment")
    config = json.loads(first)
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False)
    seed_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    target = work / "direct-instance.html"
    run([
        cli, "experiment", "--preset", "quadratic", "--dimension", "6",
        "--condition-number", "20", "--steps", "8", "--methods", "gd", "cg",
        "--format", "html", "--output", str(target),
    ], work, env)
    text = target.read_text(encoding="utf-8")
    if "<svg" not in text or "gd" not in text or "cg" not in text:
        raise RuntimeError("Direct instance controls did not produce the expected visual experiment")
    return {"direct_override": "passed", "seeded_config_sha256": seed_hash}


def main() -> None:
    dist = ROOT / "dist"
    wheels, sdists = sorted(dist.glob("*.whl")), sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError("Expected exactly one wheel and one sdist")
    artifacts = wheels + sdists
    expected = json.loads((ROOT / "release-manifest.json").read_text())["version"]
    records = []
    for artifact in artifacts:
        with tempfile.TemporaryDirectory(prefix="chainbench-install-") as tmp:
            work = Path(tmp)
            envdir = work / "venv"
            venv.EnvBuilder(with_pip=True).create(envdir)
            bindir = envdir / ("Scripts" if os.name == "nt" else "bin")
            python = str(bindir / ("python.exe" if os.name == "nt" else "python"))
            cli = str(bindir / ("chainbench.exe" if os.name == "nt" else "chainbench"))
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)
            env["PYTHONNOUSERSITE"] = "1"
            run([python, "-m", "pip", "install", str(artifact.resolve())], work, env)
            run([python, "-m", "pip", "check"], work, env)
            code = (
                "import json,chainbench; from importlib.metadata import version; "
                "print(json.dumps({'file':chainbench.__file__,"
                "'module_version':chainbench.__version__,'version':version('chainbench')}))"
            )
            info = json.loads(run([python, "-I", "-c", code], work, env))
            if ROOT in Path(info["file"]).resolve().parents:
                raise RuntimeError("Smoke test imported the checkout instead of the distribution")
            if info["version"] != expected or info["module_version"] != expected:
                raise RuntimeError("Installed version does not match the release manifest")
            listing = run([cli, "list"], work, env).splitlines()
            rows = json.loads(run([cli, "check", "all", "--json"], work, env))
            validate_rows(rows, listing)
            run([python, "-I", "-m", "chainbench", "--version"], work, env)
            for format_name in ("html", "markdown", "json", "csv"):
                target = work / f"report.{format_name}"
                run([cli, "report", "--format", format_name, "--output", str(target)], work, env)
                if not target.stat().st_size:
                    raise RuntimeError("Empty exported report")
                if format_name == "json":
                    exported = json.loads(target.read_text(encoding="utf-8"))
                    validate_rows(exported, listing)
                    if exported != rows:
                        raise RuntimeError("JSON report differs from installed checks")
                elif format_name == "csv":
                    with target.open(newline="") as f:
                        exported = list(csv.DictReader(f))
                    if [r["slug"] for r in exported] != listing:
                        raise RuntimeError("CSV registry differs from installed checks")
                    if [r["status"] for r in exported] != [r["status"] for r in rows]:
                        raise RuntimeError("CSV statuses differ from installed checks")
                elif format_name == "html":
                    validate_html(target.read_text(encoding="utf-8"), rows)
            plot = work / "nesterov.svg"
            run([cli, "plot", "nesterov-1983", "--output", str(plot)], work, env)
            if "<svg" not in plot.read_text(encoding="utf-8"):
                raise RuntimeError("Standalone plot export is not SVG")
            import xml.etree.ElementTree as ET
            svg_record = ET.fromstring(plot.read_text(encoding='utf8')).find('{http://www.w3.org/2000/svg}metadata')
            validate_canonical_plot(json.loads(svg_record.text))
            experiments = exercise_experiments(cli, work, env, expected)
            instance_controls = exercise_instance_controls(cli, work, env)
            from smoke_workflows import exercise_workflows
            advanced = exercise_workflows(cli, work, env, expected, run)
            records.append({
                "artifact": artifact.name,
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "version": expected,
                "checks": len(rows), "slugs": listing,
                "statuses": [r["status"] for r in rows],
                "installed_outside_checkout": True,
                "pip_check": "passed", "exports": ["html", "markdown", "csv", "json"],
                "plot_svg": "passed", "visual_evidence": "matched", "experiments": experiments,
                "instance_controls": instance_controls, "advanced_workflows": advanced,
            })
            print(f"CLEAN INSTALL PASSED: {artifact.name}", flush=True)
    report = {"python": platform.python_version(), "artifacts": records,
              "source_commit": os.environ.get("GITHUB_SHA")}
    (dist / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sums = [
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
        for p in sorted(dist.iterdir()) if p.is_file() and p.name != "SHA256SUMS"
    ]
    (dist / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
