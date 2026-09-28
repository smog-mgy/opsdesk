"""型号机械闸:拿 ch04 评估真判出来的那条幻觉当第一条用例。"""
from app.core import model_guard as g

EVIDENCE = (" 空压机 变频版(型号 MH-AC30): 排气量:6m3/min\n"
    " 三相异步电机(型号 M-1001): 额定功率 7.5kW")
ANSWER_BAD = "确认排气量正常(针对 MH-CAD1 型号),空压机(MH-AC30)质保 12 个月。"
ANSWER_OK = "确认排气量正常(针对 MH-AC30 型号)。"


def test_揪出证据里没有的型号():
    assert g.unsupported_models(ANSWER_BAD, EVIDENCE) == ["MH-CAD1"]


def test_型号都来自证据时放行():
    assert g.unsupported_models(ANSWER_OK, EVIDENCE) == []


def test_没提型号也放行():
    assert g.unsupported_models("备件已到,待派单[1]。", EVIDENCE) == []


def test_多个型号按出现顺序去重():
    bad = g.unsupported_models("MH-XX9 与 MH-YY1,再提一次 MH-XX9", EVIDENCE)
    assert bad == ["MH-XX9", "MH-YY1"]


def test_大小写不一致也算没命中():
    # 型号本该是从证据里复制过去的,大小写都对不上说明是模型自己写的
    assert g.unsupported_models("针对 mh-ac30 型号", EVIDENCE) == []      # 不匹配型号形态,不误报
    assert g.unsupported_models("针对 MH-Ac30 型号", EVIDENCE) == ["MH-Ac30"]


def test_不把普通编号当型号():
    for s in ("[1]", "6m3/min", "7.5kW", "MH-", "MHLP100"):
        assert g.models_in(s) == [], s


def test_重写提示只点名不猜正确型号():
    hint = g.repair_hint(["MH-CAD1"])
    assert "MH-CAD1" in hint and "MH-AC30" not in hint
