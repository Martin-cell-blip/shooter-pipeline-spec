"""四态汇总与退出码。0 = 无 FAIL 且无因异常导致的 NOT_RUN（允许 open REVIEW 与因缺输入的 NOT_RUN）；1 = 有 FAIL；2 = 有异常型 NOT_RUN 或加载失败。"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ORDER = ["FAIL", "REVIEW", "NOT_RUN", "PASS"]


def summarize(results: list[dict]) -> dict:
    c = Counter(r["status"] for r in results)
    exc = [r for r in results if r["status"] == "NOT_RUN" and "exception" in r.get("detail", "")]
    if c["FAIL"]:
        code, final = 1, "FAIL"
    elif exc:
        code, final = 2, "ERROR"
    else:
        code, final = 0, ("READY_FOR_HUMAN_REVIEW" if c["REVIEW"] or c["NOT_RUN"] else "PASS")
    return {"counts": dict(c), "exit_code": code, "final": final, "exception_not_run": len(exc)}


def to_markdown(results: list[dict], title: str) -> str:
    s = summarize(results)
    lines = [f"# {title}", "",
             f"**结论：{s['final']}**（exit {s['exit_code']}）— " + " / ".join(f"{k} {s['counts'].get(k, 0)}" for k in ORDER), "",
             "终态不设自动批准；READY_FOR_HUMAN_REVIEW 表示机器已无 FAIL，剩余 REVIEW / NOT_RUN 须人工逐条处置并写入决定文件。", ""]
    for status in ORDER:
        rows = [r for r in results if r["status"] == status]
        if not rows:
            continue
        lines += [f"## {status} ({len(rows)})", "", "| check | hero | detail |", "|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['check']} | {r['hero']} | {r['detail'].replace('|', '\\|')} |")
        lines.append("")
    return "\n".join(lines)


def write_reports(results: list[dict], out_dir: Path, name: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pj, pm = out_dir / f"{name}.json", out_dir / f"{name}.md"
    with open(pj, "w", encoding="utf-8") as f:
        json.dump({"summary": summarize(results), "results": results}, f, ensure_ascii=False, indent=2, default=str)
    with open(pm, "w", encoding="utf-8") as f:
        f.write(to_markdown(results, name))
    return pj, pm
