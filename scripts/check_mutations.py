"""Four targeted fault injections; detection is not a general mutation-coverage claim."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("unsafe-cg-norm", "src/chainbench/methods.py", "return float(np.hypot.reduce(x))",
     "return float(np.linalg.norm(x))", "", "tests/test_audit_regressions.py::test_cg_is_invariant_to_global_system_scale"),
    ("missing-fista-momentum", "src/chainbench/methods.py",
     "y = xn + ((t - 1) / tn) * (xn - x)", "y = xn.copy()", "def fista(",
     "tests/test_recurrences.py::test_fista_third_iterate_contains_acceleration_and_l1_threshold"),
    ("missing-observation-guard", "src/chainbench/checks.py", "if self.observed is None:",
     "if False:", "", "tests/test_audit_regressions.py::test_missing_or_invalid_observation_is_not_a_result"),
    ("missing-install-hash-binding", "scripts/publish_release.py",
     'if record.get("sha256") != digest(dist / name):', "if False:", "",
     "tests/test_publication_evidence.py::test_reject_distribution_changed_after_smoke_test"),
]


def main() -> None:
    evidence = []
    for name, file, before, after, scope, test in CASES:
        with tempfile.TemporaryDirectory(prefix="chainbench-mutation-") as tmp:
            work = Path(tmp) / "source"
            shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(
                ".git", ".venv", "dist", "build", "__pycache__", ".pytest_cache", ".coverage", "*.egg-info"
            ))
            target = work / file
            source = target.read_text(encoding="utf-8")
            start = source.index(scope) if scope else 0
            prefix, body = source[:start], source[start:]
            if body.count(before) != 1:
                raise RuntimeError(f"Mutation {name} no longer identifies exactly one expression")
            target.write_text(prefix + body.replace(before, after, 1), encoding="utf-8")
            junit = Path(tmp) / "result.xml"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(work / "src")
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test, "--junitxml", str(junit), "-q"],
                cwd=work, env=env, text=True, capture_output=True, timeout=60,
            )
            if not junit.is_file():
                raise RuntimeError(f"Mutation test did not execute: {name}\n{result.stderr}")
            tree = ET.parse(junit)
            failed = [c.attrib["name"] for c in tree.iter("testcase") if c.find("failure") is not None]
            errors = [c for c in tree.iter("testcase") if c.find("error") is not None]
            if result.returncode != 1 or not failed or errors:
                raise RuntimeError(f"Mutation was not detected by assertions: {name}\n{result.stdout}\n{result.stderr}")
            evidence.append({"mutation": name, "detected_by": failed})
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
