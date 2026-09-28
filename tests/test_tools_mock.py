from app.tools import business
from app.tools.builtin.tickets_query import query_ticket, query_device

USER = "u-mock"
MINE = business.list_user_tickets(USER)[0]["ticket_id"]   # 这个用户名下真实存在的一单


async def test_query_ticket_deterministic_and_shaped():
    # 身份由执行引擎注入,查自己的单才有数据(归属校验见 tests/tools/test_order_ownership.py)
    r1 = await query_ticket.ainvoke({"ticket_id": MINE, "user_id": USER})
    r2 = await query_ticket.ainvoke({"ticket_id": MINE, "user_id": USER})
    assert r1 == r2                                  # 同种子可复现
    assert r1["ticket_id"] == MINE
    assert r1["status"] in {"待派单", "处理中", "待配件", "已解决", "已关闭"}
    assert r1["priority"] in {"P1", "P2", "P3"}
    assert r1["device"] and r1["fault_type"]


async def test_query_device_names_and_determinism():
    assert query_ticket.name == "query_ticket"
    assert query_device.name == "query_device"
    p1 = await query_device.ainvoke({"device_name": "M-1001"})
    p2 = await query_device.ainvoke({"device_name": "M-1001"})
    assert p1 == p2                                   # 同种子可复现
    assert "model" in p1 and "line" in p1
