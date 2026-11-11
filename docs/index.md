# MCP Server for Azure DevOps Server (formerly TFS)

This is a Model Context Protocol (MCP) server for **Azure DevOps Server, formerly known as Team Foundation Server (TFS)**, the self-hosted, on-premises edition of Azure DevOps. It lets AI tools such as Claude, GitHub Copilot, Cursor, and others work directly with your Azure DevOps Server.

> **Not for Azure DevOps Services** (cloud, `dev.azure.com`). For the cloud service, use Microsoft's official [Azure DevOps MCP server](https://github.com/microsoft/azure-devops-mcp).

With this MCP server, you can let your AI assistant work with your Azure DevOps Server data and actions, for example around work items, wiki pages, pull requests, repositories, and related review workflows.

## Why this MCP server is necessary?

AI assistants cannot access external systems and act on external data without tools/connectors. In MCP-based setups, those capabilities are provided through MCP servers.

This MCP server provides that bridge to Azure DevOps Server so your assistant can:

- authenticate against your on-premises environment,
- execute DevOps API calls safely,
- and use structured tools for your day-to-day DevOps workflows.

This project is that bridge layer between your AI agent and your Azure DevOps Server.

Without this MCP server (or another equivalent integration), your assistant usually cannot:

- list repositories, pull requests, and work items from your Azure DevOps Server,
- retrieve commit and file diffs for review workflows,
- read or update wiki pages,
- create or update work items and PR comments using tool calls.

Also, Microsoft states in its [Azure DevOps MCP - FAQ](https://github.com/microsoft/azure-devops-mcp/blob/main/docs/FAQ.md) that their MCP server supports Azure DevOps Services only and they currently do not plan support for Azure DevOps Server. This MCP server fills that gap for Azure DevOps Server, formerly known as Team Foundation Server (TFS).

## What makes this server stand out

One of the most important features of this server is **NTLM authentication** support, which is required by many on-premises and enterprise environments where users authenticate with their Windows domain credentials, either directly or over VPN. Most MCP servers for Azure DevOps target only cloud-hosted Azure DevOps Services with token-based auth and cannot connect to these environments.

This means you can use this server in environments where:

- NTLM is the only supported authentication method on your Azure DevOps Server instance,
- your organization requires VPN access and domain credentials to reach internal systems,
- PAT or OAuth token auth is blocked or not enabled by policy.

## What this server provides

- **NTLM authentication** (Windows domain credentials) for on-prem and VPN-based enterprise environments.
- PAT and OAuth bearer token authentication as alternatives.
- Tooling for Azure DevOps Server workflows, such as pull requests, repositories, work items, wiki pages, and similar scenarios.
- Support for enterprise environments where direct cloud integrations are not possible.

## Documentation

- [Getting Started](./getting-started.md) - Setup steps for installing and configuring this MCP server in your AI client.

## Project

- [GitHub Repository](https://github.com/zwitbaum/mcp-devops-on-prem) - Source code, issues, and releases.
- [PyPI Package](https://pypi.org/project/mcp-devops-onpremise) - Install via pip or uvx.

---

*Community project, not affiliated with or endorsed by Microsoft. Azure DevOps is a trademark of Microsoft.*
