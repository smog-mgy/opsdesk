"""ch11 工程师工单台 API:列表(分页/状态筛选/关键词)、详情、状态流转(状态机校验 409)、
处理人/备注、WebSocket 心跳与状态变更广播。数据真库(tickets + conversations)。"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.api import engineer as engineer_api
from app.db import repository

USER = "u-reporter"


@pytest.fixture
def app():
    a = FastAPI()
    a.include_router(engineer_api.router)
    return a


@pytest.fixture
async def client(app, db_session_factory):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


async def _seed(desc="3号包装线 西门子空压机（PU-1002）上电后无法启动") -> str:
    cid = await repository.create_conversation(USER)
    return await repository.create_ticket(cid, desc, "报修")


async def test_list_paginates_and_filters(client):
    no1 = await _seed()
    no2 = await _seed("动力站 变频器（TS-4001）温度过高")
    r = await client.get("/api/engineer/tickets", params={"page": 1, "size": 10})
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 2 and {t["ticket_no"] for t in d["items"]} >= {no1, no2}
    # 状态筛选
    r2 = await client.get("/api/engineer/tickets", params={"status": "待派单"})
    assert all(t["status"] == "待派单" for t in r2.json()["items"])
    # 关键词(描述)
    r3 = await client.get("/api/engineer/tickets", params={"keyword": "PU-1002"})
    assert no1 in {t["ticket_no"] for t in r3.json()["items"]}
    # 非法状态 → 400
    assert (await client.get("/api/engineer/tickets",
                             params={"status": "瞎写"})).status_code == 400
    # 列表带报修人
    row = [t for t in r.json()["items"] if t["ticket_no"] == no1][0]
    assert row["user_id"] == USER


async def test_detail_and_404(client):
    no1 = await _seed()
    r = await client.get(f"/api/engineer/tickets/{no1}")
    assert r.status_code == 200
    assert r.json()["ticket_no"] == no1 and r.json()["status"] == "待派单"
    assert (await client.get("/api/engineer/tickets/NO-SUCH")).status_code == 404


async def test_status_flow_valid_and_invalid(client):
    no1 = await _seed()
    # 待派单 → 处理中(合法)+ 填处理人
    r = await client.patch(f"/api/engineer/tickets/{no1}",
                           json={"status": "处理中", "handler": "王工"})
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "处理中" and d["handler"] == "王工"
    # 处理中 → 待配件(合法)+ 填备注
    r2 = await client.patch(f"/api/engineer/tickets/{no1}",
                            json={"status": "待配件", "progress_note": "配件缺货,已下单"})
    assert r2.status_code == 200 and r2.json()["status"] == "待配件"
    # 待配件 → 处理中(合法,回环)
    r3 = await client.patch(f"/api/engineer/tickets/{no1}", json={"status": "处理中"})
    assert r3.status_code == 200 and r3.json()["status"] == "处理中"
    # 处理中 → 已解决(合法)
    r4 = await client.patch(f"/api/engineer/tickets/{no1}",
                            json={"status": "已解决", "progress_note": "更换完成,复测正常"})
    assert r4.status_code == 200 and r4.json()["status"] == "已解决"
    # 已解决 → 任何(终态,非法 409)
    r5 = await client.patch(f"/api/engineer/tickets/{no1}", json={"status": "待派单"})
    assert r5.status_code == 409
    # 待派单 → 待配件(跳状态,非法 409)
    no2 = await _seed()
    r6 = await client.patch(f"/api/engineer/tickets/{no2}", json={"status": "待配件"})
    assert r6.status_code == 409


async def test_patch_404_and_bad_status(client):
    assert (await client.patch("/api/engineer/tickets/NO-SUCH",
                               json={"status": "处理中"})).status_code == 404
    no1 = await _seed()
    assert (await client.patch(f"/api/engineer/tickets/{no1}",
                               json={"status": "瞎写"})).status_code == 400


async def test_status_flow_endpoint(client):
    r = await client.get("/api/engineer/status-flow")
    assert r.status_code == 200
    d = r.json()
    assert d["states"] == ["待派单", "处理中", "待配件", "已解决"]
    assert d["flow"]["待派单"] == ["处理中", "已解决"]
    assert d["flow"]["处理中"] == ["待配件", "已解决"]
    assert d["flow"]["已解决"] == []


def test_ws_heartbeat(app):
    # WebSocket 心跳:ping → pong(同步 TestClient,不依赖 DB 数据)
    with TestClient(app) as c:
        with c.websocket_connect("/api/engineer/ws") as ws:
            ws.send_text("ping")
            assert ws.receive_json() == {"type": "pong"}


async def test_broadcast_pushes_ticket_update(client, monkeypatch):
    sent = []

    class FakeWS:
        async def send_json(self, payload):
            sent.append(payload)

    monkeypatch.setattr(engineer_api, "_ws_clients", {FakeWS()})
    no1 = await _seed()
    r = await client.patch(f"/api/engineer/tickets/{no1}",
                           json={"status": "处理中", "handler": "李工"})
    assert r.status_code == 200
    assert sent and sent[-1]["type"] == "ticket_updated"
    assert sent[-1]["ticket"]["status"] == "处理中"
    assert sent[-1]["ticket"]["handler"] == "李工"
