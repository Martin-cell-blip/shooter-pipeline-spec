"""校验入口。
用法：python -m pipeline.check <proposal_name> [--out reports]
退出码：0 无 FAIL；1 有 FAIL；2 加载/异常。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .checks import run_proposal
from .loader import ROOT, load_hero_dir, load_invariants, load_proposal, load_schema
from .report import summarize, write_reports


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("proposal")
    ap.add_argument("--out", default="reports")
    args = ap.parse_args(argv)
    try:
        schema, inv = load_schema(), load_invariants()
        proposal = load_proposal(args.proposal)
        before = load_hero_dir(proposal["before"])
        baseline = load_hero_dir("baseline")
    except Exception as e:  # noqa: BLE001
        print(f"LOAD ERROR: {e!r}", file=sys.stderr)
        return 2
    results = run_proposal(schema, inv, proposal, before, baseline)
    pj, pm = write_reports(results, ROOT / args.out, proposal["proposal_id"])
    s = summarize(results)
    print(f"{s['final']}  " + "  ".join(f"{k}={v}" for k, v in sorted(s["counts"].items())) + f"\n-> {pm.relative_to(ROOT)}")
    return s["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
