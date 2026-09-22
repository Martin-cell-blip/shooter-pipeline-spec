"""事后比对：执行方提案 × 审核方反推 × 官方开发者注释 → REVIEW 项清单（给人看的）。
机器只做三件事：①逐条方向是否一致 ②整体方向是否一致 ③有无官方意图可比。意图文本本身的相似度不做机器判定，只并排列出。
用法：python -m pipeline.reconcile 2026-09-08 kiriko 1"""
from __future__ import annotations

import argparse
import json
import sys

from .loader import ROOT, load_patch, load_yaml


def reconcile(date: str, hero: str, n: int) -> dict:
    prop = load_yaml(ROOT / "proposals" / "agent" / f"{date}_{hero}_run{n}.yaml")["heroes"][hero]
    rev = load_yaml(ROOT / "reviews" / f"{date}_{hero}_run{n}.yaml")
    patch = load_patch(date)
    entry = next((e for e in patch["entries"] if e["hero"] == hero), None)
    official_intent = (entry or {}).get("intent")
    official_dir = (entry or {}).get("direction")
    items = []
    rdir = {c["path"]: c for c in rev.get("per_change") or []}
    for c in prop.get("changes") or []:
        r = rdir.get(c["path"])
        if r is None:
            items.append({"level": "REVIEW", "what": f"{c['path']}: reviewer did not cover this change"}); continue
        if r.get("direction") != c.get("expected_direction"):
            items.append({"level": "REVIEW", "what": f"{c['path']}: executor declared {c.get('expected_direction')}, reviewer inferred {r.get('direction')}",
                          "executor_why": c.get("why"), "reviewer_basis": r.get("basis")})
    if rev.get("overall_direction") != prop.get("overall_direction"):
        items.append({"level": "REVIEW", "what": f"overall: executor {prop.get('overall_direction')} vs reviewer {rev.get('overall_direction')}"})
    if official_dir and rev.get("overall_direction") != official_dir:
        items.append({"level": "REVIEW", "what": f"overall: reviewer {rev.get('overall_direction')} vs official patch file {official_dir}"})
    if not official_intent:
        items.append({"level": "REVIEW", "what": "no official developer comment for this hero/date — reviewer inference stands alone, human must judge"})
    for s in rev.get("suspicious") or []:
        items.append({"level": "REVIEW", "what": f"reviewer flagged suspicious: {s}"})
    return {"date": date, "hero": hero, "run": n, "items": items,
            "side_by_side": {"official_intent": official_intent, "reviewer_inferred_intent": rev.get("inferred_intent"),
                             "reviewer_confidence": rev.get("confidence"), "reviewer_cannot_determine": rev.get("cannot_determine"),
                             "executor_mixed_rationale": prop.get("mixed_rationale")}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("date"); ap.add_argument("hero"); ap.add_argument("run", type=int)
    a = ap.parse_args(argv)
    res = reconcile(a.date, a.hero, a.run)
    out = ROOT / "reviews" / f"{a.date}_{a.hero}_run{a.run}_reconcile.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
