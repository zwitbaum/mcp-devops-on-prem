# Releasing

This page is for maintainers. It describes how a new version reaches PyPI, the MCP Registry, and the Claude plugin directory.

## Why the plugin version is pinned

The Claude plugin directory blocks plugins whose launcher is unpinned. `claude-plugin/.mcp.json` therefore always runs an exact version, `uvx mcp-devops-onpremise==X.Y.Z`, never `@latest` or a range. The plugin version in `claude-plugin/.claude-plugin/plugin.json` must also go up with every release; if it stays the same, Claude Code users keep their cached copy.

Users still get updates automatically. The directory follows the `plugin-release` branch, validates and scans each new commit, and installed plugins update without user action.

The directory must never see a pinned version that isn't on PyPI yet, or the plugin breaks for every user. That's why it tracks `plugin-release` and not `main`: the release workflow moves `plugin-release` only after the PyPI upload has succeeded and the new version can be downloaded.

Manual setups (`uvx mcp-devops-onpremise@latest` in an MCP client config) aren't affected. `@latest` stays valid there.

## Release flow

1. **Bump the version** in every file that carries it:

   ```bash
   python scripts/bump_version.py X.Y.Z --dry-run   # preview
   python scripts/bump_version.py X.Y.Z
   ```

   This updates `pyproject.toml`, `src/mcp_devops/__init__.py`, `server.json` (both fields), `manifest.json`, `uv.lock`, `claude-plugin/.claude-plugin/plugin.json`, the pin in `claude-plugin/.mcp.json`, and `claude-plugin/README.md`. It also moves the `[Unreleased]` notes in `CHANGELOG.md` to a new `[X.Y.Z] - <today>` section and updates the compare links. Fill in `[Unreleased]` before you run it.

2. **Review** the changes with `git diff`, and check them with `python scripts/bump_version.py --check`.

3. **Commit** the changes on `main`.

4. **Tag and push:**

   ```bash
   git tag vX.Y.Z
   git push && git push --tags
   ```

5. **CI publishes automatically** (`.github/workflows/publish.yml`):
   - verifies that the tag matches the version in every file, and stops otherwise
   - builds the package and uploads it to PyPI
   - publishes `server.json` to the MCP Registry and creates the GitHub release
   - waits until `mcp-devops-onpremise==X.Y.Z` can be downloaded from PyPI (up to 10 minutes), then moves the `plugin-release` branch to the tagged commit

6. **The Claude plugin directory** detects the new commit on `plugin-release`, validates it, and users get the update automatically.

If the PyPI step or the availability check fails, `plugin-release` stays where it was and users keep the previous version. Fix the cause, then re-run the failed jobs of the workflow.

## One-time setup

- In the developer portal ([claude.ai/directory/manage](https://claude.ai/directory/manage)), set the tracked branch to `plugin-release` and the plugin path to `claude-plugin`.
- Optional: add the GitHub push webhook from the portal so new commits are detected right away.
- If `plugin-release` is protected, allow GitHub Actions to force-push to it. The workflow creates the branch on the first release if it doesn't exist.

## Review of new versions

Plugins that launch a package with `uvx` may be held for a human reviewer on each new version. The previously published version stays live in the meantime.
