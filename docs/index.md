# MCP DevOps On-Premise

MCP DevOps On-Premise is a Model Context Protocol (MCP) server which allows you to use AI tools, such as Claude, GitHub Copilot, Cursor, and others, directly with your DevOps On-Premise environment.

With this MCP server, you can let your AI assistant work with your DevOps data and actions, for example around work items, wiki pages, pull requests, repositories, and related review workflows.

## Why this MCP server is necessary?

AI assistants cannot access external systems and act on external data without tools/connectors. In MCP-based setups, those capabilities are provided through MCP servers.

This MCP server provides that bridge to DevOps On-Premise so your assistant can:

- authenticate against your on-prem environment,
- execute DevOps API calls safely,
- and use structured tools for your day-to-day DevOps workflows.

This project is that bridge layer between your AI agent and your DevOps Server.

Without this MCP server (or another equivalent integration), your assistant usually cannot:

- list repositories, pull requests, and work items from your on-prem instance,
- retrieve commit and file diffs for review workflows,
- read or update wiki pages,
- create or update work items and PR comments using tool calls.

Also, Microsoft states in its [Azure DevOps MCP - FAQ](https://github.com/microsoft/azure-devops-mcp/blob/main/docs/FAQ.md) that their MCP server supports Azure DevOps Services only and they currently do not plan Azure DevOps On-Prem support. This MCP server fills that gap for on-prem environments.

## What this server provides

- On-prem-friendly authentication options (NTLM, PAT, OAuth bearer token).
- Tooling for DevOps workflows, such as pull requests, repositories, work items, wiki pages, and similar scenarios.
- Support for enterprise environments where direct cloud integrations are not possible.

## Documentation

- [Getting Started](./getting-started.md) - Setup steps for installing and configuring this MCP server in your AI client.
