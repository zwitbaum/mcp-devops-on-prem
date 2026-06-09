# Getting Started with MCP DevOps On-Premise

This guide provides everything you need to install and start using MCP DevOps On-Premise with your AI assistant.

## Prerequisites

Before you begin, make sure the following are ready:

- [ ] Python 3.10 or later installed
- [ ] uv installed
- [ ] Your on-prem Azure DevOps Server project URL (format: `https://<server>/<organization>/<project>`)
- [ ] Credentials for one of the supported [authentication methods](#authentication)

### Python 3.10 or later

First, check whether Python is already installed. Open a Command Prompt (`cmd`) or PowerShell and enter:

```
python --version
```

or the short form:

```
python -V
```

Both commands display the installed Python version. If Python 3.10 or later is shown, you can skip the installation below.

If Python is not installed or the version is too old, download it from [python.org](https://www.python.org/downloads/).

> **Windows:** Check **"Add Python to PATH"** during installation.  
> `pip` is included with Python, so no separate install is needed.

### uv

`uv` is a fast Python package manager that powers the one-click installs and the ephemeral server launch.

> **Windows users:** Open **Command Prompt** (`cmd`) or **PowerShell** to run all commands in this guide.

First, check whether uv is already installed:

```
uv --version
```

This will return the version number if uv is already available. If the command is not found, install uv:

```
pip install uv
```

> More info: [uv documentation](https://github.com/astral-sh/uv)

## Authentication

The server supports three authentication methods. If you are unsure which one works in your environment, **start with NTLM** because it is the most common for on-prem/VPN setups. NTLM is usually the simplest first setup and is also the fallback if other methods do not work. Test the server with NTLM first, then switch to PAT or OAuth if your environment supports them.

| Method | When to use |
|---|---|
| NTLM (username + password) | Corporate network, VPN, Windows / Active Directory auth. Recommended for first setup and fallback. |
| PAT (Personal Access Token) | Use when PATs are enabled and allowed. Good when you do not want to store your account password in config. |
| OAuth Bearer Token | Advanced / CI/CD only; requires OAuth 2.0 configured on your DevOps Server |

### Option 1: NTLM (Username + Password, recommended for on-prem/VPN)

Typical for on-premises Azure DevOps Server accessed via VPN or Windows Authentication.

| Variable | Value |
|---|---|
| `DEVOPS_USERNAME` | `DOMAIN\your-username` |
| `DEVOPS_PASSWORD` | Your Windows / Active Directory password |

### Option 2: Personal Access Token (PAT)

PAT is simpler to configure but may not work if your on-prem server blocks token-based access or requires VPN + NTLM.

To create a PAT: open your DevOps profile → **Personal access tokens** → **New token**.  
See: [Microsoft docs: Create a PAT](https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate)

Important PAT notes:

- PATs can expire.
- PAT creation and token-based authentication can be disabled by server or organization policy.
- Some environments still require VPN + NTLM, even when PAT exists.

| Variable | Value |
|---|---|
| `DEVOPS_PAT` | Your personal access token |
| `DEVOPS_USERNAME` | *(optional)* Your username |

### Option 3: OAuth Bearer Token (advanced / CI/CD only)

OAuth Bearer tokens work only if your on-prem Azure DevOps Server has OAuth 2.0 configured, which is uncommon in standard on-prem setups. This method is mainly useful for automated pipelines that receive short-lived tokens from an identity provider.

Where to get an OAuth bearer token:

- From your organization's OAuth 2.0 flow configured by your DevOps/Identity administrators.
- In CI/CD, from your pipeline runtime or secret injection process when your platform provides an OAuth token.

If you do not know how to obtain this token in your environment, ask your DevOps administrator and use NTLM first.

| Variable | Value |
|---|---|
| `DEVOPS_TOKEN` | Your OAuth Bearer token |

> If you are unsure whether OAuth is available in your environment, use NTLM or PAT instead.

## Installation Options

### Quick Install

Click one of the buttons below to install directly in your IDE. You will be prompted for credentials:

[![Install in VS Code](https://img.shields.io/badge/Install_in-VS_Code-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=devops-onprem&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-devops-onpremise%40latest%22%5D%2C%22env%22%3A%7B%22DEVOPS_API_URL%22%3A%22%24%7Binput%3Adevops_api_url%7D%22%2C%22DEVOPS_USERNAME%22%3A%22%24%7Binput%3Adevops_username%7D%22%2C%22DEVOPS_PASSWORD%22%3A%22%24%7Binput%3Adevops_password%7D%22%7D%2C%22inputs%22%3A%5B%7B%22id%22%3A%22devops_api_url%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Azure%20DevOps%20API%20URL%20%28https%3A%2F%2Fserver%2Forg%2Fproject%29%22%7D%2C%7B%22id%22%3A%22devops_username%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Username%20%28DOMAIN%5C%5Cusername%29%22%7D%2C%7B%22id%22%3A%22devops_password%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Password%20or%20PAT%22%2C%22password%22%3Atrue%7D%5D%7D)
[![Install in VS Code Insiders](https://img.shields.io/badge/Install_in-VS_Code_Insiders-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=devops-onprem&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-devops-onpremise%40latest%22%5D%2C%22env%22%3A%7B%22DEVOPS_API_URL%22%3A%22%24%7Binput%3Adevops_api_url%7D%22%2C%22DEVOPS_USERNAME%22%3A%22%24%7Binput%3Adevops_username%7D%22%2C%22DEVOPS_PASSWORD%22%3A%22%24%7Binput%3Adevops_password%7D%22%7D%2C%22inputs%22%3A%5B%7B%22id%22%3A%22devops_api_url%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Azure%20DevOps%20API%20URL%20%28https%3A%2F%2Fserver%2Forg%2Fproject%29%22%7D%2C%7B%22id%22%3A%22devops_username%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Username%20%28DOMAIN%5C%5Cusername%29%22%7D%2C%7B%22id%22%3A%22devops_password%22%2C%22type%22%3A%22promptString%22%2C%22description%22%3A%22Password%20or%20PAT%22%2C%22password%22%3Atrue%7D%5D%7D&quality=insiders)
[![Install in Cursor](https://img.shields.io/badge/Install_in-Cursor-000000?style=flat-square&logoColor=white)](https://cursor.com/en/install-mcp?name=devops-onprem&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJtY3AtZGV2b3BzLW9ucHJlbWlzZUBsYXRlc3QiXSwiZW52Ijp7fX0=)

### Manual Installation

The following AI tools support manual MCP server configuration. Select your tool for step-by-step instructions:

<details>
<summary>VS Code</summary>

Follow the MCP install [guide](https://code.visualstudio.com/docs/copilot/chat/mcp-servers#_add-an-mcp-server), then use the [Configuration](#configuration) below.

After installation, the devops-onprem MCP server will be available for use with your GitHub Copilot agent in VS Code.
</details>

<details>
<summary>VS Code Insiders</summary>

Follow the MCP install [guide](https://code.visualstudio.com/docs/copilot/chat/mcp-servers#_add-an-mcp-server), then use the [Configuration](#configuration) below.

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
   - **Command (with optional arguments)**: `uvx mcp-devops-onpremise@latest`
   - **Environment Variables**: add as described in the [Configuration](#configuration) section below.
6. Click "Save" to add the server

For detailed instructions, see the [Visual Studio MCP documentation](https://learn.microsoft.com/visualstudio/ide/mcp-servers).
</details>

<details>
<summary>Cursor</summary>

Go to `Cursor Settings` -> `MCP` -> `Add new MCP Server`. Name to your liking, use `command` type with the command from the [Configuration](#configuration) below. You can also verify the config or add arguments via clicking `Edit`.
</details>

<details>
<summary>Goose</summary>

Go to `Advanced settings` -> `Extensions` -> `Add custom extension`. Name to your liking, use type `STDIO`, and set the `command` from the [Configuration](#configuration) below. Click "Add Extension".
</details>

<details>
<summary>LM Studio</summary>

Go to `Program` in the right sidebar -> `Install` -> `Edit mcp.json`. Use the [Configuration](#configuration) below.
</details>

<details>
<summary>Amp</summary>

Add via the Amp VS Code extension settings screen or by updating your `settings.json` file:

```json
"amp.mcpServers": {
  "devops-onprem": {
    "command": "uvx",
    "args": [
      "mcp-devops-onpremise@latest"
    ],
    "env": {}
  }
}
```

**Amp CLI Setup:**

```bash
amp mcp add devops-onprem -- uvx mcp-devops-onpremise@latest
```
</details>

<details>
<summary>Claude Code</summary>

Use the Claude Code CLI to add the MCP server:

```bash
claude mcp add devops-onprem uvx mcp-devops-onpremise@latest
```
</details>

<details>
<summary>Claude Desktop</summary>

Follow the MCP install [guide](https://modelcontextprotocol.io/quickstart/user), then use the [Configuration](#configuration) below.
</details>

<details>
<summary>Codex</summary>

Create or edit the configuration file `~/.codex/config.toml` and add:

```toml
[mcp_servers.devops-onprem]
command = "uvx"
args = ["mcp-devops-onpremise@latest"]
```

For more information, see the [Codex MCP documentation](https://github.com/openai/codex/blob/main/codex-rs/config.md#mcp_servers).
</details>

<details>
<summary>Gemini CLI</summary>

Follow the MCP install [guide](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md#configure-the-mcp-server-in-settingsjson), then use the [Configuration](#configuration) below.
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
        "mcp-devops-onpremise@latest"
      ],
      "enabled": true
    }
  }
}
```
</details>

<details>
<summary>Qodo Gen</summary>

Open [Qodo Gen](https://docs.qodo.ai/qodo-documentation/qodo-gen) chat panel in VSCode or IntelliJ → Connect more tools → + Add new MCP → Paste the [Configuration](#configuration) below.

Click Save.
</details>

<details>
<summary>Warp</summary>

Go to `Settings` -> `AI` -> `Manage MCP Servers` -> `+ Add` to [add an MCP Server](https://docs.warp.dev/knowledge-and-collaboration/mcp#adding-an-mcp-server). Use the [Configuration](#configuration) below.

Alternatively, use the slash command `/add-mcp` in the Warp prompt and paste the [Configuration](#configuration) below.
</details>

<details>
<summary>Windsurf</summary>

Follow Windsurf MCP [documentation](https://docs.windsurf.com/windsurf/cascade/mcp). Use the [Configuration](#configuration) below.
</details>

<details>
<summary>GitHub Copilot CLI</summary>

GitHub Copilot CLI supports adding MCP servers interactively and through a config file.

**Option 1: Interactive setup with `/mcp add`**

1. Open GitHub Copilot CLI in interactive mode.
2. Run `/mcp add`.
3. Enter **Server Name**: `devops-onprem`.
4. Choose **Server Type**: `STDIO` for command-based servers.
5. Fill in command/url settings from the [Configuration](#configuration) below and set **Tools** to `*`.
6. Press `Ctrl+S` to save.

**Option 2: Edit `~/.copilot/mcp-config.json`**

Use the [Configuration](#configuration) below.

For more information, see the [GitHub Copilot CLI MCP documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers).
</details>

<details>
<summary>GitHub Copilot Coding Agent</summary>

GitHub Copilot Coding Agent can use MCP servers to extend its capabilities. Add the [Configuration](#configuration) below to your repository settings under **Copilot > Coding agent**. The `"tools": ["*"]` setting enables all available tools.

For more information, see the [GitHub Copilot Coding Agent MCP documentation](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/extend-coding-agent-with-mcp).
</details>

### Standalone Server Installation (optional)

In most cases you do not need to install the server separately because the IDE integrations above handle this automatically via `uvx`. If you need to run or test the server outside an IDE:

**Ephemeral (recommended, no permanent install):**

```
uvx mcp-devops-onpremise@latest
```

**Permanent install:**

```
pip install mcp-devops-onpremise
```

## Configuration

The `DEVOPS_API_URL` must point to your full project URL:

```
https://<your-devops-server>/<organization>/<project>
```

### With NTLM (username + password)

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

### With PAT

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

### With OAuth Bearer Token

```json
{
  "mcpServers": {
    "devops-onprem": {
      "command": "uvx",
      "args": ["mcp-devops-onpremise@latest"],
      "env": {
        "DEVOPS_API_URL": "https://your-devops-server/your-organization/your-project",
        "DEVOPS_TOKEN": "your-oauth-bearer-token"
      }
    }
  }
}
```

> If you used a permanent install, replace `"command": "uvx"` with `"command": "mcp-devops-onpremise"` and remove the `"args"` line.

## Start and Validate

After saving your MCP configuration:

1. Start or reload your MCP-enabled AI client.
2. Ensure the `devops-onprem` server appears in the available tools list.
3. Run a simple read-only prompt to confirm, for example:
   - *list repositories in this project*
   - *get pull request x from repo y*
   - *get work item x*

If tools are visible and respond, setup is complete.

## Troubleshooting

### MD4 Support (NTLM only)

NTLM authentication requires the MD4 hash algorithm, which is not included in all Python environments. If you encounter an MD4-related error, install `pycryptodome`:

```
pip install pycryptodome
```

> Skip this step if you use PAT or OAuth.
