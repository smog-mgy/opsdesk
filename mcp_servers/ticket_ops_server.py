"""工单流转 MCP Server（:8102）—— 运维工单助手场景。
查询工单当前处理状态、处理人、优先级、处理备注、更新时间。独立进程，由 make mcp-up 拉起。
ch11 改造:数据源从固定 mock 切到 MySQL 真库(tickets 表),与工程师工单台、内置 query_ticket 同源。
"""
import logging
import os

from mcp.server.fastmcp import FastMCP
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

mcp = FastMCP("ticket_ops")

# 真库:与 app 同库(tickets)。测试可经 OPSDESK_MCP_DB_URL 覆盖指向测试库。
_DB_URL = os.getenv("OPSDESK_MCP_DB_URL") or settings.database_url
_engine = create_async_engine(_DB_URL, pool_pre_ping=True)
_session = async_sessionmaker(_engine, expire_on_commit=False)


@mcp.tool()
async def query_ticket_progress(ticket_id: str) -> dict:
    """查询工单流转进度：传入工单号（如 T20261001144639001），返回当前状态、处理人、优先级、处理备注、更新时间。"""
    tid = (ticket_id or "").strip().upper()
    async with _session() as s:
        row = (await s.execute(
            text("SELECT ticket_no, status, priority, handler, progress_note, updated_at "
                 "FROM tickets WHERE ticket_no = :tid"),
            {"tid": tid},
        )).mappings().first()
    if row is None:
        return {"found": False, "ticket_id": tid, "message": "未找到该工单，请核对工单号"}
    return {
        "found": True,
        "ticket_id": tid,
        "node": row["status"],
        "assignee": row["handler"] or "待分配",
        "priority": row["priority"],
        "eta": "",
        "detail": row["progress_note"] or "",
        "updated_at": str(row["updated_at"]),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.streamable_http_app(), host="127.0.0.1", port=8102)
