"""ch11 起:query_ticket 读真库(MySQL tickets)。同单两次查询结果一致(读库稳定);
字段形状对齐工单四态枚举。query_device 仍为纯 mock(设备台账演示,不落库)。"""
import pytest_asyncio

from app.tools.builtin.tickets_query import query_ticket, query_device

USER = "u-mock"


@pytest_asyncio.fixture()
async def ticket_no(db_session_factory):
    """在测试库里造一笔该用户的真工单,返回工单号。"""
    from app.db import repository
    cid = await repository.create_conversation(USER)
    return await repository.create_ticket(
        cid, "3号包装线 西门子空压机（PU-1002）上电后无法启动", "报修")


async def test_query_ticket_real_db_stable_and_shaped(ticket_no):
    # 身份由执行引擎注入,查自己的单才有数据(归属校验见 tests/tools/test_ticket_ownership.py)
    r1 = await query_ticket.ainvoke({"ticket_id": ticket_no, "user_id": USER})
    r2 = await query_ticket.ainvoke({"ticket_id": ticket_no, "user_id": USER})
    assert r1 == r2                                  # 真库读取稳定
    assert r1["ticket_id"] == ticket_no
    assert r1["status"] in {"待派单", "处理中", "待配件", "已解决"}
    assert r1["priority"] in {"P1", "P2", "P3"}
    assert r1["description"]


async def test_query_device_names_and_determinism():
    assert query_ticket.name == "query_ticket"
    assert query_device.name == "query_device"
    p1 = await query_device.ainvoke({"device_name": "M-1001"})
    p2 = await query_device.ainvoke({"device_name": "M-1001"})
    assert p1 == p2                                   # 同种子可复现
    assert "model" in p1 and "line" in p1
