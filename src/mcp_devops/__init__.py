"""MCP DevOps On-Premise server package."""

from __future__ import annotations

import argparse
import os

__version__ = "2.0.0"

from mcp_devops.shared import mcp, validate_configuration
import mcp_devops.tools  # noqa: F401 - registers all tool decorators


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the MCP DevOps On-Premise server.")
    parser.add_argument("--version", "-V", action="store_true", help="Show package version and exit.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http", "http"),
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="Transport to use. Defaults to MCP_TRANSPORT or stdio.",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "127.0.0.1"),
        help="Host/interface to bind for HTTP transport. Defaults to MCP_HOST or 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8000")),
        help="Port to bind for HTTP transport. Defaults to MCP_PORT or 8000.",
    )
    parser.add_argument(
        "--path",
        default=os.getenv("MCP_PATH"),
        help="Optional HTTP mount path when supported by FastMCP.",
    )
    return parser


def main() -> None:
    """Entry point for uvx / uv run / pipx installation."""
    args = _build_parser().parse_args()

    if args.version:
        print(__version__)
        return

    validate_configuration()

    transport = "streamable-http" if args.transport == "http" else args.transport
    run_kwargs: dict[str, object] = {"transport": transport}
    if transport == "streamable-http":
        run_kwargs["host"] = args.host
        run_kwargs["port"] = args.port
        if args.path:
            run_kwargs["path"] = args.path

    mcp.run(**run_kwargs)


if __name__ == "__main__":
    main()
