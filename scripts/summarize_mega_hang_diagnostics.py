#!/usr/bin/env python3
"""Summarize per-study mega diagnostics events into a hang-oriented report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Dict, List


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * 0.95))
    return ordered[idx]


def _load_rows(path: Path) -> List[dict]:
    rows: List[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rows.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diag-jsonl",
        type=Path,
        default=Path("output/mega_hang_diagnostics.jsonl"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("output/mega_hang_diagnostics_summary.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("output/mega_hang_diagnostics_summary.md"),
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=30,
    )
    args = parser.parse_args()

    if not args.diag_jsonl.exists():
        raise FileNotFoundError(f"Missing diagnostics file: {args.diag_jsonl}")

    rows = _load_rows(args.diag_jsonl)
    by_attempt: Dict[str, Dict[str, dict]] = {}
    parse_times: List[float] = []
    extract_times: List[float] = []

    for row in rows:
        attempt_id = str(row.get("attempt_id", ""))
        if attempt_id:
            by_attempt.setdefault(attempt_id, {})
            by_attempt[attempt_id][str(row.get("event", "unknown"))] = row

        probe = row.get("parser_probe") or {}
        t = probe.get("elapsed_sec")
        if isinstance(t, (int, float)):
            parse_times.append(float(t))
        et = row.get("pipeline_elapsed_sec")
        if isinstance(et, (int, float)):
            extract_times.append(float(et))

    pre_only = []
    completed = []
    for attempt_id, events in by_attempt.items():
        pre = events.get("pre_extract")
        res = events.get("result")
        if pre and not res:
            pre_only.append(pre)
        if res:
            completed.append(res)

    status_counts: Dict[str, int] = {}
    pipeline_timed_out_completed = 0
    fallback_used_count = 0
    fallback_effect_count = 0
    for res in completed:
        status = str(res.get("status", ""))
        status_counts[status] = status_counts.get(status, 0) + 1
        if bool(res.get("pipeline_timed_out")):
            pipeline_timed_out_completed += 1
        if bool(res.get("pipeline_fallback_used")):
            fallback_used_count += 1
            try:
                fallback_effect_count += int(res.get("pipeline_fallback_effect_count") or 0)
            except (TypeError, ValueError):
                pass

    top_hangs = pre_only[: args.top_n]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "diag_jsonl": str(args.diag_jsonl),
        "rows_loaded": len(rows),
        "attempts_seen": len(by_attempt),
        "completed_attempts": len(completed),
        "pre_only_attempts": len(pre_only),
        "status_counts_completed": status_counts,
        "pipeline_timed_out_completed": pipeline_timed_out_completed,
        "pipeline_fallback_used_count": fallback_used_count,
        "pipeline_fallback_effect_count": fallback_effect_count,
        "parser_probe_elapsed_sec": {
            "count": len(parse_times),
            "median": round(median(parse_times), 4) if parse_times else None,
            "p95": round(_p95(parse_times), 4) if parse_times else None,
            "max": round(max(parse_times), 4) if parse_times else None,
        },
        "pipeline_elapsed_sec": {
            "count": len(extract_times),
            "median": round(median(extract_times), 4) if extract_times else None,
            "p95": round(_p95(extract_times), 4) if extract_times else None,
            "max": round(max(extract_times), 4) if extract_times else None,
        },
        "top_pre_only_attempts": [
            {
                "attempt_id": row.get("attempt_id"),
                "study_id": row.get("study_id"),
                "pmcid": row.get("pmcid"),
                "fast_mode": row.get("fast_mode"),
                "pdf_path": row.get("pdf_path"),
                "pdf_size_bytes": row.get("pdf_size_bytes"),
                "parser_probe": row.get("parser_probe"),
                "recorded_at_utc": row.get("recorded_at_utc"),
            }
            for row in top_hangs
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines: List[str] = []
    lines.append("# Mega Hang Diagnostics Summary")
    lines.append("")
    lines.append(f"- Generated UTC: {summary['generated_at_utc']}")
    lines.append(f"- Source diagnostics: `{args.diag_jsonl}`")
    lines.append(f"- Attempts seen: {summary['attempts_seen']}")
    lines.append(f"- Completed attempts: {summary['completed_attempts']}")
    lines.append(f"- Pre-only attempts (likely timed out during extraction): {summary['pre_only_attempts']}")
    lines.append(f"- Pipeline timed-out (completed result rows): {summary['pipeline_timed_out_completed']}")
    lines.append(f"- Fallback used: {summary['pipeline_fallback_used_count']} attempts, {summary['pipeline_fallback_effect_count']} effects")
    lines.append("")
    lines.append("## Timing")
    lines.append("")
    lines.append(
        f"- Parser probe: count={summary['parser_probe_elapsed_sec']['count']}, "
        f"median={summary['parser_probe_elapsed_sec']['median']}, "
        f"p95={summary['parser_probe_elapsed_sec']['p95']}, "
        f"max={summary['parser_probe_elapsed_sec']['max']}"
    )
    lines.append(
        f"- Pipeline elapsed (completed only): count={summary['pipeline_elapsed_sec']['count']}, "
        f"median={summary['pipeline_elapsed_sec']['median']}, "
        f"p95={summary['pipeline_elapsed_sec']['p95']}, "
        f"max={summary['pipeline_elapsed_sec']['max']}"
    )
    lines.append("")
    lines.append("## Completed Status Mix")
    lines.append("")
    if status_counts:
        for k, v in sorted(status_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- No completed result events in this diagnostics set.")
    lines.append("")
    lines.append("## Top Pre-Only Attempts")
    lines.append("")
    lines.append("| Rank | Study ID | PMCID | Parser Probe (s) | PDF Size (bytes) |")
    lines.append("|---:|---|---|---:|---:|")
    for idx, row in enumerate(summary["top_pre_only_attempts"], start=1):
        probe = row.get("parser_probe") or {}
        elapsed = probe.get("elapsed_sec")
        lines.append(
            f"| {idx} | {row.get('study_id') or ''} | {row.get('pmcid') or ''} | "
            f"{elapsed if elapsed is not None else ''} | {row.get('pdf_size_bytes') or ''} |"
        )
    lines.append("")

    args.output_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote JSON: {args.output_json}")
    print(f"Wrote MD: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
