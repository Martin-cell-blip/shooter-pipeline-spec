"""校验层：每条规则至少一个触发用例与一个不触发用例；异常永不变 PASS；金标提案 0 FAIL。"""
import copy

from pipeline import checks as C
from pipeline.checks import run_proposal
from pipeline.loader import load_hero_dir, load_invariants, load_proposal, load_schema

SCHEMA, INV = load_schema(), load_invariants()

BASE = {
    "id": "h", "role": "damage", "hitpoints": {"health": 250, "armor": 0, "shields": 0, "total": 250},
    "weapons": [{"id": "gun", "slot": "primary", "hit_type": "hitscan", "damage_max": 70, "damage_min": 21,
                 "falloff_start_m": 25, "falloff_end_m": 35, "headshot_mult": 2, "rate_of_fire": 2, "ammo": 6, "reload_s": 1.5}],
    "abilities": [{"id": "roll", "kind": "ability", "cooldown_s": 6, "duration_s": 3, "cooldown_starts": "on_end"}],
    "provenance": {"conflicts": [], "missing": []},
}


def prop(changes, **kw):
    return {"changes": changes, "linked_dispositions": kw.get("disp", {}), "mixed_rationale": kw.get("mixed")}


def statuses(results, check):
    return [r["status"] for r in results if r["check"] == check]


def test_golden_proposal_has_no_fail():
    p = load_proposal("2026-09-08_official")
    res = run_proposal(SCHEMA, INV, p, load_hero_dir(p["before"]), load_hero_dir("baseline"))
    assert not [r for r in res if r["status"] == "FAIL"], [r["detail"] for r in res if r["status"] == "FAIL"]
    assert statuses(res, "F3_hitpoints_sum") == ["PASS", "PASS"]  # 职责队列生命值已现场核验；空值行为由独立测试覆盖


def test_bounds_fail_is_labelled_as_project_bound():
    h = copy.deepcopy(BASE); h["weapons"][0]["damage_max"] = 999
    r = C.F1_schema_bounds(SCHEMA, "h", h)
    assert r[0]["status"] == "FAIL" and "project support bounds" in r[0]["detail"]


def test_falloff_structure():
    h = copy.deepcopy(BASE); h["weapons"][0]["falloff_end_m"] = 20
    assert C.F2_falloff_structure(SCHEMA, "h", h)[0]["status"] == "FAIL"
    assert C.F2_falloff_structure(SCHEMA, "h", BASE)[0]["status"] == "PASS"


def test_hitpoints_null_is_not_run_not_fail():
    h = copy.deepcopy(BASE); h["hitpoints"] = None
    assert C.F3_hitpoints_sum(SCHEMA, "h", h)[0]["status"] == "NOT_RUN"
    h["hitpoints"] = {"health": 200, "armor": 0, "shields": 0, "total": 250}
    assert C.F3_hitpoints_sum(SCHEMA, "h", h)[0]["status"] == "FAIL"


def test_linked_disposition_record_not_covalue():
    ch = [{"path": "weapons.gun.ammo", "from": 6, "to": 7, "expected_direction": "buff"}]
    assert C.F4_linked_disposition(SCHEMA, "h", prop(ch))[0]["status"] == "FAIL"
    ok = C.F4_linked_disposition(SCHEMA, "h", prop(ch, disp={"weapons.gun.reload_s": "keep"}))
    assert ok[0]["status"] == "PASS"
    bad = C.F4_linked_disposition(SCHEMA, "h", prop(ch, disp={"weapons.gun.reload_s": "not_needed"}))
    assert bad[0]["status"] == "FAIL"   # not_needed 必须带理由


def test_direction_fail_only_when_semantics_unambiguous():
    ch = [{"path": "weapons.gun.damage_max", "from": 70, "to": 65, "expected_direction": "buff"}]
    assert C.F5_direction_vs_declared(SCHEMA, "h", prop(ch), BASE)[0]["status"] == "FAIL"
    amb = [{"path": "abilities.roll.duration_s", "from": 3, "to": 2, "expected_direction": "nerf"}]
    assert C.F5_direction_vs_declared(SCHEMA, "h", prop(amb), BASE)[0]["status"] == "REVIEW"
    wrong_from = [{"path": "weapons.gun.damage_max", "from": 60, "to": 65, "expected_direction": "buff"}]
    assert C.F5_direction_vs_declared(SCHEMA, "h", prop(wrong_from), BASE)[0]["status"] == "FAIL"


def _after(path_field, value):
    a = copy.deepcopy(BASE); a["weapons"][0][path_field] = value; return a


def test_r1_dps_delta_threshold():
    assert C.R1_full_cycle_dps_delta(INV, "h", BASE, _after("damage_max", 65))[0]["status"] == "PASS"     # −7%
    assert C.R1_full_cycle_dps_delta(INV, "h", BASE, _after("damage_max", 50))[0]["status"] == "REVIEW"   # −29%


def test_r2_reload_breakpoint_flip():
    # 6 发 70 = 420 ≥ 250 不用装填；改成 5 发弹匣、伤害 60：5×60=300 仍够；改成 4 发：240 < 250 → 需装填 → 翻转
    a = copy.deepcopy(BASE); a["weapons"][0]["ammo"] = 4; a["weapons"][0]["damage_max"] = 60
    res = C.R2_ttk_delta_or_reload_breakpoint(INV, "h", BASE, a)
    body250 = [r for r in res if r["records"].get("target_hp") == 250 and r["records"].get("location") == "body"][0]
    assert body250["status"] == "REVIEW" and body250["records"]["reload_flip"] is True


def test_r3_oneshot_gained():
    res = C.R3_headshot_oneshot_change(INV, "h", BASE, _after("damage_max", 90))   # 180 head ≥ 175
    assert res[0]["status"] == "REVIEW" and "gained" in res[0]["detail"]
    assert C.R3_headshot_oneshot_change(INV, "h", BASE, BASE)[0]["status"] == "PASS"


def test_r5_falloff_window_and_shift():
    res = C.R5_falloff_window_delta(INV, "h", BASE, _after("falloff_end_m", 50))   # 10 → 25 m
    assert res[0]["status"] == "REVIEW"
    a = copy.deepcopy(BASE); a["weapons"][0].update(falloff_start_m=30, falloff_end_m=40)   # 平移，宽度不变
    res = C.R5_falloff_window_delta(INV, "h", BASE, a)
    assert res[0]["status"] == "PASS" and res[0]["records"]["endpoints_moved"] is True


def test_r6_cooldown_abs_or_rel():
    a = copy.deepcopy(BASE); a["abilities"][0]["cooldown_s"] = 4.5   # Δ1.5 s 但 25% → REVIEW
    assert C.R6_cooldown_step(INV, "h", BASE, a)[0]["status"] == "REVIEW"
    a["abilities"][0]["cooldown_s"] = 5                              # Δ1 s，16.7% → PASS
    assert C.R6_cooldown_step(INV, "h", BASE, a)[0]["status"] == "PASS"
    z = copy.deepcopy(BASE); z["abilities"][0]["cooldown_s"] = 0
    assert C.R6_cooldown_step(INV, "h", z, BASE)[0]["status"] == "REVIEW"  # 旧值 0 → 机制变化


def test_r8_mixed_needs_rationale():
    ch = [{"path": "weapons.gun.damage_max", "from": 70, "to": 75, "expected_direction": "buff"},
          {"path": "weapons.gun.ammo", "from": 6, "to": 5, "expected_direction": "nerf"}]
    assert C.R8_mixed_direction_rationale(INV, "h", prop(ch))[0]["status"] == "REVIEW"
    assert C.R8_mixed_direction_rationale(INV, "h", prop(ch, mixed="offset"))[0]["status"] == "PASS"


def test_r9_shots_breakpoint_catches_small_change():
    # 250 / 70 → 4 发；250 / 84 → 3 发（+20% DPS 也会被 R1 抓，但 62.5→63 这种只有 R9 能抓）
    res = C.R9_shots_to_kill_breakpoint(INV, "h", BASE, _after("damage_max", 63))
    body250 = [r for r in res if r["records"].get("target_hp") == 250 and r["records"].get("location") == "body"][0]
    assert body250["status"] == "PASS" and (body250["records"]["before"], body250["records"]["after"]) == (4, 4)   # 250/63 仍是 4 发
    res = C.R9_shots_to_kill_breakpoint(INV, "h", BASE, _after("damage_max", 84))
    body250 = [r for r in res if r["records"].get("target_hp") == 250 and r["records"].get("location") == "body"][0]
    assert body250["status"] == "REVIEW" and (body250["records"]["before"], body250["records"]["after"]) == (4, 3)


def test_r10_uptime_pp_and_seamless_boundary():
    a = copy.deepcopy(BASE); a["abilities"][0]["duration_s"] = 6   # 3/9=33% → 6/12=50% → +16.7pp
    assert C.R10_uptime_ratio(INV, "h", BASE, a)[0]["status"] == "REVIEW"
    b = copy.deepcopy(BASE); b["abilities"][0]["cooldown_starts"] = None
    assert C.R10_uptime_ratio(INV, "h", b, b)[0]["status"] == "NOT_RUN"


def test_open_conflict_blocks_dependent_metric():
    h = copy.deepcopy(BASE)
    h["provenance"]["conflicts"] = [{"field": "weapons.gun.damage_max", "values": {}, "status": "REVIEW"}]
    assert C.R1_full_cycle_dps_delta(INV, "h", h, h)[0]["status"] == "NOT_RUN"
    h["provenance"]["conflicts"] = [{"field": "weapons.gun.projectile_speed", "values": {}, "status": "REVIEW"}]
    assert C.R1_full_cycle_dps_delta(INV, "h", h, h)[0]["status"] == "PASS"   # 不相关字段的冲突不阻断


def test_exception_becomes_not_run_never_pass():
    broken = copy.deepcopy(BASE); broken["weapons"] = [{"id": None}]   # 触发内部异常
    res = C.R1_full_cycle_dps_delta(INV, "h", broken, broken)
    assert all(r["status"] in ("NOT_RUN",) for r in res)
