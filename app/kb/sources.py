"""建库材料清单:哪些文件进知识库、各自算什么内容类型。

一处定义、三处共用——离线建库 CLI(scripts/build_kb.py)、切块预览(scripts/show_kb.py)、
录入页(/kb)。三边各写一份就会出现「预览看到三份、实际入库四份」这种对不上的账。
"""
import pathlib

# app/kb/sources.py → parents[0]=app/kb, parents[1]=app, parents[2]=项目根(opsdesk)
KB_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "kb"

# 文件 → content_type(运维工单助手场景)
SOURCE_TYPES: dict[str, str] = {
    "ops-faq.md": "faq",
    "ticket-policy.md": "policy",
    "sla-benefits.md": "policy",      # 服务等级与响应承诺,规则型归 policy
    "fault-handbook.md": "manual",    # 常见故障排查手册
    "safety-regulations.md": "manual",  # 安全操作规程
    "device-manual.md": "spec",       # 设备台账与参数,带具体编号,供 BM25 精确词命中
}

# 录入页允许选的内容类型:政策/手册这类没有天然问题,questions 落章节标题
CONTENT_TYPES: tuple[str, ...] = ("faq", "policy", "manual", "spec")
CONTENT_TYPE_DESC: dict[str, str] = {
    "faq": "运维 FAQ:questions 填真实问法",
    "policy": "制度条款:questions 填章节标题、category 填上级路径",
    "manual": "手册(故障排查/安全规程):同政策,按标题层级切",
    "spec": "设备台账:含具体编号,精确词召回靠它",
}
