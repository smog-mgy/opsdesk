"""工单归属校验(真库):工具只认「这一单是不是这个人的」,不认模型说了什么。

为什么要有这组测试:query_ticket 早先只收 ticket_id,报个号就把单查出来念给用户听,
这是最经典的越权访问(IDOR)。身份不能让模型填——用户自称是谁,模型就按谁处理——
所以 user_id 走执行引擎注入,工具内部拿 user_id + ticket_no 双条件查。

ch11 起数据源切真库:归属 = tickets 行经 conversation_id join conversations 取报修人。
"""
import pytest
import pytest_asyncio

from app.tools import business
from app.tools.builtin.tickets_query import query_ticket
from app.tools.builtin.ticket_confirm import submit_ticket

USER = "u-alice"
OTHER = "u-bob"


@pytest_asyncio.fixture()
async def alice_ticket(db_session_factory):
    """在测试库里造一笔 alice 的真工单(私有单,别人名下查不到)。"""
    from app.db import repository
    cid = await repository.create_conversation(USER)
    return await repository.create_ticket(cid, "1号总装线 M-1001 电机过热", "报修")


async def test_owns_ticket_只认自己名下的单(alice_ticket):
    assert await business.owns_ticket(USER, alice_ticket) is True
    assert await business.owns_ticket(OTHER, alice_ticket) is False


async def test_owns_ticket_空身份一律不放行(alice_ticket):
    # user_id 没注入到(空串)时不能当成「谁都行」,否则漏一个调用点就等于没做校验
    assert await business.owns_ticket("", alice_ticket) is False


async def test_查自己的工单照常返回(alice_ticket):
    out = await query_ticket.ainvoke({"ticket_id": alice_ticket, "user_id": USER})
    assert out["ticket_id"] == alice_ticket
    assert out["status"] in {"待派单", "处理中", "待配件", "已解决"}
    assert out["description"]


async def test_查别人的工单被拒且不泄露任何字段(alice_ticket):
    out = await query_ticket.ainvoke({"ticket_id": alice_ticket, "user_id": OTHER})
    assert out.get("code") == "ticket_not_owned"
    # 除了 error/code 两个键,工单任何信息都不能漏(工单号能顺着查到资产归属)
    assert set(out.keys()) == {"error", "code"}


async def test_不存在的单和别人的单回同一句话(alice_ticket):
    # 两种情况回不同的话就成了枚举 oracle:攻击者靠回答差异就能挨个试出哪些单真实存在
    his = await query_ticket.ainvoke({"ticket_id": alice_ticket, "user_id": OTHER})
    nobody = await query_ticket.ainvoke({"ticket_id": "999999", "user_id": USER})
    assert his["error"] == nobody["error"]
    assert his["code"] == nobody["code"] == "ticket_not_owned"


async def test_处理确认也过同一道校验(alice_ticket):
    # 写操作有二次确认门,但确认的是「要不要退」,不是「这单是不是你的」
    out = await submit_ticket.ainvoke(
        {"ticket_id": alice_ticket, "reason": "设备已恢复,确认处理", "user_id": OTHER})
    assert out.get("code") == "ticket_not_owned"


@pytest.mark.parametrize("bad", ["", None])
async def test_身份缺失时读写都拒(bad, alice_ticket):
    out = await query_ticket.ainvoke({"ticket_id": alice_ticket, "user_id": bad or ""})
    assert out.get("code") == "ticket_not_owned"
