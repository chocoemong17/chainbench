"""Publish verified bytes at their tested commit; never replace an existing release."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_files(version: str, sha: str) -> list[Path]:
    """Fail before any network write if evidence or distribution bytes changed."""
    dist = ROOT / "dist"
    expected = {f"chainbench-{version}-py3-none-any.whl", f"chainbench-{version}.tar.gz"}
    names = expected | {"verification.json", "SHA256SUMS", "build-environment.txt"}
    files = sorted(dist.iterdir())
    if {p.name for p in files} != names or any(p.is_symlink() or not p.is_file() for p in files):
        raise RuntimeError("Expected only the verified distribution/evidence files, without symlinks")
    report = json.loads((dist / "verification.json").read_text(encoding="utf-8"))
    if report.get("source_commit") != sha:
        raise RuntimeError("Install verification belongs to a different commit")
    records = report.get("artifacts")
    if not isinstance(records, list) or len(records) != 2:
        raise RuntimeError("Expected two verified distribution records")
    found = set()
    baseline = None
    for record in records:
        name = record.get("artifact")
        if name not in expected or name in found or record.get("version") != version:
            raise RuntimeError("Verification artifact name/version mismatch")
        found.add(name)
        if record.get("sha256") != digest(dist / name):
            raise RuntimeError("Distribution changed after its installation verification")
        statuses, slugs = record.get("statuses"), record.get("slugs")
        if (
            not isinstance(statuses, list) or not statuses
            or any(s not in ("CONSISTENT", "INFO") for s in statuses)
            or "CONSISTENT" not in statuses
            or not isinstance(slugs, list) or len(slugs) != len(statuses)
            or any(not isinstance(s, str) or not s for s in slugs)
            or len(set(slugs)) != len(slugs)
            or type(record.get("checks")) is not int or record["checks"] != len(slugs)
            or record.get("installed_outside_checkout") is not True
            or record.get("pip_check") != "passed"
            or record.get("exports") != ["html", "markdown", "csv", "json"]
            or record.get("plot_svg") != "passed"
            or record.get("visual_evidence") != "matched"
        ):
            raise RuntimeError("Invalid or unsuccessful installed-package evidence")
        experiments = record.get("experiments")
        expected_methods = {
            "quadratic": ["gd", "smooth-fista", "heavy-ball", "cg", "proximal-point"],
            "diagonal-lasso": ["ista", "fista"], "simplex": ["frank-wolfe"],
        }
        if not isinstance(experiments, list) or len(experiments) != len(expected_methods):
            raise RuntimeError("Missing installed experiment evidence")
        for experiment, (preset, methods) in zip(experiments, expected_methods.items()):
            if (not isinstance(experiment, dict) or experiment.get("preset") != preset
                    or experiment.get("methods") != methods
                    or type(experiment.get("rows")) is not int or experiment["rows"] < len(methods)
                    or experiment.get("exports") != ["json", "csv", "markdown", "html"]
                    or experiment.get("saved_config_rerun") != "matched"
                    or not re.fullmatch(r"[0-9a-f]{64}", str(experiment.get("config_sha256", "")))):
                raise RuntimeError("Invalid installed experiment evidence")
        controls = record.get("instance_controls")
        if (
            not isinstance(controls, dict)
            or controls.get("direct_override") != "passed"
            or not re.fullmatch(r"[0-9a-f]{64}", str(controls.get("seeded_config_sha256", "")))
        ):
            raise RuntimeError("Missing installed instance-control evidence")
        advanced = record.get("advanced_workflows")
        if advanced != {
            "learning": "matched", "sweep": "matched", "replay": "matched",
            "gd_tight": "matched", "stress": "matched", "landscape": "matched",
            "shewchuk_reproduction": "matched",
            "simplex_geometry": "matched",
            "inspectable_stress": "matched",
            "proximal_geometry": "matched",
            "offline_tour": "matched",
            "fista_deblurring": "matched",
        }:
            raise RuntimeError("Missing installed learning-workflow evidence")
        summary = (slugs, statuses, experiments, controls, advanced)
        if baseline is not None and summary != baseline:
            raise RuntimeError("Wheel and sdist results disagree")
        baseline = summary
    checksums = {}
    for line in (dist / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        value, sep, name = line.partition("  ")
        if not sep or not re.fullmatch(r"[0-9a-f]{64}", value) or name in checksums:
            raise RuntimeError("Invalid checksum manifest")
        checksums[name] = value
    actual = {p.name: digest(p) for p in files if p.name != "SHA256SUMS"}
    if checksums != actual:
        raise RuntimeError("Checksums do not match the verified local assets")
    return files


def tag_commit(repo: str, tag: str) -> str | None:
    # Unlike treating every nonzero `gh release view` exit as "missing", a
    # successful matching-refs response distinguishes absence from network/auth failure.
    refs = json.loads(command("gh", "api", f"repos/{repo}/git/matching-refs/tags/{tag}"))
    exact = [ref for ref in refs if ref["ref"] == f"refs/tags/{tag}"]
    if not exact:
        return None
    obj = exact[0]["object"]
    for _ in range(8):
        if obj["type"] == "commit":
            return obj["sha"]
        if obj["type"] != "tag":
            break
        obj = json.loads(command("gh", "api", f"repos/{repo}/git/tags/{obj['sha']}"))["object"]
    raise RuntimeError("Release tag does not resolve to a commit")


def require_tag_target(repo: str, tag: str, sha: str, *, may_be_absent: bool = False) -> None:
    actual = tag_commit(repo, tag)
    if actual == sha or (may_be_absent and actual is None):
        return
    raise RuntimeError("Release tag points to a different commit or is missing; refusing publication")


def main() -> None:
    repo, sha = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"]
    if repo != "chocoemong17/chainbench" or os.environ["GITHUB_REF"] != "refs/heads/main":
        raise RuntimeError("Releases are restricted to the owner's main branch")
    if command("git", "rev-parse", "HEAD") != sha:
        raise RuntimeError("Checkout does not match the tested event commit")
    manifest = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise RuntimeError("Expected a numeric semantic version")
    if manifest.get("channel") != "alpha":
        raise RuntimeError("Only the experimental alpha channel is configured")
    notes = ROOT / "docs" / f"RELEASE_NOTES_{version}.md"
    if not notes.is_file():
        raise RuntimeError("Release notes are missing")
    tag = f"v{version}"
    files = verified_files(version, sha)
    require_tag_target(repo, tag, sha, may_be_absent=True)
    # Pagination is explicit; an authentication/network error raises, never implies absence.
    pages = json.loads(command("gh", "api", f"repos/{repo}/releases?per_page=100",
                               "--paginate", "--slurp"))
    for page in pages:
        for existing in page:
            if existing["tag_name"] == tag:
                if existing["draft"]:
                    raise RuntimeError("A draft already exists; inspect it instead of overwriting it")
                require_tag_target(repo, tag, sha)
                print(f"Already published; unchanged: {existing['html_url']}")
                return
    # Create the lightweight tag explicitly: draft-release creation need not create it yet.
    if tag_commit(repo, tag) is None:
        command("gh", "api", f"repos/{repo}/git/refs", "--method", "POST",
                "-f", f"ref=refs/tags/{tag}", "-f", f"sha={sha}")
    require_tag_target(repo, tag, sha)
    command("gh", "release", "create", tag, "--repo", repo, "--verify-tag", "--target", sha,
            "--title", f"ChainBench {tag}", "--notes-file", str(notes), "--draft", "--prerelease")
    require_tag_target(repo, tag, sha)
    command("gh", "release", "upload", tag, *[str(p) for p in files], "--repo", repo)
    assets = json.loads(command("gh", "release", "view", tag, "--repo", repo, "--json", "assets"))
    remote = {a["name"]: a["size"] for a in assets["assets"]}
    if remote != {p.name: p.stat().st_size for p in files}:
        raise RuntimeError("Uploaded assets do not match local files; draft remains unpublished")
    with tempfile.TemporaryDirectory(prefix="chainbench-assets-") as tmp:
        command("gh", "release", "download", tag, "--repo", repo, "--dir", tmp)
        for original in files:
            if digest(Path(tmp) / original.name) != digest(original):
                raise RuntimeError("Release asset download differs from the verified file")
    verified_files(version, sha)
    require_tag_target(repo, tag, sha)
    command("gh", "release", "edit", tag, "--repo", repo, "--draft=false", "--prerelease")
    print(command("gh", "release", "view", tag, "--repo", repo, "--json", "url", "--jq", ".url"))


if __name__ == "__main__":
    main()
