"""MCP DevOps On-Premise server package."""

from mcp_devops.shared import mcp
import mcp_devops.tools  # noqa: F401 - registers all tool decorators


def main():
    """Entry point for uvx / uv run / pipx installation."""
    mcp.run()


if __name__ == "__main__":
    main()
