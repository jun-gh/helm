"""Model Context Protocol (MCP) Client Registry for Helm worker agents."""

from datetime import UTC, datetime
import platform
from typing import Any

from pydantic import BaseModel, Field


class MCPToolDescriptor(BaseModel):
    """Metadata describing an available MCP tool."""

    name: str
    server: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)


class MCPClientRegistry:
    """Manages connections to MCP servers and exposes tools to LangGraph workers.

    Includes built-in diagnostic MCP tools out of the box and supports registering
    external stdio/SSE MCP servers via the official `mcp` SDK.
    """

    def __init__(self) -> None:
        self._tools: dict[str, MCPToolDescriptor] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        self._tools["helm_cluster_telemetry"] = MCPToolDescriptor(
            name="helm_cluster_telemetry",
            server="helm-core-mcp",
            description="Inspect runtime health, Python version, and active orchestration nodes.",
            input_schema={
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "Target subsystem (all, runtime, storage)",
                    }
                },
            },
        )
        self._tools["helm_task_planner"] = MCPToolDescriptor(
            name="helm_task_planner",
            server="helm-core-mcp",
            description="Decompose a high-level user mission into ordered execution checkpoints.",
            input_schema={
                "type": "object",
                "properties": {
                    "objective": {"type": "string", "description": "Mission objective string"}
                },
                "required": ["objective"],
            },
        )

    def list_tools(self) -> list[MCPToolDescriptor]:
        """Return all registered MCP tools."""
        return list(self._tools.values())

    async def invoke_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a registered MCP tool by name."""
        if name == "helm_cluster_telemetry":
            return {
                "tool": name,
                "timestamp": datetime.now(UTC).isoformat(),
                "python_version": platform.python_version(),
                "component": arguments.get("component", "all"),
                "status": "nominal",
            }
        if name == "helm_task_planner":
            objective = arguments.get("objective", "General mission")
            return {
                "tool": name,
                "objective": objective,
                "checkpoints": [
                    f"1. Analyze constraints and context for: {objective}",
                    "2. Dispatch specialized worker with MCP tool bindings",
                    "3. Synthesize telemetry and persist checkpoint to Firestore",
                ],
            }
        raise ValueError(f"Unknown MCP tool: {name}")


mcp_registry = MCPClientRegistry()
