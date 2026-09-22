"""REVIEW 决定文件格式校验（第 9 步）。机器只管格式，不管决定对不对。
规则：
  - 每条 decision ∈ {accepted, false_positive, needs_revision, resolved}；pending 计为未处置
  - reason 非空且 ≥ 10 字符；scope 非空且必须包含该条的 hero，且不得是全局字样（all / 全部 / * / global）
  - 每条 REVIEW 项在决定文件里必须有对应条目（以 reconcile 结果与 reports/*.json 的 REVIEW 项为准）
退出码：0 全部通过；1 有未处置或格式违规；2 文件缺失/损坏。
用法：python -m pipeline.decisions [--allow-pending]"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import yaml

from .loader import ROOT

VALID = {"accepted", "false_positive", "needs_revision", "resolved"}
GLOBAL_WORDS = ("all", "全部", "*", "global", "全局", "所有")


def expected_items() -> set[tuple[str, str]]:
    """当前应被处置的 (hero, item) 集合：reconcile 项 + 校验报告 REVIEW 项。"""
    out = set()
    for f in sorted(glob.glob(str(ROOT / "reviews" / "*_reconcile.json"))):
        r = json.load(open(f, encoding="utf-8"))
        for it in r["items"]:
            out.add((r["hero"], it["what"]))
    for f in sorted(glob.glob(str(ROOT / "reports" / "*.json"))):
        if os.path.basename(f).endswith("_official.json"):
            continue
        rep = json.load(open(f, encoding="utf-8"))
        for r in rep["results"]:
            if r["status"] == "REVIEW":
                out.add((r["hero"], f"{r['check']}: {r['detail']}"))
    return out


def validate(path=None, allow_pending: bool = False) -> tuple[list[str], dict]:
    path = path or ROOT / "reviews" / "decisions.yaml"
    try:
        doc = yaml.safe_load(open(path, encoding="utf-8"))
        items = doc["items"]
    except Exception as e:  # noqa: BLE001
        return [f"LOAD: {e!r}"], {}
    problems = []
    counts = {"total": len(items), "pending": 0, "decided": 0}
    seen = set()
    for i, it in enumerate(items):
        tag = f"#{i} {it.get('hero')} | {str(it.get('item'))[:60]}"
        seen.add((it.get("hero"), it.get("item")))
        dec = it.get("decision")
        if dec == "pending":
            counts["pending"] += 1
            if not allow_pending:
                problems.append(f"{tag}: still pending")
            continue
        if dec not in VALID:
            problems.append(f"{tag}: decision {dec!r} not in {sorted(VALID)}"); continue
        counts["decided"] += 1
        reason = str(it.get("reason") or "").strip()
        scope = str(it.get("scope") or "").strip()
        if len(reason) < 10:
            problems.append(f"{tag}: reason missing or too short (<10 chars)")
        if not scope:
            problems.append(f"{tag}: scope missing")
        else:
            low = scope.lower()
            if any(w in low for w in GLOBAL_WORDS) and not it.get("hero", "") in scope:
                problems.append(f"{tag}: scope looks global ({scope!r})")
            if str(it.get("hero")) not in scope:
                problems.append(f"{tag}: scope must name the hero ({it.get('hero')})")
    missing = expected_items() - seen
    for hero, what in sorted(missing):
        problems.append(f"MISSING entry for {hero} | {what[:80]}")
    return problems, counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--allow-pending", action="store_true")
    a = ap.parse_args(argv)
    problems, counts = validate(allow_pending=a.allow_pending)
    print(f"decisions: {counts}")
    for p in problems:
        print("  -", p)
    if any(p.startswith("LOAD") for p in problems):
        return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
