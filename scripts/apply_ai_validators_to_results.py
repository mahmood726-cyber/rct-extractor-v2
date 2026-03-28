#!/usr/bin/env python3
"""Apply AI-style validator gates to extraction results JSONL.

Validators:
1) doc_type: reject non-paper artifacts (media kit, permissions pages, admin docs)
2) rct_design: require RCT-results-like study design signals
3) effect_context: require plausible effect-context evidence for best match

When a row is gated out, status is converted to no_extraction and best/top
matches are cleared, while an audit block is preserved in-row.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover - optional import
    fitz = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.rct_classifier import RCTClassifier, StudyType


ALLOWED_EFFECT_TYPES = {"HR", "OR", "RR", "MD", "SMD", "WMD", "RD", "ARD"}

NON_PAPER_PATTERNS = [
    r"\bmedia\s+kit\b",
    r"\bauthor\s+permission\s+guidelines?\b",
    r"\bpermissions?\s*@",
    r"\bright[s]?link\b",
    r"\ball\s+rights\s+reserved\b",
    r"\bhowcanishareit\.com\b",
    r"\breferencement\s+des\s+publications\b",
    r"\bcomit[eé]\s+de\s+coordination\b",
    r"\bcopyright\s+[0-9]{4}\b",
]

ARTICLE_SECTION_PATTERNS = [
    r"\babstract\b",
    r"\bbackground\b",
    r"\bmethods?\b",
    r"\bresults?\b",
    r"\bconclusions?\b",
    r"\bintroduction\b",
]

TRIAL_SIGNAL_PATTERNS = [
    r"\brandomi[sz]ed\b",
    r"\brandomly\s+assigned\b",
    r"\bclinical\s+trial\b",
    r"\bplacebo\b",
    r"\bdouble[- ]blind\b",
    r"\btrial\s+registration\b",
    r"\bnct[0-9]{8}\b",
    r"\bprimary\s+(?:end\s*point|outcome)\b",
    r"\bhazard\s+ratio\b",
    r"\bodds\s+ratio\b",
    r"\brisk\s+ratio\b",
]

RESULTS_SIGNAL_PATTERNS = [
    r"\bresults?\b",
    r"\bprimary\s+(?:end\s*point|outcome)\b",
    r"\bhazard\s+ratio\b",
    r"\bodds\s+ratio\b",
    r"\brisk\s+ratio\b",
    r"\b95%?\s*(?:ci|confidence)\b",
    r"\bp\s*[<=>]\s*0\.",
]

NON_RCT_DESIGN_PATTERNS = [
    r"\bsystematic\s+review\b",
    r"\bmeta[- ]analysis\b",
    r"\bcohort\s+study\b",
    r"\bcase[- ]control\b",
    r"\bcross[- ]sectional\b",
    r"\bretrospective\b",
    r"\bregistry\s+(?:study|analysis|data)\b",
    r"\breal[- ]world\b",
    r"\bpropensity\s+score\b",
    r"\bmachine\s+learning\b",
    r"\bmachine\s+learning\s+to\s+predict\b",
    r"\bprognostic\b",
    r"\bobservational\b",
    r"\bincidence\s+and\s+risk\s+factors\b",
    r"\bmedicare\s+beneficiaries\b",
    r"\bhospitali[sz]ed\s+with\s+sepsis\b",
    r"\basymptomatic\s+subjects?\b",
]

STRONG_NON_RCT_PATTERNS = [
    r"\bincidence\s+and\s+risk\s+factors\b",
    r"\bmedicare\s+beneficiaries\b",
    r"\bhospitali[sz]ed\s+with\s+sepsis\b",
    r"\bmachine\s+learning\s+to\s+predict\b",
    r"\bprognostic\b",
    r"\basymptomatic\s+subjects?\b",
    r"\bcohort\s+study\b",
    r"\bcase[- ]control\b",
    r"\bcross[- ]sectional\b",
    r"\bretrospective\b",
    r"\bobservational\b",
]

HARD_NON_RCT_MARKERS = [
    r"\bincidence\s+and\s+risk\s+factors\b",
    r"\bmedicare\s+beneficiaries\b",
    r"\bhospitali[sz]ed\s+with\s+sepsis\b",
    r"\bmachine\s+learning\s+to\s+predict\b",
    r"\basymptomatic\s+subjects?\b",
]

PROTOCOL_ONLY_PATTERNS = [
    r"\bstudy\s+protocol\b",
    r"\btrial\s+protocol\b",
    r"\bprotocol\s+(?:for|of)\b",
    r"\bwill\s+be\s+randomi[sz]ed\b",
    r"\bplanned\s+enrollment\b",
]

SINGLE_ARM_PATTERNS = [
    r"\bsingle[- ]arm\b",
    r"\bnon[- ]randomi[sz]ed\b",
    r"\bnonrandomi[sz]ed\b",
    r"\bwithout\s+(?:a\s+)?control\s+group\b",
]

EFFECT_CONTEXT_PATTERNS = [
    r"\b95%?\s*(?:ci|confidence)\b",
    r"\bhazard\s+ratio\b",
    r"\bodds\s+ratio\b",
    r"\brisk\s+ratio\b",
    r"\bmean\s+difference\b",
    r"\bp\s*[<=>]\s*0\.",
    r"\bvs\.?\b",
    r"\bversus\b",
]

EVENT_COUNT_PATTERN = re.compile(r"\b\d+\s+of\s+\d+\b", flags=re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_latest_rows(path: Path) -> List[Dict]:
    latest: Dict[str, Dict] = {}
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            rel = str(row.get("pdf_relpath") or "").replace("\\", "/").strip()
            if not rel:
                continue
            latest[rel] = row
    return [latest[key] for key in sorted(latest.keys())]


def _write_jsonl(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_pdf_head_text(pdf_path: Path, *, max_pages: int, max_chars: int) -> str:
    if fitz is None:
        return ""
    try:
        doc = fitz.open(str(pdf_path))
    except Exception:
        return ""
    chunks: List[str] = []
    try:
        n = min(int(max_pages), int(doc.page_count))
        for idx in range(n):
            page = doc.load_page(idx)
            chunks.append(page.get_text("text"))
            if sum(len(c) for c in chunks) >= int(max_chars):
                break
    finally:
        doc.close()
    text = "\n".join(chunks)
    if len(text) > int(max_chars):
        text = text[: int(max_chars)]
    return text


def _count_pattern_hits(text: str, patterns: Sequence[str]) -> Tuple[int, List[str]]:
    hits: List[str] = []
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits.append(pat)
    return len(hits), hits


@dataclass
class ValidatorDecision:
    passed: bool
    score: float
    reason: str
    details: Dict


def _doc_type_validator(head_text: str) -> ValidatorDecision:
    text = head_text or ""
    nonpaper_count, nonpaper_hits = _count_pattern_hits(text, NON_PAPER_PATTERNS)
    section_count, section_hits = _count_pattern_hits(text, ARTICLE_SECTION_PATTERNS)
    trial_count, trial_hits = _count_pattern_hits(text, TRIAL_SIGNAL_PATTERNS)

    # Strong non-paper detection: non-paper signatures with weak scientific structure.
    fail = nonpaper_count >= 1 and section_count < 2 and trial_count < 2
    passed = not fail
    score = max(0.0, min(1.0, 0.65 + 0.07 * section_count + 0.05 * trial_count - 0.25 * nonpaper_count))
    reason = "ok" if passed else "non_paper_signatures_detected"
    return ValidatorDecision(
        passed=passed,
        score=score,
        reason=reason,
        details={
            "nonpaper_count": nonpaper_count,
            "nonpaper_hits": nonpaper_hits,
            "section_count": section_count,
            "section_hits": section_hits,
            "trial_signal_count": trial_count,
            "trial_signal_hits": trial_hits,
        },
    )


def _rct_design_validator(head_text: str, classifier: RCTClassifier, *, mode: str) -> ValidatorDecision:
    text = head_text or ""
    classification = classifier.classify(text)
    trial_count, trial_hits = _count_pattern_hits(text, TRIAL_SIGNAL_PATTERNS)
    section_count, _ = _count_pattern_hits(text, ARTICLE_SECTION_PATTERNS)
    results_count, results_hits = _count_pattern_hits(text, RESULTS_SIGNAL_PATTERNS)
    non_rct_count, non_rct_hits = _count_pattern_hits(text, NON_RCT_DESIGN_PATTERNS)
    strong_non_rct_count, strong_non_rct_hits = _count_pattern_hits(text, STRONG_NON_RCT_PATTERNS)
    hard_non_rct_marker_count, hard_non_rct_marker_hits = _count_pattern_hits(text, HARD_NON_RCT_MARKERS)
    protocol_count, protocol_hits = _count_pattern_hits(text, PROTOCOL_ONLY_PATTERNS)
    single_arm_count, single_arm_hits = _count_pattern_hits(text, SINGLE_ARM_PATTERNS)

    classifier_rct = (
        classification.study_type in {StudyType.RCT_RESULTS, StudyType.RCT_SECONDARY}
        and classification.has_results
    )
    if mode == "strict":
        explicit_observational = (
            (non_rct_count >= 2 and trial_count < 2)
            or (non_rct_count >= 1 and trial_count == 0 and results_count < 2)
        )
        explicit_protocol_only = protocol_count >= 2 and results_count < 2
    else:  # balanced
        weak_other_with_strong_non_rct = (
            strong_non_rct_count >= 3
            and trial_count <= 1
            and hard_non_rct_marker_count >= 1
            and classification.study_type == StudyType.OTHER
            and float(classification.confidence) <= 0.35
        )
        explicit_observational = (
            (strong_non_rct_count >= 2 and trial_count == 0)
            or (non_rct_count >= 4 and trial_count == 0 and results_count < 2)
            or weak_other_with_strong_non_rct
        )
        explicit_protocol_only = protocol_count >= 3 and results_count == 0 and trial_count == 0

    if mode == "strict":
        explicit_single_arm = single_arm_count >= 1
    else:
        # In balanced mode, "single-arm/nonrandomized" terms often appear in
        # background/discussion text. Treat them as hard exclusion only when
        # they co-occur with additional non-RCT evidence or weak trial signals.
        explicit_single_arm = (
            single_arm_count >= 1
            and (
                hard_non_rct_marker_count >= 1
                or strong_non_rct_count >= 2
                or trial_count == 0
                or results_count == 0
                or (
                    classification.study_type == StudyType.OTHER
                    and float(classification.confidence) <= 0.35
                    and trial_count < 3
                )
                or (
                    classification.study_type == StudyType.LETTER
                    and trial_count <= 2
                    and results_count <= 1
                )
            )
        )
    hard_non_rct = (
        explicit_observational
        or explicit_protocol_only
        or explicit_single_arm
    )
    strong_trial_signals = trial_count >= 2 and results_count >= 1
    passed = not hard_non_rct

    if hard_non_rct:
        if explicit_single_arm:
            reason = "explicit_single_arm_or_nonrandomized"
        elif explicit_protocol_only:
            reason = "explicit_protocol_no_results"
        else:
            reason = "explicit_non_rct_design"
    elif classifier_rct:
        reason = "ok_classifier"
    elif strong_trial_signals:
        reason = "ok_signal_override"
    else:
        reason = "weak_but_not_explicit_non_rct"

    score = max(0.0, min(1.0, float(classification.confidence)))
    return ValidatorDecision(
        passed=passed,
        score=score,
        reason=reason,
        details={
            "study_type": classification.study_type.value,
            "is_rct": bool(classification.is_rct),
            "has_results": bool(classification.has_results),
            "recommendation": classification.recommendation,
            "confidence": float(classification.confidence),
            "signals_found": list(classification.signals_found),
            "signals_against": list(classification.signals_against),
            "trial_signal_count": trial_count,
            "trial_signal_hits": trial_hits,
            "results_signal_count": results_count,
            "results_signal_hits": results_hits,
            "non_rct_count": non_rct_count,
            "non_rct_hits": non_rct_hits,
            "strong_non_rct_count": strong_non_rct_count,
            "strong_non_rct_hits": strong_non_rct_hits,
            "hard_non_rct_marker_count": hard_non_rct_marker_count,
            "hard_non_rct_marker_hits": hard_non_rct_marker_hits,
            "protocol_count": protocol_count,
            "protocol_hits": protocol_hits,
            "single_arm_count": single_arm_count,
            "single_arm_hits": single_arm_hits,
            "validator_mode": mode,
        },
    )


def _effect_context_validator(row: Dict) -> ValidatorDecision:
    best = row.get("best_match") if isinstance(row.get("best_match"), dict) else {}
    source = str(best.get("source_text") or "")
    source_lower = source.lower()
    effect_type = str(best.get("type") or "").upper().strip()
    confidence = _to_float(best.get("calibrated_confidence")) or 0.0
    has_ci = best.get("ci_lower") is not None and best.get("ci_upper") is not None

    effect_count, effect_hits = _count_pattern_hits(source, EFFECT_CONTEXT_PATTERNS)
    has_event_counts = bool(EVENT_COUNT_PATTERN.search(source))
    lax_source = source_lower.startswith("[lax]")
    computed_source = source_lower.startswith("[computed from raw data]")
    nonpaper_count, _ = _count_pattern_hits(source, NON_PAPER_PATTERNS)

    effect_type_ok = effect_type in ALLOWED_EFFECT_TYPES
    context_ok = has_ci or effect_count >= 1 or has_event_counts
    source_ok = len(source.strip()) >= 18 and not lax_source and nonpaper_count == 0

    # computed raw-data sources can still be valid if context exists
    if computed_source and has_event_counts:
        context_ok = True

    passed = effect_type_ok and context_ok and source_ok
    score = max(
        0.0,
        min(
            1.0,
            0.25
            + (0.35 if effect_type_ok else 0.0)
            + (0.25 if context_ok else 0.0)
            + (0.15 if source_ok else 0.0)
            + min(0.2, float(confidence) * 0.2),
        ),
    )
    reason = "ok" if passed else "weak_effect_context"
    return ValidatorDecision(
        passed=passed,
        score=score,
        reason=reason,
        details={
            "effect_type": effect_type or None,
            "confidence": confidence,
            "has_ci": bool(has_ci),
            "effect_pattern_count": effect_count,
            "effect_pattern_hits": effect_hits,
            "has_event_counts": has_event_counts,
            "source_len": len(source.strip()),
            "source_is_lax": lax_source,
            "source_is_computed": computed_source,
        },
    )


def _gate_row(row: Dict, classifier: RCTClassifier, args: argparse.Namespace) -> Tuple[Dict, Optional[str]]:
    out = dict(row)
    status = str(out.get("status") or "")
    best = out.get("best_match") if isinstance(out.get("best_match"), dict) else {}
    has_effect = best.get("effect_size") is not None
    if status != "extracted" or not has_effect:
        out["ai_validator"] = {
            "version": "v1",
            "applied": False,
            "reason": "status_not_extracted_or_missing_effect",
        }
        return out, None

    pdf_path = Path(str(out.get("pdf_path") or ""))
    head_text = _read_pdf_head_text(
        pdf_path,
        max_pages=int(args.max_pages),
        max_chars=int(args.max_chars),
    )

    doc_dec = _doc_type_validator(head_text)
    rct_dec = _rct_design_validator(head_text, classifier=classifier, mode=str(args.validator_mode))
    eff_dec = _effect_context_validator(out)

    best_conf = _to_float(best.get("calibrated_confidence")) or 0.0
    rct_details = rct_dec.details if isinstance(rct_dec.details, dict) else {}
    hard_non_rct_marker_count = int(rct_details.get("hard_non_rct_marker_count") or 0)
    single_arm_count = int(rct_details.get("single_arm_count") or 0)
    protocol_count = int(rct_details.get("protocol_count") or 0)
    rct_override = (
        not rct_dec.passed
        and best_conf >= float(args.rct_override_confidence)
        and eff_dec.passed
        and hard_non_rct_marker_count == 0
        and single_arm_count == 0
        and protocol_count == 0
    )

    passes = [doc_dec.passed, rct_dec.passed, eff_dec.passed]
    pass_count = sum(1 for item in passes if item)

    exclude_reasons: List[str] = []
    if not doc_dec.passed:
        exclude_reasons.append(f"doc_type:{doc_dec.reason}")
    if not rct_dec.passed and not rct_override:
        exclude_reasons.append(f"rct_design:{rct_dec.reason}")
    if not eff_dec.passed and best_conf < float(args.effect_override_confidence):
        exclude_reasons.append(f"effect_context:{eff_dec.reason}")

    # Exclude on any hard failure (doc or rct), or on effect-context failure
    # unless confidence override is very high.
    gate_exclude = len(exclude_reasons) > 0
    decision = "exclude" if gate_exclude else "pass"

    out["ai_validator"] = {
        "version": "v1",
        "applied": True,
        "decision": decision,
        "pass_count": pass_count,
        "validators": {
            "doc_type": {
                "passed": doc_dec.passed,
                "score": doc_dec.score,
                "reason": doc_dec.reason,
                "details": doc_dec.details,
            },
            "rct_design": {
                "passed": rct_dec.passed,
                "score": rct_dec.score,
                "reason": rct_dec.reason,
                "details": rct_dec.details,
            },
            "effect_context": {
                "passed": eff_dec.passed,
                "score": eff_dec.score,
                "reason": eff_dec.reason,
                "details": eff_dec.details,
            },
        },
        "exclude_reasons": exclude_reasons,
        "best_confidence": best_conf,
        "rct_override_applied": bool(rct_override),
        "rct_override_confidence": float(args.rct_override_confidence),
    }

    if gate_exclude:
        out["status"] = "no_extraction"
        out["n_extractions"] = 0
        out["best_match"] = None
        out["top_extractions"] = []
        meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
        warnings = meta.get("pipeline_warnings")
        if not isinstance(warnings, list):
            warnings = []
        warnings = list(warnings) + [f"AI validator gated extraction: {'; '.join(exclude_reasons)}"]
        meta["pipeline_warnings"] = warnings
        meta["validator_gated"] = True
        out["meta"] = meta
        return out, ",".join(exclude_reasons)

    return out, None


def _iter_rows(rows: Iterable[Dict], classifier: RCTClassifier, args: argparse.Namespace) -> Tuple[List[Dict], Dict]:
    out_rows: List[Dict] = []
    reason_counts: Counter = Counter()
    counts = Counter()
    for row in rows:
        counts["rows_total"] += 1
        if str(row.get("status") or "") == "extracted" and isinstance(row.get("best_match"), dict):
            if row["best_match"].get("effect_size") is not None:
                counts["rows_extracted_in"] += 1

        out, reason = _gate_row(row, classifier=classifier, args=args)
        out_rows.append(out)
        if reason:
            counts["rows_gated_excluded"] += 1
            for item in reason.split(","):
                reason_counts[item] += 1

        if str(out.get("status") or "") == "extracted" and isinstance(out.get("best_match"), dict):
            if out["best_match"].get("effect_size") is not None:
                counts["rows_extracted_out"] += 1

    payload = {
        "counts": dict(counts),
        "gated_reason_counts": dict(sorted(reason_counts.items())),
    }
    return out_rows, payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--max-chars", type=int, default=20000)
    parser.add_argument(
        "--validator-mode",
        type=str,
        choices=("strict", "balanced"),
        default="balanced",
        help="strict: maximal non-RCT filtering; balanced (default): recover recall while filtering explicit non-RCT cases.",
    )
    parser.add_argument(
        "--effect-override-confidence",
        type=float,
        default=0.97,
        help="Do not gate on effect_context failure if confidence >= this value.",
    )
    parser.add_argument(
        "--rct-override-confidence",
        type=float,
        default=0.99,
        help="Do not gate on rct_design failure when confidence >= this value and there are no hard non-RCT markers.",
    )
    args = parser.parse_args()

    if not args.input_jsonl.exists():
        raise FileNotFoundError(f"--input-jsonl not found: {args.input_jsonl}")
    if args.max_pages <= 0:
        raise ValueError("--max-pages must be > 0")
    if args.max_chars <= 0:
        raise ValueError("--max-chars must be > 0")
    if args.effect_override_confidence < 0 or args.effect_override_confidence > 1:
        raise ValueError("--effect-override-confidence must be in [0,1]")
    if args.rct_override_confidence < 0 or args.rct_override_confidence > 1:
        raise ValueError("--rct-override-confidence must be in [0,1]")

    rows = _load_latest_rows(args.input_jsonl)
    classifier = RCTClassifier()
    out_rows, stats = _iter_rows(rows, classifier=classifier, args=args)
    _write_jsonl(args.output_jsonl, out_rows)

    summary = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "input_jsonl": str(args.input_jsonl).replace("\\", "/"),
            "max_pages": int(args.max_pages),
            "max_chars": int(args.max_chars),
            "validator_mode": str(args.validator_mode),
            "effect_override_confidence": float(args.effect_override_confidence),
            "rct_override_confidence": float(args.rct_override_confidence),
        },
        "outputs": {
            "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
            "summary_json": str(args.summary_json).replace("\\", "/"),
        },
        **stats,
    }
    _write_json(args.summary_json, summary)

    print(f"Wrote: {args.output_jsonl}")
    print(f"Wrote: {args.summary_json}")
    print(
        "Rows extracted in/out: "
        f"{summary['counts'].get('rows_extracted_in', 0)} -> {summary['counts'].get('rows_extracted_out', 0)}; "
        f"gated={summary['counts'].get('rows_gated_excluded', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
