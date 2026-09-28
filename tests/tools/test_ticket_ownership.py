"""工单归属校验:工具只认「这一单是不是这个人的」,不认模型说了什么。

为什么要有这组测试:query_ticket 早先只收 ticket_id,报个号就把单查出来念给用户听,
这是最经典的越权访问(IDOR)。身份不能让模型填——用户自称是谁,模型就按谁处理——
所以 user_id 走执行引擎注入,工具内部拿 user_id + ticket_id 双条件查。
"""
import pytest

from app.tools import business
from app.tools.builtin.tickets_query import query_ticket
from app.tools.builtin.ticket_confirm import submit_ticket

USER = "u-alice"
OTHER = "u-bob"


def _own(uid: str) -> str:
    """取这个用户的**私有**单(跳过每人都有的演示单),否则「别人的单」根本不成立。"""
    return [o["ticket_id"] for o in business.list_user_tickets(uid)
            if o["ticket_id"] not in business.DEMO_TICKET_IDS][0]


def test_owns_ticket_只认自己名下的单():
    mine = _own(USER)
    assert business.owns_ticket(USER, mine) is True
    assert business.owns_ticket(OTHER, mine) is False


def test_owns_ticket_空身份一律不放行():
    # user_id 没注入到(空串)时不能当成「谁都行」,否则漏一个调用点就等于没做校验
    assert business.owns_ticket("", _own(USER)) is False


async def test_查自己的工单照常返回():
    mine = _own(USER)
    out = await query_ticket.ainvoke({"ticket_id": mine, "user_id": USER})
    assert out["ticket_id"] == mine
    assert "fault_type" in out and out["fault_type"]          # 自己的单该给的字段一样不少


async def test_查别人的工单被拒且不泄露任何字段():
    his = _own(OTHER)
    out = await query_ticket.ainvoke({"ticket_id": his, "user_id": USER})
    assert out.get("code") == "ticket_not_owned"
    # 备件、设备、处理记录一个都不能漏出去(工单号能顺着查到资产归属)
    for leaked in ("spare_no", "asset_no", "handler", "status", "created_at"):
        assert leaked not in out


async def test_不存在的单和别人的单回同一句话():
    # 两种情况回不同的话就成了枚举 oracle:攻击者靠回答差异就能挨个试出哪些单真实存在
    his = await query_ticket.ainvoke({"ticket_id": _own(OTHER), "user_id": USER})
    nobody = await query_ticket.ainvoke({"ticket_id": "999999", "user_id": USER})
    assert his["error"] == nobody["error"]
    assert his["code"] == nobody["code"] == "ticket_not_owned"


async def test_处理确认也过同一道校验():
    # 写操作有二次确认门,但确认的是「要不要退」,不是「这单是不是你的」
    out = await submit_ticket.ainvoke(
        {"ticket_id": _own(OTHER), "reason": "设备已恢复,确认处理", "user_id": USER})
    assert out.get("code") == "ticket_not_owned"


@pytest.mark.parametrize("bad", ["", None])
async def test_身份缺失时读写都拒(bad):
    mine = _own(USER)
    out = await query_ticket.ainvoke({"ticket_id": mine, "user_id": bad or ""})
    assert out.get("code") == "ticket_not_owned"


def test_演示单每个账号都有():
    # 文档和评估脚本里到处写着 1001,让它对谁都成立,例子才拿来即跑;
    # 归属校验要看的是私有单那部分
    for uid in (USER, OTHER, "u-随便一个人"):
        for demo in business.DEMO_TICKET_IDS:
            assert business.owns_ticket(uid, demo) is True
    assert business.owns_ticket(USER, _own(OTHER)) is False
