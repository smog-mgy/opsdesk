"""工单流转 MCP Server（:8102）—— 运维工单助手场景。
查询工单当前处理节点、处理人、预计完成时间。独立进程，由 make mcp-up 拉起。
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ticket_ops")

# 模拟工单流转节点（固定数据，接入真实工单系统时替换为查询逻辑）
TICKET_FLOW = {
    "WO-2026-0001": {"node": "已解决", "assignee": "王工", "eta": "已完成", "detail": "变频器程序故障已修复并回执"},
    "WO-2026-0002": {"node": "处理中", "assignee": "张工", "eta": "2026-09-30", "detail": "电机轴承异响，正在更换"},
    "WO-2026-0003": {"node": "待派单", "assignee": "待分配", "eta": "2026-09-28", "detail": "等待当班工程师接单"},
    "WO-2026-0004": {"node": "待配件", "assignee": "李工", "eta": "2026-10-03", "detail": "等待备件 SP-1003 到货"},
}


@mcp.tool()
def query_ticket_progress(ticket_id: str) -> dict:
    """查询工单流转进度：传入工单号（如 WO-2026-0001），返回当前节点、处理人、预计完成时间。"""
    t = TICKET_FLOW.get(ticket_id.upper())
    if not t:
        return {"found": False, "ticket_id": ticket_id, "message": "未找到该工单，请核对工单号"}
    return {"found": True, "ticket_id": ticket_id.upper(), **t}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.streamable_http_app(), host="127.0.0.1", port=8102)
