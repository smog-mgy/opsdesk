import logging

from app.tools import mcp_client, registry
from app.tools.registry import ToolSpec


class _FakeTool:
    def __init__(self, name):
        self.name = name
        self.description = f"{name} 描述"
        self.args_schema = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}


async def test_mcp_connections_include_ops_servers():
    """运维版 MCP:备件库存(:8101) + 工单流转(:8102) 两路连接在册。"""
    conns = mcp_client._connections()
    assert set(conns) == {"spare_part", "ticket_ops"}
    assert conns["spare_part"]["url"].endswith("/mcp")
    assert conns["ticket_ops"]["url"].endswith("/mcp")


async def test_fetch_mcp_specs_marks_source_and_permission(monkeypatch):
    """MCP 工具标记 source=mcp,按我们侧规则只读放行(不在 WRITE_TOOLS)。"""
    async def fake_get_tools(*, server_name=None):
        if server_name == "spare_part":
            return [_FakeTool("query_spare_part")]
        return [_FakeTool("query_ticket_progress")]
    monkeypatch.setattr(mcp_client, "_get_tools_of", fake_get_tools)
    specs = await mcp_client.fetch_mcp_specs()
    by = {s.name: s for s in specs}
    assert set(by) == {"query_spare_part", "query_ticket_progress"}
    assert by["query_spare_part"].source == "mcp" and by["query_spare_part"].mcp_server == "spare_part"
    assert by["query_ticket_progress"].source == "mcp" and by["query_ticket_progress"].mcp_server == "ticket_ops"
    assert all(s.permission == "read" for s in specs)          # 我们侧规则:MCP 不在写清单→只读
