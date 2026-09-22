"""迭代 2（吸收外部项目机制）的测试：预分类器四态、模型 vs 正则一致性、overkill、唯一 id、评估回归门。"""
from collections import Counter

import pytest

from pipeline import checks as C
from pipeline import metrics as M
from pipeline.compare import compare
from pipeline.evaluate import evaluate, gate
from pipeline.loader import ROOT, load_schema
from pipeline.preclassify import classify_line, classify_raw

SCHEMA = load_schema()


@pytest.mark.parametrize("line,old,new,unit,mode", [
    ("Cooldown reduced from 12 to 10 seconds. (5v5)", 12, 10, "s", "5v5"),
    ("Regeneration rate increased from 12.5% to 15% per second.", 12.5, 15, "pct", None),
    ("Cast time decreased from 0.065s to 0.016s.", 0.065, 0.016, "s", None),
    ("Ultimate Charge cost reduction increased to 60% (Up from 50%).", 50, 60, "pct", None),
    ("Cooldown reduction per target increased to 2.5s (Up from 2s).", 2, 2.5, "s", None),
    ("Return damage reduced to 30 (Down from 40).", 40, 30, None, None),
    ("Projectile travel speed reduced from 24 to 18 meters per second.", 24, 18, "m_per_s", None),
    ("Armor reduced from 300 to 250 (6v6).", 300, 250, None, "6v6"),
])
def test_numeric_patterns(line, old, new, unit, mode):
    r = classify_line(line)
    assert r["state"] == "NUMERIC" and (r["old"], r["new"]) == (old, new) and r["mode"] == mode
    assert r["unit"] == unit


def test_verb_number_contradiction_is_flagged_not_rewritten():
    r = classify_line("Damage reduced from 10 to 12.")
    assert r["state"] == "NUMERIC" and (r["old"], r["new"]) == (10, 12) and r.get("suspicious")


@pytest.mark.parametrize("line,state,tag", [
    ("Notches on side of shield reduced in size.", "KNOWN_SEMANTIC", "VISUAL_ONLY"),
    ("Explosive bolt impact sound effects reduced.", "KNOWN_SEMANTIC", "AUDIO_ONLY"),
    ("A new first-person bootup animation lasting 1 second has been added.", "KNOWN_SEMANTIC", "ANIMATION_ADDED"),
    ("Ultimate Cost reduced by 6%.", "KNOWN_SEMANTIC", "RELATIVE_ONLY_CHANGE"),
    ("Stuns and mobility locking effects on a carried target now disconnect Lifeline.", "KNOWN_SEMANTIC", "INTERACTION_RULE"),
])
def test_semantic_ontology(line, state, tag):
    r = classify_line(line)
    assert (r["state"], r["tag"]) == (state, tag)


def test_unknown_and_partial_states():
    assert classify_line("Now uses a completely different resource model.")["state"] == "UNKNOWN"
    r = classify_line("Camera shake reduced during ultimate.")   # 与 CAMERA_CONTROL 共享 camera 一词
    assert r["state"] == "PARTIALLY_CLASSIFIED" and "camera" in r["keyword_hits"]


def test_real_corpus_has_no_silent_misparse():
    """官方页面全部 68 条真实条目：数值行必须全部 NUMERIC；非数值行不得被误判 NUMERIC；UNKNOWN 数量登记（本体回填的待办）。"""
    lines = [l for l in open(ROOT / "config" / "corpus" / "patch_lines_2026-09-22.txt", encoding="utf-8") if l.startswith("- ")]
    recs = [classify_line(l) for l in lines]
    c = Counter(r["state"] for r in recs)
    assert c["NUMERIC"] == 58, c        # 含 "to 20% of healing (Down from 30%)" 这种中间带修饰语的形态
    for r in recs:
        if r["state"] == "NUMERIC":
            assert r["old"] != r["new"]
    assert c["UNKNOWN"] == 0, [r["line"] for r in recs if r["state"] == "UNKNOWN"]
    assert not [r for r in recs if r.get("suspicious")], [r["line"] for r in recs if r.get("suspicious")]


def test_classify_raw_skips_dev_comments_and_keeps_hierarchy():
    raw = open(ROOT / "config" / "patches" / "2026-09-08_raw.txt", encoding="utf-8").read()
    recs = classify_raw(raw, "D.Mon")
    assert {r["ability"] for r in recs} >= {"Plasma Saber", "Power Barrier", "Call Mech", "Portable Fusion Repeater"}
    assert not any("Developer Comments" in r["line"] for r in recs)
    assert [r for r in recs if r["ability"] is None][0]["mode"] == "6v6"


def test_compare_flags_llm_numbers_that_disagree_with_regex():
    golden = {"heroes": {"h": {"overall_direction": "nerf", "changes": [{"path": "weapons.g.damage_max", "from": 65, "to": 60, "expected_direction": "nerf"}], "unmapped": []}}}
    agent = {"heroes": {"h": {"overall_direction": "nerf", "changes": [{"path": "weapons.g.damage_max", "from": 65, "to": 60, "expected_direction": "nerf",
                                                                        "why": "Damage reduced from 65 to 50."}], "unmapped": []}}}
    assert compare(agent, golden)["totals"]["numeric_vs_regex_mismatch"] == 1
    agent["heroes"]["h"]["changes"][0]["why"] = "Damage reduced from 65 to 60."
    assert compare(agent, golden)["totals"]["numeric_vs_regex_mismatch"] == 0


def test_overkill_explains_breakpoint_proximity():
    saber65 = {"id": "s", "hit_type": "melee", "damage_max": 65, "headshot_mult": 1}
    saber60 = {"id": "s", "hit_type": "melee", "damage_max": 60, "headshot_mult": 1}
    assert M.overkill(saber65, 250, "body")["value"] == 10      # 4×65−250：离断点只剩 10
    assert M.overkill(saber60, 250, "body")["value"] == 50      # 5×60−250：多打一刀后余量变大


def test_r9_records_overkill():
    before = {"weapons": [{"id": "s", "hit_type": "melee", "damage_max": 65, "headshot_mult": 1}], "provenance": {}}
    after = {"weapons": [{"id": "s", "hit_type": "melee", "damage_max": 60, "headshot_mult": 1}], "provenance": {}}
    from pipeline.loader import load_invariants
    res = [r for r in C.R9_shots_to_kill_breakpoint(load_invariants(), "h", before, after) if r["records"].get("target_hp") == 250]
    assert res[0]["records"]["overkill_before"] == 10 and res[0]["records"]["overkill_after"] == 50


def test_f8_unique_ids():
    dup = {"weapons": [{"id": "gun"}, {"id": "gun"}], "abilities": []}
    assert C.F8_unique_ids(SCHEMA, "h", dup)[0]["status"] == "FAIL"
    assert C.F8_unique_ids(SCHEMA, "h", {"weapons": [{"id": "a"}], "abilities": [{"id": "b"}]})[0]["status"] == "PASS"


def test_evaluate_and_gate_detect_regression():
    cur = evaluate()
    assert cur["n_cases"] >= 7 and cur["metrics"]["numeric_precision"] is not None
    worse = {"metrics": {**cur["metrics"], "numeric_precision": 1.0}, "per_case": cur["per_case"]}
    cur_bad = {**cur, "metrics": {**cur["metrics"], "numeric_precision": 0.5}}
    assert gate(cur_bad, worse)
    assert gate(cur, cur) == []
