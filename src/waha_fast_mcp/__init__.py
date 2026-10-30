"""Single-module MCP server for WAHA (WhatsApp HTTP API)."""

from .server import WahaClient, WahaError, mcp

__all__ = ["WahaClient", "WahaError", "mcp"]
