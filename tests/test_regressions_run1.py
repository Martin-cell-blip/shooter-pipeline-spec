"""run 1（2026-09-22，docs/RUN_LOG.md）暴露的缺陷固化为回归测试。每条注明指回的记录。"""
import copy

from pipeline import checks as C
from pipeline.agent import PROPOSAL_FORMAT
from pipeline.checks import run_proposal
from pipeline.compare import acceptance_ok, compare
from pipeline.loader import load_hero_dir, load_invariants, load_proposal, load_schema

SCHEMA, INV = load_schema(), load_invariants()


def test_G1_golden_wuyang_direction_is_nerf():
    """G1：金标误写 buff 被 F5 抓出；修正后金标 09-08 必须 0 FAIL。"""
    p = load_proposal("2026-09-08_official")
    los = [c for c in p["heroes"]["wuyang"]["changes"] if c["path"].endswith("los_timeout_s")][0]
    assert los["expected_direction"] == "nerf"
    res = run_proposal(SCHEMA, INV, p, load_hero_dir(p["before"]), load_hero_dir("baseline"))
    assert not [r for r in res if r["status"] == "FAIL"], [r["detail"] for r in res if r["status"] == "FAIL"]


def test_G2_linked_disposition_not_required_when_partner_absent():
    """G2：近战武器没有 damage_min，改 damage_max 不得要求处置。"""
    before = {"weapons": [{"id": "saber", "hit_type": "melee", "damage_max": 65}]}
    ch = [{"path": "weapons.saber.damage_max", "from": 65, "to": 60, "expected_direction": "nerf"}]
    r = C.F4_linked_disposition(SCHEMA, "h", {"changes": ch, "linked_dispositions": {}}, before)
    assert r[0]["status"] == "PASS"
    before_with = {"weapons": [{"id": "saber", "hit_type": "hitscan", "damage_max": 65, "damage_min": 20}]}
    r = C.F4_linked_disposition(SCHEMA, "h", {"changes": ch, "linked_dispositions": {}}, before_with)
    assert r[0]["status"] == "FAIL"


def test_A1_disposition_keyed_on_changed_field_is_not_accepted():
    """A1（D.Mon run 1）：处置键写在被改字段上而不是伙伴字段上 → 仍 FAIL。"""
    before = {"weapons": [{"id": "pfr", "hit_type": "hitscan", "damage_max": 12, "falloff_start_m": 30, "falloff_end_m": 40}]}
    ch = [{"path": "weapons.pfr.falloff_start_m", "from": 30, "to": 20, "expected_direction": "nerf"}]
    wrong = {"weapons.pfr.falloff_start_m": "not_needed: keep end"}
    assert C.F4_linked_disposition(SCHEMA, "h", {"changes": ch, "linked_dispositions": wrong}, before)[0]["status"] == "FAIL"
    right = {"weapons.pfr.falloff_end_m": "keep"}
    assert C.F4_linked_disposition(SCHEMA, "h", {"changes": ch, "linked_dispositions": right}, before)[0]["status"] == "PASS"


def test_A2_prompt_grammar_covers_hitpoints_by_mode_and_partner_key():
    """A2（D.Mon run 1 两次）：Agent 按我给的路径语法拼出 hitpoints.armor.v6——语法必须写明 hitpoints_by_mode。"""
    assert "hitpoints_by_mode.<v5|v6>.<field>" in PROPOSAL_FORMAT
    assert "<partner_path>" in PROPOSAL_FORMAT
    assert "Developer Comments" in PROPOSAL_FORMAT   # A3：unmapped 不收注释


def test_A2_wrong_hitpoints_path_is_caught_by_apply():
    p = load_proposal("2026-09-17_official")
    bad = copy.deepcopy(p)
    bad["heroes"]["dmon"]["changes"][0]["path"] = "hitpoints.armor.v5"
    res = run_proposal(SCHEMA, INV, bad, load_hero_dir(p["before"]), load_hero_dir("baseline"))
    assert any(r["check"] == "apply" and r["status"] == "FAIL" for r in res)


def test_compare_unmapped_classification():
    """compare 必须区分：正确保留 / 硬凑进字段 / 静默丢弃 / 把注释当条目。"""
    golden = {"heroes": {"h": {"overall_direction": "nerf", "changes": [{"path": "weapons.g.damage_max", "from": 65, "to": 60, "expected_direction": "nerf"}],
                                "unmapped": ["Cast time decreased from 0.065s to 0.016s.", "Notches on side of shield reduced in size."]}}}
    agent = {"heroes": {"h": {"overall_direction": "nerf",
                              "changes": [{"path": "weapons.g.damage_max", "from": 65, "to": 60, "expected_direction": "nerf"},
                                          {"path": "abilities.b.cast_time_s", "from": 0.065, "to": 0.016, "expected_direction": "buff", "why": "Cast time decreased from 0.065s to 0.016s."}],
                              "unmapped": ["Projected Barrier remains unchanged, encouraging more proactive use on allies."]}}}
    r = compare(agent, golden)
    t = r["totals"]
    assert t["extra"] == 1 and t["unmapped_forced"] == 1 and t["unmapped_dropped"] == 1 and t["agent_extra_unmapped"] == 1
    assert not acceptance_ok(r)
    good = {"heroes": {"h": {"overall_direction": "nerf", "changes": golden["heroes"]["h"]["changes"], "unmapped": list(golden["heroes"]["h"]["unmapped"])}}}
    assert acceptance_ok(compare(good, golden))


def test_empty_proposal_fails_acceptance():
    golden = load_proposal("2026-09-17_official")
    assert not acceptance_ok(compare({"heroes": {"dmon": {"changes": [], "unmapped": []}}}, golden))


def test_A4_line_both_mapped_and_unmapped_fails():
    """A4（D.Mon 09-17 run 2）：把已映射的行又抄进 unmapped → F7 FAIL。"""
    ph = {"changes": [{"path": "abilities.fusion_repeater.damage", "from": 16, "to": 15, "expected_direction": "nerf", "why": "Fusion Repeater: Damage reduced from 16 to 15."}],
          "unmapped": ["- Damage reduced from 16 to 15.", "- Damage per bullet reduced from 45 to 36."]}
    r = C.F7_unmapped_vs_changes(SCHEMA, "h", ph)
    assert [x["status"] for x in r] == ["FAIL"]
    ph["unmapped"] = ["- Damage per bullet reduced from 45 to 36."]
    assert C.F7_unmapped_vs_changes(SCHEMA, "h", ph)[0]["status"] == "PASS"
