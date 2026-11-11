#!/usr/bin/env python3
"""Bump or check the release version in every file that carries it.

Usage:
    python scripts/bump_version.py X.Y.Z            # update all version spots
    python scripts/bump_version.py X.Y.Z --dry-run  # show the diff, write nothing
    python scripts/bump_version.py --check          # exit 1 if versions disagree
    python scripts/bump_version.py --check --expect X.Y.Z

The Claude plugin pins the package to an exact version (``uvx mcp-devops-onpremise==X.Y.Z``),
so the pin and ``plugin.json`` must move together with the package version on every release.

Files are read and written as bytes and edited in place, so existing line endings
(CRLF in a Windows working tree, LF in CI) are preserved. Standard library only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PACKAGE = "mcp-devops-onpremise"
REPO_ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
CHANGELOG = "CHANGELOG.md"

_V = r"(?P<v>[^\"'`\s]+)"  # a version value; validated separately


@dataclass(frozen=True)
class Spot:
    """A place in a file that holds the version, located by a regex with a ``v`` group."""

    path: str
    label: str
    pattern: str
    count: int = 1
    scope: str | None = None  # optional regex whose ``body`` group limits the search


SPOTS: tuple[Spot, ...] = (
    Spot(
        "pyproject.toml",
        '[project] version = "X.Y.Z"',
        rf'(?m)^version = "{_V}"',
        scope=r"(?ms)^\[project\][ \t]*\r?\n(?P<body>.*?)(?=^\[|\Z)",
    ),
    Spot("src/mcp_devops/__init__.py", '__version__ = "X.Y.Z"', rf'(?m)^__version__ = "{_V}"'),
    Spot("server.json", '"version" (top level and package entry)', rf'"version": "{_V}"', count=2),
    Spot("manifest.json", 'top-level "version"', rf'(?m)^  "version": "{_V}"'),
    Spot("uv.lock", f"{PACKAGE} package version", rf'(?m)^name = "{PACKAGE}"\r?\nversion = "{_V}"'),
    Spot("claude-plugin/.claude-plugin/plugin.json", '"version"', rf'(?m)^  "version": "{_V}"'),
    Spot("claude-plugin/.mcp.json", f"{PACKAGE}==X.Y.Z", rf"{re.escape(PACKAGE)}=={_V}"),
    Spot("claude-plugin/README.md", f"uvx {PACKAGE}==X.Y.Z", rf"`uvx {re.escape(PACKAGE)}=={_V}`"),
)

_UNRELEASED_HEADING = re.compile(r"(?m)^## \[Unreleased\][ \t]*\r?\n")
_RELEASE_HEADING = re.compile(r"(?m)^## \[(?P<v>[^\]]+)\]")
_UNRELEASED_LINK = re.compile(r"(?m)^\[Unreleased\]: (?P<base>\S+?)/compare/v(?P<v>\S+?)\.\.\.HEAD")


class VersionError(Exception):
    """A version spot is missing, duplicated, or inconsistent."""


@dataclass
class Found:
    spot: Spot
    versions: list[str]
    spans: list[tuple[int, int]]  # absolute (start, end) of each ``v`` group


def read_text(root: Path, rel: str) -> str:
    # Decode bytes directly: no newline translation, so CRLF/LF survive a round trip.
    return (root / rel).read_bytes().decode("utf-8")


def find_spot(text: str, spot: Spot) -> Found:
    offset, region = 0, text
    if spot.scope:
        scope = re.search(spot.scope, text)
        if not scope:
            raise VersionError(f"{spot.path}: section for {spot.label} not found")
        offset, region = scope.start("body"), scope.group("body")
    matches = list(re.finditer(spot.pattern, region))
    if len(matches) != spot.count:
        raise VersionError(f"{spot.path}: expected {spot.count} match(es) for {spot.label}, found {len(matches)}")
    return Found(
        spot,
        [m.group("v") for m in matches],
        [(offset + m.start("v"), offset + m.end("v")) for m in matches],
    )


def latest_changelog_version(text: str) -> str:
    if len(_UNRELEASED_HEADING.findall(text)) != 1:
        raise VersionError(f"{CHANGELOG}: expected exactly one '## [Unreleased]' heading")
    for m in _RELEASE_HEADING.finditer(text):
        if m.group("v") != "Unreleased":
            return m.group("v")
    raise VersionError(f"{CHANGELOG}: no '## [X.Y.Z]' release heading found")


def collect(root: Path) -> tuple[str, list[Found], list[str]]:
    """Return (reference version from pyproject.toml, found spots, list of problems)."""
    problems: list[str] = []
    found: list[Found] = []
    for spot in SPOTS:
        try:
            found.append(find_spot(read_text(root, spot.path), spot))
        except (OSError, VersionError) as exc:
            problems.append(str(exc))
    reference = next((f.versions[0] for f in found if f.spot.path == "pyproject.toml"), None)
    if reference is None:
        return "", found, problems or ["pyproject.toml: version not found"]
    if not SEMVER.match(reference):
        problems.append(f"pyproject.toml: version {reference!r} is not X.Y.Z")
    for f in found:
        for v in f.versions:
            if v != reference:
                problems.append(f"{f.spot.path}: {f.spot.label} is {v}, expected {reference}")
    try:
        latest = latest_changelog_version(read_text(root, CHANGELOG))
        if latest != reference:
            problems.append(f"{CHANGELOG}: latest release heading is [{latest}], expected [{reference}]")
    except (OSError, VersionError) as exc:
        problems.append(str(exc))
    return reference, found, problems


def bump_changelog(text: str, old: str, new: str, today: str) -> tuple[str, list[str]]:
    """Move the Unreleased notes into a new release section and update the compare links."""
    notes: list[str] = []
    nl = "\r\n" if "\r\n" in text else "\n"
    if re.search(rf"(?m)^## \[{re.escape(new)}\]", text):
        raise VersionError(f"{CHANGELOG}: section [{new}] already exists")
    heading = _UNRELEASED_HEADING.search(text)
    if not heading:
        raise VersionError(f"{CHANGELOG}: '## [Unreleased]' heading not found")
    nxt = re.compile(r"(?m)^## \[").search(text, heading.end())
    if not nxt:
        raise VersionError(f"{CHANGELOG}: no release section after '## [Unreleased]'")

    content = text[heading.end() : nxt.start()].strip()
    content = re.sub(r"(?:^|\r?\n)---$", "", content).strip()  # drop the section separator
    if not content:
        notes.append(f"WARNING: {CHANGELOG} [Unreleased] is empty; add release notes to [{new}]")

    section = f"---{nl}{nl}## [{new}] - {today}{nl}{nl}"
    if content:
        section += f"{content}{nl}{nl}"
    section += f"---{nl}{nl}"
    text = text[: heading.end()] + nl + section + text[nxt.start() :]

    link = _UNRELEASED_LINK.search(text)
    if link:
        base = link.group("base")
        new_links = f"[Unreleased]: {base}/compare/v{new}...HEAD"
        if not re.search(rf"(?m)^\[{re.escape(new)}\]:", text):
            new_links += f"{nl}[{new}]: {base}/compare/v{old}...v{new}"
        text = text[: link.start()] + new_links + text[link.end() :]
    else:
        notes.append(f"WARNING: {CHANGELOG} has no '[Unreleased]: .../compare/vX.Y.Z...HEAD' link; links not updated")
    return text, notes


def plan_bump(root: Path, new: str, today: str) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """Compute {path: (old_text, new_text)} without writing. Raises VersionError on any problem."""
    if not SEMVER.match(new):
        raise VersionError(f"{new!r} is not a valid X.Y.Z version")
    old, found, problems = collect(root)
    if problems:
        raise VersionError("current versions are inconsistent, fix first:\n  " + "\n  ".join(problems))
    if tuple(map(int, new.split("."))) <= tuple(map(int, old.split("."))):
        raise VersionError(f"new version {new} must be greater than current version {old}")

    changes: dict[str, tuple[str, str]] = {}
    for f in found:  # each path appears in exactly one Spot
        before = after = read_text(root, f.spot.path)
        for start, end in sorted(f.spans, reverse=True):  # right to left keeps offsets valid
            after = after[:start] + new + after[end:]
        changes[f.spot.path] = (before, after)

    log_before = read_text(root, CHANGELOG)
    log_after, notes = bump_changelog(log_before, old, new, today)
    changes[CHANGELOG] = (log_before, log_after)
    return changes, notes


def show_diff(path: str, before: str, after: str) -> None:
    diff = difflib.unified_diff(before.splitlines(), after.splitlines(), f"a/{path}", f"b/{path}", lineterm="", n=1)
    for line in diff:
        print(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", nargs="?", help="new version X.Y.Z")
    parser.add_argument("--check", action="store_true", help="verify all spots agree; write nothing")
    parser.add_argument("--expect", metavar="X.Y.Z", help="with --check: also require this exact version")
    parser.add_argument("--dry-run", action="store_true", help="print the diff instead of writing files")
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="release date (default: today)")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.check == bool(args.version):
        parser.error("give either a version or --check")

    if args.check:
        reference, found, problems = collect(args.root)
        if args.expect and reference != args.expect:
            problems.append(f"expected version {args.expect}, but pyproject.toml has {reference or 'none'}")
        if problems:
            print("Version check FAILED:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 1
        spots = sum(len(f.versions) for f in found) + 1  # +1 for the CHANGELOG heading
        print(f"Version check OK: {spots} spots in {len(found) + 1} files are at {reference}")
        return 0

    try:
        changes, notes = plan_bump(args.root, args.version, args.date)
    except VersionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for path, (before, after) in changes.items():
        if args.dry_run:
            show_diff(path, before, after)
        else:
            (args.root / path).write_bytes(after.encode("utf-8"))
            print(f"updated {path}")
    for note in notes:
        print(note, file=sys.stderr)
    print(f"{'Would bump' if args.dry_run else 'Bumped'} to {args.version} in {len(changes)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
