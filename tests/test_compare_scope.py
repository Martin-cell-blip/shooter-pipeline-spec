import copy

from pipeline.compare import compare, acceptance_ok
from pipeline.loader import load_proposal


def test_empty_hero_mapping_cannot_pass():
    golden = load_proposal("2026-09-08_official")
    assert not acceptance_ok(compare({"heroes": {}}, golden))


def test_partial_requires_explicit_scope_and_rejects_extra_heroes():
    golden = load_proposal("2026-09-08_official")
    proposal = {"heroes": {"winston": copy.deepcopy(golden["heroes"]["winston"])}}
    assert not acceptance_ok(compare(proposal, golden))
    assert acceptance_ok(compare(proposal, golden, ["winston"]))
    assert not acceptance_ok(compare(proposal, golden, []))
    assert not acceptance_ok(compare(proposal, golden, ["unknown"]))
    proposal["heroes"]["unexpected"] = {"changes": []}
    assert not acceptance_ok(compare(proposal, golden, ["winston"]))


def test_duplicate_paths_are_not_silently_collapsed():
    golden = load_proposal("2026-09-17_official")
    proposal = copy.deepcopy(golden)
    proposal["heroes"]["dmon"]["changes"].append(copy.deepcopy(proposal["heroes"]["dmon"]["changes"][0]))
    assert not acceptance_ok(compare(proposal, golden))
