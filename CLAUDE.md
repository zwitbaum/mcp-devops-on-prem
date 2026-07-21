# MCP DevOps On-Premise

Project context for recommenders and repository analysis tools.

## Component Metadata

- **Name:** `mcp-devops-onpremise`
- **Display name:** `DevOps On-Premises`
- **Type:** `mcp-server`
- **Primary language:** `Python`
- **Runtime:** `uv`
- **SDK:** `FastMCP`
- **License:** `Apache-2.0`
- **Repository:** `https://github.com/zwitbaum/mcp-devops-on-prem`
- **Docs:** `https://zwitbaum.github.io/mcp-devops-on-prem`
- **Entrypoint:** `mcp_devops:main`
- **CLI:** `mcp-devops-onpremise`
- **Target system:** `Azure DevOps Server / TFS (on-prem)`
- **Plugin status:** not a native Claude plugin package; connect as an MCP server

## Connection and Auth

- **Default transport:** `stdio`
- **Optional transport:** `streamable-http` / `http`
- **HTTP endpoint:** `/mcp`
- **Default local HTTP URL:** `http://127.0.0.1:8000/mcp`
- **Required env:** `DEVOPS_API_URL`
- **Auth mode rule:** configure exactly one mode
- **NTLM:** `DEVOPS_USERNAME` + `DEVOPS_PASSWORD`
- **PAT:** `DEVOPS_PAT`
- **Bearer token:** `DEVOPS_TOKEN`
- **Optional runtime env:** `MCP_TRANSPORT`, `MCP_HOST`, `MCP_PORT`, `MCP_PATH`, `DEVOPS_AUTH_DEBUG`

## Codebase Anchors

- **`src/mcp_devops/__init__.py`:** CLI entrypoint, transport parsing, startup validation
- **`src/mcp_devops/shared.py`:** FastMCP instance, auth selection, config validation, REST helpers
- **`src/mcp_devops/tools/pull_request_tools.py`:** pull request and thread/comment tools
- **`src/mcp_devops/tools/repository_tools.py`:** repository, commit, diff, and file tools
- **`src/mcp_devops/tools/work_item_tools.py`:** work item CRUD, WIQL, comments, links, attachments
- **`src/mcp_devops/tools/wiki_tools.py`:** wiki page tools
- **`tests/`:** pytest unit and smoke tests
- **`manifest.json`:** MCP-facing metadata and tool descriptions

## Exposed Tool Groups

- **Repositories:** list repos, get repo details, list commit changes, diff commits, read file content, line-level diff
  - `devops_repository_list`
  - `devops_repository_get`
  - `devops_repository_commit_changes`
  - `devops_repository_diffs_commits`
  - `devops_repository_item_content`
  - `devops_get_item_content_diff`

- **Pull Requests:** get PRs, list threads, list thread comments, create comments, reply, update thread, update/delete comments
  - `devops_pull_request_get`
  - `devops_pull_request_list_threads`
  - `devops_pull_request_list_thread_comments`
  - `devops_pull_request_create_comment`
  - `devops_pull_request_reply_comment`
  - `devops_pull_request_update_thread`
  - `devops_pull_request_update_comment`
  - `devops_pull_request_delete_comment`

- **Work Items:** get, query by WIQL, create, update, delete, undelete, relation links, artifact links, comments, attachments
  - `devops_work_item_get`
  - `devops_work_item_attachment_get`
  - `devops_work_item_type_get`
  - `devops_work_item_query_by_wiql`
  - `devops_work_item_create`
  - `devops_work_item_update`
  - `devops_work_item_delete`
  - `devops_work_item_undelete`
  - `devops_work_item_link_update`
  - `devops_work_item_artifact_link_update`
  - `devops_work_item_comment_list`
  - `devops_work_item_comment_add`
  - `devops_work_item_comment_update`
  - `devops_work_item_comment_delete`

- **Wiki:** get by wiki ID/page ID, create/update, update, delete
  - `devops_wiki_page_get`
  - `devops_wiki_page_create_or_update`
  - `devops_wiki_page_update`
  - `devops_wiki_page_delete`
- **Search:** code, work item, and wiki full-text search
  - `devops_code_search`
  - `devops_work_item_search`
  - `devops_wiki_search`

## Local Commands

- **Install deps:** `uv sync --group dev`
- **Run stdio server:** `uv run mcp-devops-onpremise`
- **Run HTTP server:** `uv run mcp-devops-onpremise --transport http --host 127.0.0.1 --port 8000`
- **HTTP helper:** `scripts/start_http_server.ps1`
- **HTTP helper (cmd):** `scripts/start_http_server.cmd`
- **HTTP smoke client:** `scripts/test_http.py`
- **Tests:** `uv run pytest tests/`
- **Lint:** `uv run ruff check src/`
- **Format:** `uv run ruff format src/`

## Dependency Anchors

- **Runtime packages:** `fastmcp`, `requests`, `requests-ntlm`, `python-dotenv`
- **Dev packages:** `pytest`, `pytest-cov`, `pytest-asyncio`, `responses`, `ruff`, `black`, `isort`

## Matching Tags

- **Tags:** `mcp-server`, `python`, `fastmcp`, `azure-devops`, `azure-devops-server`, `tfs`, `on-prem`, `ntlm`, `pull-requests`, `work-items`, `wiki`, `enterprise-devtools`
