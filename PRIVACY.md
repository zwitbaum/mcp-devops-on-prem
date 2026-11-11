# Privacy Policy

_Last updated: 2026-11-11_

This policy covers the open-source MCP server `mcp-devops-onpremise` and the "Azure DevOps Server (formerly TFS)" Claude plugin that launches it (together, "the software"), published at https://github.com/zwitbaum/mcp-devops-on-prem.

## Data collection

The software runs entirely on your own computer. The author does not operate any server for it and does not collect, receive or see any of your data. There is no telemetry, analytics, crash reporting or tracking.

## Data usage and storage

- **Configuration:** You provide your Azure DevOps Server URL and credentials (username and password, or a Personal Access Token, or an OAuth bearer token). They are used only to authenticate requests to that server. When you use the Claude plugin, passwords and tokens are kept by Claude in your system's secure credential store; when you configure the server manually, they stay wherever you put them (for example your MCP client configuration or environment variables).
- **DevOps content:** Repository files, pull requests, work items, wiki pages and search results are fetched from your server only when a tool is called, and returned to the AI client that called it. The software does not cache or persist this content.
- **Files on disk:** The software writes a file to your disk only when you ask it to save a work item attachment to a folder.

## Third-party sharing

The software sends requests only to the Azure DevOps Server URL you configure. It does not share data with the author or any other third party. Content that the software returns to your AI client (for example Claude) is then handled under that client provider's own privacy policy. Installing the software via `uvx` or `pip` downloads the package from PyPI, which is subject to PyPI's policies.

## Data retention

The software keeps no data after a tool call completes and has no retention of its own. Credentials remain in your configuration until you remove them. Attachment files you chose to save remain on your disk until you delete them.

## Contact

Questions about this policy: open an issue at https://github.com/zwitbaum/mcp-devops-on-prem/issues.
