"""确定性预分类器（迭代 2，借鉴 dota-patch-intelligence 的四态分类：NUMERIC / KNOWN_SEMANTIC / PARTIALLY_CLASSIFIED / UNKNOWN）。

在任何 LLM 之前，对补丁原文的每一条目行做纯规则分类：
  NUMERIC              能解析出 old/new（含单位、模式）——这一层不需要模型；模型给出的 from/to 若与它不一致即为可疑
  KNOWN_SEMANTIC       命中 spec/ontology.yaml 的已知非数值模式
  PARTIALLY_CLASSIFIED 未命中模式但与本体关键词有交集（置信 0.5，须人看）
  UNKNOWN              兜底，须人看并回填本体
用法：python -m pipeline.preclassify config/patches/2026-09-08_raw.txt [--hero D.Mon]"""
from __future__ import annotations

import argparse
import re
import sys

import yaml

from .loader import ROOT

NUM = r"[0-9]+(?:\.[0-9]+)?"
UNIT = r"(?:meters per second|per second|seconds?|meters?|degrees?|m/s|%|s|m)?"   # 最长优先，否则 s 会吃掉 seconds 的首字母
# 形态 A：... from X[unit] to Y[unit] ...
P_FROM_TO = re.compile(rf"\bfrom\s+({NUM})\s*({UNIT})\s+to\s+({NUM})\s*({UNIT})", re.I)
# 形态 B：... to Y[unit] (Up|Down from X[unit])
P_TO_UPDOWN = re.compile(rf"\bto\s+({NUM})\s*({UNIT})[^()]{{0,30}}?\((?:up|down)\s+from\s+({NUM})\s*({UNIT})\)", re.I)   # 允许 "to 20% of healing (Down from 30%)"
P_MODE = re.compile(r"\((5v5|6v6)\)")
P_TRAIL_UNIT = re.compile(rf"\b(seconds?|meters?|degrees?|per second|m/s)\b", re.I)
VERBS_UP = ("increased", "raised", "improved", "extended")
VERBS_DOWN = ("reduced", "decreased", "lowered", "shortened")


def load_ontology() -> dict:
    return yaml.safe_load(open(ROOT / "spec" / "ontology.yaml", encoding="utf-8"))


def _norm_unit(u: str | None, line: str) -> str | None:
    u = (u or "").strip().lower()
    if not u:
        m = P_TRAIL_UNIT.search(line)
        u = m.group(1).lower() if m else ""
    return {"": None, "s": "s", "second": "s", "seconds": "s", "m": "m", "meter": "m", "meters": "m",
            "degree": "deg", "degrees": "deg", "%": "pct", "per second": "per_s", "meters per second": "m_per_s", "m/s": "m_per_s"}.get(u, u)


def classify_line(line: str, ontology: dict | None = None) -> dict:
    """返回 {state, old, new, unit, mode, verb_direction, tag, confidence, reason}。"""
    ont = ontology or load_ontology()
    text = line.strip().lstrip("-• ").strip()
    low = text.lower()
    mode = (P_MODE.search(text) or [None, None])[1]
    out = {"line": text, "mode": mode}
    m = P_FROM_TO.search(text)
    if m:
        old, u1, new, u2 = m.groups()
        out.update(state="NUMERIC", old=float(old), new=float(new), unit=_norm_unit(u2 or u1, text), confidence=1.0,
                   reason="from-X-to-Y pattern")
    else:
        m = P_TO_UPDOWN.search(text)
        if m:
            new, u1, old, u2 = m.groups()
            out.update(state="NUMERIC", old=float(old), new=float(new), unit=_norm_unit(u1 or u2, text), confidence=1.0,
                       reason="to-Y-(Up/Down-from-X) pattern")
    if out.get("state") == "NUMERIC":
        up, down = any(v in low for v in VERBS_UP), any(v in low for v in VERBS_DOWN)
        out["verb_direction"] = "up" if up and not down else ("down" if down and not up else None)   # 两个都出现（技能名里含 increased）不判
        # 动词与数值方向自洽性：说 reduced 但 new > old → 标可疑（不改判，交人）
        if out["verb_direction"] == "up" and out["new"] < out["old"] or out["verb_direction"] == "down" and out["new"] > out["old"]:
            out["suspicious"] = "verb contradicts numbers"
        return out
    for t in ont["tags"]:
        if any(p in low for p in t["patterns"]):
            out.update(state="KNOWN_SEMANTIC", tag=t["tag"], kind=t["kind"], default_direction=t["default_direction"],
                       config_relevant=t["config_relevant"], confidence=0.9, reason=f"ontology pattern match ({t['tag']})")
            return out
    # 关键词交集启发（Dota 项目的 keyword weighting）：本体所有 pattern 里长度>4 的词
    vocab = {w for t in ont["tags"] for p in t["patterns"] for w in p.split() if len(w) > 4}
    hits = sorted(w for w in vocab if w in low)
    if hits:
        out.update(state="PARTIALLY_CLASSIFIED", confidence=0.5, keyword_hits=hits, reason="shares vocabulary with ontology; needs human review")
    else:
        out.update(state="UNKNOWN", confidence=0.0, reason="no pattern, no vocabulary overlap; needs human review and ontology backfill")
    return out


def classify_raw(raw: str, hero_en: str | None = None) -> list[dict]:
    """按 raw.txt 的层级（## 英雄 / ### 技能 / - 条目）分类；Developer Comments 不是条目，跳过。"""
    ont = load_ontology(); out = []; hero = None; ability = None
    for ln in raw.splitlines():
        if ln.startswith("## "):
            hero, ability = ln[3:].strip(), None; continue
        if ln.startswith("### "):
            ability = ln[4:].strip(); continue
        if not ln.startswith("- "):
            continue
        if hero_en and hero != hero_en:
            continue
        rec = classify_line(ln, ont); rec.update(hero=hero, ability=ability); out.append(rec)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("raw_path"); ap.add_argument("--hero")
    a = ap.parse_args(argv)
    recs = classify_raw(open(ROOT / a.raw_path, encoding="utf-8").read(), a.hero)
    from collections import Counter
    print(Counter(r["state"] for r in recs))
    for r in recs:
        extra = f"{r.get('old')}→{r.get('new')} {r.get('unit') or ''} {('['+r['mode']+']') if r.get('mode') else ''}" if r["state"] == "NUMERIC" else (r.get("tag") or r.get("keyword_hits") or "")
        print(f"  {r['state']:<22} {r['hero']:<10} {str(r['ability'])[:22]:<22} {extra!s:<28} {r['line'][:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
