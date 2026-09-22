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
        "unmapped_kept", "unmapped_forced", "unmapped_dropped", "agent_extra_unmapped"]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9.]+", " ", str(s).lower()).strip()


def compare(agent: dict, golden: dict) -> dict:
    out = {"heroes": {}, "totals": {k: 0 for k in KEYS}}
    T = out["totals"]
    for hero, gph in golden["heroes"].items():
        aph = (agent.get("heroes") or {}).get(hero)
        if aph is None:
            continue
        g = {c["path"]: c for c in gph["changes"]}
        a = {c["path"]: c for c in aph.get("changes") or []}
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
    return t["missing"] == 0 and t["wrong_value"] == 0 and t["extra"] == 0 and t["unmapped_forced"] == 0 and t["unmapped_dropped"] == 0 and t["agent_extra_unmapped"] == 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("agent_proposal"); ap.add_argument("--golden", default="2026-09-08_official")
    a = ap.parse_args(argv)
    res = compare(load_yaml(ROOT / a.agent_proposal), load_proposal(a.golden))
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    return 0 if acceptance_ok(res) else 1


if __name__ == "__main__":
    sys.exit(main())
