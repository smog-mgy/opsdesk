"""ch10 权威归并术语表:全系统唯一一份,10 类运维主题类目。
数据处理、预标、训练、推理、评测、前端全部 import 这里,不许各自抄一份。
元组顺序即 label id,训练/推理共用。
severity 是容错档位:归错会带偏补知识优先级的类目从严。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TopicClass:
    name: str
    boundary: str                 # 一句边界说明:什么算这一类,近邻类目靠它划开
    examples: tuple[str, ...]     # 用户的说法示例
    severity: str                 # 容错档位:严 / 中 / 宽


TOPIC_CLASSES: tuple[TopicClass, ...] = (
    TopicClass("设备报修", "设备故障需要报修、建工单;修归这里,咨询归故障咨询",
               ("报修", "设备坏了", "要修", "停机了", "帮我建个工单"), "严"),
    TopicClass("工单查询", "工单进度、状态、优先级、派单情况",
               ("工单到哪了", "处理进度", "查工单", "谁在处理", "工单状态"), "严"),
    TopicClass("故障咨询", "故障现象怎么排查、可能原因;不带报修意图的咨询归这里",
               ("电机过热", "过流报警", "排查步骤", "什么原因", "怎么查"), "严"),
    TopicClass("巡检维保", "巡检内容、周期、维保合同与费用",
               ("巡检", "维保", "保养", "合同", "季度巡检", "维保费用"), "中"),
    TopicClass("备件库存", "备件有没有、什么时候到货、领用",
               ("备件", "库存", "什么时候到货", "领用", "有没有现货"), "中"),
    TopicClass("安全规程", "安全作业、停送电、工作票、LOTO",
               ("安全", "挂牌", "验电", "工作票", "停送电", "上锁"), "严"),
    TopicClass("服务承诺", "响应时效、值班安排、SLA 等级",
               ("多久响应", "几点有人", "P1", "P2", "P3", "值班"), "中"),
    TopicClass("投诉", "对处理不满意、要求升级",
               ("投诉", "不满意", "态度差", "要投诉", "升级"), "中"),
    TopicClass("设备信息", "设备台账、参数、型号、位置",
               ("设备参数", "型号", "在哪条线", "铭牌", "台账"), "中"),
    TopicClass("其他", "上面都对不上的,先兜底",
               ("闲聊", "在吗", "转人工", "几点上班"), "宽"),
)

TOPIC_NAMES: tuple[str, ...] = tuple(c.name for c in TOPIC_CLASSES)
LABEL2ID: dict[str, int] = {name: i for i, name in enumerate(TOPIC_NAMES)}
ID2LABEL: dict[int, str] = {i: name for i, name in enumerate(TOPIC_NAMES)}
NUM_CLASSES = len(TOPIC_CLASSES)
SEVERITY: dict[str, str] = {c.name: c.severity for c in TOPIC_CLASSES}


def terminology_table() -> str:
    """预标/造数 prompt 用的术语表文本:类目:边界说明(示例)。"""
    return "\n".join(
        f"- {c.name}:{c.boundary}(示例:{'、'.join(c.examples)})" for c in TOPIC_CLASSES
    )
