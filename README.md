<div align="center">

# MCP DevOps On-Premise

Model Context Protocol [MCP](https://modelcontextprotocol.io/) server for **on-premises Azure DevOps** that lets AI assistants browse repositories, review pull requests, manage work items, and interact with wikis.

[![License: MIT](https://img.shields.io/badge/license-Apache%20License%202.0-blue)](https://opensource.org/licenses/apache-2.0)
[![PyPI - Version](https://img.shields.io/pypi/v/mcp-devops-onpremise)](https://pypi.org/project/mcp-devops-onpremise)

<div class="toc">
  <a href="#overview">Overview</a> •  
  <a href="#getting-started">Getting Started</a> •
  <a href="#installation-guide">Installation Guide</a> •
  <a href="#updating">Updating</a> •
  <a href="#available-tools">Available Tools</a> •
  <a href="#development">Development</a>
</div>

</div>


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

## Getting Started

### Quick Install

**Prerequisites:** [Python 3.10+](#prerequisites) and [uv](#uv) are required. If not yet installed, see [Prerequisites](#prerequisites) in the Installation Guide below.

Click one of the buttons below to install directly in your IDE — you will be prompted for credentials:

[![Install in VS Code](https://img.shields.io/badge/Install_in-VS_Code-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=devops-onprem&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-devops-onpremise%22%5D%2C%22env%22%3A%7B%22DEVOPS_API_URL%22%3A%22%24%7Binput%3Adevops_api_url%7D%22%2C%22DEVOPS_USERNAME%22%3A%22%24%7Binput%3Adevops_username%7D%22%2C%22DEVOPS_PASSWORD%22%3A%22%24%7Binput%3Adevops_password%7D%22%7D%2C%22inputs%22%3A%5B%7B%22id%22%3A%22devops_api_url%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Azure%20DevOps%20API%20URL%20%28https%3A%2F%2Fserver%2Forg%2Fproject%29%22%7D%2C%7B%22id%22%3A%22devops_username%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Username%20%28DOMAIN%5C%5Cusername%29%22%7D%2C%7B%22id%22%3A%22devops_password%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Password%20or%20PAT%22%2C%22password%22%3Atrue%7D%5D%7D)
[![Install in VS Code Insiders](https://img.shields.io/badge/Install_in-VS_Code_Insiders-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=devops-onprem&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-devops-onpremise%22%5D%2C%22env%22%3A%7B%22DEVOPS_API_URL%22%3A%22%24%7Binput%3Adevops_api_url%7D%22%2C%22DEVOPS_USERNAME%22%3A%22%24%7Binput%3Adevops_username%7D%22%2C%22DEVOPS_PASSWORD%22%3A%22%24%7Binput%3Adevops_password%7D%22%7D%2C%22inputs%22%3A%5B%7B%22id%22%3A%22devops_api_url%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Azure%20DevOps%20API%20URL%20%28https%3A%2F%2Fserver%2Forg%2Fproject%29%22%7D%2C%7B%22id%22%3A%22devops_username%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Username%20%28DOMAIN%5C%5Cusername%29%22%7D%2C%7B%22id%22%3A%22devops_password%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Password%20or%20PAT%22%2C%22password%22%3Atrue%7D%5D%7D&quality=insiders)
[![Install in Cursor](https://img.shields.io/badge/Install_in-Cursor-000000?style=flat-square&logoColor=white)](https://cursor.com/en/install-mcp?name=devops-onprem&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJtY3AtZGV2b3BzLW9ucHJlbWlzZSJdLCJlbnYiOnt9fQ==)

For other platforms, see [Manual Installation](#manual-installation) below.


### Manual Installation

> For the server command and environment variable settings used in the steps below, see [Configuration](#configuration) in the Installation Guide.

<details>
<summary>VS Code</summary>

Follow the MCP install [guide](https://code.visualstudio.com/docs/copilot/chat/mcp-servers#_add-an-mcp-server), use the [configuration](#configuration) below. 

After installation, the devops-onprem MCP server will be available for use with your GitHub Copilot agent in VS Code.
</details>

<details>
<summary>VS Code Insiders</summary>

Follow the MCP install [guide](https://code.visualstudio.com/docs/copilot/chat/mcp-servers#_add-an-mcp-server), use the [configuration](#configuration) below.

After installation, the devops-onprem MCP server will be available for use with your GitHub Copilot agent in VS Code Insiders.
</details>

<details>
<summary>Visual Studio</summary>

1. Open Visual Studio
2. Navigate to the GitHub Copilot Chat window
3. Click the tools icon (🛠️) in the chat toolbar
4. Click the + "Add Custom MCP Server" button to open the "Configure MCP server" dialog
5. Fill in the configuration:
   - **Server ID**: `devops-onprem`
   - **Type**: Select `stdio` from the dropdown
   - **Command (with optional arguments)**: `uvx mcp-devops-onpremise`
   - **Envisronment Variables**: add like described in the Configuration chapter.
6. Click "Save" to add the server

For detailed instructions, see the [Visual Studio MCP documentation](https://learn.microsoft.com/visualstudio/ide/mcp-servers).
</details>

<details>
<summary>Cursor</summary>

Go to `Cursor Settings` -> `MCP` -> `Add new MCP Server`. Name to your liking, use `command` type with the command from the [configuration](#configuration) below. You can also verify config or add command like arguments via clicking `Edit`.
</details>

<details>
<summary>Goose</summary>

Go to `Advanced settings` -> `Extensions` -> `Add custom extension`. Name to your liking, use type `STDIO`, and set the `command` from the [configuration](#configuration) below. Click "Add Extension".
</details>

<details>
<summary>LM Studio</summary>

Go to `Program` in the right sidebar -> `Install` -> `Edit mcp.json`. Use the [configuration](#configuration) below.
</details>

<details>
<summary>Amp</summary>

Add via the Amp VS Code extension settings screen or by updating your settings.json file:

```json
"amp.mcpServers": 
  "devops-onprem": {
    "command": "uvx",
    "args": [
      "mcp-devops-onpremise"
    ],
    "env": {}
  }

```

**Amp CLI Setup:**

Add via the `amp mcp add` command below:

```bash
amp mcp add devops-onprem -- uvx mcp-devops-onpremise
```
</details>

<details>
<summary>Claude Code</summary>

Use the Claude Code CLI to add the devops-onprem MCP server:

```bash
claude mcp add devops-onprem uvx mcp-devops-onpremise
```
</details>

<details>
<summary>Claude Desktop</summary>

Follow the MCP install [guide](https://modelcontextprotocol.io/quickstart/user), use the [configuration](#configuration) below.
</details>

<details>
<summary>Codex</summary>

Create or edit the configuration file `~/.codex/config.toml` and add:

```toml
[mcp_servers.devops-onprem]
command = "uvx"
args = ["mcp-devops-onpremise"]
```

For more information, see the [Codex MCP documentation](https://github.com/openai/codex/blob/main/codex-rs/config.md#mcp_servers).
</details>

<details>
<summary>Gemini CLI</summary>

Follow the MCP install [guide](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md#configure-the-mcp-server-in-settingsjson), use the [configuration](#configuration) below.
</details>

<details>
<summary>OpenCode</summary>

Follow the MCP Servers [documentation](https://opencode.ai/docs/mcp-servers/). For example in `~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "devops-onprem": {
      "type": "local",
      "command": [
        "uvx",
        "mcp-devops-onpremise"
      ],
      "enabled": true
    }
  }
}
```
</details>

<details>
<summary>Qodo Gen</summary>

Open [Qodo Gen](https://docs.qodo.ai/qodo-documentation/qodo-gen) chat panel in VSCode or IntelliJ → Connect more tools → + Add new MCP → Paste the [configuration](#configuration) below.

Click Save.
</details>

<details>
<summary>Warp</summary>

Go to `Settings` -> `AI` -> `Manage MCP Servers` -> `+ Add` to [add an MCP Server](https://docs.warp.dev/knowledge-and-collaboration/mcp#adding-an-mcp-server). Use the [configuration](#configuration) below.

Alternatively, use the slash command `/add-mcp` in the Warp prompt and paste the [configuration](#configuration) below.
</details>

<details>
<summary>Windsurf</summary>

Follow Windsurf MCP [documentation](https://docs.windsurf.com/windsurf/cascade/mcp). Use the [configuration](#configuration) below.
</details>

<details>
<summary>GitHub Copilot CLI</summary>

GitHub Copilot CLI supports adding MCP servers interactively and through a config file.

#### Option 1: Interactive setup with `/mcp add`

1. Open GitHub Copilot CLI in interactive mode.
2. Run `/mcp add`.
3. Enter **Server Name**: `devops-onprem`.
4. Choose **Server Type**:
   - `STDIO` for command-based servers
   - `HTTP` for remote servers
5. Fill in command/url settings from the [configuration](#configuration) below and set **Tools** to `*`.
6. Press `Ctrl+S` to save.

#### Option 2: Edit `~/.copilot/mcp-config.json`

Use the [configuration](#configuration) below.

For more information, see the [GitHub Copilot CLI MCP documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers).
</details>

<details>
<summary>GitHub Copilot Coding Agent</summary>

GitHub Copilot Coding Agent can use MCP servers to extend its capabilities. Use the [configuration](#configuration) below — add it to your repository settings under **Copilot > Coding agent**.

Add this configuration to your repository settings under **Copilot > Coding agent**. The `"tools": ["*"]` setting enables all available tools from the MCP server.

For more information, see the [GitHub Copilot Coding Agent MCP documentation](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/extend-coding-agent-with-mcp).
</details>


## Installation Guide

### Prerequisites

#### Python 3.10 or later

If Python is not installed on your machine, download it from [python.org](https://www.python.org/downloads/).

> **Windows:** Check **"Add Python to PATH"** during installation.  
> `pip` is included with Python — no separate install needed.

#### uv

`uv` is a fast Python package manager that powers the one-click installs and the ephemeral server launch.

> **Windows users:** Open **Command Prompt** (`cmd`) or **PowerShell** to run all commands in this guide.

```
pip install uv
```

> More info: [uv documentation](https://github.com/astral-sh/uv)

### Standalone Server Installation (optional)

In most cases you do not need to install the server separately — the IDE integrations in [Getting Started](#getting-started) handle this automatically via `uvx`. If you need to run or test the server outside an IDE:

**Ephemeral (recommended, no permanent install):**

```
uvx mcp-devops-onpremise
```

**Permanent install:**

```
pip install mcp-devops-onpremise
```

### Authentication

The server supports three authentication methods. **Start with NTLM (username + password) if you connect via VPN or are on a corporate network. Use PAT if it is available and works in your environment.**

#### Option 1: Username + Password (NTLM — most common for on-prem/VPN)

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

OAuth Bearer tokens work only if your on-prem Azure DevOps Server has OAuth 2.0 configured — uncommon in standard on-prem setups. Mainly useful for Azure DevOps Services (cloud) or automated pipelines that receive short-lived tokens from an identity provider.

| Variable | Value |
|---|---|
| `DEVOPS_TOKEN` | Your OAuth Bearer token |

> If you are unsure whether OAuth is available, use NTLM or PAT instead.

### MD4 Support (NTLM only, optional)

NTLM authentication requires the MD4 hash algorithm, which is not included in all Python environments. If you encounter an MD4-related error, install `pycryptodome`:

```
pip install pycryptodome
```

> Skip this step if you use PAT or OAuth.

### Configuration

The `DEVOPS_API_URL` must point to your full project URL:
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

> If you used a permanent install, replace `"command": "uvx"` with `"command": "mcp-devops-onpremise"` and remove the `"args"` line.

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