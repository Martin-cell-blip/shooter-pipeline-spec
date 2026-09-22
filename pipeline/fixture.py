"""构造「改动前」夹具：baseline 回填官方 from 值。幂等。
用法：python -m pipeline.fixture build 2026-09-08"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from .loader import CONFIG, apply_changes, get_path, load_hero_dir, load_patch


def build(date: str) -> list[Path]:
    patch = load_patch(date)
    baseline = load_hero_dir("baseline")
    out_dir = CONFIG / "fixtures" / f"{date}_before"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for entry in patch["entries"]:
        hero = baseline[entry["hero"]]
        # 补丁文件用 field，提案用 path；此处统一
        entry = {**entry, "changes": [{**c, "path": c.get("path") or c["field"]} for c in entry["changes"]]}
        # 先核对：baseline 上这些字段确实等于官方 to 值，否则夹具前提不成立
        mismatch = [c["path"] for c in entry["changes"] if get_path(hero, c["path"]) != c["to"]]
        if mismatch:
            raise SystemExit(f"{entry['hero']}: baseline does not carry official 'to' values at {mismatch}; fixture precondition fails")
        before = apply_changes(hero, entry["changes"], use="from")
        prov = before.setdefault("provenance", {})
        prov["fixture"] = {
            "kind": "constructed_before_snapshot",
            "patch": date,
            "method": "baseline with official 'from' values written back on listed paths",
            "assumes": ["patch entries cover all numeric changes for this hero on that date",
                        "no later patch touched these paths before baseline fetch (2026-09-22)"],
            "restored_paths": [c["path"] for c in entry["changes"]],
        }
        p = out_dir / f"{entry['hero']}.yaml"
        with open(p, "w", encoding="utf-8") as f:
            yaml.safe_dump(before, f, allow_unicode=True, sort_keys=False)
        written.append(p)
    return written


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "build":
        raise SystemExit(__doc__)
    for p in build(sys.argv[2]):
        print("wrote", p.relative_to(CONFIG.parent))
