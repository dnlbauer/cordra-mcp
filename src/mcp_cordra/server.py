"""MCP server for Cordra digital object repository."""

import asyncio

from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("mcp-cordra")


@mcp.tool()
async def ping() -> str:
    """Simple ping tool to test server connectivity."""
    return "pong"


def main() -> None:
    """Main entry point for the MCP server."""
    asyncio.run(mcp.run())


if __name__ == "__main__":
    main()