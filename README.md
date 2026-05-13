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

**Option A - Ephemeral (no permanent install, recommended for most users):**

`uvx` downloads and runs the server on demand. Nothing is permanently installed.

```
uvx mcp-devops-onpremise
```

**Option B - Permanent install:**

```
uv pip install mcp-devops-onpremise
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

Add the server to your MCP client configuration (`mcp.json` for Claude Desktop, Cursor, Windsurf, etc.).

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

> Replace `uvx` with `uv run mcp-devops-onpremise` if you used Option B (permanent install) in Step 3.

## Updating

### Check the current installed version

```
uvx mcp-devops-onpremise --version
```

### Check if a newer version is available

Visit the [releases page on GitHub](https://github.com/your-org/mcp-devops-onpremise/releases) or check PyPI:

```
pip index versions mcp-devops-onpremise
```

### Update to the latest version

**If you use `uvx` (Option A):** `uvx` always fetches the latest version automatically - no action needed.

**If you installed permanently (Option B):**

```
uv pip install --upgrade mcp-devops-onpremise
```

## Available Tools

| Tool | Description |
|---|---|
| `devops_pull_request_get` | Retrieve a pull request by ID |
| `devops_pull_request_create_comment` | Create an inline or general PR comment |
| `devops_pull_request_update_comment` | Update an existing PR comment |
| `devops_pull_request_delete_comment` | Delete a PR comment |
| `devops_repository_list` | List all repositories |
| `devops_repository_get` | Get repository details |
| `devops_repository_commit_changes` | List files changed in a commit |
| `devops_repository_diffs_commits` | Diff between two commits |
| `devops_repository_item_content` | Get raw file content at a commit |
| `devops_get_item_content_diff` | Get line-level diff between two file versions |
| `devops_get_work_item` | Retrieve a work item by ID |
| `devops_wiki_page_get_by_url` | Get wiki page metadata/content by URL |
| `devops_wiki_page_create_or_update` | Create or update a wiki page |
| `devops_wiki_page_update` | Update an existing wiki page |
| `devops_wiki_page_delete` | Delete a wiki page |

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