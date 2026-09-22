"""执行 Agent：把非结构化补丁说明翻译成提案格式的配置改动。

输入：①补丁原文（config/patches/<date>_raw.txt 中该英雄的段落）②该英雄的改动前快照 ③schema 的字段与方向语义 ④提案格式说明。
输出：proposals/agent/<date>_<hero>_run<N>.yaml，以及 runs/<date>/<hero>_run<N>.json（完整 prompt、原始回复、模型、时间）。
边界：Agent 不读 baseline（那是答案）、不读校验器、不自评；解析失败原样记录并退出码 2，不做"修一修再交"。
用法：python -m pipeline.agent 2026-09-08 kiriko [--model deepseek-chat] [--run N]"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import yaml

from .loader import CONFIG, ROOT, load_hero_dir, load_schema

PROPOSAL_FORMAT = """输出一个 YAML 文档，且只输出 YAML（不要 markdown 围栏、不要解释）。结构：
proposal_id: <string>
before: fixtures/<date>_before
heroes:
  <hero_id>:
    overall_direction: buff | nerf | mixed
    mixed_rationale: <string 或 null>        # 既有 buff 又有 nerf 时必须说明对冲理由
    changes:
      - path: <weapons.<weapon_id>.<field> | abilities.<ability_id>.<field>[.v5|.v6] | hitpoints.<field>>
        from: <number>                        # 必须等于改动前快照上的值
        to: <number>
        expected_direction: buff | nerf | ambiguous
        why: <string，引用补丁原文中的依据>
        mode: 5v5 | 6v6                       # 仅当条目标注了模式
    linked_dispositions:                      # 若改动了 schema.linked 中某对字段之一，对另一个给处置：keep | changed | "not_needed: <理由>"
      <path>: <disposition>
    unmapped:                                 # 原文中无法映射到快照任何字段的条目，原样列出，不要硬凑
      - <原文行>
规则：
- path 必须是改动前快照中真实存在的键；不存在就放进 unmapped。
- from 取快照上的值；若原文的 from 与快照不一致，仍按快照写 from，并在 why 里说明不一致。
- expected_direction 按字段方向语义判断；语义为 ambiguous 的字段按原文上下文判断并在 why 说明。
- 不要修改与原文无关的字段。"""


def hero_section(raw: str, hero_en: str) -> str:
    m = re.search(rf"^## {re.escape(hero_en)}\n(.*?)(?=^## |\Z)", raw, flags=re.S | re.M)
    if not m:
        raise SystemExit(f"hero {hero_en} not found in raw patch text")
    return m.group(0).strip()


def schema_excerpt(schema: dict) -> str:
    lines = ["字段方向语义（higher_is：数值变大对该英雄是 buff 还是 nerf；ambiguous 需按上下文判断）："]
    for sec, m in (schema.get("semantics") or {}).items():
        lines.append(f"- {sec}: " + ", ".join(f"{k}={v}" for k, v in m.items()))
    lines.append("联动字段对（改其一须对另一个给处置记录）：" + "; ".join("+".join(p) for p in schema["weapon"]["linked"]))
    lines.append("单位：距离 m，时间 s，射速 shots/s，速度 m/s。")
    return "\n".join(lines)


def build_prompt(date: str, hero_id: str, schema: dict) -> tuple[str, str]:
    raw = (CONFIG / "patches" / f"{date}_raw.txt").read_text(encoding="utf-8")
    before = load_hero_dir(f"fixtures/{date}_before")[hero_id]
    snapshot = {k: v for k, v in before.items() if k != "provenance"}
    system = ("你是射击游戏数值管线里的配置改动执行者。任务：把官方补丁说明的自然语言条目翻译成对配置表的精确改动提案。"
              "你只负责提取与映射，不负责判断改动是否合理；不确定的映射不要猜，放进 unmapped。")
    user = "\n\n".join([
        f"# 补丁原文（{date}）\n{hero_section(raw, before['name_en'])}",
        f"# 改动前快照（{hero_id}）\n```yaml\n{yaml.safe_dump(snapshot, allow_unicode=True, sort_keys=False)}```",
        f"# 字段语义\n{schema_excerpt(schema)}",
        f"# 提案格式\n{PROPOSAL_FORMAT.replace('<date>', date)}",
    ])
    return system, user


def call_deepseek(system: str, user: str, model: str) -> dict:
    from openai import OpenAI
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("DEEPSEEK_API_KEY not set")
    client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
    t0 = dt.datetime.now(dt.timezone.utc)
    resp = client.chat.completions.create(model=model, temperature=0,
                                          messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    t1 = dt.datetime.now(dt.timezone.utc)
    return {"content": resp.choices[0].message.content, "model": resp.model, "usage": resp.usage.model_dump() if resp.usage else None,
            "started": t0.isoformat(), "seconds": (t1 - t0).total_seconds()}


def parse_yaml_output(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:yaml)?\s*|\s*```$", "", t, flags=re.S)  # 记录违规但仍尝试解析
    return yaml.safe_load(t)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("date"); ap.add_argument("hero")
    ap.add_argument("--model", default="deepseek-chat"); ap.add_argument("--run", type=int, default=None)
    a = ap.parse_args(argv)
    schema = load_schema()
    system, user = build_prompt(a.date, a.hero, schema)
    run_dir = ROOT / "runs" / a.date; run_dir.mkdir(parents=True, exist_ok=True)
    n = a.run or (len(list(run_dir.glob(f"{a.hero}_run*.json"))) + 1)
    out_prop = ROOT / "proposals" / "agent" / f"{a.date}_{a.hero}_run{n}.yaml"
    out_prop.parent.mkdir(parents=True, exist_ok=True)
    rec = {"date": a.date, "hero": a.hero, "run": n, "model_requested": a.model,
           "prompt_sha256": hashlib.sha256((system + user).encode()).hexdigest(), "system": system, "user": user}
    try:
        r = call_deepseek(system, user, a.model)
        rec.update(r)
        rec["fenced_output"] = r["content"].strip().startswith("```")
        parsed = parse_yaml_output(r["content"])
        rec["parse"] = "ok"
        with open(out_prop, "w", encoding="utf-8") as f:
            f.write(f"# agent output — {a.model} — run {n} — raw record: runs/{a.date}/{a.hero}_run{n}.json\n")
            yaml.safe_dump(parsed, f, allow_unicode=True, sort_keys=False)
        code = 0
    except Exception as e:  # noqa: BLE001
        rec["parse"] = f"error: {e!r}"; code = 2
    with open(run_dir / f"{a.hero}_run{n}.json", "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print(f"run {n}: parse={rec['parse']} fenced={rec.get('fenced_output')} -> {out_prop.relative_to(ROOT) if code == 0 else '(no proposal written)'}")
    return code


if __name__ == "__main__":
    sys.exit(main())
