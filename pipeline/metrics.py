"""固定场景下的派生指标。每个函数要么返回带完整记录的结果 dict，要么返回 {'status': 'NOT_RUN', 'reason': ...}。
不做任何跨英雄判断；场景参数见 spec/invariants.yaml → scenario。"""
from __future__ import annotations

import math
from typing import Any

NOT_RUN = "NOT_RUN"


def _nr(reason: str) -> dict:
    return {"status": NOT_RUN, "reason": reason}


def _num(x: Any) -> float | None:
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def weapon_damage_per_event(w: dict, location: str) -> float | None:
    dmg = _num(w.get("damage_max"))
    if dmg is None:
        return None
    pellets = w.get("pellets_per_shot") or 1
    mult = _num(w.get("headshot_mult")) or 1
    per = dmg * (mult if location == "head" else 1)
    return per * pellets


def full_cycle_dps(w: dict, scenario: dict) -> dict:
    """完整周期身体 DPS：一弹匣伤害 / (射击时间 + 装填时间)。beam 按每秒伤害与每秒弹药消耗。"""
    if w.get("hit_type") == "beam":
        dps = _num(w.get("damage_max"))
        ammo, reload = _num(w.get("ammo")), _num(w.get("reload_s"))
        if dps is None:
            return _nr("beam damage per second missing")
        if ammo is None or reload is None or not w.get("ammo_per_s"):
            return {"status": "OK", "value": dps, "note": "beam: reload cycle not modelled (ammo_per_s absent), value = damage per second while firing"}
        fire_s = ammo / w["ammo_per_s"]
        return {"status": "OK", "value": dps * fire_s / (fire_s + reload), "fire_s": fire_s, "reload_s": reload}
    per = weapon_damage_per_event(w, "body")
    rof, ammo, reload = _num(w.get("rate_of_fire")), _num(w.get("ammo")), _num(w.get("reload_s"))
    if per is None or rof is None:
        return _nr("damage_max or rate_of_fire missing")
    if ammo is None or reload is None:
        return _nr("ammo or reload_s missing (full-cycle DPS needs both)")
    consumption = w.get("ammo_consumption") or 1
    shots = math.floor(ammo / consumption)
    if shots < 1:
        return _nr("magazine holds < 1 shot")
    fire_s = shots / rof
    return {"status": "OK", "value": per * shots / (fire_s + reload), "shots_per_magazine": shots,
            "fire_s": fire_s, "reload_s": reload, "theoretical_dps_no_reload": per * rof}


def shots_to_kill(w: dict, hp: float, location: str) -> dict:
    per = weapon_damage_per_event(w, location)
    if per is None:
        return _nr("damage_max missing")
    if location == "head" and (_num(w.get("headshot_mult")) or 1) <= 1:
        return {"status": "OK", "value": None, "note": "weapon cannot headshot"}
    if per <= 0:
        return {"status": "OK", "value": None, "note": "weapon deals no damage"}
    return {"status": "OK", "value": math.ceil(hp / per), "damage_per_event": per}


def overkill(w: dict, hp: float, location: str) -> dict:
    """击杀所需射击事件的总伤害减去目标生命值（DRG calculator 的 Average Overkill 在固定场景下的确定性版本）。
    解释小幅伤害改动为什么会跨断点：overkill 越接近 0，再削一点就多打一枪。"""
    stk = shots_to_kill(w, hp, location)
    if stk["status"] != "OK" or stk["value"] is None:
        return stk
    total = stk["value"] * stk["damage_per_event"]
    return {"status": "OK", "value": total - hp, "shots": stk["value"], "margin_ratio": (total - hp) / hp}


def ttk(w: dict, hp: float, location: str, scenario: dict) -> dict:
    """离散射击事件：第 k 发落在 (k-1)/rof；弹匣耗尽加一次 reload_s。beam 连续。"""
    rec = {"distance_m": scenario.get("distance_m", 0), "first_shot_at_s": scenario.get("first_shot_at_s", 0),
           "includes_travel_time": scenario.get("includes_travel_time", False), "target_hp": hp, "location": location}
    if w.get("hit_type") == "beam":
        dps = _num(w.get("damage_max"))
        if dps is None or dps <= 0:
            return _nr("beam dps missing")
        if location == "head":
            return {"status": "OK", "value": None, "note": "beam cannot headshot", **rec}
        ammo, per_s = _num(w.get("ammo")), _num(w.get("ammo_per_s"))
        t = hp / dps
        needs_reload = bool(ammo and per_s and t > ammo / per_s)
        if needs_reload:
            t += _num(w.get("reload_s")) or 0
        return {"status": "OK", "value": t, "requires_reload": needs_reload, **rec}
    stk = shots_to_kill(w, hp, location)
    if stk["status"] != "OK":
        return stk
    n = stk["value"]
    if n is None:
        return {"status": "OK", "value": None, "note": stk.get("note"), **rec}
    rof, ammo, reload = _num(w.get("rate_of_fire")), _num(w.get("ammo")), _num(w.get("reload_s"))
    if rof is None:
        return _nr("rate_of_fire missing")
    consumption = w.get("ammo_consumption") or 1
    shots_per_mag = math.floor(ammo / consumption) if ammo else None
    t = (n - 1) / rof + rec["first_shot_at_s"]
    requires_reload = False
    if shots_per_mag is not None and n > shots_per_mag:
        if reload is None:
            return _nr("kill needs reload but reload_s missing")
        reloads = math.ceil(n / shots_per_mag) - 1
        t += reloads * reload
        requires_reload = True
    return {"status": "OK", "value": t, "shots": n, "requires_reload": requires_reload,
            "shots_per_magazine": shots_per_mag, **rec}


def headshot_oneshot(w: dict, hp: float) -> dict:
    """单发爆头能否秒杀 hp。蓄力/能量型武器需要条件字段（charge_conditions），缺失 → NOT_RUN。"""
    mult = _num(w.get("headshot_mult")) or 1
    if mult <= 1:
        return {"status": "OK", "value": False, "note": "cannot headshot"}
    per = weapon_damage_per_event(w, "head")
    if per is None:
        return _nr("damage_max missing")
    if w.get("charged") or w.get("energy_based"):
        cond = w.get("charge_conditions")
        if not cond:
            return _nr("charged/energy weapon without charge_conditions (energy, charge time, damage gain) — cannot state the one-shot conditions")
        return {"status": "OK", "value": per >= hp, "damage_head": per, "conditions": cond}
    return {"status": "OK", "value": per >= hp, "damage_head": per, "conditions": "none (plain shot, distance within falloff start)"}


def falloff_window(w: dict) -> dict:
    s, e = _num(w.get("falloff_start_m")), _num(w.get("falloff_end_m"))
    if s is None and e is None:
        return {"status": "OK", "value": None, "has_falloff": False}
    if s is None or e is None:
        return _nr("only one of falloff_start_m / falloff_end_m present")
    return {"status": "OK", "value": e - s, "has_falloff": True, "start": s, "end": e}


def uptime_ratio(a: dict, mode_key: str | None = None) -> dict:
    dur = _num(a.get("duration_s"))
    cd = a.get("cooldown_s")
    if isinstance(cd, dict):
        if mode_key is None:
            return _nr("cooldown is mode-split; mode not specified")
        cd = cd.get(mode_key)
    cd = _num(cd)
    if dur is None or cd is None:
        return _nr("duration_s or cooldown_s missing")
    starts = a.get("cooldown_starts")
    if starts not in ("on_cast", "on_end"):
        return _nr("cooldown_starts unknown — duration/cooldown must not be presented as coverage")
    if starts == "on_cast":
        if cd == 0:
            return _nr("cooldown 0 with on_cast: ratio undefined")
        return {"status": "OK", "value": dur / cd, "cooldown_starts": starts}
    return {"status": "OK", "value": dur / (dur + cd), "cooldown_starts": starts}


def rel_change(before: float | None, after: float | None) -> float | None:
    if before is None or after is None:
        return None
    if before == 0:
        return None
    return (after - before) / abs(before)
