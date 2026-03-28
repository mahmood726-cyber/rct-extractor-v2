#!/usr/bin/env python3
"""Build blinded multi-agent pre-adjudication queue from multiple extraction passes.

This script combines multiple extraction result JSONLs (same PDF corpus, different
agent settings) into:
- Auto-accepted rows (high-confidence agreement)
- Conflict queue (human review required)
- Optional adjudication template prefill with only auto-accepted rows populated
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


RATIO_TYPES = {"OR", "RR", "HR"}
DIFF_TYPES = {"MD", "SMD", "WMD"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_effect_type(value: object) -> Optional[str]:
    text = str(value or "").strip().upper()
    if not text:
        return None
    alias = {
        "RISK RATIO": "RR",
        "ODDS RATIO": "OR",
        "HAZARD RATIO": "HR",
        "MEAN DIFFERENCE": "MD",
        "STANDARDIZED MEAN DIFFERENCE": "SMD",
    }
    return alias.get(text, text)


def _effect_family(effect_type: Optional[str]) -> Optional[str]:
    if not effect_type:
        return None
    if effect_type in RATIO_TYPES:
        return "ratio"
    if effect_type in DIFF_TYPES:
        return "difference"
    return effect_type


def _normalize_relpath(value: object) -> str:
    return str(value or "").replace("\\", "/").strip()


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


def _load_latest_results_by_rel(path: Path) -> Dict[str, Dict]:
    latest: Dict[str, Dict] = {}
    for row in _load_jsonl(path):
        rel = _normalize_relpath(row.get("pdf_relpath"))
        if not rel:
            continue
        latest[rel] = row
    return latest


def _parse_pass_spec(spec: str) -> Tuple[str, Path]:
    token = str(spec or "").strip()
    if "=" not in token:
        raise ValueError(f"Invalid --pass-spec '{spec}'. Expected label=path.")
    label, raw_path = token.split("=", 1)
    label = label.strip()
    path = Path(raw_path.strip())
    if not label:
        raise ValueError(f"Invalid --pass-spec '{spec}': missing label.")
    if not path.exists():
        raise FileNotFoundError(f"Pass results file not found: {path}")
    return label, path


def _vote_from_result(result_row: Optional[Dict], label: str) -> Dict:
    status = str((result_row or {}).get("status") or "")
    best = (result_row or {}).get("best_match") if isinstance((result_row or {}).get("best_match"), dict) else {}
    effect_type = _normalize_effect_type(best.get("type"))
    effect_size = _to_float(best.get("effect_size"))
    ci_low = _to_float(best.get("ci_lower"))
    ci_high = _to_float(best.get("ci_upper"))
    confidence = _to_float(best.get("calibrated_confidence"))
    source_text = str(best.get("source_text") or "")
    source_len = len(source_text.strip())
    has_ci = ci_low is not None and ci_high is not None
    include_pred = status == "extracted" and effect_size is not None
    return {
        "agent": label,
        "status": status or "missing",
        "include_pred": bool(include_pred),
        "effect_type": effect_type,
        "effect_family": _effect_family(effect_type),
        "effect_size": effect_size,
        "ci_lower": ci_low,
        "ci_upper": ci_high,
        "has_ci": has_ci,
        "confidence": confidence,
        "source_text": source_text,
        "source_len": source_len,
        "page_number": _to_int(best.get("page_number")),
    }


def _rel_err(a: float, b: float, zero_abs_tolerance: float) -> float:
    if abs(b) < 1e-12:
        return abs(a - b) / max(zero_abs_tolerance, 1e-12)
    return abs(a - b) / abs(b)


def _pair_agreement(
    left: Dict,
    right: Dict,
    *,
    point_tol: float,
    ci_tol: float,
    zero_abs_tolerance: float,
) -> Optional[Dict]:
    if not bool(left.get("include_pred")) or not bool(right.get("include_pred")):
        return None
    if left.get("effect_size") is None or right.get("effect_size") is None:
        return None

    lf = left.get("effect_family")
    rf = right.get("effect_family")
    if lf is None or rf is None or lf != rf:
        return None

    point_rel = _rel_err(float(left["effect_size"]), float(right["effect_size"]), zero_abs_tolerance)
    if point_rel > point_tol:
        return None

    has_ci_l = bool(left.get("has_ci"))
    has_ci_r = bool(right.get("has_ci"))
    ci_rel = None
    if has_ci_l and has_ci_r:
        l_low = _to_float(left.get("ci_lower"))
        l_high = _to_float(left.get("ci_upper"))
        r_low = _to_float(right.get("ci_lower"))
        r_high = _to_float(right.get("ci_upper"))
        if None not in (l_low, l_high, r_low, r_high):
            ci_rel = max(
                _rel_err(float(l_low), float(r_low), zero_abs_tolerance),
                _rel_err(float(l_high), float(r_high), zero_abs_tolerance),
            )
            if ci_rel > ci_tol:
                return None

    confidence_values = [v for v in (_to_float(left.get("confidence")), _to_float(right.get("confidence"))) if v is not None]
    avg_conf = (sum(confidence_values) / len(confidence_values)) if confidence_values else None
    return {
        "agents": [left.get("agent"), right.get("agent")],
        "point_rel_error": point_rel,
        "ci_rel_error": ci_rel,
        "avg_confidence": avg_conf,
    }


def _consensus_from_votes(
    votes: List[Dict],
    *,
    point_tol: float,
    ci_tol: float,
    zero_abs_tolerance: float,
    weak_single_conf_max: float,
    weak_single_source_len_max: int,
    allow_majority_weak_exclude: bool,
) -> Dict:
    includes = [v for v in votes if bool(v.get("include_pred"))]
    excludes = [v for v in votes if not bool(v.get("include_pred"))]
    n_agents = len(votes)

    if len(includes) == 0:
        return {
            "decision": "auto_exclude",
            "reason": "unanimous_no_extraction",
            "review_required": False,
            "gold": {
                "included": False,
                "effect_type": None,
                "point_estimate": None,
                "ci_lower": None,
                "ci_upper": None,
                "p_value": None,
                "source_text": "",
                "page_number": None,
                "notes": "ensemble_auto_exclude_unanimous",
            },
            "agreement": {},
        }

    best_pair = None
    for i in range(len(includes)):
        for j in range(i + 1, len(includes)):
            pair = _pair_agreement(
                includes[i],
                includes[j],
                point_tol=point_tol,
                ci_tol=ci_tol,
                zero_abs_tolerance=zero_abs_tolerance,
            )
            if pair is None:
                continue
            score = (
                1 if pair.get("ci_rel_error") is not None else 0,
                -float(pair.get("point_rel_error") or 0.0),
                -float(pair.get("ci_rel_error") if pair.get("ci_rel_error") is not None else 999.0),
                float(pair.get("avg_confidence") if pair.get("avg_confidence") is not None else 0.0),
            )
            if best_pair is None or score > best_pair["score"]:
                best_pair = {"pair": pair, "score": score, "left": includes[i], "right": includes[j]}

    if best_pair is not None:
        left = best_pair["left"]
        right = best_pair["right"]
        left_effect = float(left["effect_size"])
        right_effect = float(right["effect_size"])
        gold_effect = (left_effect + right_effect) / 2.0

        left_ci_low = _to_float(left.get("ci_lower"))
        right_ci_low = _to_float(right.get("ci_lower"))
        left_ci_high = _to_float(left.get("ci_upper"))
        right_ci_high = _to_float(right.get("ci_upper"))
        gold_ci_low = (left_ci_low + right_ci_low) / 2.0 if None not in (left_ci_low, right_ci_low) else None
        gold_ci_high = (left_ci_high + right_ci_high) / 2.0 if None not in (left_ci_high, right_ci_high) else None

        src_vote = left if len(str(left.get("source_text") or "")) >= len(str(right.get("source_text") or "")) else right
        return {
            "decision": "auto_include",
            "reason": "multi_agent_pair_agreement",
            "review_required": False,
            "gold": {
                "included": True,
                "effect_type": left.get("effect_type") or right.get("effect_type"),
                "point_estimate": gold_effect,
                "ci_lower": gold_ci_low,
                "ci_upper": gold_ci_high,
                "p_value": None,
                "source_text": str(src_vote.get("source_text") or ""),
                "page_number": src_vote.get("page_number"),
                "notes": (
                    "ensemble_auto_include;"
                    f" agents={','.join(str(x) for x in best_pair['pair']['agents'])};"
                    f" point_rel={best_pair['pair']['point_rel_error']:.4f}"
                ),
            },
            "agreement": best_pair["pair"],
        }

    if allow_majority_weak_exclude and len(excludes) >= max(2, n_agents - 1) and len(includes) == 1:
        single = includes[0]
        conf = _to_float(single.get("confidence"))
        has_ci = bool(single.get("has_ci"))
        source_len = int(single.get("source_len") or 0)
        weak = (
            (conf is None or conf <= weak_single_conf_max)
            and (not has_ci)
            and source_len <= weak_single_source_len_max
        )
        if weak:
            return {
                "decision": "auto_exclude",
                "reason": "majority_no_extraction_single_weak_extract",
                "review_required": False,
                "gold": {
                    "included": False,
                    "effect_type": None,
                    "point_estimate": None,
                    "ci_lower": None,
                    "ci_upper": None,
                    "p_value": None,
                    "source_text": "",
                    "page_number": None,
                    "notes": "ensemble_auto_exclude_majority_weak_single",
                },
                "agreement": {
                    "single_extract_agent": single.get("agent"),
                    "single_extract_confidence": conf,
                    "single_extract_has_ci": has_ci,
                    "single_extract_source_len": source_len,
                },
            }

    return {
        "decision": "conflict",
        "reason": "multi_agent_disagreement",
        "review_required": True,
        "gold": {
            "included": None,
            "effect_type": None,
            "point_estimate": None,
            "ci_lower": None,
            "ci_upper": None,
            "p_value": None,
            "source_text": "",
            "page_number": None,
            "notes": "ensemble_conflict_requires_human",
        },
        "agreement": {},
    }


def _build_prefill_row(base_row: Dict, consensus: Dict) -> Dict:
    out = dict(base_row)
    out["gold"] = dict(consensus.get("gold") or {})
    notes = str(out.get("adjudication_notes") or "").strip()
    prefix = f"ensemble_pre_adjudication:{consensus.get('decision')}:{consensus.get('reason')}"
    out["adjudication_notes"] = f"{prefix}; {notes}" if notes else prefix
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=Path("data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225"),
    )
    parser.add_argument(
        "--pass-spec",
        action="append",
        required=True,
        help="Agent result mapping: label=path_to_results_jsonl. Provide at least 3.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--consensus-point-tol", type=float, default=0.10)
    parser.add_argument("--consensus-ci-tol", type=float, default=0.20)
    parser.add_argument("--zero-abs-tolerance", type=float, default=0.02)
    parser.add_argument("--allow-majority-weak-exclude", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--weak-single-conf-max", type=float, default=0.60)
    parser.add_argument("--weak-single-source-len-max", type=int, default=30)
    args = parser.parse_args()

    if len(args.pass_spec) < 3:
        raise ValueError("Provide at least three --pass-spec values.")
    if args.consensus_point_tol <= 0:
        raise ValueError("--consensus-point-tol must be > 0")
    if args.consensus_ci_tol <= 0:
        raise ValueError("--consensus-ci-tol must be > 0")
    if args.zero_abs_tolerance <= 0:
        raise ValueError("--zero-abs-tolerance must be > 0")

    benchmark_dir = args.benchmark_dir
    if not benchmark_dir.exists():
        raise FileNotFoundError(f"--benchmark-dir not found: {benchmark_dir}")

    cohort_path = benchmark_dir / "benchmark_cohort.jsonl"
    if not cohort_path.exists():
        cohort_path = benchmark_dir / "benchmark_subset.jsonl"
    adjudication_path = benchmark_dir / "adjudication_template.jsonl"
    if not cohort_path.exists():
        raise FileNotFoundError(f"Missing benchmark cohort file: {cohort_path}")
    if not adjudication_path.exists():
        raise FileNotFoundError(f"Missing adjudication template file: {adjudication_path}")

    pass_specs: List[Tuple[str, Path]] = [_parse_pass_spec(spec) for spec in args.pass_spec]
    pass_maps: Dict[str, Dict[str, Dict]] = {}
    for label, path in pass_specs:
        pass_maps[label] = _load_latest_results_by_rel(path)

    cohort_rows = _load_jsonl(cohort_path)
    adjudication_rows = _load_jsonl(adjudication_path)
    adjudication_by_id = {str(row.get("benchmark_id") or ""): row for row in adjudication_rows if row.get("benchmark_id")}

    output_dir = args.output_dir or (benchmark_dir / "ensemble_pre_adjudication")
    votes_path = output_dir / "ensemble_votes.jsonl"
    auto_path = output_dir / "auto_accept.jsonl"
    conflict_path = output_dir / "conflicts.jsonl"
    prefill_path = output_dir / "adjudication_template_ensemble_prefill.jsonl"
    summary_path = output_dir / "summary.json"
    summary_md_path = output_dir / "summary.md"

    votes_rows: List[Dict] = []
    auto_rows: List[Dict] = []
    conflict_rows: List[Dict] = []
    prefill_rows: List[Dict] = []
    decision_counts: Counter = Counter()
    reason_counts: Counter = Counter()
    pass_status_counts: Dict[str, Counter] = {label: Counter() for label, _ in pass_specs}

    for cohort_row in cohort_rows:
        bid = str(cohort_row.get("benchmark_id") or "")
        rel = _normalize_relpath(cohort_row.get("pdf_relpath"))
        if not bid or not rel:
            continue

        votes: List[Dict] = []
        for label, _ in pass_specs:
            result_row = pass_maps.get(label, {}).get(rel)
            vote = _vote_from_result(result_row, label=label)
            votes.append(vote)
            pass_status_counts[label][str(vote.get("status") or "missing")] += 1

        consensus = _consensus_from_votes(
            votes,
            point_tol=float(args.consensus_point_tol),
            ci_tol=float(args.consensus_ci_tol),
            zero_abs_tolerance=float(args.zero_abs_tolerance),
            weak_single_conf_max=float(args.weak_single_conf_max),
            weak_single_source_len_max=int(args.weak_single_source_len_max),
            allow_majority_weak_exclude=bool(args.allow_majority_weak_exclude),
        )
        decision = str(consensus.get("decision") or "")
        reason = str(consensus.get("reason") or "")
        decision_counts[decision] += 1
        reason_counts[reason] += 1

        row_payload = {
            "benchmark_id": bid,
            "study_id": cohort_row.get("study_id"),
            "pmid": cohort_row.get("pmid"),
            "pmcid": cohort_row.get("pmcid"),
            "pdf_relpath": rel,
            "decision": decision,
            "reason": reason,
            "review_required": bool(consensus.get("review_required")),
            "votes": votes,
            "consensus_gold": consensus.get("gold"),
            "agreement": consensus.get("agreement") or {},
        }
        votes_rows.append(row_payload)

        base_adj = adjudication_by_id.get(bid) or {
            "benchmark_id": bid,
            "study_id": cohort_row.get("study_id"),
            "pdf_relpath": rel,
            "pmcid": cohort_row.get("pmcid"),
            "pmid": cohort_row.get("pmid"),
            "gold": {
                "included": None,
                "effect_type": None,
                "point_estimate": None,
                "ci_lower": None,
                "ci_upper": None,
                "p_value": None,
                "source_text": "",
                "page_number": None,
                "notes": "",
            },
            "adjudication_notes": "",
        }
        prefill_row = _build_prefill_row(base_adj, consensus)
        if decision == "conflict":
            # Keep unresolved rows null in the prefilled adjudication file.
            prefill_row["gold"] = {
                "included": None,
                "effect_type": None,
                "point_estimate": None,
                "ci_lower": None,
                "ci_upper": None,
                "p_value": None,
                "source_text": "",
                "page_number": None,
                "notes": "ensemble_conflict_requires_human",
            }
            conflict_rows.append(row_payload)
        else:
            auto_rows.append(row_payload)
        prefill_rows.append(prefill_row)

    votes_rows.sort(key=lambda row: str(row.get("benchmark_id") or ""))
    auto_rows.sort(key=lambda row: str(row.get("benchmark_id") or ""))
    conflict_rows.sort(key=lambda row: str(row.get("benchmark_id") or ""))
    prefill_rows.sort(key=lambda row: str(row.get("benchmark_id") or ""))

    _write_jsonl(votes_path, votes_rows)
    _write_jsonl(auto_path, auto_rows)
    _write_jsonl(conflict_path, conflict_rows)
    _write_jsonl(prefill_path, prefill_rows)

    summary = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "benchmark_dir": str(benchmark_dir).replace("\\", "/"),
            "cohort_jsonl": str(cohort_path).replace("\\", "/"),
            "adjudication_template_jsonl": str(adjudication_path).replace("\\", "/"),
            "pass_specs": [{"label": label, "results_jsonl": str(path).replace("\\", "/")} for label, path in pass_specs],
            "consensus_point_tol": float(args.consensus_point_tol),
            "consensus_ci_tol": float(args.consensus_ci_tol),
            "zero_abs_tolerance": float(args.zero_abs_tolerance),
            "allow_majority_weak_exclude": bool(args.allow_majority_weak_exclude),
            "weak_single_conf_max": float(args.weak_single_conf_max),
            "weak_single_source_len_max": int(args.weak_single_source_len_max),
        },
        "counts": {
            "rows_total": len(votes_rows),
            "auto_accept_total": len(auto_rows),
            "conflict_total": len(conflict_rows),
            "decision_counts": dict(sorted(decision_counts.items())),
            "reason_counts": dict(sorted(reason_counts.items())),
            "pass_status_counts": {
                label: dict(sorted(counter.items()))
                for label, counter in pass_status_counts.items()
            },
        },
        "paths": {
            "votes_jsonl": str(votes_path).replace("\\", "/"),
            "auto_accept_jsonl": str(auto_path).replace("\\", "/"),
            "conflicts_jsonl": str(conflict_path).replace("\\", "/"),
            "adjudication_prefill_jsonl": str(prefill_path).replace("\\", "/"),
            "summary_json": str(summary_path).replace("\\", "/"),
            "summary_md": str(summary_md_path).replace("\\", "/"),
        },
    }
    _write_json(summary_path, summary)

    lines: List[str] = []
    lines.append("# Blinded Ensemble Pre-Adjudication Summary")
    lines.append("")
    lines.append(f"- Generated UTC: {summary.get('generated_at_utc')}")
    lines.append(f"- Rows total: {summary['counts']['rows_total']}")
    lines.append(f"- Auto-accepted: {summary['counts']['auto_accept_total']}")
    lines.append(f"- Conflicts: {summary['counts']['conflict_total']}")
    lines.append("")
    lines.append("## Decision Counts")
    lines.append("")
    for key, value in sorted((summary["counts"].get("decision_counts") or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Agent Status Counts")
    lines.append("")
    for label, counts in sorted((summary["counts"].get("pass_status_counts") or {}).items()):
        lines.append(f"- {label}: {counts}")
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append(f"- Votes JSONL: `{summary['paths']['votes_jsonl']}`")
    lines.append(f"- Auto-accept JSONL: `{summary['paths']['auto_accept_jsonl']}`")
    lines.append(f"- Conflicts JSONL: `{summary['paths']['conflicts_jsonl']}`")
    lines.append(f"- Adjudication prefill JSONL: `{summary['paths']['adjudication_prefill_jsonl']}`")
    summary_md_path.parent.mkdir(parents=True, exist_ok=True)
    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {votes_path}")
    print(f"Wrote: {auto_path}")
    print(f"Wrote: {conflict_path}")
    print(f"Wrote: {prefill_path}")
    print(f"Wrote: {summary_path}")
    print(f"Wrote: {summary_md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
