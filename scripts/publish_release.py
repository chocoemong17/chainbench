"""Publish only a fully tested main-branch commit; never overwrite an existing release."""
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


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["GITHUB_SHA"]
    if repo != "chocoemong17/chainbench" or os.environ["GITHUB_REF"] != "refs/heads/main":
        raise RuntimeError("Releases are restricted to the owner's main branch")
    if command("git", "rev-parse", "HEAD") != sha:
        raise RuntimeError("Checkout does not match the tested event commit")
    manifest = json.loads((ROOT / "release-manifest.json").read_text())
    version = manifest["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise RuntimeError("Expected a numeric semantic version")
    tag = f"v{version}"
    notes = ROOT / "docs" / f"RELEASE_NOTES_{version}.md"
    report = json.loads((ROOT / "dist" / "verification.json").read_text())
    if len(report["artifacts"]) != 2 or any(a["version"] != version for a in report["artifacts"]):
        raise RuntimeError("Distribution verification is missing or for a different version")
    lookup = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo, "--json", "isDraft,url"],
        text=True, capture_output=True,
    )
    if lookup.returncode == 0:
        existing = json.loads(lookup.stdout)
        if existing["isDraft"]:
            raise RuntimeError("A draft already exists; inspect it instead of overwriting it")
        ref = json.loads(command("gh", "api", f"repos/{repo}/git/ref/tags/{tag}"))["object"]
        if ref["type"] == "tag":
            ref = json.loads(command("gh", "api", f"repos/{repo}/git/tags/{ref['sha']}"))["object"]
        if ref["sha"] != sha:
            raise RuntimeError("Existing release points to a different commit; use a new version")
        print(f"Already published: {existing['url']}")
        return
    files = sorted(p for p in (ROOT / "dist").iterdir() if p.is_file())
    command("gh", "release", "create", tag, "--repo", repo, "--target", sha,
            "--title", f"ChainBench {tag}", "--notes-file", str(notes), "--draft", "--prerelease")
    command("gh", "release", "upload", tag, *[str(p) for p in files], "--repo", repo)
    assets = json.loads(command("gh", "release", "view", tag, "--repo", repo, "--json", "assets"))
    remote = {a["name"]: a["size"] for a in assets["assets"]}
    if remote != {p.name: p.stat().st_size for p in files}:
        raise RuntimeError("Uploaded assets do not match local files; draft remains unpublished")
    with tempfile.TemporaryDirectory(prefix="chainbench-assets-") as tmp:
        command("gh", "release", "download", tag, "--repo", repo, "--dir", tmp)
        for original in files:
            downloaded = Path(tmp) / original.name
            if hashlib.sha256(downloaded.read_bytes()).digest() != hashlib.sha256(original.read_bytes()).digest():
                raise RuntimeError("Release asset download differs from the verified file")
    command("gh", "release", "edit", tag, "--repo", repo, "--draft=false", "--prerelease")
    print(command("gh", "release", "view", tag, "--repo", repo, "--json", "url", "--jq", ".url"))


if __name__ == "__main__":
    main()
