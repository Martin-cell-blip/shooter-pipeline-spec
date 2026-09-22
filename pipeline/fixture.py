"""构造「改动前」夹具：baseline 回填官方 from 值。幂等。
处理补丁叠加：目标日期 D 之后还有补丁改过同一英雄时，先按时间倒序撤销那些补丁（回填其 from），再撤销 D 本身。
用法：python -m pipeline.fixture build 2026-09-08"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from .loader import CONFIG, apply_changes, get_path, load_hero_dir, load_patch


def _norm(entry: dict) -> dict:
    """补丁文件用 field，提案用 path；统一；丢弃 field 为空的不可映射条目（那是给 Agent 的考题，不参与夹具）。"""
    return {**entry, "changes": [{**c, "path": c.get("path") or c["field"]} for c in entry["changes"] if (c.get("path") or c.get("field"))]}


def _all_patches() -> list[dict]:
    out = []
    for p in sorted((CONFIG / "patches").glob("*.yaml")):
        d = load_patch(p.stem)
        d["date"] = str(d["date"])   # YAML 会把裸日期解析成 date 对象，统一为字符串
        out.append(d)
    return out


def build(date: str) -> list[Path]:
    patches = _all_patches()
    target = next(p for p in patches if p["date"] == date)
    later = sorted([p for p in patches if p["date"] > date], key=lambda p: p["date"], reverse=True)
    baseline = load_hero_dir("baseline")
    out_dir = CONFIG / "fixtures" / f"{date}_before"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for entry in target["entries"]:
        entry = _norm(entry)
        hero_id = entry["hero"]
        hero = baseline[hero_id]
        undone = []
        # 1) 先撤销更晚的补丁（时间倒序）
        for lp in later:
            for le in lp["entries"]:
                if le["hero"] != hero_id:
                    continue
                le = _norm(le)
                mismatch = [c["path"] for c in le["changes"] if get_path(hero, c["path"]) != c["to"]]
                if mismatch:
                    raise SystemExit(f"{hero_id}: cannot undo later patch {lp['date']} — baseline does not carry its 'to' values at {mismatch}")
                hero = apply_changes(hero, le["changes"], use="from")
                undone.append({"patch": lp["date"], "paths": [c["path"] for c in le["changes"]]})
        # 2) 核对目标补丁的 to 值现在都在（撤销晚期补丁之后的状态）
        mismatch = [c["path"] for c in entry["changes"] if get_path(hero, c["path"]) != c["to"]]
        if mismatch:
            raise SystemExit(f"{hero_id}: state after undoing later patches does not carry official 'to' values at {mismatch}; fixture precondition fails")
        before = apply_changes(hero, entry["changes"], use="from")
        prov = before.setdefault("provenance", {})
        prov["fixture"] = {
            "kind": "constructed_before_snapshot",
            "patch": date,
            "method": "baseline; later patches undone in reverse order; then official 'from' values written back on listed paths",
            "later_patches_undone": undone,
            "assumes": ["patch entries cover all numeric changes for this hero on each listed date",
                        "no unlisted patch touched these paths before baseline fetch (2026-09-22)"],
            "restored_paths": [c["path"] for c in entry["changes"]],
        }
        p = out_dir / f"{hero_id}.yaml"
        with open(p, "w", encoding="utf-8") as f:
            yaml.safe_dump(before, f, allow_unicode=True, sort_keys=False)
        written.append(p)
    return written


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "build":
        raise SystemExit(__doc__)
    for p in build(sys.argv[2]):
        print("wrote", p.relative_to(CONFIG.parent))
