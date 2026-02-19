#!/usr/bin/env python3
"""Build a debug shortlist from timeout-skipped studies in a batched mega report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def _safe_name(study_id: str) -> str:
    return study_id.replace(" ", "_").replace("/", "_")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_matched_index(path: Path) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        study_id = row.get("study_id")
        if not study_id:
            continue
        out[str(study_id)] = row
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-json",
        type=Path,
        default=Path("output/mega_batched_run_report_cont_to_500_fast2s.json"),
    )
    parser.add_argument(
        "--mega-matched-jsonl",
        type=Path,
        default=Path("gold_data/mega/mega_matched.jsonl"),
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path("gold_data/mega/pdfs"),
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=40,
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("output/mega_timeout_shortlist_500.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("output/mega_timeout_shortlist_500.md"),
    )
    args = parser.parse_args()

    if args.top_n <= 0:
        raise ValueError("--top-n must be > 0")
    if not args.report_json.exists():
        raise FileNotFoundError(f"Missing report: {args.report_json}")

    report = _load_json(args.report_json)
    matched = _load_matched_index(args.mega_matched_jsonl) if args.mega_matched_jsonl.exists() else {}

    rounds: List[dict] = report.get("rounds", [])
    skipped_rows: List[dict] = []
    for rec in rounds:
        sid = rec.get("auto_skipped_study_id")
        if not sid:
            continue
        sid = str(sid)
        mm = matched.get(sid, {})
        pmcid = mm.get("pmcid")
        pdf_name = f"{_safe_name(sid)}_{pmcid}.pdf" if pmcid else None
        pdf_path = args.pdf_dir / pdf_name if pdf_name else None
        skipped_rows.append(
            {
                "round": rec.get("round"),
                "study_id": sid,
                "pmcid": pmcid,
                "pdf_path": str(pdf_path) if pdf_path else None,
                "pdf_exists": bool(pdf_path and pdf_path.exists()),
                "first_author": mm.get("first_author"),
                "year": mm.get("year"),
                "comparisons_count": len(mm.get("comparisons", []) or []),
                "timeout_sec": report.get("round_timeout_sec"),
            }
        )

    shortlist = skipped_rows[: args.top_n]
    output_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "report_json": str(args.report_json),
        "start_rows": report.get("start_rows"),
        "end_rows": report.get("end_rows"),
        "total_added": report.get("total_added"),
        "round_timeout_sec": report.get("round_timeout_sec"),
        "total_rounds": len(rounds),
        "total_auto_skipped": len(skipped_rows),
        "unique_auto_skipped": len({r["study_id"] for r in skipped_rows}),
        "top_n": args.top_n,
        "shortlist": shortlist,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(output_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines: List[str] = []
    lines.append("# Mega Timeout Shortlist (500 Checkpoint)")
    lines.append("")
    lines.append(f"- Generated UTC: {output_payload['generated_at_utc']}")
    lines.append(f"- Source report: `{args.report_json}`")
    lines.append(
        f"- Rows: {output_payload['start_rows']} -> {output_payload['end_rows']} (+{output_payload['total_added']})"
    )
    lines.append(
        f"- Auto-skipped in run: {output_payload['total_auto_skipped']} (unique {output_payload['unique_auto_skipped']})"
    )
    lines.append(f"- Timeout per round: {output_payload['round_timeout_sec']}s")
    lines.append("")
    lines.append("## Top Timeout-Skipped Studies")
    lines.append("")
    lines.append("| Rank | Round | Study ID | PMCID | PDF Exists | Comparisons |")
    lines.append("|---:|---:|---|---|---:|---:|")
    for idx, row in enumerate(shortlist, start=1):
        lines.append(
            f"| {idx} | {row['round']} | {row['study_id']} | "
            f"{row['pmcid'] or ''} | {'yes' if row['pdf_exists'] else 'no'} | "
            f"{row['comparisons_count']} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- These are the earliest timeout-skipped studies from the selected run report.")
    lines.append("- Use this list for targeted parser-stage timing and hang diagnostics.")
    lines.append("")

    args.output_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote JSON: {args.output_json}")
    print(f"Wrote MD: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
