import uuid

import pytest

from app.kb import milvus_client as mc

URI = "http://localhost:19530"


@pytest.fixture()
def coll():
    client = mc.get_client(uri=URI)
    name = f"test_kb_{uuid.uuid4().hex[:8]}"
    mc.ensure_collection(client, collection=name)
    rows = [
        {"id": 1, "dense": [0.1] * 1024, "text": "费用 报修响应 不满10元",
         "question": "费用怎么算", "answer": "报修响应,否则10元",
         "section_path": "费用政策", "content_type": "faq", "category": "费用"},
        {"id": 2, "dense": [0.2] * 1024, "text": "智能变频器 Pro 型号 自动清理",
         "question": "Pro 型号功能", "answer": "自动清理除臭",
         "section_path": "设备手册 / 变频器", "content_type": "manual", "category": "设备手册"},
    ]
    mc.upsert_vectors(client, rows, collection=name)
    mc.flush(client, collection=name)          # 新数据须 flush 才可被检索
    client.load_collection(name)
    import time; time.sleep(2)                  # 等 sparse 索引对新段生效
    yield client, name
    mc.drop(client, name)


def test_bm25_hits_model_number(coll):
    client, name = coll
    hits = mc.bm25_search(client, "变频器 Pro 型号", top_k=2, collection=name)
    assert hits[0]["id"] == 2
    assert hits[0]["section_path"] == "设备手册 / 变频器"


def test_hybrid_returns_scored_hits(coll):
    client, name = coll
    hits = mc.hybrid_search(client, [0.1] * 1024, "费用", top_k=2, recall=10, collection=name)
    assert hits
    assert {"id", "score", "question", "answer", "section_path", "content_type", "category"} <= hits[0].keys()


def test_category_filter(coll):
    client, name = coll
    hits = mc.bm25_search(client, "型号 费用", top_k=5, category="费用", collection=name)
    assert all(h["category"] == "费用" for h in hits)
    assert all(h["id"] == 1 for h in hits)
