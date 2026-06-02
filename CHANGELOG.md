# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

[Unreleased]: https://github.com/zwitbaum/mcp-devops-on-prem/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/zwitbaum/mcp-devops-on-prem/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/zwitbaum/mcp-devops-on-prem/releases/tag/v0.1.0
