"""验收「提取与应用」：把 Agent 提案与官方金标逐条比对。
不评判合理性，只回答：官方列出的每处改动，Agent 是否找到了正确路径、正确的 from/to；是否多出了官方没有的改动。
用法：python -m pipeline.compare proposals/agent/2026-09-08_kiriko_run1.yaml [--golden 2026-09-08_official]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .loader import ROOT, load_proposal, load_yaml


def compare(agent: dict, golden: dict) -> dict:
    out = {"heroes": {}, "totals": {"matched": 0, "wrong_value": 0, "missing": 0, "extra": 0, "direction_mismatch": 0, "unmapped": 0}}
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
                rows.append({"path": path, "verdict": "missing"}); out["totals"]["missing"] += 1; continue
            if (ac.get("from"), ac.get("to")) != (gc["from"], gc["to"]):
                rows.append({"path": path, "verdict": "wrong_value", "agent": (ac.get("from"), ac.get("to")), "golden": (gc["from"], gc["to"])}); out["totals"]["wrong_value"] += 1
            else:
                rows.append({"path": path, "verdict": "matched"}); out["totals"]["matched"] += 1
            if ac.get("expected_direction") != gc["expected_direction"]:
                rows[-1]["direction"] = {"agent": ac.get("expected_direction"), "golden": gc["expected_direction"]}; out["totals"]["direction_mismatch"] += 1
        for path in a.keys() - g.keys():
            rows.append({"path": path, "verdict": "extra", "agent": (a[path].get("from"), a[path].get("to"))}); out["totals"]["extra"] += 1
        um = aph.get("unmapped") or []
        out["totals"]["unmapped"] += len(um)
        out["heroes"][hero] = {"rows": rows, "unmapped": um, "overall_direction": {"agent": aph.get("overall_direction"), "golden": gph.get("overall_direction")}}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("agent_proposal"); ap.add_argument("--golden", default="2026-09-08_official")
    a = ap.parse_args(argv)
    res = compare(load_yaml(ROOT / a.agent_proposal), load_proposal(a.golden))
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    t = res["totals"]
    return 0 if t["missing"] == 0 and t["wrong_value"] == 0 and t["extra"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
