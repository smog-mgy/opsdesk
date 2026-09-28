from app.core.taxonomy import (ID2LABEL, LABEL2ID, NUM_CLASSES, TOPIC_CLASSES,
                               TOPIC_NAMES, terminology_table)


def test_ten_unique_classes():
    assert NUM_CLASSES == 10
    assert len(set(TOPIC_NAMES)) == 10


def test_four_leads_first():
    assert TOPIC_NAMES[:4] == ("设备报修", "工单查询", "故障咨询", "巡检维保")


def test_every_class_has_boundary_examples_severity():
    for c in TOPIC_CLASSES:
        assert c.boundary.strip()
        assert len(c.examples) >= 3 or c.name == "其他"
        assert c.severity in ("严", "中", "宽")


def test_label_id_roundtrip():
    for name, i in LABEL2ID.items():
        assert ID2LABEL[i] == name
    assert LABEL2ID["设备报修"] == 0 and LABEL2ID["其他"] == 9


def test_terminology_table_covers_all():
    table = terminology_table()
    for name in TOPIC_NAMES:
        assert name in table
