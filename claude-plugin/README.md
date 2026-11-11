# Azure DevOps Server (formerly TFS)

Connects Claude to **Azure DevOps Server, formerly known as Team Foundation Server (TFS)**, the self-hosted, on-premises edition of Azure DevOps, so you can browse repositories, review pull requests and their diffs, search code, manage work items, and read or edit wiki pages in plain language.

*Not for Azure DevOps Services (dev.azure.com).*

The plugin starts the open-source MCP server [`mcp-devops-onpremise`](https://pypi.org/project/mcp-devops-onpremise/) locally on your computer with `uvx`. Source code: [zwitbaum/mcp-devops-on-prem](https://github.com/zwitbaum/mcp-devops-on-prem).

## Requirements

- Claude Code: the terminal, the IDE extensions, or the **Code** tab of the Claude desktop app. The plugin runs a local MCP server and asks for your credentials when you enable it, so it does nothing in claude.ai chat or in Cowork.
- [uv](https://docs.astral.sh/uv/) installed and on your `PATH` (`pip install uv`).
- Network access from your computer to your Azure DevOps Server (company network or VPN).
- An account on that server, using either NTLM (Windows domain username and password) or a Personal Access Token (PAT).

## Setup

When you enable the plugin, Claude asks for:

| Setting | What to enter |
|---|---|
| Azure DevOps Server project URL | `https://<server>/<collection>/<project>`, for example `https://devops.example.com/DefaultCollection/MyProject` |
| Username (NTLM) | `DOMAIN\username`, or empty when you use a PAT |
| Password (NTLM) | Your domain password, or empty when you use a PAT |
| Personal Access Token | Your PAT, or empty when you use username and password |

Fill in **either** username and password **or** a PAT, not both. Passwords and tokens are stored in your system's secure credential store, not in plain-text settings.

## What it can do

- **Repositories:** list and inspect repositories, read files, compare commits and file diffs.
- **Pull requests:** read PRs and comment threads; create or update PRs, reviewers, votes, and comments.
- **Work items:** read, query (WIQL), create, update, link, delete and restore work items and their comments; download attachments.
- **Search:** code, work item and wiki search.
- **Wiki:** read, create, update and delete wiki pages.

Every tool is annotated as read-only or as modifying, so Claude asks before it changes or deletes anything.

## What it runs, sends and stores

- **Runs:** `uvx mcp-devops-onpremise==2.2.0`, which downloads the pinned package from PyPI on first use and runs it as a local process.
- **Sends:** requests only to the Azure DevOps Server URL you configure, authenticated with your credentials. There is no telemetry and no other destination.
- **Stores:** nothing, except when you ask Claude to download a work item attachment to a folder, which writes that file to your disk.

## Privacy policy

See [PRIVACY.md](https://github.com/zwitbaum/mcp-devops-on-prem/blob/main/PRIVACY.md).

## Support

Report issues at [github.com/zwitbaum/mcp-devops-on-prem/issues](https://github.com/zwitbaum/mcp-devops-on-prem/issues).

## License

Apache-2.0, see [LICENSE](LICENSE).
