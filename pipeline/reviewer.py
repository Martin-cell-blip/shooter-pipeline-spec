"""审核 Agent（零上下文）：只读「改动前 → 改动后」的配置 diff，反推这次补丁想干什么。

输入隔离：只给 {path, from, to} 列表 + 字段方向语义 + 单位表。**不给**执行方的 why / expected_direction / mixed_rationale，
不给开发者注释，不给校验报告，不给补丁原文。审核方的产出与这些东西的比对由 reconcile.py 在事后做。
输出：reviews/<date>_<hero>_run<N>.yaml；完整 prompt 与原始回复存 runs/<date>/<hero>_review_run<N>.json。
用法：python -m pipeline.reviewer proposals/agent/2026-09-08_kiriko_run1.yaml [--model deepseek-chat]"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys

import yaml

from .agent import call_deepseek, parse_yaml_output, schema_excerpt
from .loader import ROOT, load_schema, load_yaml

REVIEW_FORMAT = """输出一个 YAML 文档，且只输出 YAML（不要 markdown 围栏、不要解释）。结构：
hero: <hero_id>
per_change:
  - path: <与输入相同>
    direction: buff | nerf | ambiguous      # 只依据字段语义与数值增减；语义 ambiguous 的字段说明你依据什么判断
    basis: <一句话>
overall_direction: buff | nerf | mixed
inferred_intent: <2–4 句：这组改动合起来想解决什么问题；只能从数值本身推，不要编造背景>
confidence: high | medium | low
cannot_determine: [<从 diff 无法判断的事项，例如"对冲是否抵消""是否针对某模式">]
suspicious: [<看起来自相矛盾或不像出自同一意图的改动，没有就留空列表>]"""


def build_review_prompt(proposal: dict, schema: dict) -> tuple[str, str, dict]:
    (hero_id, ph), = proposal["heroes"].items()
    diff = [{"path": c["path"], "from": c.get("from"), "to": c.get("to")} for c in ph.get("changes") or []]
    system = ("你是射击游戏数值管线里的独立审核者。你只能看到一组配置数值的改动前后值，看不到任何说明。"
              "任务：从数值本身反推这次改动的方向与意图。不要假设你知道这次补丁的背景。")
    user = "\n\n".join([
        f"# 配置 diff（{hero_id}）\n```yaml\n{yaml.safe_dump(diff, allow_unicode=True, sort_keys=False)}```",
        f"# 字段语义\n{schema_excerpt(schema)}",
        f"# 输出格式\n{REVIEW_FORMAT}",
    ])
    # 泄漏自检：执行方的说明性字段与开发者注释关键词不得出现在审核输入中
    leaked = [k for k in ("why", "expected_direction", "mixed_rationale", "Developer Comments", "unmapped") if k in user]
    return system, user, {"hero": hero_id, "n_changes": len(diff), "leak_check": leaked}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("proposal_path"); ap.add_argument("--model", default="deepseek-chat")
    a = ap.parse_args(argv)
    proposal = load_yaml(ROOT / a.proposal_path)
    system, user, meta = build_review_prompt(proposal, load_schema())
    if meta["leak_check"]:
        print(f"ABORT: reviewer input leaks executor fields: {meta['leak_check']}", file=sys.stderr); return 2
    m = re.match(r"(\d{4}-\d{2}-\d{2})_([a-z]+)_run(\d+)", os.path.basename(a.proposal_path))
    date, hero, n = m.group(1), m.group(2), int(m.group(3))
    out_dir = ROOT / "reviews"; out_dir.mkdir(exist_ok=True)
    run_dir = ROOT / "runs" / date; run_dir.mkdir(parents=True, exist_ok=True)
    rec = {"date": date, "hero": hero, "executor_run": n, "model_requested": a.model, "reads": "diff only",
           "prompt_sha256": hashlib.sha256((system + user).encode()).hexdigest(), "system": system, "user": user, **meta}
    try:
        r = call_deepseek(system, user, a.model); rec.update(r)
        parsed = parse_yaml_output(r["content"]); rec["parse"] = "ok"
        out = out_dir / f"{date}_{hero}_run{n}.yaml"
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"# reviewer output — {a.model} — reads diff only — raw record: runs/{date}/{hero}_review_run{n}.json\n")
            yaml.safe_dump(parsed, f, allow_unicode=True, sort_keys=False)
        code = 0
    except Exception as e:  # noqa: BLE001
        rec["parse"] = f"error: {e!r}"; code = 2
    with open(run_dir / f"{hero}_review_run{n}.json", "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print(f"review {date} {hero} run{n}: parse={rec['parse']} -> reviews/{date}_{hero}_run{n}.yaml" if code == 0 else f"review failed: {rec['parse']}")
    return code


if __name__ == "__main__":
    sys.exit(main())
