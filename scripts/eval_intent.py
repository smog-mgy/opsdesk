"""意图分类标注评估:八类判对率 + confidence 可解析 + 怪问题落其他 + 多轮漂移。需聊天上游可调通。
用法:.venv/bin/python -m scripts.eval_intent"""
import asyncio

from app.core.intent import classify

SAMPLES = [
    ("我的工单 WO-2026-0001 处理到哪了", "查工单"), ("工单什么状态了", "查工单"),
    ("帮我报修一下电机", "报修"), ("VFD-3005 过载报警,要报修", "报修"),
    ("电机过热报警怎么排查", "故障咨询"), ("变频器报过流是什么原因", "故障咨询"),
    ("巡检服务包含什么内容", "巡检"), ("维保合同一年多少钱", "合同费用"),
    ("夜里设备故障有人值班吗", "合同费用"), ("巡检报告什么时候发", "巡检"),
    ("你们这什么破服务,我要投诉", "投诉"), ("处理太慢了给我个说法", "投诉"),
    ("运维热线是多少", "其他"), ("设备台账在哪查", "其他"),
    ("你好呀", "闲聊"), ("今天天气不错", "闲聊"),
    ("帮我写一段 Python 代码", "其他"), ("阿斯顿发发", "其他"),
]


async def main():
    passed = bad_json = 0
    for q, expect in SAMPLES:
        r = await classify(q)
        got = r.get("intent")
        conf = r.get("confidence")
        ok = got == expect
        json_ok = got in ("报修", "查工单", "故障咨询", "巡检", "合同费用", "投诉", "闲聊", "其他") \
            and isinstance(conf, float) and 0.0 <= conf <= 1.0
        bad_json += not json_ok
        passed += ok
        print(f"{'✅' if ok else '❌'} {q!r} -> {got}(conf={conf}) 期望={expect}")

    # 多轮漂移:报修→查工单→报修,当前句意图应随上下文
    hist = "用户:VFD-3005过载报警,帮我报修\n助手:已登记工单,正在派单\n用户:那工单现在到哪了\n助手:处理中,张工在排查\n"
    r = await classify("那现在什么情况", hist)
    print(f"多轮漂移『那现在什么情况』(查工单后)-> {r['intent']}(期望 查工单)")

    print(f"\n判对 {passed}/{len(SAMPLES)};JSON 越界 {bad_json} 条(glm 非确定性,抖动如实重跑记录)")


if __name__ == "__main__":
    asyncio.run(main())
