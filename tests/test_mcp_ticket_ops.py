"""ch11 MCP 工单流转:query_ticket_progress 数据源切到 MySQL 真库(tickets),与工程师台同源。"""
import pytest

from app.db import repository
from mcp_servers import ticket_ops_server

USER = "u-reporter"


@pytest.fixture
def use_test_db(db_session_factory):
    # MCP server 的会话工厂指向测试库(生产库 engine 是懒连接,不实际触碰)
    ticket_ops_server._session = db_session_factory
    yield


async def test_progress_from_real_db(use_test_db):
    cid = await repository.create_conversation(USER)
    no = await repository.create_ticket(cid, "动力站 变频器温度过高", "报修")
    out = await ticket_ops_server.query_ticket_progress(no)
    assert out["found"] is True
    assert out["node"] == "待派单" and out["assignee"] == "待分配"
    assert out["priority"] == "P2"

    # 工程师改状态/处理人/备注后,AI 侧 MCP 工具应能查到最新真库进度
    await repository.update_ticket_status(no, "处理中", handler="王工", progress_note="已上门检修")
    out2 = await ticket_ops_server.query_ticket_progress(no)
    assert out2["node"] == "处理中"
    assert out2["assignee"] == "王工"
    assert out2["detail"] == "已上门检修"
    assert out2["updated_at"]


async def test_progress_not_found(use_test_db):
    out = await ticket_ops_server.query_ticket_progress("T-NOT-EXIST")
    assert out["found"] is False


async def test_formatter_renders_real_fields():
    """格式化器输出真库字段(状态/处理人/优先级/备注/更新时间),不含 mock 的 eta。"""
    from app.tools.mcp_client import _fmt_ticket_ops

    s = _fmt_ticket_ops({
        "found": True, "ticket_id": "T20261001144639001", "node": "已解决",
        "assignee": "苗工", "priority": "P2", "detail": "更换完成,复测正常",
        "updated_at": "2026-10-01 07:57:04",
    })
    assert "已解决" in s and "苗工" in s and "P2" in s
    assert "更换完成,复测正常" in s and "2026-10-01 07:57:04" in s

    miss = _fmt_ticket_ops({"found": False, "ticket_id": "T-NOT-EXIST"})
    assert "未找到工单 T-NOT-EXIST" == miss
