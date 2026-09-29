"""Install BOTH distributions into separate clean environments outside the checkout."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import subprocess
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout


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
            if [r["slug"] for r in rows] != listing:
                raise RuntimeError("CLI registry and report disagree")
            if any(r["status"] == "NOT CONSISTENT" for r in rows):
                raise RuntimeError("Installed numerical suite failed")
            run([python, "-I", "-m", "chainbench", "--version"], work, env)
            for format_name in ("markdown", "json", "csv"):
                target = work / f"report.{format_name}"
                run([cli, "report", "--format", format_name, "--output", str(target)], work, env)
                if not target.stat().st_size:
                    raise RuntimeError("Empty exported report")
                if format_name == "json":
                    assert len(json.loads(target.read_text())) == len(rows)
                elif format_name == "csv":
                    with target.open(newline="") as f:
                        assert len(list(csv.DictReader(f))) == len(rows)
            records.append({
                "artifact": artifact.name,
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "version": expected,
                "checks": len(rows),
                "statuses": [r["status"] for r in rows],
                "installed_outside_checkout": True,
                "pip_check": "passed", "exports": ["markdown", "csv", "json"],
            })
            print(f"CLEAN INSTALL PASSED: {artifact.name}", flush=True)
    report = {"python": platform.python_version(), "artifacts": records}
    (dist / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    sums = [
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
        for p in sorted(dist.iterdir()) if p.is_file() and p.name != "SHA256SUMS"
    ]
    (dist / "SHA256SUMS").write_text("\n".join(sums) + "\n")


if __name__ == "__main__":
    main()
