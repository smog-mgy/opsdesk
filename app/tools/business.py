"""工单数据源(ch11 起切真库)。

历史:本模块原为纯 mock 数据源(随机种子固定 → 同键稳定),ch08 起工具实现迁至
app/tools/builtin/,本模块只留被 graph 节点(fetch_ticket / agent_tools)与 builtin
工具(query_ticket)共用的快照/归属/列表函数。

ch11:工程师工单处理闭环后,工单数据切换到 MySQL 真库(tickets + conversations,
报修人经 conversation_id join 取得)。函数签名保持不变,调用方(graph 节点、工具)
无感切换;内部实现从「随机生成」改为「真库读写」,新增 async。

业务域:企业设备运维工单。工单号真库格式 TYYYYMMDDHHMMSSnnn。
query_device 设备台账仍在 builtin 内演示(不落库),不受本模块影响。
"""
import re


def _extract_device(text: str) -> str:
    """从问题描述尽力提取设备(括号型号或连字符编号),展示用,提取不到留空。"""
    m = re.search(r"[（(]([A-Za-z0-9]+[-][A-Za-z0-9]+)[）)]", text or "")
    if m:
        return m.group(1)
    m = re.search(r"[A-Za-z]{2,}\d{3,}", text or "")
    return m.group(0) if m else ""


def _extract_line(text: str) -> str:
    """从问题描述尽力提取产线(如 3号包装),展示用,提取不到留空。"""
    m = re.search(r"\d+号[\u4e00-\u9fff]*?线", text or "")
    return m.group(0) if m else ""


async def ticket_snapshot(ticket_id: str) -> dict | None:
    """工单快照(真库)。query_ticket 工具与 fetch_ticket 节点同源。查不到返回 None。"""
    from app.db import repository  # 延迟 import,避免与 tools 包环引用
    t = await repository.get_ticket(ticket_id)
    if t is None:
        return None
    return {
        "ticket_id": t["ticket_no"],
        "status": t["status"],
        "priority": t["priority"],
        "handler": t["handler"] or "",
        "progress_note": t["progress_note"] or "",
        "description": t["description"],
        "ticket_type": t["ticket_type"],
        "submitted_at": (t["created_at"] or "")[:19].replace("T", " "),
        "updated_at": t["updated_at"],
        "device": _extract_device(t["description"]),
        "line": _extract_line(t["description"]),
        "fault_type": "",
        "assignee": t["handler"] or "",
    }


async def owns_ticket(user_id: str, ticket_id: str) -> bool:
    """这张工单是不是这个人提交的(真库归属校验)。

    空 user_id 一律不放行:身份是注入进来的,注入没接上就是空串,那种情况下放行等于没做校验。
    查不到或归属不符都返回 False——工具层据此回 NOT_OWNED 同一句话,防枚举 oracle。
    """
    if not user_id or not ticket_id:
        return False
    from app.db import repository
    owner = await repository.get_ticket_owner(ticket_id)
    return owner == user_id


async def list_user_tickets(user_id: str) -> list[dict]:
    """按报修人列出该用户的全部工单(真库,created_at 倒序)。前端点选回填 ticket_id 即可查询。"""
    if not user_id:
        return []
    from app.db import repository
    items = await repository.list_user_tickets(user_id)
    return [
        {
            "ticket_id": t["ticket_no"],
            "device": _extract_device(t["description"]),
            "line": _extract_line(t["description"]),
            "status": t["status"],
            "priority": t["priority"],
            "ticket_type": t["ticket_type"],
            "description": t["description"],
        }
        for t in items
    ]
