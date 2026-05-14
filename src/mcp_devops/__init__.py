"""MCP DevOps On-Premise server package."""

__version__ = "0.1.0"

from mcp_devops.shared import mcp
import mcp_devops.tools  # noqa: F401 - registers all tool decorators


def main():
    """Entry point for uvx / uv run / pipx installation."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print(__version__)
        return

    mcp.run()


if __name__ == "__main__":
    main()
