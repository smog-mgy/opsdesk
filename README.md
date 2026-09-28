# 企业设备运维工单助手（OpsDesk）

基于 **LangGraph + RAG + Function Calling** 构建的企业设备运维助手：员工通过对话完成**设备报修、工单进度查询、常见故障排查指导、巡检维保咨询、安全规程查询**，系统自动检索知识库、调用业务工具、校验工单归属，答不上来时不编造、引导补充信息。

## 核心能力

| 能力 | 说明 | 实现方式 |
| --- | --- | --- |
| 设备报修与建单 | 识别报修意图，收集设备编号/故障现象，创建工单 | Function Calling（`create_ticket`）+ 前端表单确认 |
| 工单进度查询 | 查状态、优先级、处理进度，含**归属校验**（非本人工单拒答） | `query_ticket` 工具 + 身份注入 |
| 故障排查指导 | 电机过热、变频器过流、PLC 报警等排障步骤 | RAG 检索 `fault-handbook` 知识库 |
| 巡检/维保咨询 | 巡检内容、周期、维保合同、响应时效 SLA | RAG 检索知识库 |
| 安全规程查询 | LOTO 停送电、验电、工作票等规程 | RAG 检索知识库 |
| 多轮上下文 | 指代消解（"那台变频器"→具体设备）、意图漂移识别 | LangGraph 状态 + 摘要记忆 |

## 技术栈

- **后端**：FastAPI + LangGraph / LangChain
- **数据**：SQLAlchemy / MySQL（业务数据）、Milvus（向量库，混合检索 BM25+向量+重排）
- **模型**：硅基流动托管 DeepSeek-V4-Flash（聊天）、BAAI/bge-m3（嵌入）、bge-reranker-v2-m3（重排）
- **工具系统**：内置 `@tool` 注册中心 + 统一执行引擎，写操作二次确认、权限清单控制
- **前端**：原生 HTML/JS 单页（无框架），SSE 流式对话

## 系统架构

```
用户消息
  └─ /api/chat (SSE)
      └─ LangGraph 状态图
          ├─ 指代消解 resolve_reference
          ├─ 意图分类 classify_intent（9 类：报修/查工单/故障咨询/巡检维保/备件咨询/合同费用/投诉/闲聊/其他）
          ├─ 路由分流 route_by_intent
          │   ├─ knowledge → 混合检索（BM25 + 向量 + 重排）→ 证据 → 主 Agent
          │   ├─ ticket_flow → 查工单 → 归属校验 → 主 Agent
          │   ├─ complaint_reply → 投诉安抚话术
          │   └─ script_reply → 兜底话术（不编造）
          └─ 主 Agent（工具调用）→ 回答
```

回答全程带**知识库证据**（引用片段）与**工具审计轨迹**，可观测、可追溯。

## 目录结构

| 位置 | 内容 |
| --- | --- |
| `app/api/` | HTTP 入口：聊天、Agent、知识库录入、复核、评估、成本看板 |
| `app/graph/` | LangGraph 状态图：`state`/`nodes`/`routing`/`build` |
| `app/core/` | 意图、指代、检索、重排、置信度、摘要、可观测 |
| `app/kb/` | 知识库：切块、嵌入、MySQL+Milvus 双写、去重、挖知识 |
| `app/tools/` | 工具系统：内置工具、注册中心、统一执行引擎 |
| `app/db/` | 表模型与仓储 |
| `app/static/` | 前端页面：聊天、知识库录入、待审、观测、分类器评估 |
| `data/kb/` | 运维知识库源文档（6 份） |
| `sql/` | 建表与种子数据 |
| `scripts/` | 构建、评估、冒烟脚本 |

## 快速开始

环境要求：Python 3.12+（uv 管理）、Docker（跑 MySQL / Milvus）、内存建议 8G+。

```bash
# 1. 安装依赖
uv sync

# 2. 配置上游模型（硅基流动注册，一个 API Key 三处共用）
cp .env.example .env
# 编辑 .env：CHAT_API_KEY / EMBED_API_KEY / RERANK_API_KEY

# 3. 起数据库 + 灌测试数据
docker compose up -d
make seed          # FAQ 种子
make seed-conv     # 历史会话种子

# 4. 建知识库（RAG 必需）
make kb-build      # 切块落 MySQL
make kb-vectorize  # 向量化写 Milvus

# 5. 启动
make dev
```

浏览器打开 <http://localhost:8000> 即聊天页。

## 演示场景

```bash
# 报修
curl -s http://localhost:8000/api/agent -H 'Content-Type: application/json' \
  -d '{"user_id":"u1","message":"VFD-3005 变频器过载报警,帮我报修"}'

# 查工单（非本人工单会被拒）
curl -s http://localhost:8000/api/agent -H 'Content-Type: application/json' \
  -d '{"user_id":"u1","message":"我的工单 WO-2026-0001 处理到哪了"}'

# 故障排查（RAG）
curl -s http://localhost:8000/api/agent -H 'Content-Type: application/json' \
  -d '{"user_id":"u1","message":"电机过热报警怎么排查"}'
```

## 数据说明

- **知识库**（`data/kb/`）：6 份运维文档——设备台账、运维 FAQ、故障排查手册、工单制度、服务等级承诺、安全规程，切 37 块向量入 Milvus
- **设备台账**：M-1001 电机 / PLC-2002 / VFD-3005 变频器 / TS-4001 传感器 / PU-1002 空压机
- **工单**：演示单 WO-2026-0001/0002（每个账号名下均有）+ 随机生成的快照（同号稳定可复现）
- **种子会话**：电机报修、变频器咨询、夜班询问 3 组历史会话（供多轮与指代演示）

## 安全与可信设计

- **工单归属校验**：`owns_ticket` 唯一判定点，工具层与节点层同源，空身份不放行
- **拒答不乱答**：知识库无证据时明确说查不到，引导补充设备编号/工单号或转当班工程师
- **工具权限清单**：写操作（建单/推进）需用户在前端表单二次确认；未登记工具一律只读
- **注入防御**：模型输入、工具 schema 均视为不可信，检索证据与回答分离
- **响应时效承诺**：P1 15 分钟响应 / P2 2 小时 / P3 1 个工作日（知识库口径）

## 测试与评估

```bash
make test            # 单测
make smoke-rag       # 混合检索冒烟
make eval-rag        # 四策略召回对比
make eval-check      # 评估集自检
uv run python -m scripts.eval_intent   # 意图分类稳定性
```

## 已知说明

- 内部字段统一使用 `ticket_id`/`ticket_data`（工单口径），无历史兼容残留
- 业务数据为演示用 mock（固定随机种子），接入真实系统时替换 `app/tools/business.py` 数据源即可
