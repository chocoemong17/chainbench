"""Publish only verified review assets to the designated concept branch in CI."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

REPO = "chocoemong17/chainbench"
BRANCH = "study/learning-foundations"
DESTINATION = "docs/reviews/learning-foundations/v2/"


def api(route, payload=None, method=None):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{route}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                 "Accept": "application/vnd.github+json", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main():
    if (os.environ.get("GITHUB_REPOSITORY") != REPO
            or os.environ.get("GITHUB_REF") != "refs/heads/" + BRANCH):
        raise RuntimeError("Review publication is restricted to the concept branch")
    source = os.environ["GITHUB_SHA"]
    if api("git/ref/heads/" + BRANCH)["object"]["sha"] != source:
        raise RuntimeError("Branch advanced; do not publish stale review assets")
    root = Path("learning-review")
    proof = json.loads((root / "verification.json").read_text(encoding="utf8"))
    assert proof["source"] == source and proof["status"] == "concept-pending-owner-review"
    assert proof["revision"] == 2 and len(proof["files"]) == 76
    assert {p.name for p in root.iterdir()} == set(proof["files"]) | {"verification.json"}
    assert sum(row["bytes"] for row in proof["files"].values()) < 12_000_000
    rows = []
    for name, info in proof["files"].items():
        if not re.fullmatch(r"(backprop|cnn|dropout)\.(en|ko)\.(gif|(?:[1-9]|10)\.png|contact[1-3]\.png)", name):
            raise ValueError("Unexpected asset name")
        raw = (root / name).read_bytes()
        assert len(raw) == info["bytes"] and hashlib.sha256(raw).hexdigest() == info["sha256"]
    for path in sorted(root.iterdir()):
        blob = api("git/blobs", {"content": base64.b64encode(path.read_bytes()).decode(),
                                "encoding": "base64"})
        rows.append({"path": DESTINATION + path.name, "mode": "100644", "type": "blob",
                     "sha": blob["sha"]})
    parent = api("git/commits/" + source)
    tree = api("git/trees", {"base_tree": parent["tree"]["sha"], "tree": rows})
    commit = api("git/commits", {"message": "Publish checked foundations concept boards",
                                 "tree": tree["sha"], "parents": [source]})
    # A concurrent branch update causes a non-fast-forward rejection; never force.
    api("git/refs/heads/" + BRANCH, {"sha": commit["sha"], "force": False}, "PATCH")
    print(json.dumps({"review_commit": commit["sha"], "render_source": source,
                      "files": len(rows), "branch": BRANCH, "production_deployed": False}))


if __name__ == "__main__":
    main()
