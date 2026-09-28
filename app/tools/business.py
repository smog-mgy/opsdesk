"""mock 数据源(纯函数,随机种子固定 → 同键稳定)。
ch08 起工具实现迁至 app/tools/builtin/(注册即定义),本模块只留被 graph 节点
(fetch_ticket)与 builtin 工具共用的快照函数,不再定义任何 @tool。

业务域:企业设备运维工单。工单号格式 WO-YYYY-NNNN,演示单号在 DEMO_TICKET_IDS,
与 nodes._TICKET_RE 的提取规则对齐。"""
import random


def ticket_snapshot(ticket_id: str) -> dict:
    """工单快照(纯函数,随机种子固定 → 同 ticket_id 稳定)。query_ticket 工具与 fetch_ticket 节点同源。"""
    rng = random.Random(f"ticket:{ticket_id}")
    return {
        "ticket_id": ticket_id,
        "status": rng.choice(["待派单", "处理中", "待配件", "已解决", "已关闭"]),
        "priority": rng.choice(["P1", "P2", "P3"]),
        "fault_type": rng.choice(["电气故障", "机械故障", "程序故障", "通信故障"]),
        "device": rng.choice(["M-1001 三相异步电机", "PLC-2002 西门子S7-1200",
                              "VFD-3005 变频器", "TS-4001 温度传感器", "PU-1002 空压机"]),
        "line": rng.choice(["1号总装线", "2号焊接线", "3号包装线", "动力站"]),
        "submitted_at": f"2026-09-{rng.randint(1, 26):02d} 08:30",
        "assignee": rng.choice(["张工", "李工", "王工"]),
    }


def owns_ticket(user_id: str, ticket_id: str) -> bool:
    """这张工单是不是这个人提交的。归属判断只有这一处,工具和节点都调它,不各判各的。

    空 user_id 一律不放行:身份是注入进来的,注入没接上就是空串,那种情况下放行等于没做校验。"""
    if not user_id or not ticket_id:
        return False
    return any(t["ticket_id"] == ticket_id for t in list_user_tickets(user_id))


# 演示单。文档、curl 例子、各章评估脚本里到处写着 WO-2026-0001 和 WO-2026-0002,
# 让每个账号名下都有这两笔,例子拿来即跑。想看归属校验拦人,随便报一个别的号
# (如 WO-2026-9999)就会被挡下。
DEMO_TICKET_IDS = ("WO-2026-0001", "WO-2026-0002")


def list_user_tickets(user_id: str) -> list[dict]:
    """按 user_id 稳定列出该用户的工单(mock,不落库):两笔演示单 + 2-4 笔随机单。
    每笔用 ticket_snapshot 同源,前端选中后回填 ticket_id 即可 query_ticket。"""
    rng = random.Random(f"user_tickets:{user_id}")
    ids = list(DEMO_TICKET_IDS)
    for _ in range(rng.randint(2, 4)):
        oid = f"WO-2026-{rng.randint(1, 9999):04d}"
        if oid not in ids:
            ids.append(oid)
    out = []
    for tid in ids:
        s = ticket_snapshot(tid)
        out.append({"ticket_id": tid, "device": s["device"],
                    "status": s["status"], "priority": s["priority"],
                    "fault_type": s["fault_type"]})
    return out



