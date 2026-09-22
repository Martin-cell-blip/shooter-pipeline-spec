"""验收「提取与应用」：把 Agent 提案与官方金标逐条比对。
不评判合理性，只回答：官方列出的每处改动，Agent 是否找到了正确路径、正确的 from/to；是否多出了官方没有的改动；
金标判定为 unmapped 的原文行，Agent 是否也放进了 unmapped（而不是硬凑到某个字段或静默丢弃）。
用法：python -m pipeline.compare proposals/agent/2026-09-08_kiriko_run1.yaml [--golden 2026-09-08_official]"""
from __future__ import annotations

import argparse
import json
import re
import sys

from .loader import ROOT, load_proposal, load_yaml

KEYS = ["matched", "wrong_value", "missing", "extra", "direction_mismatch",
        "unmapped_kept", "unmapped_forced", "unmapped_dropped", "agent_extra_unmapped",
        "missing_hero", "extra_hero", "duplicate_path", "invalid_scope", "numeric_vs_regex_mismatch"]


def regex_numbers(text: str):
    """从 why 里引用的原文中确定性抽 old/new；抽不到返回 None（不判）。"""
    from .preclassify import classify_line
    try:
        r = classify_line(text, None)
    except Exception:  # noqa: BLE001
        return None
    return (r["old"], r["new"]) if r.get("state") == "NUMERIC" else None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9.]+", " ", str(s).lower()).strip()


def compare(agent: dict, golden: dict, expected_heroes=None) -> dict:
    out = {"heroes": {}, "totals": {k: 0 for k in KEYS}}
    T = out["totals"]
    expected = set(golden["heroes"] if expected_heroes is None else expected_heroes)
    actual = agent.get("heroes") or {}
    T["invalid_scope"] = int(not expected or bool(expected - set(golden["heroes"])))
    T["missing_hero"] = len(expected - set(actual))
    T["extra_hero"] = len(set(actual) - expected)
    out["expected_heroes"] = sorted(expected)
    for hero, gph in golden["heroes"].items():
        if hero not in expected:
            continue
        aph = (agent.get("heroes") or {}).get(hero)
        if aph is None:
            continue
        g = {c["path"]: c for c in gph["changes"]}
        a = {c["path"]: c for c in aph.get("changes") or []}
        T["duplicate_path"] += len(aph.get("changes") or []) - len(a)
        rows = []
        for path, gc in g.items():
            ac = a.get(path)
            if ac is None:
                rows.append({"path": path, "verdict": "missing"}); T["missing"] += 1; continue
            if (ac.get("from"), ac.get("to")) != (gc["from"], gc["to"]):
                rows.append({"path": path, "verdict": "wrong_value", "agent": (ac.get("from"), ac.get("to")), "golden": (gc["from"], gc["to"])}); T["wrong_value"] += 1
            else:
                rows.append({"path": path, "verdict": "matched"}); T["matched"] += 1
            if ac.get("expected_direction") != gc["expected_direction"]:
                rows[-1]["direction"] = {"agent": ac.get("expected_direction"), "golden": gc["expected_direction"]}; T["direction_mismatch"] += 1
        for path in a.keys() - g.keys():
            rows.append({"path": path, "verdict": "extra", "agent": (a[path].get("from"), a[path].get("to")), "why": a[path].get("why")}); T["extra"] += 1
        # 迭代 2：模型 from/to 与确定性解析对不上 → 记 numeric_vs_regex_mismatch（模型在 NUMERIC 层没有发言权）
        for path, ac in a.items():
            rx = regex_numbers(ac.get("why", ""))
            if rx and (float(ac.get("from", "nan")), float(ac.get("to", "nan"))) != rx:
                rows.append({"path": path, "verdict": "numeric_vs_regex_mismatch", "agent": (ac.get("from"), ac.get("to")), "regex": rx}); T["numeric_vs_regex_mismatch"] += 1
        # unmapped：金标里每条 unmapped 原文，在 Agent 输出里去哪了
        a_um = [_norm(x) for x in (aph.get("unmapped") or [])]
        a_why = " || ".join(_norm(c.get("why", "")) for c in aph.get("changes") or [])
        um_rows = []
        for line in gph.get("unmapped") or []:
            n = _norm(line)
            key = " ".join(n.split()[:5])
            if any(key in x for x in a_um):
                um_rows.append({"line": line, "verdict": "kept_unmapped"}); T["unmapped_kept"] += 1
            elif key in a_why:
                um_rows.append({"line": line, "verdict": "forced_into_field"}); T["unmapped_forced"] += 1
            else:
                um_rows.append({"line": line, "verdict": "dropped_silently"}); T["unmapped_dropped"] += 1
        g_um_keys = [" ".join(_norm(x).split()[:5]) for x in gph.get("unmapped") or []]
        for x in a_um:
            if not any(k in x for k in g_um_keys):
                um_rows.append({"line": x, "verdict": "agent_unmapped_but_golden_mapped"}); T["agent_extra_unmapped"] += 1
        out["heroes"][hero] = {"rows": rows, "unmapped": um_rows,
                               "overall_direction": {"agent": aph.get("overall_direction"), "golden": gph.get("overall_direction")}}
    return out


def acceptance_ok(res: dict) -> bool:
    t = res["totals"]
    return all(t[k] == 0 for k in ("missing", "wrong_value", "extra", "unmapped_forced", "unmapped_dropped", "agent_extra_unmapped", "missing_hero", "extra_hero", "duplicate_path", "invalid_scope", "numeric_vs_regex_mismatch"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("agent_proposal"); ap.add_argument("--golden", default="2026-09-08_official")
    ap.add_argument("--hero", action="append", help="Explicit evaluation scope; repeat for multiple heroes. Default: all golden heroes.")
    a = ap.parse_args(argv)
    res = compare(load_yaml(ROOT / a.agent_proposal), load_proposal(a.golden), a.hero)
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return 0 if acceptance_ok(res) else 1


if __name__ == "__main__":
    sys.exit(main())
