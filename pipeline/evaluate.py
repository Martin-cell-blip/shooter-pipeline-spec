"""汇总评估 + 验证日志 + 回归门（迭代 2，借鉴 dota-patch-intelligence 的 VALIDATION.md 与 regressionGate.ts）。

对每个 (date, hero) 取最新一次执行 Agent 输出（revisions/ 下的手工修订版不计入模型指标），与官方金标比对，汇总：
  numeric_precision = matched / (matched + wrong_value + extra)
  numeric_recall    = matched / (matched + missing)
  unmapped_handling = unmapped_kept / (kept + forced + dropped)
写入 reports/validation_log/<utc>_<prompt_sha8>.json（引擎版本 = 执行 Agent 提案格式文本的 sha256 前 8 位）。
回归门：与上一条日志相比，任一指标下降 → exit 1（CI 红），并指出是哪个 (date, hero) 变差。
用法：python -m pipeline.evaluate [--no-gate]"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import sys

from .agent import PROPOSAL_FORMAT
from .compare import compare
from .loader import ROOT, load_proposal, load_yaml

THRESHOLDS = {"numeric_precision": 0.98, "numeric_recall": 0.95, "unmapped_handling": 0.90}   # 借 Dota 项目的门槛量级；n 小，只作 REVIEW 提示不作 FAIL


def latest_runs() -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], tuple[int, str]] = {}
    for f in glob.glob(str(ROOT / "proposals" / "agent" / "*_run*.yaml")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})_([a-z]+)_run(\d+)\.yaml$", os.path.basename(f))
        if not m:
            continue
        key, n = (m.group(1), m.group(2)), int(m.group(3))
        if key not in out or n > out[key][0]:
            out[key] = (n, f)
    return {k: v[1] for k, v in out.items()}


def evaluate() -> dict:
    per = {}; agg = {"matched": 0, "wrong_value": 0, "missing": 0, "extra": 0, "unmapped_kept": 0, "unmapped_forced": 0, "unmapped_dropped": 0, "direction_mismatch": 0}
    for (date, hero), f in sorted(latest_runs().items()):
        golden = load_proposal(f"{date}_official")
        if hero not in golden["heroes"]:
            continue
        res = compare(load_yaml(f), golden, [hero])
        t = res["totals"]
        per[f"{date}/{hero}"] = {"file": os.path.relpath(f, ROOT), **{k: t[k] for k in agg}}
        for k in agg:
            agg[k] += t[k]
    def ratio(a, b): return round(a / b, 4) if b else None
    metrics = {"numeric_precision": ratio(agg["matched"], agg["matched"] + agg["wrong_value"] + agg["extra"]),
               "numeric_recall": ratio(agg["matched"], agg["matched"] + agg["missing"]),
               "unmapped_handling": ratio(agg["unmapped_kept"], agg["unmapped_kept"] + agg["unmapped_forced"] + agg["unmapped_dropped"])}
    below = [k for k, v in metrics.items() if v is not None and v < THRESHOLDS[k]]
    return {"engine": hashlib.sha256(PROPOSAL_FORMAT.encode()).hexdigest()[:8], "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "n_cases": len(per), "aggregate": agg, "metrics": metrics, "below_threshold": below, "per_case": per}


def previous_log() -> dict | None:
    logs = sorted(glob.glob(str(ROOT / "reports" / "validation_log" / "*.json")))
    return json.load(open(logs[-1], encoding="utf-8")) if logs else None


def gate(cur: dict, prev: dict | None) -> list[str]:
    if not prev:
        return []
    regress = []
    for k, v in cur["metrics"].items():
        pv = prev["metrics"].get(k)
        if v is not None and pv is not None and v < pv:
            regress.append(f"{k}: {pv} -> {v}")
    for case, c in cur["per_case"].items():
        p = prev["per_case"].get(case)
        if p and (c["matched"] < p["matched"] or c["wrong_value"] > p["wrong_value"] or c["missing"] > p["missing"] or c["extra"] > p["extra"]):
            regress.append(f"{case}: worse than previous log ({p['file']} -> {c['file']})")
    return regress


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--no-gate", action="store_true"); ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    cur = evaluate(); prev = previous_log()
    regress = [] if a.no_gate else gate(cur, prev)
    print(json.dumps({k: cur[k] for k in ("engine", "n_cases", "metrics", "below_threshold")}, ensure_ascii=False))
    for r in regress:
        print("  REGRESSION:", r)
    if not a.no_write and not regress:
        d = ROOT / "reports" / "validation_log"; d.mkdir(parents=True, exist_ok=True)
        p = d / f"{cur['utc'].replace(':', '').replace('+0000', 'Z')}_{cur['engine']}.json"
        json.dump(cur, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("  ->", p.relative_to(ROOT))
    return 1 if regress else 0


if __name__ == "__main__":
    sys.exit(main())
