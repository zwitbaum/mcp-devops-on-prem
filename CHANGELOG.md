# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.1.1] - 2026-06-18

### Fixed
- packaging: added the PyPI README ownership marker required by the official MCP Registry verification
- registry metadata: added a root `server.json` file using the current MCP Registry schema and field names

---

## [1.1.0] - 2026-06-16

### Added
- added CLI transport selection for `stdio`, `streamable-http`, and `http`, with configurable host, port, and optional path
- added validation of configuration: now fails fast at startup when `DEVOPS_API_URL` is missing/invalid or multiple auth modes are configured

### Fixed
- `_decode_json_response`: now handles Azure DevOps JSON responses with a UTF-8 BOM
- `_normalize_mcp_url`: HTTP client connections now target the FastMCP `/mcp` endpoint automatically

---

## [1.0.0] - 2026-06-15

### Added
- `devops_work_item_query_by_wiql`: execute a WIQL (Work Item Query Language) query and return matching work items, with automatic field resolution and batched item lookup (up to 200 results)

### Changed
- `shared.py`: extracted `DEVOPS_API_VERSION` constant to a single location in `shared.py`; all tool modules now import and use this constant
- `pyproject.toml`: updated development status classifier to `Production/Stable`

---

## [0.3.0] - 2026-06-07

### Added
- `devops_work_item_type_get`: get the definition of a work item type by name
- `devops_work_item_create`: create a new work item with typed fields and optional Html/Markdown format hint
- `devops_work_item_update`: update fields on an existing work item using JSON Patch (add/replace/remove)
- `devops_work_item_delete`: delete a work item by ID; soft-deletes to Recycle Bin by default, or permanently with `destroy=True` (requires project permission)
- `devops_work_item_undelete`: restore a soft-deleted work item from the Recycle Bin
- `devops_work_item_link_update`: add or remove a relation link between two work items (parent, child, related, successor, predecessor, etc.)
- `devops_work_item_artifact_link_update`: add or remove an artifact link (Pull Request, Build, Commit, Branch, Changeset, Versioned Item) on a work item
- `devops_work_item_comment_list`: list comments on a work item with configurable format and count
- `devops_work_item_comment_add`: add a comment to a work item
- `devops_work_item_comment_update`: update an existing comment on a work item
- `devops_work_item_comment_delete`: delete a comment from a work item

### Changed
- `devops_work_item_create`: default field format is Html (not Markdown); Markdown is opt-in per field
- `repository_tools.py`: moved private helpers to top of file for consistency

---

## [0.2.0] - 2026-06-02

### Changed
- `devops_work_item_get`: reworked to return a compact, focused object instead of the raw API response

### Added
- `devops_work_item_attachment_get`: new tool to download a work item attachment by GUID; returns base64-encoded content or saves to a local path

---

## [0.1.0] - 2026-05-14

### Added
- Initial release
- Pull request tools: get, list threads, list thread comments, create/reply/update/delete comment, update thread status
- Repository tools: list, get, commit changes, diff commits, item content, line-level content diff
- Work item tool: get by numeric ID (raw API response)
- Wiki tools: get by URL, create or update, update, delete
- NTLM, PAT, and OAuth Bearer token authentication
- GitHub Actions CI and PyPI publish workflows

[Unreleased]: https://github.com/zwitbaum/mcp-devops-on-prem/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/zwitbaum/mcp-devops-on-prem/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/zwitbaum/mcp-devops-on-prem/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/zwitbaum/mcp-devops-on-prem/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/zwitbaum/mcp-devops-on-prem/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/zwitbaum/mcp-devops-on-prem/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/zwitbaum/mcp-devops-on-prem/releases/tag/v0.1.0
