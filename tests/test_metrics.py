"""度量层：用手算可核的数字锁住计算口径（离散射击、装填、beam、NOT_RUN 门控）。"""
import math

from pipeline import metrics as M

SC = {"targets_hp": [175, 250], "hit_location": ["body", "head"], "distance_m": 0, "first_shot_at_s": 0, "includes_travel_time": False}

CASSIDY = {"id": "peacekeeper", "hit_type": "hitscan", "damage_max": 70, "damage_min": 21, "falloff_start_m": 25, "falloff_end_m": 35,
           "headshot_mult": 2, "rate_of_fire": 2, "ammo": 6, "reload_s": 1.5}
TRACER = {"id": "pulse_pistols", "hit_type": "hitscan", "damage_max": 5.75, "headshot_mult": 2, "rate_of_fire": 20,
          "pellets_per_shot": 2, "ammo_consumption": 2, "ammo": 40, "reload_s": 1}
TESLA = {"id": "tesla_cannon", "hit_type": "beam", "damage_max": 70, "headshot_mult": 1, "ammo": 120, "ammo_per_s": 20, "reload_s": 1.5}


def test_full_cycle_dps_includes_reload():
    r = M.full_cycle_dps(CASSIDY, SC)
    # 6 发 × 70 = 420；射击 6/2 = 3 s；+1.5 s 装填 → 420 / 4.5
    assert r["status"] == "OK" and math.isclose(r["value"], 420 / 4.5)
    assert r["theoretical_dps_no_reload"] == 140


def test_ttk_discrete_shots_first_shot_at_zero():
    r = M.ttk(CASSIDY, 250, "body", SC)
    assert r["shots"] == 4 and math.isclose(r["value"], 3 / 2) and r["requires_reload"] is False


def test_tracer_250_needs_reload():
    # 20 次射击事件 × 11.5 = 230 < 250 → 第 22 发前须装填一次
    r = M.ttk(TRACER, 250, "body", SC)
    assert r["shots"] == 22 and r["requires_reload"] is True
    assert math.isclose(r["value"], 21 / 20 + 1)


def test_tracer_175_no_reload():
    r = M.ttk(TRACER, 175, "body", SC)
    assert r["shots"] == 16 and r["requires_reload"] is False


def test_beam_ttk_and_cycle():
    r = M.ttk(TESLA, 250, "body", SC)
    assert math.isclose(r["value"], 250 / 70) and r["requires_reload"] is False
    c = M.full_cycle_dps(TESLA, SC)
    assert math.isclose(c["value"], 70 * 6 / 7.5)


def test_headshot_oneshot_plain_vs_charged():
    assert M.headshot_oneshot(CASSIDY, 175)["value"] is False
    charged = {"id": "x", "damage_max": 120, "headshot_mult": 1.5, "charged": True}
    assert M.headshot_oneshot(charged, 175)["status"] == "NOT_RUN"
    charged["charge_conditions"] = {"energy": "full"}
    assert M.headshot_oneshot(charged, 175)["value"] is True


def test_uptime_requires_cooldown_starts():
    a = {"id": "b", "duration_s": 7, "cooldown_s": 10}
    assert M.uptime_ratio(a)["status"] == "NOT_RUN"
    a["cooldown_starts"] = "on_end"
    assert math.isclose(M.uptime_ratio(a)["value"], 7 / 17)
    a["cooldown_starts"] = "on_cast"
    assert math.isclose(M.uptime_ratio(a)["value"], 0.7)


def test_rel_change_zero_base_is_none():
    assert M.rel_change(0, 5) is None
