#!/usr/bin/env python3
"""Apply blinded dual-LLM validation on borderline extraction rows.

This script is designed to run *after* deterministic validators.
It sends only borderline rows to two independent judges (A/B), merges their
votes, and can optionally gate rejected rows to no_extraction.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover - optional import
    fitz = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


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
    return [latest[k] for k in sorted(latest.keys())]


def _write_jsonl(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_pdf_head_text(pdf_path: Path, *, max_pages: int, max_chars: int) -> str:
    if fitz is None:
        return ""
    try:
        doc = fitz.open(str(pdf_path))
    except Exception:
        return ""
    chunks: List[str] = []
    total_chars = 0
    try:
        n = min(int(max_pages), int(doc.page_count))
        for idx in range(n):
            page = doc.load_page(idx)
            text = page.get_text("text")
            chunks.append(text)
            total_chars += len(text)
            if total_chars >= int(max_chars):
                break
    finally:
        doc.close()
    text = "\n".join(chunks)
    if len(text) > int(max_chars):
        text = text[: int(max_chars)]
    return text


def _extract_json_object(text: str) -> Optional[Dict]:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Brace-scan fallback for mixed prose + JSON outputs.
    start = raw.find("{")
    if start < 0:
        return None
    depth = 0
    for idx in range(start, len(raw)):
        ch = raw[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                chunk = raw[start : idx + 1]
                try:
                    parsed = json.loads(chunk)
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def _build_prompt_payload(row: Dict, head_text: str) -> Dict:
    best = row.get("best_match") if isinstance(row.get("best_match"), dict) else {}
    return {
        "study_id": str(row.get("study_id") or ""),
        "pdf_relpath": str(row.get("pdf_relpath") or ""),
        "proposed_extraction": {
            "type": best.get("type"),
            "effect_size": _to_float(best.get("effect_size")),
            "ci_lower": _to_float(best.get("ci_lower")),
            "ci_upper": _to_float(best.get("ci_upper")),
            "p_value": _to_float(best.get("p_value")),
            "source_text": str(best.get("source_text") or ""),
            "page_number": best.get("page_number"),
        },
        "head_text": head_text,
    }


def _build_prompts(payload: Dict, judge_name: str) -> Tuple[str, str]:
    system_prompt = (
        "You are an independent blinded validator for cardiology RCT PDF extraction quality.\n"
        "You must return JSON only."
    )
    user_prompt = (
        f"Judge: {judge_name}\n"
        "Task: Validate whether the proposed extraction should be accepted.\n"
        "Return strictly JSON with keys:\n"
        "{\n"
        '  "doc_type": "paper|non_paper|unclear",\n'
        '  "rct_results": "yes|no|unclear",\n'
        '  "extraction_supported": "yes|no|unclear",\n'
        '  "final_decision": "accept|reject|review",\n'
        '  "confidence": <0..1>,\n'
        '  "reasons": ["short reason", "..."],\n'
        '  "evidence_spans": ["short quote", "..."]\n'
        "}\n\n"
        "Rules:\n"
        "- Reject if this is not a research paper.\n"
        "- Reject if this appears non-randomized/observational/protocol-only.\n"
        "- Reject if the proposed extraction is not directly supported.\n"
        "- Accept only when all three checks are positive.\n"
        "- Use review when uncertain.\n\n"
        f"INPUT JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    return system_prompt, user_prompt


def _call_openai(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency path
        raise RuntimeError("openai package is required for provider=openai") from exc

    client = OpenAI(api_key=api_key)
    # Prefer Responses API, fallback to Chat Completions for compatibility.
    try:
        response = client.responses.create(
            model=model,
            temperature=float(temperature),
            max_output_tokens=int(max_output_tokens),
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = getattr(response, "output_text", None)
        if isinstance(text, str) and text.strip():
            return text
    except Exception:
        pass

    response = client.chat.completions.create(
        model=model,
        temperature=float(temperature),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=int(max_output_tokens),
    )
    message = response.choices[0].message.content
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        parts = []
        for item in message:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return str(message or "")


def _call_anthropic(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
    try:
        import anthropic  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency path
        raise RuntimeError("anthropic package is required for provider=anthropic") from exc

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        temperature=float(temperature),
        max_tokens=int(max_output_tokens),
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    chunks = []
    for item in response.content:
        text = getattr(item, "text", None)
        if isinstance(text, str):
            chunks.append(text)
    return "\n".join(chunks)


def _count_pattern_hits(text: str, patterns: Sequence[str]) -> int:
    return sum(1 for p in patterns if re.search(p, text, flags=re.IGNORECASE))


def _mock_judge_output(payload: Dict, seed: int) -> Dict:
    text = str(payload.get("head_text") or "")
    src = str((payload.get("proposed_extraction") or {}).get("source_text") or "")
    non_paper_pats = [
        r"\bmedia\s+kit\b",
        r"\bauthor\s+permission\s+guidelines?\b",
        r"\bright[s]?link\b",
        r"\breferencement\s+des\s+publications\b",
    ]
    non_rct_pats = [
        r"\bobservational\b",
        r"\bcohort\b",
        r"\bretrospective\b",
        r"\bmachine\s+learning\s+to\s+predict\b",
        r"\bincidence\s+and\s+risk\s+factors\b",
    ]
    rct_pats = [
        r"\brandomi[sz]ed\b",
        r"\bplacebo\b",
        r"\bprimary\s+outcome\b",
        r"\bhazard\s+ratio\b",
        r"\bodds\s+ratio\b",
        r"\brisk\s+ratio\b",
    ]
    support_pats = [
        r"\bhazard\s+ratio\b",
        r"\bodds\s+ratio\b",
        r"\brisk\s+ratio\b",
        r"\b95%?\s*(?:ci|confidence)\b",
        r"\b\d+\s+of\s+\d+\b",
    ]

    np_hits = _count_pattern_hits(text, non_paper_pats)
    nr_hits = _count_pattern_hits(text, non_rct_pats)
    rct_hits = _count_pattern_hits(text, rct_pats)
    support_hits = _count_pattern_hits(src, support_pats)
    rng = random.Random(seed)
    jitter = rng.uniform(-0.05, 0.05)

    if np_hits >= 1:
        return {
            "doc_type": "non_paper",
            "rct_results": "no",
            "extraction_supported": "no",
            "final_decision": "reject",
            "confidence": _clamp(0.9 + jitter, 0.0, 1.0),
            "reasons": ["non-paper signatures"],
            "evidence_spans": [],
        }
    if nr_hits >= 2 and rct_hits == 0:
        return {
            "doc_type": "paper",
            "rct_results": "no",
            "extraction_supported": "no",
            "final_decision": "reject",
            "confidence": _clamp(0.85 + jitter, 0.0, 1.0),
            "reasons": ["observational/non-rct signals"],
            "evidence_spans": [],
        }
    if rct_hits >= 2 and support_hits >= 1:
        return {
            "doc_type": "paper",
            "rct_results": "yes",
            "extraction_supported": "yes",
            "final_decision": "accept",
            "confidence": _clamp(0.8 + jitter, 0.0, 1.0),
            "reasons": ["rct and effect support present"],
            "evidence_spans": [src[:160]],
        }
    return {
        "doc_type": "paper",
        "rct_results": "unclear",
        "extraction_supported": "unclear",
        "final_decision": "review",
        "confidence": _clamp(0.55 + jitter, 0.0, 1.0),
        "reasons": ["insufficient certainty"],
        "evidence_spans": [src[:160]] if src else [],
    }


def _rules_judge_output(payload: Dict, *, variant: str) -> Dict:
    text = str(payload.get("head_text") or "")
    src = str((payload.get("proposed_extraction") or {}).get("source_text") or "")
    non_paper_pats = [
        r"\bmedia\s+kit\b",
        r"\bauthor\s+permission\s+guidelines?\b",
        r"\bright[s]?link\b",
        r"\breferencement\s+des\s+publications\b",
        r"\bcomit[eé]\s+de\s+coordination\b",
    ]
    strong_non_rct_pats = [
        r"\bmachine\s+learning\s+to\s+predict\b",
        r"\bincidence\s+and\s+risk\s+factors\b",
        r"\bmedicare\s+beneficiaries\b",
        r"\bhospitali[sz]ed\s+with\s+sepsis\b",
        r"\basymptomatic\s+subjects?\b",
        r"\bobservational\b",
        r"\bretrospective\b",
        r"\bcohort\s+study\b",
    ]
    rct_pats = [
        r"\brandomi[sz]ed\b",
        r"\brandomly\s+assigned\b",
        r"\bplacebo\b",
        r"\bprimary\s+(?:end\s*point|outcome)\b",
        r"\bnct[0-9]{8}\b",
    ]
    results_pats = [
        r"\bhazard\s+ratio\b",
        r"\bodds\s+ratio\b",
        r"\brisk\s+ratio\b",
        r"\b95%?\s*(?:ci|confidence)\b",
        r"\bp\s*[<=>]\s*0\.",
        r"\b\d+\s+of\s+\d+\b",
    ]

    np_hits = _count_pattern_hits(text, non_paper_pats)
    non_rct_hits = _count_pattern_hits(text, strong_non_rct_pats)
    rct_hits = _count_pattern_hits(text, rct_pats)
    res_hits_head = _count_pattern_hits(text, results_pats)
    res_hits_src = _count_pattern_hits(src, results_pats)

    if np_hits >= 1:
        return {
            "doc_type": "non_paper",
            "rct_results": "no",
            "extraction_supported": "no",
            "final_decision": "reject",
            "confidence": 0.95,
            "reasons": ["non-paper signatures"],
            "evidence_spans": [],
        }

    # Variant A is precision-first, B is recall-first.
    if variant == "a":
        if non_rct_hits >= 2 and rct_hits <= 1:
            return {
                "doc_type": "paper",
                "rct_results": "no",
                "extraction_supported": "no",
                "final_decision": "reject",
                "confidence": 0.88,
                "reasons": ["strong non-rct design markers"],
                "evidence_spans": [],
            }
        if rct_hits >= 2 and (res_hits_head + res_hits_src) >= 2:
            return {
                "doc_type": "paper",
                "rct_results": "yes",
                "extraction_supported": "yes",
                "final_decision": "accept",
                "confidence": 0.80,
                "reasons": ["rct and effect-support present"],
                "evidence_spans": [src[:180]] if src else [],
            }
        return {
            "doc_type": "paper",
            "rct_results": "unclear",
            "extraction_supported": "unclear",
            "final_decision": "review",
            "confidence": 0.58,
            "reasons": ["insufficient evidence for precision gate"],
            "evidence_spans": [src[:180]] if src else [],
        }

    # variant b (recall-first)
    if non_rct_hits >= 3 and rct_hits == 0:
        return {
            "doc_type": "paper",
            "rct_results": "no",
            "extraction_supported": "no",
            "final_decision": "reject",
            "confidence": 0.84,
            "reasons": ["multiple strong non-rct markers"],
            "evidence_spans": [],
        }
    if rct_hits >= 1 and (res_hits_head + res_hits_src) >= 2:
        return {
            "doc_type": "paper",
            "rct_results": "yes",
            "extraction_supported": "yes" if res_hits_src >= 1 else "unclear",
            "final_decision": "accept" if res_hits_src >= 1 else "review",
            "confidence": 0.74 if res_hits_src >= 1 else 0.60,
            "reasons": ["likely rct with effect-context support"],
            "evidence_spans": [src[:180]] if src else [],
        }
    return {
        "doc_type": "paper",
        "rct_results": "unclear",
        "extraction_supported": "unclear",
        "final_decision": "review",
        "confidence": 0.56,
        "reasons": ["uncertain classification"],
        "evidence_spans": [src[:180]] if src else [],
    }


def _call_provider(
    *,
    provider: str,
    model: str,
    api_key_env: str,
    system_prompt: str,
    user_prompt: str,
    payload: Dict,
    temperature: float,
    max_output_tokens: int,
    mock_seed: int,
) -> Tuple[Optional[Dict], Optional[str], str]:
    provider = str(provider or "").strip().lower()
    if provider == "mock":
        parsed = _mock_judge_output(payload, seed=mock_seed)
        return parsed, None, json.dumps(parsed, ensure_ascii=False)
    if provider == "rules_a":
        parsed = _rules_judge_output(payload, variant="a")
        return parsed, None, json.dumps(parsed, ensure_ascii=False)
    if provider == "rules_b":
        parsed = _rules_judge_output(payload, variant="b")
        return parsed, None, json.dumps(parsed, ensure_ascii=False)

    api_key = os.environ.get(api_key_env, "").strip()
    if not api_key:
        return None, f"missing_api_key_env:{api_key_env}", ""

    try:
        if provider == "openai":
            raw = _call_openai(
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        elif provider == "anthropic":
            raw = _call_anthropic(
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        else:
            return None, f"unsupported_provider:{provider}", ""
    except Exception as exc:  # pragma: no cover - runtime external call
        return None, f"provider_call_failed:{type(exc).__name__}:{exc}", ""

    parsed = _extract_json_object(raw)
    if parsed is None:
        return None, "response_not_json_object", raw
    return parsed, None, raw


def _normalize_judge_output(raw: Dict) -> Dict:
    doc_type = str(raw.get("doc_type") or "").strip().lower()
    rct_results = str(raw.get("rct_results") or "").strip().lower()
    extraction_supported = str(raw.get("extraction_supported") or "").strip().lower()
    final_decision = str(raw.get("final_decision") or "").strip().lower()
    confidence = _to_float(raw.get("confidence"))
    reasons = raw.get("reasons")
    evidence = raw.get("evidence_spans")

    if doc_type not in {"paper", "non_paper", "unclear"}:
        doc_type = "unclear"
    if rct_results not in {"yes", "no", "unclear"}:
        rct_results = "unclear"
    if extraction_supported not in {"yes", "no", "unclear"}:
        extraction_supported = "unclear"
    if final_decision not in {"accept", "reject", "review"}:
        final_decision = "review"
    confidence = _clamp(float(confidence if confidence is not None else 0.5), 0.0, 1.0)

    normalized_reasons: List[str] = []
    if isinstance(reasons, list):
        for item in reasons:
            text = str(item or "").strip()
            if text:
                normalized_reasons.append(text[:200])
    elif isinstance(reasons, str) and reasons.strip():
        normalized_reasons = [reasons.strip()[:200]]

    normalized_evidence: List[str] = []
    if isinstance(evidence, list):
        for item in evidence:
            text = str(item or "").strip()
            if text:
                normalized_evidence.append(text[:220])
    elif isinstance(evidence, str) and evidence.strip():
        normalized_evidence = [evidence.strip()[:220]]

    # Deterministic vote mapping.
    if (
        final_decision == "reject"
        or doc_type == "non_paper"
        or rct_results == "no"
        or extraction_supported == "no"
    ):
        vote = "reject"
    elif (
        final_decision == "accept"
        and doc_type == "paper"
        and rct_results == "yes"
        and extraction_supported == "yes"
    ):
        vote = "accept"
    else:
        vote = "review"

    return {
        "doc_type": doc_type,
        "rct_results": rct_results,
        "extraction_supported": extraction_supported,
        "final_decision": final_decision,
        "confidence": confidence,
        "reasons": normalized_reasons,
        "evidence_spans": normalized_evidence,
        "vote": vote,
    }


def _merge_votes(
    a: Optional[Dict],
    b: Optional[Dict],
    *,
    min_agreement_confidence: float,
    conflict_policy: str,
) -> Dict:
    if a is None or b is None:
        return {
            "decision": "error_keep",
            "reason": "judge_error",
            "confidence": None,
            "reject_votes": 0,
            "accept_votes": 0,
            "review_votes": 0,
        }

    votes = [str(a.get("vote") or "review"), str(b.get("vote") or "review")]
    reject_votes = sum(1 for v in votes if v == "reject")
    accept_votes = sum(1 for v in votes if v == "accept")
    review_votes = sum(1 for v in votes if v == "review")
    avg_conf = (float(a.get("confidence") or 0.0) + float(b.get("confidence") or 0.0)) / 2.0

    if reject_votes == 2 and avg_conf >= float(min_agreement_confidence):
        return {
            "decision": "reject",
            "reason": "dual_reject",
            "confidence": avg_conf,
            "reject_votes": reject_votes,
            "accept_votes": accept_votes,
            "review_votes": review_votes,
        }
    if accept_votes == 2 and avg_conf >= float(min_agreement_confidence):
        return {
            "decision": "accept",
            "reason": "dual_accept",
            "confidence": avg_conf,
            "reject_votes": reject_votes,
            "accept_votes": accept_votes,
            "review_votes": review_votes,
        }
    if conflict_policy == "exclude" and reject_votes >= 1 and accept_votes == 0:
        return {
            "decision": "reject",
            "reason": "conflict_policy_exclude",
            "confidence": avg_conf,
            "reject_votes": reject_votes,
            "accept_votes": accept_votes,
            "review_votes": review_votes,
        }
    return {
        "decision": "conflict_keep",
        "reason": "disagreement_or_uncertain",
        "confidence": avg_conf,
        "reject_votes": reject_votes,
        "accept_votes": accept_votes,
        "review_votes": review_votes,
    }


def _mark_rejected(out: Dict, *, reason: str) -> None:
    out["status"] = "no_extraction"
    out["n_extractions"] = 0
    out["best_match"] = None
    out["top_extractions"] = []
    meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    warnings = meta.get("pipeline_warnings")
    if not isinstance(warnings, list):
        warnings = []
    warnings = list(warnings)
    warnings.append(f"Dual LLM validator gated extraction: {reason}")
    meta["pipeline_warnings"] = warnings
    meta["dual_llm_validator_gated"] = True
    out["meta"] = meta


def _candidate_reasons(row: Dict, args: argparse.Namespace) -> List[str]:
    reasons: List[str] = []
    status = str(row.get("status") or "")
    best = row.get("best_match") if isinstance(row.get("best_match"), dict) else {}
    effect = _to_float(best.get("effect_size"))
    if status != "extracted" or effect is None:
        return reasons

    best_conf = _to_float(best.get("calibrated_confidence"))
    if best_conf is not None and best_conf <= float(args.candidate_max_best_confidence):
        reasons.append("best_confidence_below_threshold")

    ai = row.get("ai_validator") if isinstance(row.get("ai_validator"), dict) else {}
    validators = ai.get("validators") if isinstance(ai.get("validators"), dict) else {}
    doc_v = validators.get("doc_type") if isinstance(validators.get("doc_type"), dict) else {}
    rct_v = validators.get("rct_design") if isinstance(validators.get("rct_design"), dict) else {}
    eff_v = validators.get("effect_context") if isinstance(validators.get("effect_context"), dict) else {}

    doc_score = _to_float(doc_v.get("score"))
    rct_score = _to_float(rct_v.get("score"))
    eff_score = _to_float(eff_v.get("score"))
    rct_reason = str(rct_v.get("reason") or "")

    if doc_score is not None and doc_score <= float(args.candidate_max_doc_score):
        reasons.append("doc_score_low")
    if rct_score is not None and rct_score <= float(args.candidate_max_rct_score):
        reasons.append("rct_score_low")
    if eff_score is not None and eff_score <= float(args.candidate_max_effect_score):
        reasons.append("effect_score_low")
    if rct_reason == "weak_but_not_explicit_non_rct":
        reasons.append("rct_reason_weak_non_explicit")

    if not ai:
        reasons.append("missing_ai_validator_block")
    return reasons


def _iter_rows(rows: Iterable[Dict], args: argparse.Namespace) -> Tuple[List[Dict], List[Dict], Dict]:
    out_rows: List[Dict] = []
    audit_rows: List[Dict] = []
    counts = Counter()
    counts["rows_total"] = 0

    processed_candidates = 0
    for row in rows:
        counts["rows_total"] += 1
        out = dict(row)
        cand_reasons = _candidate_reasons(out, args=args)
        is_candidate = len(cand_reasons) > 0
        if not is_candidate:
            out["dual_llm_validator"] = {
                "version": "v1",
                "applied": False,
                "reason": "not_borderline_candidate",
            }
            out_rows.append(out)
            continue

        if args.max_candidates is not None and processed_candidates >= int(args.max_candidates):
            out["dual_llm_validator"] = {
                "version": "v1",
                "applied": False,
                "reason": "candidate_limit_reached",
                "candidate_reasons": cand_reasons,
            }
            out_rows.append(out)
            counts["candidate_limit_skipped"] += 1
            continue

        processed_candidates += 1
        counts["candidates_total"] += 1
        pdf_path = Path(str(out.get("pdf_path") or ""))
        head_text = _read_pdf_head_text(
            pdf_path,
            max_pages=int(args.max_pages),
            max_chars=int(args.max_chars),
        )
        payload = _build_prompt_payload(out, head_text=head_text)

        sys_a, usr_a = _build_prompts(payload, judge_name="A")
        raw_a, err_a, raw_text_a = _call_provider(
            provider=str(args.provider_a),
            model=str(args.model_a),
            api_key_env=str(args.api_key_env_a),
            system_prompt=sys_a,
            user_prompt=usr_a,
            payload=payload,
            temperature=float(args.temperature),
            max_output_tokens=int(args.max_output_tokens),
            mock_seed=1000003 + processed_candidates,
        )
        if float(args.sleep_sec) > 0:
            time.sleep(float(args.sleep_sec))

        sys_b, usr_b = _build_prompts(payload, judge_name="B")
        raw_b, err_b, raw_text_b = _call_provider(
            provider=str(args.provider_b),
            model=str(args.model_b),
            api_key_env=str(args.api_key_env_b),
            system_prompt=sys_b,
            user_prompt=usr_b,
            payload=payload,
            temperature=float(args.temperature),
            max_output_tokens=int(args.max_output_tokens),
            mock_seed=2000003 + processed_candidates,
        )

        norm_a = _normalize_judge_output(raw_a) if raw_a is not None else None
        norm_b = _normalize_judge_output(raw_b) if raw_b is not None else None
        merged = _merge_votes(
            norm_a,
            norm_b,
            min_agreement_confidence=float(args.min_agreement_confidence),
            conflict_policy=str(args.conflict_policy),
        )

        decision = str(merged.get("decision") or "")
        counts[f"decision_{decision}"] += 1
        if err_a:
            counts["judge_a_errors"] += 1
        if err_b:
            counts["judge_b_errors"] += 1

        if decision == "reject":
            _mark_rejected(out, reason=str(merged.get("reason") or "dual_llm_reject"))
            counts["rows_gated_rejected"] += 1
        elif decision == "conflict_keep":
            meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
            warnings = meta.get("pipeline_warnings")
            if not isinstance(warnings, list):
                warnings = []
            warnings = list(warnings)
            warnings.append("Dual LLM validator conflict: manual review recommended")
            meta["pipeline_warnings"] = warnings
            meta["dual_llm_validator_conflict"] = True
            out["meta"] = meta

        out["dual_llm_validator"] = {
            "version": "v1",
            "applied": True,
            "candidate_reasons": cand_reasons,
            "decision": decision,
            "reason": merged.get("reason"),
            "decision_confidence": merged.get("confidence"),
            "providers": {
                "judge_a": {"provider": args.provider_a, "model": args.model_a},
                "judge_b": {"provider": args.provider_b, "model": args.model_b},
            },
            "judge_a": {
                "error": err_a,
                "normalized": norm_a,
                "raw_response_preview": (raw_text_a or "")[:500],
            },
            "judge_b": {
                "error": err_b,
                "normalized": norm_b,
                "raw_response_preview": (raw_text_b or "")[:500],
            },
            "merge": merged,
        }

        audit_rows.append(
            {
                "study_id": out.get("study_id"),
                "pdf_relpath": out.get("pdf_relpath"),
                "status_before": row.get("status"),
                "status_after": out.get("status"),
                "candidate_reasons": cand_reasons,
                "decision": decision,
                "reason": merged.get("reason"),
                "decision_confidence": merged.get("confidence"),
                "judge_a_error": err_a,
                "judge_b_error": err_b,
                "judge_a_vote": (norm_a or {}).get("vote"),
                "judge_b_vote": (norm_b or {}).get("vote"),
            }
        )
        out_rows.append(out)

    return out_rows, audit_rows, dict(counts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--audit-jsonl", type=Path, default=None)

    parser.add_argument(
        "--provider-a",
        type=str,
        choices=("mock", "rules_a", "rules_b", "openai", "anthropic"),
        default="rules_a",
    )
    parser.add_argument(
        "--provider-b",
        type=str,
        choices=("mock", "rules_a", "rules_b", "openai", "anthropic"),
        default="rules_b",
    )
    parser.add_argument("--model-a", type=str, default="gpt-4.1-mini")
    parser.add_argument("--model-b", type=str, default="claude-3-5-sonnet-latest")
    parser.add_argument("--api-key-env-a", type=str, default="OPENAI_API_KEY")
    parser.add_argument("--api-key-env-b", type=str, default="ANTHROPIC_API_KEY")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-output-tokens", type=int, default=700)

    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--max-chars", type=int, default=18000)
    parser.add_argument("--sleep-sec", type=float, default=0.0)

    parser.add_argument("--candidate-max-best-confidence", type=float, default=0.96)
    parser.add_argument("--candidate-max-doc-score", type=float, default=0.75)
    parser.add_argument("--candidate-max-rct-score", type=float, default=0.45)
    parser.add_argument("--candidate-max-effect-score", type=float, default=0.80)
    parser.add_argument("--max-candidates", type=int, default=None)

    parser.add_argument("--min-agreement-confidence", type=float, default=0.60)
    parser.add_argument("--conflict-policy", type=str, choices=("keep", "exclude"), default="keep")
    args = parser.parse_args()

    if not args.input_jsonl.exists():
        raise FileNotFoundError(f"--input-jsonl not found: {args.input_jsonl}")
    if args.max_pages <= 0:
        raise ValueError("--max-pages must be > 0")
    if args.max_chars <= 0:
        raise ValueError("--max-chars must be > 0")
    if args.max_output_tokens <= 50:
        raise ValueError("--max-output-tokens must be > 50")
    if args.max_candidates is not None and args.max_candidates <= 0:
        raise ValueError("--max-candidates must be > 0 when provided")
    for key in (
        "temperature",
        "candidate_max_best_confidence",
        "candidate_max_doc_score",
        "candidate_max_rct_score",
        "candidate_max_effect_score",
        "min_agreement_confidence",
    ):
        value = float(getattr(args, key))
        if value < 0.0 or value > 1.0:
            raise ValueError(f"--{key.replace('_', '-')} must be in [0,1]")

    rows = _load_latest_rows(args.input_jsonl)
    out_rows, audit_rows, counts = _iter_rows(rows, args=args)
    _write_jsonl(args.output_jsonl, out_rows)
    if args.audit_jsonl is not None:
        _write_jsonl(args.audit_jsonl, audit_rows)

    summary = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "input_jsonl": str(args.input_jsonl).replace("\\", "/"),
            "provider_a": args.provider_a,
            "provider_b": args.provider_b,
            "model_a": args.model_a,
            "model_b": args.model_b,
            "max_pages": int(args.max_pages),
            "max_chars": int(args.max_chars),
            "candidate_max_best_confidence": float(args.candidate_max_best_confidence),
            "candidate_max_doc_score": float(args.candidate_max_doc_score),
            "candidate_max_rct_score": float(args.candidate_max_rct_score),
            "candidate_max_effect_score": float(args.candidate_max_effect_score),
            "max_candidates": int(args.max_candidates) if args.max_candidates is not None else None,
            "min_agreement_confidence": float(args.min_agreement_confidence),
            "conflict_policy": str(args.conflict_policy),
            "temperature": float(args.temperature),
            "max_output_tokens": int(args.max_output_tokens),
        },
        "outputs": {
            "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
            "summary_json": str(args.summary_json).replace("\\", "/"),
            "audit_jsonl": str(args.audit_jsonl).replace("\\", "/") if args.audit_jsonl is not None else None,
        },
        "counts": counts,
    }
    _write_json(args.summary_json, summary)

    print(f"Wrote: {args.output_jsonl}")
    print(f"Wrote: {args.summary_json}")
    if args.audit_jsonl is not None:
        print(f"Wrote: {args.audit_jsonl}")
    print(
        "Dual LLM candidates processed: "
        f"{counts.get('candidates_total', 0)}; "
        f"gated={counts.get('rows_gated_rejected', 0)}; "
        f"errors(A/B)={counts.get('judge_a_errors', 0)}/{counts.get('judge_b_errors', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
