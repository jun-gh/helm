"""MCP tool discovery and inspection endpoints."""

from fastapi import APIRouter

from app.mcp_layer.client import MCPToolDescriptor, mcp_registry

router = APIRouter(prefix="/tools", tags=["mcp-tools"])


@router.get("", response_model=list[MCPToolDescriptor])
async def list_mcp_tools() -> list[MCPToolDescriptor]:
    """List all registered Model Context Protocol (MCP) tools available to workers."""
    return mcp_registry.list_tools()
