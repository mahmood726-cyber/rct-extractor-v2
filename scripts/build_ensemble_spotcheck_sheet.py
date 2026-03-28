#!/usr/bin/env python3
"""Build a compact manual spot-check packet from ensemble auto-accepted rows."""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_csv(path: Path, rows: Sequence[Dict]) -> None:
    fieldnames = [
        "spotcheck_rank",
        "spotcheck_bucket",
        "benchmark_id",
        "pmid",
        "pmcid",
        "study_id",
        "pdf_relpath",
        "pdf_abs_path",
        "consensus_included",
        "consensus_effect_type",
        "consensus_point_estimate",
        "consensus_ci_lower",
        "consensus_ci_upper",
        "consensus_page_number",
        "consensus_source_text",
        "ensemble_pair_agents",
        "ensemble_avg_confidence",
        "ensemble_point_rel_error",
        "ensemble_ci_rel_error",
        "agent_A_status",
        "agent_A_include_pred",
        "agent_A_effect_type",
        "agent_A_effect_size",
        "agent_A_ci_lower",
        "agent_A_ci_upper",
        "agent_A_confidence",
        "agent_B_status",
        "agent_B_include_pred",
        "agent_B_effect_type",
        "agent_B_effect_size",
        "agent_B_ci_lower",
        "agent_B_ci_upper",
        "agent_B_confidence",
        "agent_C_status",
        "agent_C_include_pred",
        "agent_C_effect_type",
        "agent_C_effect_size",
        "agent_C_ci_lower",
        "agent_C_ci_upper",
        "agent_C_confidence",
        "manual_check_included",
        "manual_check_effect_type",
        "manual_check_point_estimate",
        "manual_check_ci_lower",
        "manual_check_ci_upper",
        "manual_check_page_number",
        "manual_check_notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _vote_map(row: Dict) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for vote in row.get("votes") or []:
        if not isinstance(vote, dict):
            continue
        agent = str(vote.get("agent") or "").strip()
        if not agent:
            continue
        out[agent] = vote
    return out


def _enriched_row(auto_row: Dict, cohort_by_id: Dict[str, Dict], bucket: str) -> Dict:
    bid = str(auto_row.get("benchmark_id") or "")
    cohort = cohort_by_id.get(bid) or {}
    consensus = auto_row.get("consensus_gold") if isinstance(auto_row.get("consensus_gold"), dict) else {}
    agreement = auto_row.get("agreement") if isinstance(auto_row.get("agreement"), dict) else {}
    votes = _vote_map(auto_row)

    pair_agents = agreement.get("agents") if isinstance(agreement.get("agents"), list) else []
    pair_agents_str = ",".join(str(v) for v in pair_agents if str(v).strip())
    avg_conf = _to_float(agreement.get("avg_confidence"))
    point_rel = _to_float(agreement.get("point_rel_error"))
    ci_rel = _to_float(agreement.get("ci_rel_error"))

    row: Dict[str, object] = {
        "spotcheck_bucket": bucket,
        "benchmark_id": bid,
        "pmid": auto_row.get("pmid"),
        "pmcid": auto_row.get("pmcid"),
        "study_id": auto_row.get("study_id"),
        "pdf_relpath": auto_row.get("pdf_relpath"),
        "pdf_abs_path": cohort.get("pdf_abs_path"),
        "consensus_included": consensus.get("included"),
        "consensus_effect_type": consensus.get("effect_type"),
        "consensus_point_estimate": _to_float(consensus.get("point_estimate")),
        "consensus_ci_lower": _to_float(consensus.get("ci_lower")),
        "consensus_ci_upper": _to_float(consensus.get("ci_upper")),
        "consensus_page_number": consensus.get("page_number"),
        "consensus_source_text": str(consensus.get("source_text") or ""),
        "ensemble_pair_agents": pair_agents_str,
        "ensemble_avg_confidence": avg_conf,
        "ensemble_point_rel_error": point_rel,
        "ensemble_ci_rel_error": ci_rel,
        "manual_check_included": None,
        "manual_check_effect_type": None,
        "manual_check_point_estimate": None,
        "manual_check_ci_lower": None,
        "manual_check_ci_upper": None,
        "manual_check_page_number": None,
        "manual_check_notes": "",
    }

    for agent in ("A", "B", "C"):
        vote = votes.get(agent) or {}
        row[f"agent_{agent}_status"] = vote.get("status")
        row[f"agent_{agent}_include_pred"] = vote.get("include_pred")
        row[f"agent_{agent}_effect_type"] = vote.get("effect_type")
        row[f"agent_{agent}_effect_size"] = _to_float(vote.get("effect_size"))
        row[f"agent_{agent}_ci_lower"] = _to_float(vote.get("ci_lower"))
        row[f"agent_{agent}_ci_upper"] = _to_float(vote.get("ci_upper"))
        row[f"agent_{agent}_confidence"] = _to_float(vote.get("confidence"))
    return row


def _sample_bucket(rows: List[Dict], n: int, rng: random.Random) -> List[Dict]:
    if n <= 0 or not rows:
        return []
    if n >= len(rows):
        return list(rows)
    pool = list(rows)
    rng.shuffle(pool)
    return pool[:n]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=Path("data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225"),
    )
    parser.add_argument("--target-n", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260225)
    parser.add_argument("--bucket-excludes", type=int, default=3)
    parser.add_argument("--bucket-lowconf-includes", type=int, default=3)
    parser.add_argument("--bucket-highconf-includes", type=int, default=3)
    parser.add_argument("--lowconf-threshold", type=float, default=0.85)
    parser.add_argument("--highconf-threshold", type=float, default=0.98)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    if args.target_n <= 0:
        raise ValueError("--target-n must be > 0")
    if args.bucket_excludes < 0 or args.bucket_lowconf_includes < 0 or args.bucket_highconf_includes < 0:
        raise ValueError("Bucket sizes must be >= 0")
    if not (0 <= args.lowconf_threshold <= 1):
        raise ValueError("--lowconf-threshold must be in [0,1]")
    if not (0 <= args.highconf_threshold <= 1):
        raise ValueError("--highconf-threshold must be in [0,1]")

    benchmark_dir = args.benchmark_dir
    if not benchmark_dir.exists():
        raise FileNotFoundError(f"--benchmark-dir not found: {benchmark_dir}")

    ensemble_dir = benchmark_dir / "ensemble_pre_adjudication"
    auto_path = ensemble_dir / "auto_accept.jsonl"
    cohort_path = benchmark_dir / "benchmark_cohort.jsonl"
    if not auto_path.exists():
        raise FileNotFoundError(f"Missing file: {auto_path}")
    if not cohort_path.exists():
        raise FileNotFoundError(f"Missing file: {cohort_path}")

    out_dir = args.output_dir or (ensemble_dir / "spotcheck_packet")
    rows = _load_jsonl(auto_path)
    cohort_rows = _load_jsonl(cohort_path)
    cohort_by_id = {str(r.get("benchmark_id") or ""): r for r in cohort_rows if r.get("benchmark_id")}

    excludes: List[Dict] = []
    low_conf_inc: List[Dict] = []
    high_conf_inc: List[Dict] = []
    medium_inc: List[Dict] = []

    for row in rows:
        consensus = row.get("consensus_gold") if isinstance(row.get("consensus_gold"), dict) else {}
        included = consensus.get("included")
        conf = _to_float((row.get("agreement") or {}).get("avg_confidence"))
        if included is False:
            excludes.append(row)
            continue
        if included is not True:
            continue
        if conf is not None and conf <= float(args.lowconf_threshold):
            low_conf_inc.append(row)
        elif conf is not None and conf >= float(args.highconf_threshold):
            high_conf_inc.append(row)
        else:
            medium_inc.append(row)

    rng = random.Random(int(args.seed))
    chosen: List[Dict] = []
    chosen_ids = set()

    def _add(rows_in: List[Dict], bucket: str, n: int) -> None:
        for r in _sample_bucket(rows_in, n=n, rng=rng):
            bid = str(r.get("benchmark_id") or "")
            if not bid or bid in chosen_ids:
                continue
            chosen.append(_enriched_row(r, cohort_by_id=cohort_by_id, bucket=bucket))
            chosen_ids.add(bid)

    _add(excludes, "exclude", int(args.bucket_excludes))
    _add(low_conf_inc, "low_conf_include", int(args.bucket_lowconf_includes))
    _add(high_conf_inc, "high_conf_include", int(args.bucket_highconf_includes))

    remaining_slots = int(args.target_n) - len(chosen)
    if remaining_slots > 0:
        remainder_pool = [r for r in rows if str(r.get("benchmark_id") or "") not in chosen_ids]
        for r in _sample_bucket(remainder_pool, n=remaining_slots, rng=rng):
            bid = str(r.get("benchmark_id") or "")
            if not bid or bid in chosen_ids:
                continue
            chosen.append(_enriched_row(r, cohort_by_id=cohort_by_id, bucket="fill",))
            chosen_ids.add(bid)

    chosen.sort(
        key=lambda r: (
            {"exclude": 0, "low_conf_include": 1, "high_conf_include": 2, "fill": 3}.get(str(r.get("spotcheck_bucket") or ""), 4),
            str(r.get("benchmark_id") or ""),
        )
    )
    for idx, row in enumerate(chosen, start=1):
        row["spotcheck_rank"] = idx

    csv_path = out_dir / "spotcheck_sheet.csv"
    jsonl_path = out_dir / "spotcheck_sheet.jsonl"
    summary_path = out_dir / "spotcheck_summary.json"
    readme_path = out_dir / "README.md"

    _write_csv(csv_path, chosen)
    _write_jsonl(jsonl_path, chosen)

    bucket_counts: Dict[str, int] = {}
    for row in chosen:
        key = str(row.get("spotcheck_bucket") or "unknown")
        bucket_counts[key] = bucket_counts.get(key, 0) + 1

    summary = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "benchmark_dir": str(benchmark_dir).replace("\\", "/"),
            "ensemble_auto_accept_jsonl": str(auto_path).replace("\\", "/"),
            "target_n": int(args.target_n),
            "seed": int(args.seed),
            "bucket_excludes": int(args.bucket_excludes),
            "bucket_lowconf_includes": int(args.bucket_lowconf_includes),
            "bucket_highconf_includes": int(args.bucket_highconf_includes),
            "lowconf_threshold": float(args.lowconf_threshold),
            "highconf_threshold": float(args.highconf_threshold),
        },
        "counts": {
            "auto_accept_rows_available": len(rows),
            "sample_rows": len(chosen),
            "sample_bucket_counts": dict(sorted(bucket_counts.items())),
        },
        "paths": {
            "spotcheck_csv": str(csv_path).replace("\\", "/"),
            "spotcheck_jsonl": str(jsonl_path).replace("\\", "/"),
            "summary_json": str(summary_path).replace("\\", "/"),
        },
    }
    _write_json(summary_path, summary)

    lines: List[str] = []
    lines.append("# Ensemble Spot-Check Packet")
    lines.append("")
    lines.append(f"- Generated UTC: {summary['generated_at_utc']}")
    lines.append(f"- Rows sampled: {summary['counts']['sample_rows']}")
    lines.append(f"- Bucket counts: {summary['counts']['sample_bucket_counts']}")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append(f"- CSV sheet: `{summary['paths']['spotcheck_csv']}`")
    lines.append(f"- JSONL sheet: `{summary['paths']['spotcheck_jsonl']}`")
    lines.append(f"- Summary JSON: `{summary['paths']['summary_json']}`")
    lines.append("")
    lines.append("## Manual Check Guidance")
    lines.append("")
    lines.append("- Verify `consensus_included` against the PDF.")
    lines.append("- If included=true, verify effect type, point estimate, and CI.")
    lines.append("- Record corrections in the `manual_check_*` columns.")
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {jsonl_path}")
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {readme_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
