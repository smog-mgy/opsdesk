#!/usr/bin/env bash
# 演示:两轮流式对话,第二轮须接住第一轮上下文
set -euo pipefail
SID="demo-$$"

echo "=== 第一轮:自报家门+提报修 ==="
curl -sN http://localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d "{\"session_id\": \"$SID\", \"message\": \"我是2号线班组的王小明,车间VFD-3005变频器过载报警\"}"
echo; echo "=== 第二轮:考上下文(我叫什么?报修了什么设备?) ==="
curl -sN http://localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d "{\"session_id\": \"$SID\", \"message\": \"还记得我叫什么、报修了哪台设备吗?\"}"
echo
