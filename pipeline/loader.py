"""读取 schema / sources / baseline / fixture / patch / proposal；提供路径取值与来源冲突查询。"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"


def load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_schema() -> dict:
    return load_yaml(CONFIG / "schema.yaml")


def load_invariants() -> dict:
    return load_yaml(ROOT / "spec" / "invariants.yaml")


def load_hero_dir(rel: str) -> dict[str, dict]:
    """rel 形如 'baseline' 或 'fixtures/2026-09-08_before'；返回 {hero_id: data}。"""
    d = CONFIG / rel
    out = {}
    for p in sorted(d.glob("*.yaml")):
        data = load_yaml(p)
        out[data["id"]] = data
    return out


def load_patch(date: str) -> dict:
    return load_yaml(CONFIG / "patches" / f"{date}.yaml")


def load_proposal(name: str) -> dict:
    p = ROOT / "proposals" / (name if name.endswith(".yaml") else f"{name}.yaml")
    return load_yaml(p)


# ---------- 路径寻址 ----------
# path 约定：weapons.<weapon_id>.<field> / abilities.<ability_id>.<field>[.<v5|v6>] / hitpoints.<field>

def _find_in_list(items: list, item_id: str) -> dict | None:
    for it in items:
        if it.get("id") == item_id:
            return it
    return None


def get_path(hero: dict, path: str) -> Any:
    parts = path.split(".")
    cur: Any = hero
    for i, part in enumerate(parts):
        if isinstance(cur, list):
            cur = _find_in_list(cur, part)
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
        if cur is None:
            return None
    return cur


def set_path(hero: dict, path: str, value: Any) -> None:
    parts = path.split(".")
    cur: Any = hero
    for part in parts[:-1]:
        nxt = _find_in_list(cur, part) if isinstance(cur, list) else cur.get(part)
        if nxt is None:
            raise KeyError(f"path not found: {path} (at {part})")
        cur = nxt
    last = parts[-1]
    if isinstance(cur, list):
        raise KeyError(f"cannot set list element by id: {path}")
    cur[last] = value


def apply_changes(hero: dict, changes: list[dict], use: str = "to") -> dict:
    """返回应用了 changes[*][use] 的深拷贝。"""
    h = copy.deepcopy(hero)
    for c in changes:
        set_path(h, c["path"], c[use])
    return h


def open_conflicts(hero: dict) -> set[str]:
    """未关闭的来源冲突字段路径集合（前缀匹配用）。"""
    out = set()
    for c in (hero.get("provenance") or {}).get("conflicts") or []:
        if str(c.get("status", "")).upper() == "REVIEW":
            out.add(c["field"])
    return out


def missing_fields(hero: dict) -> set[str]:
    return {m["field"] for m in ((hero.get("provenance") or {}).get("missing") or [])}


def path_blocked(hero: dict, path: str) -> str | None:
    """若 path 或其前缀处于未关闭冲突 / 缺失清单中，返回原因，否则 None。"""
    for c in open_conflicts(hero):
        if path == c or path.startswith(c + "."):
            return f"open source conflict on {c}"
    for m in missing_fields(hero):
        if path == m or path.startswith(m + "."):
            return f"field listed as missing: {m}"
    return None
