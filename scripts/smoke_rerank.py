"""直连 SiliconFlow /rerank 冒烟。不通即红线停。"""
import httpx

from app.config import settings
from app.core.rerank import _rerank_url


def main() -> None:
    url = _rerank_url()   # 跟应用同一份拼法,别在这里各拼各的
    payload = {
        "model": settings.rerank_model,
        "query": "电机过热报警怎么排查",
        "documents": [
            "P1 故障 15 分钟内响应,处理时限 2 小时。",
            "故障报修后 2 小时内到场,24 小时值守电话。",
            "M-1001 电机支持过载保护与过热报警。",
        ],
        # 字段跟 app/core/rerank.py 发的那份保持一致:冒烟要验的是应用真会发的请求形状,
        # 多带一个 return_documents 就成了验另一条路。只读 index 和 relevance_score,不要原文。
        "top_n": 3,
    }
    r = httpx.post(url, json=payload,
                   headers={"Authorization": f"Bearer {settings.rerank_api_key}"}, timeout=60)
    r.raise_for_status()
    data = r.json()
    print("原始返回:", data)
    results = data["results"]
    assert results, "rerank 返回空"
    top = max(results, key=lambda x: x["relevance_score"])
    print(f"最相关 index={top['index']} score={top['relevance_score']:.4f}")
    assert top["index"] == 1, "报修费用问题应命中第 2 条(报修人承担)"
    print("GO: rerank 链路通")


if __name__ == "__main__":
    main()
