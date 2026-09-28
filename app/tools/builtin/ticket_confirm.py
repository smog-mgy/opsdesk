from typing import Annotated

from langchain_core.tools import InjectedToolArg, tool
from pydantic import Field

from app.tools import registry
from app.tools.builtin.tickets_query import NOT_OWNED
from app.tools.business import owns_ticket


@tool
async def submit_ticket(
    ticket_id: Annotated[str, Field(description="要推进处理的工单号")],
    user_id: Annotated[str, InjectedToolArg],
    reason: Annotated[str | None, Field(description="处理说明(可选,最终以前端固定类目下拉为准)")] = None,
) -> dict:
    """判定这张工单可以推进处理(如转派、确认处理方案)后,调用本工具提交处理确认。实际提交由前端工单表单确认后落库,
    本工具只表示『这张工单可推进处理,已把提交入口交给用户』。
    发起人身份由系统注入,你不要传 user_id。"""
    # 写操作有二次确认门,但那道门确认的是「要不要推进」,不是「这单是不是你的」,归属得单独校验
    if not owns_ticket(user_id, ticket_id):
        return dict(NOT_OWNED)
    return {"status": "待用户确认", "ticket_id": ticket_id}


registry.register(registry.spec_from_langchain_tool(
    submit_ticket, source="builtin", inject_user_id=True))
