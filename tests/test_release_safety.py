import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("repo,ref", [
    ("another-owner/chainbench", "refs/heads/main"),
    ("chocoemong17/chainbench", "refs/heads/feature"),
    ("chocoemong17/chainbench", "refs/pull/22/merge"),
])
def test_publish_rejects_wrong_repo_or_branch(monkeypatch, repo, ref):
    module = load_script("publish_release")
    monkeypatch.setenv("GITHUB_REPOSITORY", repo)
    monkeypatch.setenv("GITHUB_REF", ref)
    monkeypatch.setenv("GITHUB_SHA", "commit")
    with pytest.raises(RuntimeError, match="restricted"):
        module.main()


def test_publish_rejects_untested_checkout(monkeypatch):
    module = load_script("publish_release")
    monkeypatch.setenv("GITHUB_REPOSITORY", "chocoemong17/chainbench")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", "tested")
    monkeypatch.setattr(module, "command", lambda *args: "different")
    with pytest.raises(RuntimeError, match="tested event commit"):
        module.main()


def test_smoke_install_requires_one_of_each_format(tmp_path, monkeypatch):
    module = load_script("smoke_install")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "a.whl").touch()
    (dist / "b.whl").touch()
    with pytest.raises(RuntimeError, match="one wheel and one sdist"):
        module.main()


def test_manifest_and_module_versions_match():
    from chainbench import __version__

    manifest = json.loads((ROOT / "release-manifest.json").read_text())
    assert manifest["version"] == __version__
    assert manifest["channel"] == "alpha"
