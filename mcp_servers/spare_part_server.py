"""备件库存 MCP Server（:8101）—— 运维工单助手场景。
查询备件库存余量、到货时间、领用审批状态。独立进程，由 make mcp-up 拉起。
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("spare_part")

# 模拟备件台账（固定数据，接入真实 ERP 时替换为查询逻辑）
SPARE_PARTS = {
    "SP-1001": {"name": "接触器 CJX2-2510", "stock": 5, "eta": "现货", "status": "在库"},
    "SP-1002": {"name": "保险丝 RT18-32", "stock": 20, "eta": "现货", "status": "在库"},
    "SP-1003": {"name": "电机风扇叶", "stock": 0, "eta": "2026-10-02", "status": "缺货采购中"},
    "SP-1004": {"name": "变频器散热风扇", "stock": 2, "eta": "现货", "status": "在库"},
    "SP-1005": {"name": "温控器探头", "stock": 8, "eta": "现货", "status": "在库"},
}


@mcp.tool()
def query_spare_part(spare_no: str) -> dict:
    """查询备件库存：传入备件编号（如 SP-1001），返回库存余量、到货时间与领用状态。"""
    p = SPARE_PARTS.get(spare_no.upper())
    if not p:
        return {"found": False, "spare_no": spare_no, "message": "未找到该备件，请核对编号"}
    return {"found": True, "spare_no": spare_no.upper(), **p}


@mcp.tool()
def query_spare_list(keyword: str = "") -> dict:
    """查询备件清单：可按名称关键词过滤（如「接触器」「风扇」），返回所有匹配备件。"""
    kw = keyword.strip()
    items = []
    for no, p in SPARE_PARTS.items():
        if not kw or kw in p["name"]:
            items.append({"spare_no": no, **p})
    return {"count": len(items), "items": items}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.streamable_http_app(), host="127.0.0.1", port=8101)
