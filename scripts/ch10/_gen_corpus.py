"""ch10 语料本地生成(规则模板 × 运维实体池):为 10 类主题各生成 40 条语义正确的
口语化运维问题,写入 corpus_labeled.jsonl,再复用项目纯函数 split_dataset 划分
80/10/10 生成 dataset/{train,val,test}.jsonl(跳过 LLM 造数与增强,零上游依赖)。
运行:uv run python scripts/ch10/_gen_corpus.py
"""
import json
import pathlib
import random

from app.core.taxonomy import TOPIC_CLASSES
from scripts.ch10.corpus_lib import split_dataset

OUT = pathlib.Path("data/ch10")

DEVICES = ["M-1001 电机", "M-1002 空压机", "PLC-2002", "VFD-3005 变频器",
           "TS-4001 温度传感器", "PU-1002 水泵"]
FAULTS = ["过热", "异响", "停机", "过流报警", "不启动", "漏油", "压力上不去", "乱跳闸"]
TICKETS = ["WO-2026-0001", "WO-2026-0002", "WO-2026-0003"]
SPARES = ["SP-1001 接触器", "SP-1003 电机风扇叶", "SP-1004 变频器散热风扇", "SP-1005 温控器探头"]
LINES = ["1号灌装线", "2号动力线", "3号包装线"]

# 语气前缀变体(乘数,保证每类 ≥40 条且口语多样)
PRE = ["", "请问", "麻烦问下", "师傅,", "想问一下,", "那个,", "急! ", "在线等,"]

# 每类核心模板(含 {d}/{f}/{t}/{s}/{l} 占位;无占位的是固定问法)
TEMPLATES: dict[str, list[str]] = {
    "设备报修": [
        "{d} {f}了,赶紧派人来修", "{d}又出问题了,帮我建个工单报修",
        "{d}烧了要报修,现场等着处理", "报修:{d} {f},尽快安排工程师",
        "{d}开不起来了,麻烦走报修流程", "{d}直接停机了,我要报修",
    ],
    "工单查询": [
        "工单 {t} 现在到哪一步了", "帮我查一下 {t} 的处理进度",
        "我的工单 {t} 派给谁了", "{t} 什么时候能修好",
        "工单 {t} 的优先级是多少", "{t} 处理到哪个环节了",
    ],
    "故障咨询": [
        "{d} {f}一般是什么原因", "{d}老是{f},怎么排查",
        "{d} {f}怎么处理才安全", "请教一下,{d} {f}的排查步骤",
        "{d}一直{f},是哪里坏了", "{d}出现{f},是正常现象吗",
    ],
    "巡检维保": [
        "季度巡检都检查哪些项目", "{l}的巡检周期是多久",
        "维保合同一年多少钱", "巡检报告什么时候出",
        "设备保养是你们负责还是自己搞", "年度维保包含哪些内容",
    ],
    "备件库存": [
        "备件 {s} 还有库存吗", "{s} 什么时候到货",
        "查一下 {s} 的库存余量", "{s} 缺货了,能加急采购吗",
        "领用备件 {s} 需要什么流程", "{s} 现在有现货吗",
    ],
    "安全规程": [
        "检修前要办工作票吗", "停送电要挂牌上锁吗",
        "{d} 开盖检修要注意什么安全事项", "高处作业有什么安全要求",
        "验电操作的正确步骤是什么", "动火作业需要什么手续",
    ],
    "服务承诺": [
        "P1 故障多久响应", "晚上有值班工程师吗",
        "节假日工单有人处理吗", "你们的响应时效承诺是什么",
        "报修后多久能到场", "P2 故障的处理时限是多久",
    ],
    "投诉": [
        "工单拖了三天没人管,我要投诉", "上次维修太敷衍了,这次必须给说法",
        "你们服务态度太差,我要投诉", "修完又坏,这事没完,我要投诉升级",
        "等了半天没人来,投诉你们", "处理结果我不满意,要求升级投诉",
    ],
    "设备信息": [
        "{d} 的型号参数是多少", "{d} 装在哪个产线",
        "查一下设备台账里 {d} 的信息", "{d} 的铭牌信息在哪看",
        "{d} 什么时候投用的", "{d} 的技术资料在哪查",
    ],
    "其他": [
        "今天天气真不错", "你们公司几点下班",
        "帮我翻译一段英文说明书", "能不能远程改 PLC 程序",
        "设备报废流程怎么走", "推荐一下附近有什么吃的",
    ],
}

# 多标签组合(字面同时命中两个类目)
MULTI: list[tuple[str, tuple[str, ...]]] = [
    ("{d} {f}了帮我报修,顺便查下工单 {t} 的进度", ("设备报修", "工单查询")),
    ("{d} {f}是什么原因?这台设备的型号信息也发我", ("故障咨询", "设备信息")),
    ("备件 {s} 到货了吗?到了帮我安排一下", ("备件库存", "设备报修")),
    ("巡检周期多久一次?顺便问下 P1 响应时效", ("巡检维保", "服务承诺")),
    ("修 {d} 要办工作票吗?多久能来人处理", ("安全规程", "服务承诺")),
]


def gen() -> list[dict]:
    samples: list[dict] = []
    rng = random.Random(7)
    for cls in TOPIC_CLASSES:
        tpls = TEMPLATES[cls.name]
        texts: set[str] = set()
        i = 0
        guard = 0
        while len(texts) < 40 and guard < 2000:
            guard += 1
            tpl = tpls[i % len(tpls)]
            pre = PRE[(i // len(tpls)) % len(PRE)]
            d = rng.choice(DEVICES); f = rng.choice(FAULTS)
            t = rng.choice(TICKETS); s = rng.choice(SPARES); l = rng.choice(LINES)
            text = tpl.format(d=d, f=f, t=t, s=s, l=l)
            text = (pre + text).replace("电机 过热", "电机过热").replace("变频器 过流报警", "变频器过流报警")
            i += 1
            if text in texts:
                continue
            texts.add(text)
            samples.append({"text": text, "labels": [cls.name], "origin": "simulated"})
        if len(texts) < 40:
            print(f"!! {cls.name} 仅生成 {len(texts)} 条")
    for tpl, labels in MULTI:
        for k in range(6):
            d = rng.choice(DEVICES); f = rng.choice(FAULTS)
            t = rng.choice(TICKETS); s = rng.choice(SPARES)
            pre = PRE[k % len(PRE)]
            text = (pre + tpl.format(d=d, f=f, t=t, s=s)).replace("电机 过热", "电机过热")
            samples.append({"text": text, "labels": list(labels), "origin": "simulated"})
    return samples


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    samples = gen()
    (OUT / "corpus_labeled.jsonl").write_text(
        "\n".join(json.dumps(s, ensure_ascii=False) for s in samples), encoding="utf-8")
    counts = {c.name: 0 for c in TOPIC_CLASSES}
    for s in samples:
        for lb in s["labels"]:
            counts[lb] += 1
    print("语料", len(samples), "条:", counts)

    train, val, test = split_dataset(samples)
    ds_out = OUT / "dataset"
    ds_out.mkdir(parents=True, exist_ok=True)
    for name, ds in (("train", train), ("val", val), ("test", test)):
        (ds_out / f"{name}.jsonl").write_text(
            "\n".join(json.dumps({"text": s["text"], "labels": s["labels"]}, ensure_ascii=False)
                      for s in ds), encoding="utf-8")
        print(name, len(ds))
    print("dataset 划分完成 → data/ch10/dataset/")


if __name__ == "__main__":
    main()
