import random
from typing import Annotated

from langchain_core.tools import InjectedToolArg, tool
from pydantic import Field

from app.tools import registry
from app.tools.business import ticket_snapshot, owns_ticket

# 查不到和不是本人工单回同一句话。分开回就成了枚举 oracle:攻击者靠回答差异
# 就能挨个试出哪些工单号真实存在。
NOT_OWNED = {"error": "没有找到您的这笔工单", "code": "ticket_not_owned"}


@tool
async def query_ticket(
    ticket_id: Annotated[str, Field(description="工单号,例如 WO-2026-0001")],
    user_id: Annotated[str, InjectedToolArg],
) -> dict:
    """查询工单的状态、优先级、处理进度、设备编号与故障信息。用于用户询问某张工单处理情况时。
    发起人身份由系统注入,你不要传 user_id。"""
    if not owns_ticket(user_id, ticket_id):
        return dict(NOT_OWNED)
    return ticket_snapshot(ticket_id)


@tool
async def query_device(
    device_name: Annotated[str, Field(description="设备名称或编号关键词,例如 M-1001 或 电机")],
) -> dict:
    """查询设备台账信息:设备编号、型号、额定参数、所属产线与维保状态。用于用户咨询某台设备参数时。"""
    rng = random.Random(f"device:{device_name}")
    return {
        "device_name": device_name,
        "model": rng.choice(["M-1001 三相异步电机", "PLC-2002 西门子 S7-1200", "VFD-3005 变频器", "TS-4001 温感", "PU-1002 空压机"]),
        "rated_power": f"{rng.randint(1, 40)}kW",
        "line": rng.choice(["1号总装", "2号焊接", "3号包装", "动力站"]),
        "status": rng.choice(["在役", "维保中", "待检修"]),
    }


registry.register(registry.spec_from_langchain_tool(
    query_ticket, source="builtin", inject_user_id=True))
registry.register(registry.spec_from_langchain_tool(query_device, source="builtin"))
