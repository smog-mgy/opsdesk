# 部署指南（OpsDesk 企业设备运维工单助手）

本文档描述从零部署到本机并跑通完整对话链路的步骤。**开发环境要求**：Windows/Linux/macOS + Docker Desktop（或 Docker Engine）、uv、Make（Windows 建议 Git Bash 或 WSL2 环境）。

## 1. 环境准备

- Python 3.12+（`uv` 会自动下载，无需手动建虚拟环境）
- Docker（跑 MySQL / Milvus 主栈，约 3-4G 内存）
- 上游模型 API Key（硅基流动注册，一个 Key 三处共用）

## 2. 安装依赖

```bash
uv sync
```

首次会下载 Python 并安装两百多个包，几分钟无输出属正常。

## 3. 配置 .env

```bash
cp .env.example .env
```

编辑 `.env`，填三处 API Key（同一个硅基流动 Key 即可）：

```ini
CHAT_API_KEY=sk-xxx
EMBED_API_KEY=sk-xxx
RERANK_API_KEY=sk-xxx
```

`CHAT_MODEL` 必须写上游认的真实模型名（如 `deepseek-ai/DeepSeek-V4-Flash`），写错会在启动时报 `Model does not exist`。

## 4. 起数据库 + 灌数据

```bash
docker compose up -d        # MySQL / etcd / MinIO / Milvus
```

`sql/` 目录已挂进 MySQL 初始化目录，首次启动自动建表并灌入 FAQ 种子。约 30 秒后验证：

```bash
docker exec -i opsdesk-mysql mysql -uroot -proot opsdesk -e "SHOW TABLES;"
make seed                   # FAQ 种子（幂等）
make seed-conv              # 历史会话种子（挖知识用）
```

> 中文灌数据务必带 `--default-character-set=utf8mb4`（`make seed` 已内置）。

## 5. 建知识库（RAG 必需）

```bash
make kb-build              # 切块落 MySQL
make kb-vectorize          # 向量化写 Milvus（调用嵌入模型）
make kb-preview            # 预览建库效果
```

## 6. 启动

```bash
make dev
```

浏览器打开 <http://localhost:8000> 即聊天页。`make dev` 是前台进程，停用 Ctrl+C；后台运行用 `make dev-down` 关闭。

## 7. 验证链路

```bash
# 报修
curl -s http://localhost:8000/api/agent -H 'Content-Type: application/json' \
  -d '{"user_id":"u1","message":"VFD-3005 变频器过载报警,帮我报修"}'

# 查工单（中文 body 需先落文件再传，避免 Windows 编码问题）
printf '{"user_id":"u1","message":"我的工单 WO-2026-0001 处理到哪了"}' > q.json
curl -s http://localhost:8000/api/agent -H 'Content-Type: application/json' --data-binary @q.json
```

## 端口清单

| 端口 | 服务 | 用途 |
| --- | --- | --- |
| 3306 | MySQL | 全程 |
| 19530 / 9091 | Milvus / 健康检查 | 知识库 |
| 8000 | FastAPI 应用 | 全程 |
| 3000 等 | Langfuse 观测栈（可选，`make langfuse-up`） | ch09 可观测 |

## 常见问题

- **镜像拉不下来**：etcd 在 quay.io、Langfuse MinIO 在 cgr.dev，国内需配 Docker 镜像加速或代理。
- **`make dev` 卡在 Milvus 就绪后退出**：检查 `docker compose ps` 三个依赖容器是否 healthy，内存不足时 Milvus 会反复重启，给 Docker 多分内存。
- **中文乱码**：灌数据漏了 `--default-character-set=utf8mb4`，清库重灌。
- **知识类问题答不上来**：知识库未建，跑 `make kb-build && make kb-vectorize`。
- **Windows PowerShell 报错**：PowerShell 不支持 `<` 重定向与 `.sh` 脚本，请用 Git Bash 或 WSL2。
