from app.kb import chunking


def test_split_sections_keeps_header_path():
    md = "# 报修手册\n\n## 报修政策\n\n支持在线报修。\n\n## 费用说明\n\n报修响应。"
    secs = chunking.split_sections(md)
    freight = [d for d in secs if d.metadata.get("h2") == "费用说明"]
    assert freight, "应切出「费用说明」小节"
    assert freight[0].metadata.get("h1") == "报修手册"
    assert "报修响应" in freight[0].page_content


def test_recursive_split_breaks_oversized():
    text = "句子内容。" * 60  # 300 字
    parts = chunking.recursive_split(text, chunk_size=50, chunk_overlap=0)
    assert len(parts) > 1
    assert max(len(p) for p in parts) <= 50
