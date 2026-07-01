from mn_encounter_toolkit.web.layer_reference import LAYER_BY_NUMBER, find_rules


def test_layer_info_covers_all_four_layers():
    assert set(LAYER_BY_NUMBER) == {1, 2, 3, 4}
    assert len(LAYER_BY_NUMBER[3].rules) >= 18


def test_find_rules_matches_rule_id():
    matches = find_rules("L3-BILLING-UMPI")
    assert len(matches) == 1
    layer, rule = matches[0]
    assert layer.number == 3
    assert rule.rule_id == "L3-BILLING-UMPI-REQUIRED"


def test_find_rules_matches_keyword():
    matches = find_rules("CLM02")
    assert any(rule.rule_id == "L4-CHARGE-BALANCE" for _, rule in matches)
