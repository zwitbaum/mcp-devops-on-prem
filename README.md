<div align="center">

# MCP DevOps On-Premise

Model Context Protocol [MCP](https://modelcontextprotocol.io/) server for **on-premises Azure DevOps** that lets AI assistants browse repositories, review pull requests, manage work items, and interact with wikis.

<!-- mcp-name: io.github.zwitbaum/mcp-devops-on-prem -->

[![License: MIT](https://img.shields.io/badge/license-Apache%20License%202.0-blue)](https://opensource.org/licenses/apache-2.0)
[![PyPI - Version](https://img.shields.io/pypi/v/mcp-devops-onpremise)](https://pypi.org/project/mcp-devops-onpremise)

<div class="toc">
  <a href="#overview">Overview</a> •  
  <a href="#getting-started">Getting Started</a> •  
  <a href="#updating">Updating</a> •
  <a href="#available-tools">Available Tools</a> •
  <a href="#development">Development</a>
</div>

</div>


## Overview

Many organizations use on-premise DevOps solutions such as TFS or Azure DevOps Server in their projects. Integrating these systems with modern agentic AI tools and LLMs can be difficult. The official Microsoft Azure DevOps MCP server does not support these environments and is unlikely to support them in the future.

This MCP server closes that gap and enables smooth integration with on-premise DevOps systems.

This project is under active development, with features continuously added to meet current requirements. Community needs are highly valued — if you miss any features, please submit an [Issue](../../issues). User-requested features are fast-tracked and will be prioritized and added as soon as possible.

## Key Advantages

One of the most important features of this MCP server is **NTLM authentication** support. NTLM is required by many on-premises and enterprise environments where users authenticate with Windows domain credentials, either directly or over VPN. Most MCP servers for Azure DevOps target only cloud-hosted Azure DevOps Services with token-based auth and cannot connect to these environments.

- NTLM authentication (Windows domain credentials) for on-prem and VPN-based setups where no other auth method works.
- PAT and OAuth bearer token authentication as alternatives when available.
- Enables secure access to on-prem DevOps systems from MCP-compatible AI tools such as GitHub Copilot, Claude Desktop, Cursor, Windsurf, and others.
- Works in restricted or offline environments without exposing sensitive data to external services.
- Retrieves commit diffs with clear added/removed lines, similar to the DevOps UI.
- Helps keep and track project documentation alongside code changes.
- Automates common tasks such as work item management and code review processes.

## Getting Started

### Prerequisites
[Python 3.10+](docs/getting-started.md#prerequisites) and [uv](docs/getting-started.md#uv) are required. If not yet installed, see [installation guide](docs/getting-started.md#prerequisites).

### Quick Install

Click one of the buttons below to install directly in your IDE. You will be prompted for credentials:

[![Install in VS Code](https://img.shields.io/badge/Install_in-VS_Code-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=devops-onprem&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-devops-onpremise%40latest%22%5D%2C%22env%22%3A%7B%22DEVOPS_API_URL%22%3A%22%24%7Binput%3Adevops_api_url%7D%22%2C%22DEVOPS_USERNAME%22%3A%22%24%7Binput%3Adevops_username%7D%22%2C%22DEVOPS_PASSWORD%22%3A%22%24%7Binput%3Adevops_password%7D%22%7D%2C%22inputs%22%3A%5B%7B%22id%22%3A%22devops_api_url%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Azure%20DevOps%20API%20URL%20%28https%3A%2F%2Fserver%2Forg%2Fproject%29%22%7D%2C%7B%22id%22%3A%22devops_username%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Username%20%28DOMAIN%5C%5Cusername%29%22%7D%2C%7B%22id%22%3A%22devops_password%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Password%20or%20PAT%22%2C%22password%22%3Atrue%7D%5D%7D)
[![Install in VS Code Insiders](https://img.shields.io/badge/Install_in-VS_Code_Insiders-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=devops-onprem&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-devops-onpremise%40latest%22%5D%2C%22env%22%3A%7B%22DEVOPS_API_URL%22%3A%22%24%7Binput%3Adevops_api_url%7D%22%2C%22DEVOPS_USERNAME%22%3A%22%24%7Binput%3Adevops_username%7D%22%2C%22DEVOPS_PASSWORD%22%3A%22%24%7Binput%3Adevops_password%7D%22%7D%2C%22inputs%22%3A%5B%7B%22id%22%3A%22devops_api_url%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Azure%20DevOps%20API%20URL%20%28https%3A%2F%2Fserver%2Forg%2Fproject%29%22%7D%2C%7B%22id%22%3A%22devops_username%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Username%20%28DOMAIN%5C%5Cusername%29%22%7D%2C%7B%22id%22%3A%22devops_password%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Password%20or%20PAT%22%2C%22password%22%3Atrue%7D%5D%7D&quality=insiders)
[![Install in Cursor](https://img.shields.io/badge/Install_in-Cursor-000000?style=flat-square&logoColor=white)](https://cursor.com/en/install-mcp?name=devops-onprem&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJtY3AtZGV2b3BzLW9ucHJlbWlzZUBsYXRlc3QiXSwiZW52Ijp7fX0=)

For other platforms, see [Manual Installation](docs/getting-started.md#manual-installation) in the Getting Started guide.


### Manual Installation

The MCP server can be installed manually in the following AI tools: **VS Code, Visual Studio, Cursor, Goose, LM Studio, Amp, Claude Code, Claude Desktop, Codex, Gemini CLI, OpenCode, Qodo Gen, Warp, Windsurf, GitHub Copilot CLI, GitHub Copilot Coding Agent,** and others.

For step-by-step instructions, see [Manual Installation](docs/getting-started.md#manual-installation) in the Getting Started guide.

### Configuration

The `DEVOPS_API_URL` must point to your full project URL:
```
https://<your-devops-server>/<organization>/<project>
```

The server supports three authentication methods. If you are unsure which one to use, start with NTLM because it is the most common for on-prem/VPN setups.

| Method | Description |
|---|---|
| **NTLM** (username + password) | Most common for on-prem/VPN. Usually the simplest first setup and best fallback if other options fail. |
| **PAT** (Personal Access Token) | Use when PAT is enabled and allowed. Tokens can expire, and token-based auth may be blocked by policy. Advantage: you do not store your account password in config. |
| **OAuth Bearer Token** | Advanced option for CI/CD pipelines. Requires OAuth 2.0 configured on your DevOps Server and a token source defined by your administrators. |

For detailed setup instructions for each method, see [Authentication](docs/getting-started.md#authentication) in the Getting Started guide.

#### With NTLM (username + password)

```json
{
  "mcpServers": {
    "devops-onprem": {
      "command": "uvx",
      "args": ["mcp-devops-onpremise@latest"],
      "env": {
        "DEVOPS_API_URL": "https://your-devops-server/your-organization/your-project",
        "DEVOPS_USERNAME": "DOMAIN\\your-username",
        "DEVOPS_PASSWORD": "your-password"
      }
    }
  }
}
```

#### With PAT

```json
{
  "mcpServers": {
    "devops-onprem": {
      "command": "uvx",
      "args": ["mcp-devops-onpremise@latest"],
      "env": {
        "DEVOPS_API_URL": "https://your-devops-server/your-organization/your-project",
        "DEVOPS_PAT": "your-personal-access-token"
      }
    }
  }
}
```

> If you used a permanent install, replace `"command": "uvx"` with `"command": "mcp-devops-onpremise"` and remove the `"args"` line.

## Updating

All configuration examples use `mcp-devops-onpremise@latest`, which instructs `uvx` to fetch the latest version **automatically** on every run.

For permanent installs and release notes, see [Updating](docs/getting-started.md#updating) in the Getting Started guide.

## Available Tools

### Pull Requests

| Tool | Description | Read-only |
|---|---|:---:|
| `devops_pull_request_get` | Retrieve a pull request by ID, including linked work items and commit SHAs for diffing | ✅ |
| `devops_pull_request_list_threads` | Returns a hierarchical list of non-deleted comment threads and their text comments | ✅ |
| `devops_pull_request_list_thread_comments` | List non-deleted text comments in a specific thread | ✅ |
| `devops_pull_request_create_comment` | Create a new thread with an initial comment (general or inline on a file/line) | ❌ |
| `devops_pull_request_reply_comment` | Reply to an existing comment thread | ❌ |
| `devops_pull_request_update_thread` | Update the status of a comment thread | ❌ |
| `devops_pull_request_update_comment` | Update the text of an existing comment | ❌ |
| `devops_pull_request_delete_comment` | Delete a comment from a pull request thread | ❌ |

### Repositories

| Tool | Description | Read-only |
|---|---|:---:|
| `devops_repository_list` | List all repositories in the project | ✅ |
| `devops_repository_get` | Retrieve repository details by name or ID | ✅ |
| `devops_repository_commit_changes` | List files changed in a specific commit | ✅ |
| `devops_repository_diffs_commits` | Get the difference between two commits (changed file paths) | ✅ |
| `devops_repository_item_content` | Get raw file content at a specific commit or branch | ✅ |
| `devops_get_item_content_diff` | Get line-level textual diff of a file between two commits (added lines prefixed `+`, removed `-`) | ✅ |

### Work Items

| Tool | Description | Read-only |
|---|---|:---:|
| `devops_work_item_get` | Retrieve a work item (PBI, bug, task) by numeric ID. Returns a compact object with key fields, attachments (files and inline images), and linked items (work items, pull requests, commits) | ✅ |
| `devops_work_item_attachment_get` | Download a work item attachment by its GUID, either saving locally or returning base64-encoded content | ✅ |
| `devops_work_item_type_get` | Get the definition of a work item type by name (e.g. `Bug`, `User Story`) | ✅ |
| `devops_work_item_query_by_wiql` | Execute a WIQL (Work Item Query Language) query and return matching work items | ✅ |
| `devops_work_item_create` | Create a new work item with typed fields; Html is the default format | ❌ |
| `devops_work_item_update` | Update fields on a work item using JSON Patch (add / replace / remove) | ❌ |
| `devops_work_item_delete` | Delete a work item, moves to Recycle Bin by default; use `destroy=True` for permanent deletion (requires project permission) | ❌ |
| `devops_work_item_undelete` | Restore a soft-deleted work item from the Recycle Bin | ❌ |
| `devops_work_item_link_update` | Add or remove a relation link between two work items (parent, child, related, successor, predecessor, etc.) | ❌ |
| `devops_work_item_artifact_link_update` | Add or remove an artifact link (Pull Request, Build, Commit, Branch, Changeset) on a work item | ❌ |
| `devops_work_item_comment_list` | List comments on a work item with configurable page size and format | ✅ |
| `devops_work_item_comment_add` | Add a comment to a work item | ❌ |
| `devops_work_item_comment_update` | Update an existing comment on a work item | ❌ |
| `devops_work_item_comment_delete` | Delete a comment from a work item | ❌ |

### Search

| Tool | Description | Read-only |
|---|---|:---:|
| `devops_code_search` | Search source code with optional repository, path, and branch filters | ✅ |
| `devops_work_item_search` | Search work items with optional area, type, state, and assigned-to filters | ✅ |
| `devops_wiki_search` | Search wiki pages with an optional wiki filter | ✅ |

### Wiki

| Tool | Description | Read-only |
|---|---|:---:|
| `devops_wiki_page_get` | Get wiki page metadata and optional content by wiki ID and page ID | ✅ |
| `devops_wiki_page_create_or_update` | Create or update a wiki page under a specified parent page | ❌ |
| `devops_wiki_page_update` | Update an existing wiki page by ID | ❌ |
| `devops_wiki_page_delete` | Delete an existing wiki page by ID | ❌ |

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run linting
uv run ruff check src/
uv run black --check src/

# Run tests
uv run pytest tests/
```