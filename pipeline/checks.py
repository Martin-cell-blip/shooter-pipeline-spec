"""校验器：对一个提案（before 快照 + 改动列表）产出四态结果。
每条结果 = {check, hero, status, detail, records}。启发式命中只 REVIEW；任何异常 → 该检查 NOT_RUN 并记录异常，绝不返回 PASS。"""
from __future__ import annotations

import traceback
from typing import Any

from . import metrics as M
from .loader import apply_changes, get_path, path_blocked

PASS, FAIL, REVIEW, NOT_RUN = "PASS", "FAIL", "REVIEW", "NOT_RUN"


def _r(check: str, hero: str, status: str, detail: str, **records) -> dict:
    return {"check": check, "hero": hero, "status": status, "detail": detail, "records": records}


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _guard(fn):
    """异常 → NOT_RUN，附 traceback；永不吞成 PASS。"""
    def wrapped(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:  # noqa: BLE001
            hero = a[1] if len(a) > 1 and isinstance(a[1], str) else "?"
            return [_r(fn.__name__, hero, NOT_RUN, f"exception: {e!r}", traceback=traceback.format_exc(limit=3))]
    return wrapped


# ---------------- FAIL 级 ----------------

def _bounds_for(schema: dict, section: str, field: str) -> dict | None:
    sec = schema.get(section) or {}
    spec = sec.get(field)
    return spec if isinstance(spec, dict) else None


def _walk_numeric(hero: dict):
    """yield (section, path, field, value)"""
    for w in hero.get("weapons") or []:
        for f, v in w.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                yield "weapon", f"weapons.{w['id']}.{f}", f, v
    for a in hero.get("abilities") or []:
        for f, v in a.items():
            if isinstance(v, dict):
                for mk, mv in v.items():
                    if isinstance(mv, (int, float)) and not isinstance(mv, bool):
                        yield "ability", f"abilities.{a['id']}.{f}.{mk}", f, mv
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                yield "ability", f"abilities.{a['id']}.{f}", f, v
    hp = hero.get("hitpoints")
    if isinstance(hp, dict):
        for f, v in hp.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                yield "hero.hitpoints", f"hitpoints.{f}", f, v


@_guard
def F1_schema_bounds(schema: dict, hero_id: str, after: dict) -> list[dict]:
    out = []
    for section, path, field, v in _walk_numeric(after):
        spec = (schema.get("hero", {}).get("hitpoints", {}) if section == "hero.hitpoints" else schema.get(section, {})).get(field)
        if not isinstance(spec, dict):
            continue
        lo, hi = spec.get("min"), spec.get("max")
        if (lo is not None and v < lo) or (hi is not None and v > hi):
            out.append(_r("F1_schema_bounds", hero_id, FAIL,
                          f"{path}={v} outside project support bounds [{lo}, {hi}] (config bound, not a design-legality claim)",
                          path=path, value=v, min=lo, max=hi))
    if not out:
        out.append(_r("F1_schema_bounds", hero_id, PASS, "all numeric fields within project bounds"))
    return out


@_guard
def F2_falloff_structure(schema: dict, hero_id: str, after: dict) -> list[dict]:
    out = []
    for w in after.get("weapons") or []:
        dmax, dmin = _num(w.get("damage_max")), _num(w.get("damage_min"))
        s, e = _num(w.get("falloff_start_m")), _num(w.get("falloff_end_m"))
        pid = f"weapons.{w['id']}"
        if (s is None) != (e is None):
            out.append(_r("F2_falloff_structure", hero_id, FAIL, f"{pid}: only one of falloff_start_m/falloff_end_m present", weapon=w["id"]))
        elif s is not None and not s < e:
            out.append(_r("F2_falloff_structure", hero_id, FAIL, f"{pid}: falloff_start_m ({s}) must be < falloff_end_m ({e})", weapon=w["id"]))
        if dmin is not None and dmax is not None and dmin > dmax:
            out.append(_r("F2_falloff_structure", hero_id, FAIL, f"{pid}: damage_min ({dmin}) > damage_max ({dmax})", weapon=w["id"]))
    if not out:
        out.append(_r("F2_falloff_structure", hero_id, PASS, "falloff structure consistent for all weapons"))
    return out


@_guard
def F3_hitpoints_sum(schema: dict, hero_id: str, after: dict) -> list[dict]:
    hp = after.get("hitpoints")
    if not isinstance(hp, dict):
        return [_r("F3_hitpoints_sum", hero_id, NOT_RUN, "hitpoints is null (open conflict or missing) — no numeric judgement")]
    parts = [_num(hp.get(k)) for k in ("health", "armor", "shields")]
    if any(p is None for p in parts) or _num(hp.get("total")) is None:
        return [_r("F3_hitpoints_sum", hero_id, NOT_RUN, "hitpoints components incomplete")]
    if sum(parts) != hp["total"]:
        return [_r("F3_hitpoints_sum", hero_id, FAIL, f"total {hp['total']} != health+armor+shields {sum(parts)}")]
    return [_r("F3_hitpoints_sum", hero_id, PASS, f"total {hp['total']} = sum of components")]


@_guard
def F4_linked_disposition(schema: dict, hero_id: str, proposal_hero: dict) -> list[dict]:
    linked = schema.get("weapon", {}).get("linked") or []
    changed = {c["path"] for c in proposal_hero.get("changes") or []}
    disp = proposal_hero.get("linked_dispositions") or {}
    out = []
    for path in changed:
        parts = path.split(".")
        if parts[0] != "weapons" or len(parts) < 3:
            continue
        field = parts[2]
        for pair in linked:
            if field in pair:
                partner = pair[1] if pair[0] == field else pair[0]
                partner_path = f"{parts[0]}.{parts[1]}.{partner}"
                if partner_path in changed:
                    continue  # 一起改了，本身就是处置
                d = disp.get(partner_path)
                if not d:
                    out.append(_r("F4_linked_disposition", hero_id, FAIL,
                                  f"{path} changed but linked field {partner_path} has no disposition (keep / changed / not_needed:<reason>)",
                                  path=path, partner=partner_path))
                elif str(d).startswith("not_needed") and ":" not in str(d):
                    out.append(_r("F4_linked_disposition", hero_id, FAIL, f"{partner_path}: not_needed requires a reason after ':'", partner=partner_path))
    if not out:
        out.append(_r("F4_linked_disposition", hero_id, PASS, "every touched linked pair has a disposition record"))
    return out


@_guard
def F5_direction_vs_declared(schema: dict, hero_id: str, proposal_hero: dict, before: dict) -> list[dict]:
    sem = schema.get("semantics") or {}
    out = []
    for c in proposal_hero.get("changes") or []:
        path = c["path"]; parts = path.split(".")
        section = {"weapons": "weapon", "abilities": "ability", "hitpoints": "hitpoints"}.get(parts[0])
        field = parts[1] if parts[0] == "hitpoints" else (parts[2] if len(parts) > 2 else None)
        declared = c.get("expected_direction")
        frm, to = _num(c.get("from")), _num(c.get("to"))
        if frm is None or to is None:
            out.append(_r("F5_direction_vs_declared", hero_id, REVIEW, f"{path}: non-numeric change, direction not machine-checkable", path=path)); continue
        actual_before = get_path(before, path)
        if _num(actual_before) is not None and actual_before != frm:
            out.append(_r("F5_direction_vs_declared", hero_id, FAIL, f"{path}: proposal 'from'={frm} but before-snapshot has {actual_before}", path=path)); continue
        higher_is = (sem.get(section) or {}).get(field)
        if declared not in ("buff", "nerf", "ambiguous") or declared is None:
            out.append(_r("F5_direction_vs_declared", hero_id, REVIEW, f"{path}: expected_direction missing/invalid ({declared})", path=path)); continue
        if to == frm:
            out.append(_r("F5_direction_vs_declared", hero_id, REVIEW, f"{path}: from == to, no-op change", path=path)); continue
        if higher_is not in ("buff", "nerf"):
            out.append(_r("F5_direction_vs_declared", hero_id, REVIEW,
                          f"{path}: field semantics '{higher_is}' — direction cannot be machine-judged; declared={declared}, reason='{c.get('why')}'", path=path)); continue
        actual = higher_is if to > frm else ("nerf" if higher_is == "buff" else "buff")
        if declared == "ambiguous":
            out.append(_r("F5_direction_vs_declared", hero_id, REVIEW, f"{path}: declared ambiguous but semantics say {actual}", path=path))
        elif declared != actual:
            out.append(_r("F5_direction_vs_declared", hero_id, FAIL, f"{path}: {frm}→{to} is a {actual} by field semantics but declared {declared}", path=path, actual=actual, declared=declared))
        else:
            out.append(_r("F5_direction_vs_declared", hero_id, PASS, f"{path}: {frm}→{to} = {actual}, matches declaration", path=path))
    return out or [_r("F5_direction_vs_declared", hero_id, NOT_RUN, "no changes in proposal")]


# ---------------- REVIEW 级（同英雄前后对比） ----------------

DPS_FIELDS = ("damage_max", "pellets_per_shot", "rate_of_fire", "ammo", "ammo_consumption", "reload_s", "headshot_mult", "hit_type")


def _blocked(hero_id: str, check: str, before: dict, after: dict, path: str, fields=DPS_FIELDS) -> dict | None:
    """只有当指标实际读取的字段处于未关闭冲突/缺失清单时才阻断（不按整件武器阻断）。"""
    for h in (before, after):
        for f in fields:
            why = path_blocked(h, f"{path}.{f}")
            if why:
                return _r(check, hero_id, NOT_RUN, f"{path}.{f}: {why} — dependent metric withheld", path=f"{path}.{f}")
    return None


@_guard
def P0_provenance_status(schema: dict, hero_id: str, after: dict) -> list[dict]:
    """把未关闭的来源冲突与缺失字段显式列入报告，避免它们只躺在 YAML 里。"""
    out = []
    prov = after.get("provenance") or {}
    for c in prov.get("conflicts") or []:
        if str(c.get("status", "")).upper() == "REVIEW":
            out.append(_r("P0_provenance_status", hero_id, REVIEW, f"open source conflict on {c['field']}: {c.get('values')} — {c.get('note')}", field=c["field"]))
    for m in prov.get("missing") or []:
        out.append(_r("P0_provenance_status", hero_id, NOT_RUN, f"missing field {m['field']}: {m.get('note')}", field=m["field"]))
    return out or [_r("P0_provenance_status", hero_id, PASS, "no open conflicts, no missing fields")]


@_guard
def R1_full_cycle_dps_delta(inv: dict, hero_id: str, before: dict, after: dict) -> list[dict]:
    th = inv["review_rules"][0]["threshold"]["rel"]; sc = inv["scenario"]; out = []
    for wb in before.get("weapons") or []:
        wa = next((w for w in after.get("weapons") or [] if w["id"] == wb["id"]), None)
        if wa is None:
            out.append(_r("R1_full_cycle_dps_delta", hero_id, REVIEW, f"weapon {wb['id']} removed", weapon=wb["id"])); continue
        b = _blocked(hero_id, "R1_full_cycle_dps_delta", before, after, f"weapons.{wb['id']}")
        if b: out.append(b); continue
        mb, ma = M.full_cycle_dps(wb, sc), M.full_cycle_dps(wa, sc)
        if mb["status"] != "OK" or ma["status"] != "OK":
            out.append(_r("R1_full_cycle_dps_delta", hero_id, NOT_RUN, f"{wb['id']}: {mb.get('reason') or ma.get('reason')}", weapon=wb["id"])); continue
        rc = M.rel_change(mb["value"], ma["value"])
        st = REVIEW if rc is not None and abs(rc) > th else PASS
        out.append(_r("R1_full_cycle_dps_delta", hero_id, st, f"{wb['id']}: full-cycle body DPS {mb['value']:.2f} → {ma['value']:.2f} ({(rc or 0)*100:+.1f}%)",
                      weapon=wb["id"], before=mb, after=ma, rel_change=rc, threshold=th))
    return out or [_r("R1_full_cycle_dps_delta", hero_id, NOT_RUN, "no weapons")]


@_guard
def R2_ttk_delta_or_reload_breakpoint(inv: dict, hero_id: str, before: dict, after: dict) -> list[dict]:
    th = inv["review_rules"][1]["threshold"]["rel"]; sc = inv["scenario"]; out = []
    for wb in before.get("weapons") or []:
        wa = next((w for w in after.get("weapons") or [] if w["id"] == wb["id"]), None)
        if wa is None: continue
        b = _blocked(hero_id, "R2_ttk_delta_or_reload_breakpoint", before, after, f"weapons.{wb['id']}")
        if b: out.append(b); continue
        for hp in sc["targets_hp"]:
            for loc in sc["hit_location"]:
                tb, ta = M.ttk(wb, hp, loc, sc), M.ttk(wa, hp, loc, sc)
                tag = f"{wb['id']} vs {hp}hp {loc}"
                if tb["status"] != "OK" or ta["status"] != "OK":
                    out.append(_r("R2_ttk_delta_or_reload_breakpoint", hero_id, NOT_RUN, f"{tag}: {tb.get('reason') or ta.get('reason')}", weapon=wb["id"], target_hp=hp, location=loc)); continue
                if tb["value"] is None or ta["value"] is None:
                    continue  # 不能爆头/无伤害：无 TTK，跳过（不是 NOT_RUN，是该指标不适用）
                rc = M.rel_change(tb["value"], ta["value"])
                flip = tb.get("requires_reload") != ta.get("requires_reload")
                st = REVIEW if (rc is not None and abs(rc) > th) or flip else PASS
                out.append(_r("R2_ttk_delta_or_reload_breakpoint", hero_id, st,
                              f"{tag}: TTK {tb['value']:.3f}s → {ta['value']:.3f}s ({(rc or 0)*100:+.1f}%)" + (", reload breakpoint crossed" if flip else ""),
                              weapon=wb["id"], target_hp=hp, location=loc, before=tb, after=ta, rel_change=rc, reload_flip=flip))
    return out or [_r("R2_ttk_delta_or_reload_breakpoint", hero_id, NOT_RUN, "no weapons")]


@_guard
def R3_headshot_oneshot_change(inv: dict, hero_id: str, before: dict, after: dict) -> list[dict]:
    hp = min(inv["scenario"]["targets_hp"]); out = []
    for wb in before.get("weapons") or []:
        wa = next((w for w in after.get("weapons") or [] if w["id"] == wb["id"]), None)
        if wa is None: continue
        ob, oa = M.headshot_oneshot(wb, hp), M.headshot_oneshot(wa, hp)
        if ob["status"] != "OK" or oa["status"] != "OK":
            out.append(_r("R3_headshot_oneshot_change", hero_id, NOT_RUN, f"{wb['id']}: {ob.get('reason') or oa.get('reason')}", weapon=wb["id"])); continue
        if ob["value"] != oa["value"]:
            out.append(_r("R3_headshot_oneshot_change", hero_id, REVIEW, f"{wb['id']}: one-shot headshot vs {hp}hp {'gained' if oa['value'] else 'lost'}", weapon=wb["id"], before=ob, after=oa))
        else:
            out.append(_r("R3_headshot_oneshot_change", hero_id, PASS, f"{wb['id']}: one-shot capability unchanged ({oa['value']})", weapon=wb["id"], after=oa))
    return out or [_r("R3_headshot_oneshot_change", hero_id, NOT_RUN, "no weapons")]


@_guard
def R4_change_count_stats(inv: dict, hero_id: str, proposal_hero: dict) -> list[dict]:
    cnt = {"buff": 0, "nerf": 0, "ambiguous": 0}
    for c in proposal_hero.get("changes") or []:
        cnt[c.get("expected_direction") if c.get("expected_direction") in cnt else "ambiguous"] += 1
    return [_r("R4_change_count_stats", hero_id, PASS, f"changes: {cnt} (display only, no threshold)", **cnt)]


@_guard
def R5_falloff_window_delta(inv: dict, hero_id: str, before: dict, after: dict) -> list[dict]:
    th = inv["review_rules"][4]["threshold"]["rel"]; out = []
    for wb in before.get("weapons") or []:
        wa = next((w for w in after.get("weapons") or [] if w["id"] == wb["id"]), None)
        if wa is None: continue
        fb, fa = M.falloff_window(wb), M.falloff_window(wa)
        if fb["status"] != "OK" or fa["status"] != "OK":
            out.append(_r("R5_falloff_window_delta", hero_id, NOT_RUN, f"{wb['id']}: {fb.get('reason') or fa.get('reason')}", weapon=wb["id"])); continue
        if fb["has_falloff"] != fa["has_falloff"]:
            out.append(_r("R5_falloff_window_delta", hero_id, REVIEW, f"{wb['id']}: falloff mechanic {'added' if fa['has_falloff'] else 'removed'}", weapon=wb["id"])); continue
        if not fb["has_falloff"]:
            continue
        rc = M.rel_change(fb["value"], fa["value"])
        shifted = (fb["start"], fb["end"]) != (fa["start"], fa["end"])
        st = REVIEW if (rc is not None and abs(rc) > th) else PASS
        out.append(_r("R5_falloff_window_delta", hero_id, st,
                      f"{wb['id']}: window {fb['value']}m → {fa['value']}m ({(rc or 0)*100:+.1f}%); start {fb['start']}→{fa['start']}, end {fb['end']}→{fa['end']}" + (" [endpoints moved]" if shifted else ""),
                      weapon=wb["id"], before=fb, after=fa, rel_change=rc, endpoints_moved=shifted))
    return out or [_r("R5_falloff_window_delta", hero_id, PASS, "no falloff weapons")]


def _cooldown_values(a: dict) -> dict[str, float | None]:
    cd = a.get("cooldown_s")
    if isinstance(cd, dict):
        return {k: _num(v) for k, v in cd.items()}
    return {"": _num(cd)}


@_guard
def R6_cooldown_step(inv: dict, hero_id: str, before: dict, after: dict) -> list[dict]:
    th = inv["review_rules"][5]["threshold"]; out = []
    for ab in before.get("abilities") or []:
        aa = next((a for a in after.get("abilities") or [] if a["id"] == ab["id"]), None)
        if aa is None: continue
        cb, ca = _cooldown_values(ab), _cooldown_values(aa)
        for mode in sorted(set(cb) | set(ca)):
            b, a = cb.get(mode), ca.get(mode)
            tag = ab["id"] + (f"[{mode}]" if mode else "")
            if b is None and a is None: continue
            if b is None or a is None:
                out.append(_r("R6_cooldown_step", hero_id, NOT_RUN, f"{tag}: cooldown missing on one side", ability=ab["id"], mode=mode)); continue
            if b == a:
                continue
            if b == 0:
                out.append(_r("R6_cooldown_step", hero_id, REVIEW, f"{tag}: cooldown 0 → {a}: mechanic change, not a step", ability=ab["id"], mode=mode)); continue
            da, rc = abs(a - b), abs(a - b) / b
            st = REVIEW if da > th["abs_s"] or rc > th["rel"] else PASS
            out.append(_r("R6_cooldown_step", hero_id, st, f"{tag}: cooldown {b}s → {a}s (Δ{da:.2f}s, {rc*100:.1f}%)", ability=ab["id"], mode=mode, abs=da, rel=rc, threshold=th))
    return out or [_r("R6_cooldown_step", hero_id, PASS, "no cooldown changes")]


@_guard
def R8_mixed_direction_rationale(inv: dict, hero_id: str, proposal_hero: dict) -> list[dict]:
    dirs = {c.get("expected_direction") for c in proposal_hero.get("changes") or []}
    if "buff" in dirs and "nerf" in dirs:
        if not proposal_hero.get("mixed_rationale"):
            return [_r("R8_mixed_direction_rationale", hero_id, REVIEW, "mixed buff+nerf without mixed_rationale")]
        return [_r("R8_mixed_direction_rationale", hero_id, PASS, f"mixed, rationale given: '{proposal_hero['mixed_rationale']}' (local directions only; net effect not machine-judged)", overall="mixed")]
    return [_r("R8_mixed_direction_rationale", hero_id, PASS, f"single direction {dirs}", overall=next(iter(dirs), None))]


@_guard
def R9_shots_to_kill_breakpoint(inv: dict, hero_id: str, before: dict, after: dict) -> list[dict]:
    sc = inv["scenario"]; out = []
    for wb in before.get("weapons") or []:
        wa = next((w for w in after.get("weapons") or [] if w["id"] == wb["id"]), None)
        if wa is None or wb.get("hit_type") == "beam": continue
        b = _blocked(hero_id, "R9_shots_to_kill_breakpoint", before, after, f"weapons.{wb['id']}")
        if b: out.append(b); continue
        for hp in sc["targets_hp"]:
            for loc in sc["hit_location"]:
                sb, sa = M.shots_to_kill(wb, hp, loc), M.shots_to_kill(wa, hp, loc)
                if sb["status"] != "OK" or sa["status"] != "OK":
                    out.append(_r("R9_shots_to_kill_breakpoint", hero_id, NOT_RUN, f"{wb['id']} {hp}hp {loc}: {sb.get('reason') or sa.get('reason')}", weapon=wb["id"])); continue
                if sb["value"] is None or sa["value"] is None: continue
                st = REVIEW if sb["value"] != sa["value"] else PASS
                out.append(_r("R9_shots_to_kill_breakpoint", hero_id, st, f"{wb['id']} vs {hp}hp {loc}: {sb['value']} → {sa['value']} shot events",
                              weapon=wb["id"], target_hp=hp, location=loc, before=sb["value"], after=sa["value"], pellets_per_event=wb.get("pellets_per_shot") or 1))
    return out or [_r("R9_shots_to_kill_breakpoint", hero_id, NOT_RUN, "no applicable weapons")]


@_guard
def R10_uptime_ratio(inv: dict, hero_id: str, before: dict, after: dict) -> list[dict]:
    th = inv["review_rules"][9]["threshold"]["abs_pp"]; out = []
    for ab in before.get("abilities") or []:
        aa = next((a for a in after.get("abilities") or [] if a["id"] == ab["id"]), None)
        if aa is None or _num(ab.get("duration_s")) is None: continue
        modes = list(_cooldown_values(ab).keys())
        for mode in modes:
            ub, ua = M.uptime_ratio(ab, mode or None), M.uptime_ratio(aa, mode or None)
            tag = ab["id"] + (f"[{mode}]" if mode else "")
            if ub["status"] != "OK" or ua["status"] != "OK":
                out.append(_r("R10_uptime_ratio", hero_id, NOT_RUN, f"{tag}: {ub.get('reason') or ua.get('reason')}", ability=ab["id"], mode=mode)); continue
            dpp = (ua["value"] - ub["value"]) * 100
            crossed = (ub["value"] >= 1) != (ua["value"] >= 1)
            st = REVIEW if abs(dpp) > th or crossed else PASS
            out.append(_r("R10_uptime_ratio", hero_id, st, f"{tag}: uptime {ub['value']*100:.1f}% → {ua['value']*100:.1f}% ({dpp:+.1f}pp)" + (" [seamless-coverage boundary crossed]" if crossed else ""),
                          ability=ab["id"], mode=mode, before=ub, after=ua))
    return out or [_r("R10_uptime_ratio", hero_id, PASS, "no duration-bearing abilities")]


# ---------------- 编排 ----------------

def run_proposal(schema: dict, inv: dict, proposal: dict, before_heroes: dict[str, dict], baseline: dict[str, dict] | None = None) -> list[dict]:
    """对提案中每个英雄：before = 快照；after = 快照应用 changes。返回扁平结果列表。"""
    results: list[dict] = []
    for hero_id, ph in (proposal.get("heroes") or {}).items():
        before = before_heroes.get(hero_id)
        if before is None:
            results.append(_r("load", hero_id, NOT_RUN, "hero not in before-snapshot")); continue
        try:
            after = apply_changes(before, ph.get("changes") or [], use="to")
        except KeyError as e:
            results.append(_r("apply", hero_id, FAIL, f"change path not found: {e}")); continue
        if baseline is not None and hero_id in baseline and proposal.get("after_ref") == "baseline":
            diffs = [c["path"] for c in ph.get("changes") or [] if get_path(baseline[hero_id], c["path"]) != c["to"]]
            results.append(_r("apply_vs_baseline", hero_id, FAIL if diffs else PASS,
                              ("applied values differ from baseline at: " + ", ".join(diffs)) if diffs else "applied snapshot matches baseline on every changed path"))
        results += P0_provenance_status(schema, hero_id, after)
        results += F1_schema_bounds(schema, hero_id, after)
        results += F2_falloff_structure(schema, hero_id, after)
        results += F3_hitpoints_sum(schema, hero_id, after)
        results += F4_linked_disposition(schema, hero_id, ph)
        results += F5_direction_vs_declared(schema, hero_id, ph, before)
        results += R1_full_cycle_dps_delta(inv, hero_id, before, after)
        results += R2_ttk_delta_or_reload_breakpoint(inv, hero_id, before, after)
        results += R3_headshot_oneshot_change(inv, hero_id, before, after)
        results += R4_change_count_stats(inv, hero_id, ph)
        results += R5_falloff_window_delta(inv, hero_id, before, after)
        results += R6_cooldown_step(inv, hero_id, before, after)
        results += R8_mixed_direction_rationale(inv, hero_id, ph)
        results += R9_shots_to_kill_breakpoint(inv, hero_id, before, after)
        results += R10_uptime_ratio(inv, hero_id, before, after)
    return results
