"""审核 Agent 的输入隔离与事后比对。"""
from pipeline.loader import load_proposal, load_schema
from pipeline.reviewer import build_review_prompt
from pipeline.reconcile import reconcile

SCHEMA = load_schema()


def _single(proposal, hero):
    return {"heroes": {hero: proposal["heroes"][hero]}}


def test_reviewer_input_is_diff_only():
    """审核方看不到执行方的 why / expected_direction / mixed_rationale / unmapped，也看不到开发者注释与补丁原文。"""
    p = _single(load_proposal("2026-09-08_official"), "dmon")
    system, user, meta = build_review_prompt(p, SCHEMA)
    assert meta["leak_check"] == []
    for banned in ("抵消增强", "Developer Comments", "settled into a strong position", "Notches", "expected_direction", "why:"):
        assert banned not in user
    assert "hitpoints_by_mode.v6.armor" in user and "from: 325" in user and "to: 300" in user
    assert meta["n_changes"] == 5


def test_reviewer_prompt_has_no_intent_even_when_patch_has_one():
    p = _single(load_proposal("2026-09-08_official"), "winston")
    _, user, _ = build_review_prompt(p, SCHEMA)
    assert "downtime between engagements" not in user and "offset" not in user


def test_reconcile_flags_direction_and_missing_intent(tmp_path, monkeypatch):
    """构造：执行方说 buff、审核方说 nerf → REVIEW；无官方注释 → REVIEW。"""
    from pipeline import reconcile as R
    import yaml
    root = tmp_path
    (root / "proposals" / "agent").mkdir(parents=True); (root / "reviews").mkdir(); (root / "config" / "patches").mkdir(parents=True)
    yaml.safe_dump({"heroes": {"h": {"overall_direction": "buff", "changes": [{"path": "abilities.x.duration_s", "from": 2, "to": 1, "expected_direction": "buff", "why": "cast shorter"}]}}},
                   open(root / "proposals" / "agent" / "2026-01-01_h_run1.yaml", "w", encoding="utf-8"), allow_unicode=True)
    yaml.safe_dump({"hero": "h", "overall_direction": "nerf", "per_change": [{"path": "abilities.x.duration_s", "direction": "nerf", "basis": "shorter"}],
                    "inferred_intent": "nerf", "confidence": "low", "cannot_determine": [], "suspicious": ["x"]},
                   open(root / "reviews" / "2026-01-01_h_run1.yaml", "w", encoding="utf-8"), allow_unicode=True)
    yaml.safe_dump({"date": "2026-01-01", "entries": [{"hero": "h", "intent": None, "direction": None, "changes": []}]},
                   open(root / "config" / "patches" / "2026-01-01.yaml", "w", encoding="utf-8"))
    monkeypatch.setattr(R, "ROOT", root)
    monkeypatch.setattr(R, "load_patch", lambda d: yaml.safe_load(open(root / "config" / "patches" / f"{d}.yaml", encoding="utf-8")))
    res = R.reconcile("2026-01-01", "h", 1)
    whats = " | ".join(i["what"] for i in res["items"])
    assert "executor declared buff, reviewer inferred nerf" in whats
    assert "no official developer comment" in whats
    assert "suspicious" in whats
    assert res["side_by_side"]["official_intent"] is None
