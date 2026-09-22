"""决定文件格式校验：pending / 缺理由 / 全局 scope / 漏项 都必须被抓；机器不判决定内容。"""
import yaml

from pipeline import decisions as D


def _write(tmp_path, items):
    p = tmp_path / "decisions.yaml"
    yaml.safe_dump({"items": items}, open(p, "w", encoding="utf-8"), allow_unicode=True)
    return p


def test_pending_is_a_problem_unless_allowed(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "expected_items", lambda: set())
    p = _write(tmp_path, [{"hero": "dmon", "item": "x", "decision": "pending"}])
    assert any("pending" in s for s in D.validate(p)[0])
    assert D.validate(p, allow_pending=True)[0] == []


def test_reason_scope_and_global_scope(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "expected_items", lambda: set())
    p = _write(tmp_path, [
        {"hero": "dmon", "item": "a", "decision": "accepted", "reason": "short", "scope": "dmon abilities.call_mech"},
        {"hero": "dmon", "item": "b", "decision": "accepted", "reason": "long enough reason here", "scope": None},
        {"hero": "dmon", "item": "c", "decision": "accepted", "reason": "long enough reason here", "scope": "all heroes"},
        {"hero": "dmon", "item": "d", "decision": "resolved", "reason": "long enough reason here", "scope": "dmon abilities.call_mech.duration_s"},
        {"hero": "dmon", "item": "e", "decision": "maybe", "reason": "long enough reason here", "scope": "dmon"},
    ])
    probs = D.validate(p)[0]
    assert any("#0" in s and "too short" in s for s in probs)
    assert any("#1" in s and "scope missing" in s for s in probs)
    assert any("#2" in s and ("global" in s or "must name the hero" in s) for s in probs)
    assert not any("#3" in s for s in probs)
    assert any("#4" in s and "not in" in s for s in probs)


def test_missing_expected_item_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "expected_items", lambda: {("wuyang", "overall: executor buff vs reviewer mixed")})
    p = _write(tmp_path, [{"hero": "dmon", "item": "a", "decision": "accepted", "reason": "long enough reason here", "scope": "dmon x"}])
    assert any("MISSING entry for wuyang" in s for s in D.validate(p)[0])


def test_repo_template_covers_every_expected_item():
    """仓库里的决定文件不得漏掉任何一条当前 REVIEW 项（内容可以 pending，条目不能缺）。"""
    probs, counts = D.validate(allow_pending=True)
    assert not [s for s in probs if s.startswith("MISSING")], probs
