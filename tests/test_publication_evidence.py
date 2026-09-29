"""Failure injection at the release boundary; no network or credentials are used."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

VERSION, SHA = "0.2.0", "a" * 40


def load_script(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_sums(dist):
    (dist / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
        for p in sorted(dist.iterdir()) if p.name != "SHA256SUMS"
    ), encoding="utf-8")


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    artifacts = []
    for name in (f"chainbench-{VERSION}-py3-none-any.whl", f"chainbench-{VERSION}.tar.gz"):
        (dist / name).write_bytes(b"verified distribution bytes")
        artifacts.append({
            "artifact": name, "version": VERSION,
            "sha256": hashlib.sha256((dist / name).read_bytes()).hexdigest(),
            "checks": 2, "slugs": ["condition", "observation"], "statuses": ["CONSISTENT", "INFO"],
            "installed_outside_checkout": True, "pip_check": "passed",
            "exports": ["markdown", "csv", "json"],
            "experiments": [
                {"preset": name, "methods": methods, "config_sha256": "a"*64, "rows": 100,
                 "exports": ["json", "csv", "markdown"], "saved_config_rerun": "matched"}
                for name, methods in {
                    "quadratic": ["gd", "smooth-fista", "heavy-ball", "cg", "proximal-point"],
                    "diagonal-lasso": ["ista", "fista"], "simplex": ["frank-wolfe"],
                }.items()
            ],
        })
    report = {"source_commit": SHA, "artifacts": artifacts}
    (dist / "verification.json").write_text(json.dumps(report), encoding="utf-8")
    (dist / "build-environment.txt").write_text("test fixture\n", encoding="utf-8")
    write_sums(dist)
    module = load_script("publish_release")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module, dist, report


def test_valid_publication_evidence(evidence):
    module, _, _ = evidence
    assert len(module.verified_files(VERSION, SHA)) == 5


def test_reject_distribution_changed_after_smoke_test(evidence):
    module, dist, report = evidence
    (dist / report["artifacts"][0]["artifact"]).write_bytes(b"changed after installation")
    write_sums(dist)  # Rehashing the upload alone must not bypass the install record.
    with pytest.raises(RuntimeError, match="changed after"):
        module.verified_files(VERSION, SHA)


@pytest.mark.parametrize("field,value", [
    ("version", "9.9.9"), ("artifact", "../outside.whl"), ("checks", True),
    ("statuses", ["CONSISTENT", "NOT CONSISTENT"]), ("statuses", ["INFO", "INFO"]),
    ("statuses", ["CONSISTENT", "UNKNOWN"]), ("slugs", ["same", "same"]),
    ("experiments", None), ("experiments", []),
    ("installed_outside_checkout", False), ("pip_check", "failed"), ("exports", []),
])
def test_reject_malformed_or_failed_verification(evidence, field, value):
    module, dist, report = evidence
    report["artifacts"][0][field] = value
    (dist / "verification.json").write_text(json.dumps(report), encoding="utf-8")
    write_sums(dist)
    with pytest.raises(RuntimeError):
        module.verified_files(VERSION, SHA)


def test_commit_binding_and_checksum_binding(evidence):
    module, dist, _ = evidence
    with pytest.raises(RuntimeError, match="different commit"):
        module.verified_files(VERSION, "b" * 40)
    (dist / "build-environment.txt").write_text("modified")
    with pytest.raises(RuntimeError, match="Checksums"):
        module.verified_files(VERSION, SHA)


def test_duplicate_artifact_record_rejected(evidence):
    module, dist, report = evidence
    report["artifacts"][1] = copy.deepcopy(report["artifacts"][0])
    (dist / "verification.json").write_text(json.dumps(report), encoding="utf-8")
    write_sums(dist)
    with pytest.raises(RuntimeError, match="name/version"):
        module.verified_files(VERSION, SHA)


def test_unlisted_file_rejected(evidence):
    module, dist, _ = evidence
    (dist / "not-a-release-asset.txt").write_text("unlisted")
    write_sums(dist)
    with pytest.raises(RuntimeError, match="only the verified"):
        module.verified_files(VERSION, SHA)


def test_wrong_existing_tag_target_is_rejected(monkeypatch):
    module = load_script("publish_release")
    monkeypatch.setattr(module, "command", lambda *args: json.dumps([
        {"ref": "refs/tags/v0.1.1", "object": {"type": "commit", "sha": "wrong"}}
    ]))
    with pytest.raises(RuntimeError, match="different commit"):
        module.require_tag_target("owner/repo", "v0.1.1", SHA, may_be_absent=True)


def test_tag_prefix_does_not_match_exact_tag(monkeypatch):
    module = load_script("publish_release")
    monkeypatch.setattr(module, "command", lambda *args: json.dumps([
        {"ref": "refs/tags/v0.1.10", "object": {"type": "commit", "sha": "unrelated"}}
    ]))
    assert module.tag_commit("owner/repo", "v0.1.1") is None


def test_annotated_tag_is_resolved(monkeypatch):
    module = load_script("publish_release")
    def fake(*args):
        if "matching-refs" in args[-1]:
            return json.dumps([{"ref": "refs/tags/v0.1.1", "object": {"type": "tag", "sha": "tag"}}])
        return json.dumps({"object": {"type": "commit", "sha": SHA}})
    monkeypatch.setattr(module, "command", fake)
    assert module.tag_commit("owner/repo", "v0.1.1") == SHA


@pytest.mark.parametrize("rows,listing", [
    ([], []), ([{"slug": "x", "status": "CONSISTENT", "observed": None, "threshold": 1}], ["x"]),
    ([{"slug": "x", "status": "UNKNOWN", "observed": .5, "threshold": 1}], ["x"]),
    ([{"slug": "x", "status": "CONSISTENT", "observed": 2, "threshold": 1}], ["x"]),
    ([{"slug": "x", "status": "INFO", "observed": .5, "threshold": None}], ["x"]),
])
def test_installed_suite_fails_closed(rows, listing):
    with pytest.raises(RuntimeError):
        load_script("smoke_install").validate_rows(rows, listing)


@pytest.mark.parametrize("corrupt_download", [False, True])
def test_publication_state_machine_never_publishes_bad_download(evidence, monkeypatch, corrupt_download):
    module, dist, _ = evidence
    root = dist.parent
    (root / "docs").mkdir()
    (root / "docs" / f"RELEASE_NOTES_{VERSION}.md").write_text("alpha notes", encoding="utf-8")
    (root / "release-manifest.json").write_text(json.dumps({"version": VERSION, "channel": "alpha"}))
    monkeypatch.setenv("GITHUB_REPOSITORY", "chocoemong17/chainbench")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", SHA)
    state = {"tag": False, "draft": False, "published": False}

    def fake(*args):
        if args[0] == "git":
            return SHA
        if args[1] == "api":
            endpoint = args[2]
            if "matching-refs" in endpoint:
                refs = [{"ref": f"refs/tags/v{VERSION}", "object": {"type": "commit", "sha": SHA}}]
                return json.dumps(refs if state["tag"] else [])
            if endpoint.endswith("git/refs"):
                assert f"sha={SHA}" in args
                state["tag"] = True
                return "{}"
            if "releases?" in endpoint:
                return "[[]]"
        if args[1:3] == ("release", "create"):
            assert state["tag"] and "--draft" in args and "--verify-tag" in args
            state["draft"] = True
            return "created draft"
        if args[1:3] == ("release", "upload"):
            assert state["draft"] and not state["published"]
            return "uploaded"
        if args[1:3] == ("release", "download"):
            target = Path(args[args.index("--dir") + 1])
            for file in dist.iterdir():
                (target / file.name).write_bytes(file.read_bytes())
            if corrupt_download:
                (target / "verification.json").write_bytes(b"corrupt")
            return "downloaded"
        if args[1:3] == ("release", "view"):
            if "assets" in args:
                return json.dumps({"assets": [{"name": p.name, "size": p.stat().st_size} for p in dist.iterdir()]})
            return "release URL"
        if args[1:3] == ("release", "edit"):
            state["published"] = True
            return "published"
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr(module, "command", fake)
    if corrupt_download:
        with pytest.raises(RuntimeError, match="download differs"):
            module.main()
        assert not state["published"]
    else:
        module.main()
        assert state["published"]


def test_api_failure_is_not_treated_as_tag_absence(monkeypatch):
    import subprocess
    module = load_script("publish_release")
    def fail(*args):
        raise subprocess.CalledProcessError(1, args)
    monkeypatch.setattr(module, "command", fail)
    with pytest.raises(subprocess.CalledProcessError):
        module.tag_commit("owner/repo", "v0.1.1")


@pytest.mark.parametrize("field,value", [
    ("rows", 0), ("rows", True), ("methods", []), ("preset", "other"),
    ("exports", []), ("saved_config_rerun", "skipped"), ("config_sha256", None),
])
def test_invalid_experiment_evidence_prevents_publication(evidence, field, value):
    module, dist, report = evidence
    report["artifacts"][0]["experiments"][0][field] = value
    (dist / "verification.json").write_text(json.dumps(report), encoding="utf-8")
    write_sums(dist)
    with pytest.raises(RuntimeError, match="experiment evidence"):
        module.verified_files(VERSION, SHA)


def test_wheel_and_sdist_experiment_records_must_agree(evidence):
    module, dist, report = evidence
    report["artifacts"][0]["experiments"][0]["config_sha256"] = "b"*64
    (dist / "verification.json").write_text(json.dumps(report), encoding="utf-8")
    write_sums(dist)
    with pytest.raises(RuntimeError, match="results disagree"):
        module.verified_files(VERSION, SHA)
