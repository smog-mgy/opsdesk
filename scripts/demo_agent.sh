#!/usr/bin/env bash
# 演示样例:设备报修/工单查询/故障咨询三条链路。需 opsdesk-mysql 容器 + make seed + make dev 就绪。
set -euo pipefail
BASE=http://localhost:8000

echo "== 演示1:查询工单(query_ticket 命中并校验归属)=="
curl -s $BASE/api/agent -H 'Content-Type: application/json' \
  -d '{"user_id":"u1","message":"我的工单 WO-2026-0001 处理到哪了"}' | python3 -m json.tool

echo ""
echo "== 演示2:报修渠道(query_faq 命中)=="
curl -s $BASE/api/agent -H 'Content-Type: application/json' \
  -d '{"user_id":"u1","message":"设备报修有哪些渠道"}' | python3 -m json.tool

echo ""
echo "== 演示3:故障排查(知识库检索召回 fault-handbook)=="
curl -s $BASE/api/agent -H 'Content-Type: application/json' \
