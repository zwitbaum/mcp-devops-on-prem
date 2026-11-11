"""Every file that carries the release version must agree with pyproject.toml.

The Claude plugin pins the package exactly (``uvx mcp-devops-onpremise==X.Y.Z``), so a release
that forgets one spot ships a plugin that launches the wrong version. The checks reuse
``scripts/bump_version.py`` so the test and the release script can never disagree.
"""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("bump_version", REPO_ROOT / "scripts" / "bump_version.py")
bump_version = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = bump_version  # dataclasses resolve their module through sys.modules
_spec.loader.exec_module(bump_version)

VERSIONED_FILES = sorted({spot.path for spot in bump_version.SPOTS} | {bump_version.CHANGELOG})


def _newline_style(data: bytes) -> str:
    crlf, lf = data.count(b"\r\n"), data.count(b"\n")
    return "lf" if crlf == 0 else "crlf" if crlf == lf else "mixed"


@pytest.fixture()
def repo_copy(tmp_path):
    """Copy only the versioned files, so bump tests never touch the working tree."""
    for rel in VERSIONED_FILES:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / rel, target)
    return tmp_path


def _next_patch(version: str) -> str:
    major, minor, patch = map(int, version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def test_all_version_spots_match_pyproject():
    reference, found, problems = bump_version.collect(REPO_ROOT)
    assert problems == []
    assert bump_version.SEMVER.match(reference)
    for f in found:
        assert f.versions == [reference] * f.spot.count, f.spot.path


def test_plugin_launcher_is_pinned_exactly():
    mcp_json = (REPO_ROOT / "claude-plugin" / ".mcp.json").read_text(encoding="utf-8")
    reference, _, _ = bump_version.collect(REPO_ROOT)
    assert f'"{bump_version.PACKAGE}=={reference}"' in mcp_json
    assert "@latest" not in mcp_json


def test_check_cli_passes_on_repo():
    assert bump_version.main(["--check", "--root", str(REPO_ROOT)]) == 0


def test_check_detects_inconsistent_spot(repo_copy):
    plugin = repo_copy / "claude-plugin" / ".mcp.json"
    plugin.write_bytes(plugin.read_bytes().replace(b"==", b"==9", 1))
    _, _, problems = bump_version.collect(repo_copy)
    assert any("claude-plugin/.mcp.json" in p for p in problems)
    assert bump_version.main(["--check", "--root", str(repo_copy)]) == 1


def test_check_expect_mismatch_fails():
    assert bump_version.main(["--check", "--expect", "0.0.0", "--root", str(REPO_ROOT)]) == 1


def test_bump_updates_every_spot_and_keeps_line_endings(repo_copy):
    old, _, _ = bump_version.collect(repo_copy)
    new = _next_patch(old)
    before = {rel: (repo_copy / rel).read_bytes() for rel in VERSIONED_FILES}

    assert bump_version.main([new, "--date", "2099-01-02", "--root", str(repo_copy)]) == 0

    reference, _, problems = bump_version.collect(repo_copy)
    assert (reference, problems) == (new, [])
    for rel in VERSIONED_FILES:
        assert _newline_style((repo_copy / rel).read_bytes()) == _newline_style(before[rel]), rel

    changelog = (repo_copy / bump_version.CHANGELOG).read_text(encoding="utf-8")
    assert changelog.count("## [Unreleased]") == 1
    assert (
        changelog.index("## [Unreleased]")
        < changelog.index(f"## [{new}] - 2099-01-02")
        < changelog.index(f"## [{old}]")
    )
    assert f"compare/v{new}...HEAD" in changelog
    assert f"[{new}]: " in changelog and f"compare/v{old}...v{new}" in changelog


@pytest.mark.parametrize("style", ["lf", "crlf"])
def test_bump_works_with_either_line_ending(repo_copy, style):
    """CI checks files out with LF, a Windows working tree with CRLF; both must bump cleanly."""
    for rel in VERSIONED_FILES:
        path = repo_copy / rel
        data = path.read_bytes().replace(b"\r\n", b"\n")
        path.write_bytes(data if style == "lf" else data.replace(b"\n", b"\r\n"))
    old, _, _ = bump_version.collect(repo_copy)

    assert bump_version.main([_next_patch(old), "--root", str(repo_copy)]) == 0

    assert bump_version.collect(repo_copy)[2] == []
    for rel in VERSIONED_FILES:
        assert _newline_style((repo_copy / rel).read_bytes()) == style, rel


def test_dry_run_writes_nothing(repo_copy):
    old, _, _ = bump_version.collect(repo_copy)
    before = {rel: (repo_copy / rel).read_bytes() for rel in VERSIONED_FILES}
    assert bump_version.main([_next_patch(old), "--dry-run", "--root", str(repo_copy)]) == 0
    assert {rel: (repo_copy / rel).read_bytes() for rel in VERSIONED_FILES} == before


@pytest.mark.parametrize("bad", ["2.2", "v2.3.0", "2.3.0-rc1", "02.3.0", "0.0.1"])
def test_bump_rejects_invalid_or_older_versions(repo_copy, bad):
    assert bump_version.main([bad, "--root", str(repo_copy)]) == 1
