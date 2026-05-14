# MCP DevOps On-Premise

Model Context Protocol [MCP](https://modelcontextprotocol.io/) server for **on-premises Azure DevOps** that lets AI assistants browse repositories, review pull requests, manage work items, and interact with wikis.

## Overview

Many organizations use on-premise DevOps solutions such as TFS or Azure DevOps Server in their projects. Integrating these systems with modern agentic AI tools and LLMs can be difficult. The official Microsoft Azure DevOps MCP server does not support these environments and is unlikely to support them in the future.

This MCP server closes that gap and enables smooth integration with on-premise DevOps systems.

## Key Advantages

- Supports typical on-prem DevOps authentication: NTLM (Windows login/password) and Personal Access Tokens (PAT).
- Enables secure access to on-prem DevOps systems from MCP-compatible AI tools such as GitHub Copilot, Claude Desktop, Cursor, Windsurf, and others.
- Works in restricted or offline environments without exposing sensitive data to external services.
- Retrieves commit diffs with clear added/removed lines, similar to the DevOps UI.
- Helps keep and track project documentation alongside code changes.
- Automates common tasks such as work item management and code review processes.

## Installation & Setup

### Step 1: Install Python 3.10 or later

If Python is not installed on your machine, download it from [python.org](https://www.python.org/downloads/).

> **Windows:** Check **"Add Python to PATH"** during installation.  
> `pip` is included with Python - no separate install needed.

### Step 2: Install `uv`

`uv` is a fast Python package manager used to run and install the server.

> **Windows users:** Open **Command Prompt** (`cmd`) or **PowerShell** to run all commands in this guide.

```
pip install uv
```

> More info: [uv documentation](https://github.com/astral-sh/uv)

### Step 3: Install the MCP server

**Option A - Ephemeral (recommended for most users):**

`uvx` downloads and runs the server on demand from PyPI. Nothing is permanently installed.

```
uvx mcp-devops-onpremise
```

**Option B - Permanent install:**

```
pip install mcp-devops-onpremise
```

### Step 4: Choose your authentication method

The server supports three authentication methods. **Start with NTLM (username + password) if you connect via VPN or are on a corporate network. Use PAT if it is available and works in your environment.**

#### Option 1: Username + Password (NTLM - most common for on-prem/VPN)

Typical for on-premises Azure DevOps Server accessed via VPN or Windows Auth.

| Variable | Value |
|---|---|
| `DEVOPS_USERNAME` | `DOMAIN\your-username` |
| `DEVOPS_PASSWORD` | Your Windows / Active Directory password |

#### Option 2: Personal Access Token (PAT)

PAT is simpler to configure but may not work if your on-prem server blocks token-based access or requires VPN + NTLM.

To create a PAT: open your DevOps profile → **Personal access tokens** → **New token**.
See: [Microsoft docs - Create a PAT](https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate)

| Variable | Value |
|---|---|
| `DEVOPS_PAT` | Your personal access token |
| `DEVOPS_USERNAME` | *(optional)* Your username |

#### Option 3: OAuth Bearer Token (advanced / CI/CD only)

OAuth Bearer tokens work only if your on-prem Azure DevOps Server has OAuth 2.0 configured - this is uncommon in standard on-prem setups. It is mainly useful for Azure DevOps Services (cloud) or automated pipelines that receive short-lived tokens from an identity provider.

| Variable | Value |
|---|---|
| `DEVOPS_TOKEN` | Your OAuth Bearer token |

> If you are unsure whether OAuth is available, use NTLM or PAT instead.

### Step 5: Install MD4 support (required for NTLM)

NTLM authentication requires the MD4 hash algorithm. Install the `pycryptodome` package to provide it:

```
pip install pycryptodome
```

> This step is only needed for NTLM. If you use PAT or OAuth, you can skip it.

### Step 6: Configure your MCP client

For **VS Code**, use the one-click install buttons below — they pre-configure everything and prompt you for credentials:

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_MCP_Server-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=devops-onprem&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-devops-onpremise%22%5D%2C%22env%22%3A%7B%22DEVOPS_API_URL%22%3A%22%24%7Binput%3Adevops_api_url%7D%22%2C%22DEVOPS_USERNAME%22%3A%22%24%7Binput%3Adevops_username%7D%22%2C%22DEVOPS_PASSWORD%22%3A%22%24%7Binput%3Adevops_password%7D%22%7D%2C%22inputs%22%3A%5B%7B%22id%22%3A%22devops_api_url%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Azure%20DevOps%20API%20URL%20%28https%3A%2F%2Fserver%2Forg%2Fproject%29%22%7D%2C%7B%22id%22%3A%22devops_username%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Username%20%28DOMAIN%5C%5Cusername%29%22%7D%2C%7B%22id%22%3A%22devops_password%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Password%20or%20PAT%22%2C%22password%22%3Atrue%7D%5D%7D) [![Install in VS Code Insiders](https://img.shields.io/badge/VS_Code_Insiders-Install_MCP_Server-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=devops-onprem&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-devops-onpremise%22%5D%2C%22env%22%3A%7B%22DEVOPS_API_URL%22%3A%22%24%7Binput%3Adevops_api_url%7D%22%2C%22DEVOPS_USERNAME%22%3A%22%24%7Binput%3Adevops_username%7D%22%2C%22DEVOPS_PASSWORD%22%3A%22%24%7Binput%3Adevops_password%7D%22%7D%2C%22inputs%22%3A%5B%7B%22id%22%3A%22devops_api_url%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Azure%20DevOps%20API%20URL%20%28https%3A%2F%2Fserver%2Forg%2Fproject%29%22%7D%2C%7B%22id%22%3A%22devops_username%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Username%20%28DOMAIN%5C%5Cusername%29%22%7D%2C%7B%22id%22%3A%22devops_password%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Password%20or%20PAT%22%2C%22password%22%3Atrue%7D%5D%7D&quality=insiders)

For **other clients** (Claude Desktop, Cursor, Windsurf, etc.), add the server manually to your `mcp.json`.

**The `DEVOPS_API_URL` must point to your full project URL:**
```
https://<your-devops-server>/<organization>/<project>
```

#### With NTLM (username + password)

```json
{
  "mcpServers": {
    "devops-onprem": {
      "command": "uvx",
      "args": ["mcp-devops-onpremise"],
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
      "args": ["mcp-devops-onpremise"],
      "env": {
        "DEVOPS_API_URL": "https://your-devops-server/your-organization/your-project",
        "DEVOPS_PAT": "your-personal-access-token"
      }
    }
  }
}
```

> If you used Option B (permanent install), replace `"command": "uvx"` with `"command": "mcp-devops-onpremise"` and remove the `"args"` line.

## Updating

### Check the current installed version

**If you installed permanently (Option B):**

```
mcp-devops-onpremise --version
```

### Check if a newer version is available

Visit the [releases page on GitHub](https://github.com/zwitbaum/mcp-devops-on-prem/releases) or the [CHANGELOG](https://github.com/zwitbaum/mcp-devops-on-prem/blob/main/CHANGELOG.md).

### Update to the latest version

**If you use `uvx` (Option A):** `uvx` always fetches the latest version from PyPI automatically — no action needed.

**If you installed permanently (Option B):**

```
pip install --upgrade mcp-devops-onpremise
```

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
| `devops_get_work_item` | Retrieve a single work item (PBI, bug, task) by its numeric ID | ✅ |

### Wiki

| Tool | Description | Read-only |
|---|---|:---:|
| `devops_wiki_page_get_by_url` | Get wiki page metadata (id, path) and optional content by its URL | ✅ |
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