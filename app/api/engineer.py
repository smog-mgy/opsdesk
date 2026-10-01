"""ch11 工程师工单处理闭环 API。

工单数据在 MySQL tickets 真库:AI 对话页(用户报修→查进度)与工程师页(/engineer,
列表→改状态→填处理人/备注)读写同一张表。状态流转带状态机校验(非法跳转 409),
WebSocket 把状态变更实时推给在线工程师页(刷新即见最新进度)。

工程师页与 AI 对话页分离:用户侧不感知工程师页,工程师侧不感知 AI 会话细节。
"""
import logging

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.db import repository

logger = logging.getLogger(__name__)
router = APIRouter()

# 状态机:待派单→处理中→(待配件|已解决);待配件→(处理中|已解决);已解决为终态
ALL_STATUS = ("待派单", "处理中", "待配件", "已解决")
STATUS_FLOW: dict[str, set[str]] = {
    "待派单": {"处理中", "已解决"},
    "处理中": {"待配件", "已解决"},
    "待配件": {"处理中", "已解决"},
    "已解决": set(),
}

# WebSocket 广播:状态变更推给所有在线工程师页
_ws_clients: set[WebSocket] = set()


async def _broadcast(payload: dict) -> None:
    dead: list[WebSocket] = []
    for ws in _ws_clients:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.discard(ws)


class TicketUpdate(BaseModel):
    status: str | None = Field(default=None, description="目标状态")
    handler: str | None = Field(default=None, description="处理人")
    progress_note: str | None = Field(default=None, description="处理备注/进度")


@router.get("/api/engineer/tickets")
async def list_tickets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    keyword: str | None = None,
) -> dict:
    if status and status not in ALL_STATUS:
        raise HTTPException(status_code=400, detail=f"非法状态:{status}")
    items, total = await repository.list_tickets(
        page=page, size=size, status=status, keyword=keyword
    )
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/api/engineer/tickets/{ticket_no}")
async def ticket_detail(ticket_no: str) -> dict:
    t = await repository.get_ticket(ticket_no)
    if t is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    return t


@router.patch("/api/engineer/tickets/{ticket_no}")
async def update_ticket(ticket_no: str, req: TicketUpdate) -> dict:
    cur = await repository.get_ticket(ticket_no)
    if cur is None:
        raise HTTPException(status_code=404, detail="工单不存在")
    if req.status is not None:
        if req.status not in ALL_STATUS:
            raise HTTPException(status_code=400, detail=f"非法状态:{req.status}")
        if req.status not in STATUS_FLOW[cur["status"]]:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"状态流转非法:「{cur['status']}」→「{req.status}」"
                    f"(合法目标:{_flow_targets(cur['status'])})"
                ),
            )
    updated = await repository.update_ticket_status(
        ticket_no,
        req.status or cur["status"],
        handler=req.handler if req.handler is not None else cur["handler"],
        progress_note=req.progress_note if req.progress_note is not None else cur["progress_note"],
    )
    await _broadcast({"type": "ticket_updated", "ticket": updated})
    logger.info("工程师更新工单 %s → %s(处理人=%s)", ticket_no, updated["status"], updated["handler"])
    return updated


def _flow_targets(status: str) -> list[str]:
    """按业务顺序(ALL_STATUS 下标)排合法流转目标,前端与 409 文案同序。"""
    return sorted(STATUS_FLOW[status], key=lambda s: ALL_STATUS.index(s))


@router.get("/api/engineer/status-flow")
async def status_flow() -> dict:
    return {"states": list(ALL_STATUS), "flow": {k: _flow_targets(k) for k in ALL_STATUS}}


@router.websocket("/api/engineer/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _ws_clients.add(ws)
    try:
        # 服务端单向推送为主;收心跳保持连接,收到即回 pong
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        _ws_clients.discard(ws)
    except Exception:
        _ws_clients.discard(ws)
