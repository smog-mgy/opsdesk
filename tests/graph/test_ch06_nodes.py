import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.graph import nodes


@pytest.mark.asyncio
async def test_classify_intent_writes_confidence_and_route(monkeypatch):
    async def fake_classify(query, history=""):
        return {"intent": "报修", "confidence": 0.83}
    monkeypatch.setattr(nodes.intent_mod, "classify", fake_classify)
    out = await nodes.classify_intent({"messages": [HumanMessage("这个怎么处理")],
                                       "resolved_query": "电机还能申请报修吗"})
    assert out["intent"] == "报修"
    assert out["intent_confidence"] == 0.83
    assert out["route"] == "business"                    # 报修 → business(建单确认流)
    assert out["trace"]["route"] == "business"
    assert out["trace"]["intent_confidence"] == 0.83     # 不覆盖 confidence_check 的 confidence 键


def test_get_chat_model_honors_model_override():
    from app.core.llm import get_chat_model
    m = get_chat_model(model="glm-4-flash")
    assert m.model_name == "glm-4-flash"
    d = get_chat_model()
    from app.config import settings
    assert d.model_name == settings.chat_model


@pytest.mark.asyncio
async def test_resolve_reference_passthrough_when_complete(monkeypatch):
    async def fake_resolve(q, history=""):
        return q  # 已完整,原样
    monkeypatch.setattr(nodes.coref, "resolve", fake_resolve)
    out = await nodes.resolve_reference({"messages": [HumanMessage("电机的保修期多久")]})
    assert out["resolved_query"] == "电机的保修期多久"
    assert out["trace"]["coref"] == "passthrough"


@pytest.mark.asyncio
async def test_resolve_reference_rewrites_with_history(monkeypatch):
    async def fake_resolve(q, history=""):
        return "电机还能申请报修吗"
    monkeypatch.setattr(nodes.coref, "resolve", fake_resolve)
    out = await nodes.resolve_reference({"messages": [
    HumanMessage("电机什么时候修好"), AIMessage("预计明天"), HumanMessage("这个处理到哪了")]})
    assert out["resolved_query"] == "电机还能申请报修吗"
    assert out["trace"]["coref"] == "rewrite"


# ---- Task 7: fetch_ticket + list_user_tickets + 缺单 interrupt ----

def test_extract_ticket_id():
    assert nodes._extract_ticket_id("工单1001的查工单") == "1001"
    assert nodes._extract_ticket_id("尾号 20260701 那单") == "20260701"
    assert nodes._extract_ticket_id("我要报修") is None


@pytest.mark.asyncio
async def test_fetch_ticket_uses_id_in_query():
    uid = "u1"
    mine = nodes.business.list_user_tickets(uid)[0]["ticket_id"]   # 话里报的得是他自己的单
    out = await nodes.fetch_ticket({"resolved_query": f"工单{mine}处理到哪了", "user_id": uid})
    assert out["ticket_id"] == mine
    assert out["ticket_data"]["ticket_id"] == mine            # ticket_snapshot 同源
    assert out["trace"]["fetch_ticket"]["ticket_id"] == mine


@pytest.mark.asyncio
async def test_fetch_ticket_interrupts_when_missing(monkeypatch):
    # interrupt() 只能在编译图内跑(Task 1 冒烟 D:图外直接调是 RuntimeError),
    # 故缺单路径经最小编译图 + InMemorySaver ainvoke 测真实中断 surface。
    monkeypatch.setattr(nodes.business, "list_user_tickets",
                        lambda uid: [{"ticket_id": "1001", "device": "M-1001 三相异步电机", "status": "待派单",
                        "priority": "P2", "fault_type": "电气故障"}])
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import END, START, StateGraph

    from app.graph.state import ConversationState
    b = StateGraph(ConversationState)
    b.add_node("fetch_ticket", nodes.fetch_ticket)
    b.add_edge(START, "fetch_ticket")
    b.add_edge("fetch_ticket", END)
    graph = b.compile(checkpointer=InMemorySaver())
    out = await graph.ainvoke({"resolved_query": "我要处理确认", "user_id": "u1"},
                              {"configurable": {"thread_id": "t-fetch"}})
    payload = out["__interrupt__"][0].value      # Task 1 冒烟 A/C 钉死此取法
    assert payload["type"] == "select_ticket"
    assert payload["tickets"][0]["ticket_id"] == "1001"


@pytest.mark.asyncio
async def test_fetch_order_报别人的单号也弹选择器(monkeypatch):
    # 处理确认子流程是确定性节点、不经 agent_tools,工具内那道归属校验够不着它。
    # 用户随口报一个别人的单号,不能照查,得跟「没给单号」一样落回选择器。
    monkeypatch.setattr(nodes.business, "list_user_tickets",
                        lambda uid: [{"ticket_id": "1001", "device": "M-1001 三相异步电机", "status": "待派单",
                        "priority": "P2", "fault_type": "电气故障"}])
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import END, START, StateGraph

    from app.graph.state import ConversationState
    b = StateGraph(ConversationState)
    b.add_node("fetch_ticket", nodes.fetch_ticket)
    b.add_edge(START, "fetch_ticket")
    b.add_edge("fetch_ticket", END)
    graph = b.compile(checkpointer=InMemorySaver())
    out = await graph.ainvoke({"resolved_query": "工单 8888 我要处理确认", "user_id": "u1"},
                              {"configurable": {"thread_id": "t-foreign"}})
    payload = out["__interrupt__"][0].value
    assert payload["type"] == "select_ticket"                 # 没有照着 8888 查下去
    assert [o["ticket_id"] for o in payload["tickets"]] == ["1001"]


def test_list_user_tickets_stable_and_queryable():
    from app.tools import business
    a = business.list_user_tickets("u-42")
    b = business.list_user_tickets("u-42")
    assert a == b and len(a) >= 2                            # 同 user 稳定
    snap = business.ticket_snapshot(a[0]["ticket_id"])
    assert snap["ticket_id"] == a[0]["ticket_id"] and snap["device"] == a[0]["device"]


# ---- Task 8: retrieve_policy 扩写多查 + 去重合并 ----

@pytest.mark.asyncio
async def test_retrieve_policy_expands_dedups_merges(monkeypatch):
    async def fake_expand(q):
        return ["报修政策", "报修处理政策", "报修时限"]
    # 三条 query 各自召回:id=1 在两条里出现(取高分 0.9),id=2 只在一条
    per_query = {
        "报修政策": [{"id": 1, "question": "报修", "answer": "报修处理政策", "rerank_score": 0.7,
                     "section_path": "政策/报修", "content_type": "policy"}],
        "报修处理政策": [{"id": 1, "question": "报修", "answer": "报修处理政策", "rerank_score": 0.9,
                       "section_path": "政策/报修", "content_type": "policy"},
                      {"id": 2, "question": "费用", "answer": "备件质量问题由班组承担", "rerank_score": 0.6,
                       "section_path": "政策/费用", "content_type": "policy"}],
        "报修时限": [],
    }
    async def fake_search(q, **k):
        return per_query.get(q, [])
    monkeypatch.setattr(nodes.query_understanding, "expand_queries", fake_expand)
    monkeypatch.setattr(nodes.retrieval, "search_knowledge", fake_search)
    monkeypatch.setattr(nodes.retrieval, "arrange_head_tail", lambda h: h)

    out = await nodes.retrieve_policy({"resolved_query": "这个工单处理到哪了",
                                       "ticket_data": {"status": "处理中"}})
    assert len(out["citations"]) == 2                    # id=1 去重(取 0.9)+ id=2
    ids = [c["id"] for c in out["citations"]]
    assert ids == [1, 2]                                 # 按 rerank_score 降序(0.9, 0.6)
    assert "[1]" in out["evidence"] and "[2]" in out["evidence"]
    assert out["trace"]["retrieve_policy"]["hits"] == 2
    assert out["trace"]["retrieve_policy"]["queries"] == ["报修政策", "报修处理政策", "报修时限"]


    # ---- Task 9: submit_ticket 拦截 + _agent_messages 适配 ----

@pytest.mark.asyncio
async def test_agent_tools_intercepts_submit_ticket():
    uid = "u1"
    mine = nodes.business.list_user_tickets(uid)[0]["ticket_id"]
    ai = AIMessage(content="", tool_calls=[
        {"id": "r1", "name": "submit_ticket", "args": {"ticket_id": mine, "reason": None}}])
    out = await nodes.agent_tools({"messages": [ai], "user_id": uid})
    assert out["suggested_actions"] == [{"type": "ticket_form", "draft": {"ticket_id": mine, "reason": None}}]
    tm = out["messages"][0]
    assert tm.name == "submit_ticket"                       # 合成 ToolMessage 促收敛
    assert "处理确认" in tm.content


def test_agent_messages_injects_ticket_and_policy_on_confirm():
    msgs = nodes._agent_messages({
        "route": "ticket_flow",
        "ticket_data": {"ticket_id": "1001", "status": "处理中", "device": "M-1001 三相异步电机"},
    "evidence": " 报修: 处理确认政策",
        "messages": [HumanMessage("这单怎么处理")]})
    assert isinstance(msgs, list) and isinstance(msgs[0], SystemMessage)
    assert "处理确认政策" not in msgs[0].content and "电机" not in msgs[0].content  # 不进 system
    ctx = msgs[-1].content                                   # 本轮材料紧跟用户那句
    assert "处理确认政策" in ctx                                 # 政策证据
    assert "电机" in ctx and "submit_ticket" in ctx            # 工单数据 + 判定指令
    # 顺序不能反:TICKET_JUDGE_HINT 的措辞假设证据已在前文给过
    assert ctx.index("处理确认政策") < ctx.index("submit_ticket")


def test_agent_messages_knowledge_path_still_injects_evidence():
    msgs = nodes._agent_messages({
        "route": "knowledge", "evidence": " 报修: 处理确认政策",
        "messages": [HumanMessage("报修怎么处理")]})
    assert "处理确认政策" not in msgs[0].content              # 不进 system
    assert "处理确认政策" in msgs[-1].content                 # 放宽条件后知识路不回归


# ---- Task 10: script_reply 按意图分文案 ----

@pytest.mark.asyncio
async def test_script_reply_by_intent():
    from app.core.prompts import SCRIPT_REPLY_CHITCHAT, SCRIPT_REPLY_OTHER
    chit = await nodes.script_reply({"intent": "闲聊"})
    assert chit["answer"] == SCRIPT_REPLY_CHITCHAT
    assert chit["trace"]["route"] == "fallback_script"
    other = await nodes.script_reply({"intent": "其他"})
    assert other["answer"] == SCRIPT_REPLY_OTHER
