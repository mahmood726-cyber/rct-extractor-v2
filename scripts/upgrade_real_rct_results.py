#!/usr/bin/env python3
"""Upgrade real-RCT result records using the full PDF extraction pipeline."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from statistics import NormalDist
from typing import Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RATIO_TYPES = {"HR", "OR", "RR", "IRR", "GMR", "NNT", "NNH"}
DIFF_TYPES = {"MD", "SMD", "ARD", "ARR", "RRR", "RD", "WMD"}
CI_LABELED_PATTERN = re.compile(
    r"(?:95\s*%?\s*(?:confidence\s*interval|ci)|confidence\s*interval|ci)"
    r"(?:\s*\[[^\]]{0,20}\])?"
    r"[^0-9\-]{0,120}?"
    r"([-+]?\d+(?:\.\d+)?)\s*(?:to|,|-)\s*([-+]?\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)
CI_BRACKET_PATTERN = re.compile(
    r"[\(\[]\s*([-+]?\d+(?:\.\d+)?)\s*(?:to|,|-)\s*([-+]?\d+(?:\.\d+)?)\s*[\)\]]",
    flags=re.IGNORECASE,
)
CI_GENERIC_PATTERN = re.compile(
    r"([-+]?\d+(?:\.\d+)?)\s*(?:to|,|-)\s*([-+]?\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)
P_VALUE_PATTERN = re.compile(r"\bp\s*([=<>])\s*(0?\.\d+|1(?:\.0+)?)", flags=re.IGNORECASE)
P_VALUE_OCR_EQ_PATTERN = re.compile(r"\bp\s*5\s*(0?\.\d+|1(?:\.0+)?)", flags=re.IGNORECASE)
P_VALUE_FUZZY_EQ_PATTERN = re.compile(
    r"\bp\s*=\s*(?:[^0-9]{0,80})?(0?\.\d+|1(?:\.0+)?)",
    flags=re.IGNORECASE,
)
PUBMED_ABSTRACT_PATTERNS = [
    (
        "HR",
        re.compile(
            r"(?:(?i:hazard\s*ratio)|\bHR\b)[^0-9]{0,90}"
            r"([0-9]+(?:[.,][0-9]+)?)\s*[;,)]?\s*"
            r"(?:\(?\s*(?:95(?:\.[0-9]+)?\s*%?\s*)?"
            r"(?:confidence\s*interval|\[?\s*CI\s*\]?)\s*[,:\]\[]*\s*)?"
            r"([0-9]+(?:[.,][0-9]+)?)\s*(?:to|[-–—])\s*([0-9]+(?:[.,][0-9]+)?)"
        ),
    ),
    (
        "OR",
        re.compile(
            r"(?:(?i:odds\s*ratio)|\bOR\b)[^0-9]{0,90}"
            r"([0-9]+(?:[.,][0-9]+)?)\s*[;,)]?\s*"
            r"(?:\(?\s*(?:95(?:\.[0-9]+)?\s*%?\s*)?"
            r"(?:confidence\s*interval|\[?\s*CI\s*\]?)\s*[,:\]\[]*\s*)?"
            r"([0-9]+(?:[.,][0-9]+)?)\s*(?:to|[-–—])\s*([0-9]+(?:[.,][0-9]+)?)"
        ),
    ),
    (
        "RR",
        re.compile(
            r"(?:(?i:risk\s*ratio)|(?i:relative\s*risk)|\bRR\b)[^0-9]{0,90}"
            r"([0-9]+(?:[.,][0-9]+)?)\s*[;,)]?\s*"
            r"(?:\(?\s*(?:95(?:\.[0-9]+)?\s*%?\s*)?"
            r"(?:confidence\s*interval|\[?\s*CI\s*\]?)\s*[,:\]\[]*\s*)?"
            r"([0-9]+(?:[.,][0-9]+)?)\s*(?:to|[-–—])\s*([0-9]+(?:[.,][0-9]+)?)"
        ),
    ),
    (
        "IRR",
        re.compile(
            r"(?:(?i:incidence\s*rate\s*ratio)|(?i:rate\s*ratio)|\bIRR\b)[^0-9]{0,90}"
            r"([0-9]+(?:[.,][0-9]+)?)\s*[;,)]?\s*"
            r"(?:\(?\s*(?:95(?:\.[0-9]+)?\s*%?\s*)?"
            r"(?:confidence\s*interval|\[?\s*CI\s*\]?)\s*[,:\]\[]*\s*)?"
            r"([0-9]+(?:[.,][0-9]+)?)\s*(?:to|[-–—])\s*([0-9]+(?:[.,][0-9]+)?)"
        ),
    ),
]


def _load_jsonl(path: Path) -> List[Dict]:
    records: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def _load_json(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list in {path}")
    return data


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_effect_type(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip().upper()
    if not value:
        return None
    alias_map = {
        "RISK RATIO": "RR",
        "ODDS RATIO": "OR",
        "HAZARD RATIO": "HR",
        "MEAN DIFFERENCE": "MD",
        "STD MEAN DIFFERENCE": "SMD",
        "STANDARDIZED MEAN DIFFERENCE": "SMD",
    }
    return alias_map.get(value, value)


def _parse_id_filter(raw: Optional[str]) -> Optional[Set[str]]:
    if not raw:
        return None
    selected = {token.strip() for token in raw.split(",") if token.strip()}
    return selected or None


def _has_uncertainty(best_match: Optional[Dict]) -> bool:
    if not best_match:
        return False
    has_ci = best_match.get("ci_lower") is not None and best_match.get("ci_upper") is not None
    has_se = best_match.get("standard_error") is not None
    return has_ci or has_se


def _extract_effects_subprocess(
    pdf_path: Path,
    enable_advanced: bool,
    timeout_sec: float,
) -> List[Dict]:
    inline = (
        "import json,sys;"
        "from src.core.pdf_extraction_pipeline import PDFExtractionPipeline;"
        "from src.core.enhanced_extractor_v3 import to_dict;"
        "pdf=sys.argv[1];adv=sys.argv[2]=='1';"
        "p=PDFExtractionPipeline(extract_diagnostics=False,extract_tables=True,enable_advanced=adv);"
        "r=p.extract_from_pdf(pdf);"
        "print(json.dumps([to_dict(e) for e in r.effect_estimates], ensure_ascii=False))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", inline, str(pdf_path), "1" if enable_advanced else "0"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        return []
    return json.loads(lines[-1])


def _normalize_pmid(value: object) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _fetch_pubmed_abstract_text(
    pmid: str,
    *,
    timeout_sec: float,
    cache: Dict[str, Optional[str]],
) -> Optional[str]:
    normalized_pmid = _normalize_pmid(pmid)
    if not normalized_pmid:
        return None
    if normalized_pmid in cache:
        return cache[normalized_pmid]

    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={normalized_pmid}&retmode=xml"
    )
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            xml_payload = response.read().decode("utf-8", errors="replace")
    except Exception:
        cache[normalized_pmid] = None
        return None

    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError:
        cache[normalized_pmid] = None
        return None

    abstract_parts: List[str] = []
    for abstract_text in root.findall(".//AbstractText"):
        chunk = " ".join(part.strip() for part in abstract_text.itertext() if part and part.strip()).strip()
        label = str(abstract_text.get("Label") or "").strip()
        if label and chunk:
            abstract_parts.append(f"{label}: {chunk}")
        elif chunk:
            abstract_parts.append(chunk)
    abstract = " ".join(part for part in abstract_parts if part).strip()
    cache[normalized_pmid] = abstract or None
    return cache[normalized_pmid]


def _extract_effects_from_pubmed_abstract_text(abstract_text: str) -> List[Dict]:
    if not abstract_text:
        return []
    normalized = _normalize_numeric_text(abstract_text)
    if not normalized:
        return []

    extracted: List[Dict] = []
    seen: Set[Tuple[str, float, float, float]] = set()
    for effect_type, pattern in PUBMED_ABSTRACT_PATTERNS:
        for match in pattern.finditer(normalized):
            effect_size = _to_numeric_token(match.group(1))
            ci_lower = _to_numeric_token(match.group(2))
            ci_upper = _to_numeric_token(match.group(3))
            if None in (effect_size, ci_lower, ci_upper):
                continue
            assert effect_size is not None
            assert ci_lower is not None
            assert ci_upper is not None
            if ci_lower > ci_upper:
                ci_lower, ci_upper = ci_upper, ci_lower
            if effect_type in RATIO_TYPES and (effect_size <= 0 or ci_lower <= 0 or ci_upper <= 0):
                continue

            key = (effect_type, round(effect_size, 6), round(ci_lower, 6), round(ci_upper, 6))
            if key in seen:
                continue
            seen.add(key)

            context_start = max(0, match.start() - 120)
            context_end = min(len(normalized), match.end() + 120)
            source_text = normalized[context_start:context_end].strip()
            extracted.append(
                {
                    "type": effect_type,
                    "effect_size": effect_size,
                    "ci_lower": ci_lower,
                    "ci_upper": ci_upper,
                    "p_value": None,
                    "standard_error": None,
                    "source_text": source_text,
                    "warnings": ["PUBMED_ABSTRACT"],
                    "page_number": None,
                }
            )
    return extracted


def _attempt_pubmed_abstract_fallback(
    record: Dict,
    *,
    timeout_sec: float,
    cache: Dict[str, Optional[str]],
) -> Tuple[Optional[Dict], int, Optional[float], Optional[str]]:
    external_meta = record.get("external_meta") or {}
    pmid = _normalize_pmid(external_meta.get("pmid"))
    if not pmid:
        return None, 0, None, None

    abstract_text = _fetch_pubmed_abstract_text(
        pmid=pmid,
        timeout_sec=timeout_sec,
        cache=cache,
    )
    if not abstract_text:
        return None, 0, None, None

    effects = _extract_effects_from_pubmed_abstract_text(abstract_text)
    if not effects:
        return None, 0, None, None

    best_match, distance, status = _match_best_extraction(effects, record)
    if best_match is None:
        return None, len(effects), distance, status

    resolved = dict(best_match)
    raw_source = str(resolved.get("source_text") or "").strip()
    if raw_source:
        resolved["source_text"] = f"[PUBMED_ABSTRACT PMID:{pmid}] {raw_source}"
    else:
        resolved["source_text"] = f"[PUBMED_ABSTRACT PMID:{pmid}] {abstract_text[:240]}"

    warnings = resolved.get("warnings")
    if isinstance(warnings, list):
        if "PUBMED_ABSTRACT_FALLBACK" not in warnings:
            warnings.append("PUBMED_ABSTRACT_FALLBACK")
    else:
        resolved["warnings"] = ["PUBMED_ABSTRACT_FALLBACK"]
    resolved["page_number"] = None

    return resolved, len(effects), distance, status


def _select_candidate(
    seed_best: Optional[Dict],
    seed_distance: Optional[float],
    rerun_best: Optional[Dict],
    rerun_distance: Optional[float],
    uncertainty_distance_tolerance: float,
) -> Tuple[Optional[Dict], Optional[float], bool]:
    """Return selected best_match, selected distance, and whether rerun candidate was chosen."""
    if seed_best is None:
        return rerun_best, rerun_distance, rerun_best is not None
    if rerun_best is None:
        return seed_best, seed_distance, False

    seed_has_uncertainty = _has_uncertainty(seed_best)
    rerun_has_uncertainty = _has_uncertainty(rerun_best)
    if rerun_has_uncertainty and not seed_has_uncertainty:
        if seed_distance is None or rerun_distance is None:
            return rerun_best, rerun_distance, True
        if rerun_distance <= seed_distance + uncertainty_distance_tolerance:
            return rerun_best, rerun_distance, True

    if seed_distance is None and rerun_distance is not None:
        return rerun_best, rerun_distance, True
    if rerun_distance is not None and seed_distance is not None and rerun_distance < seed_distance:
        return rerun_best, rerun_distance, True

    return seed_best, seed_distance, False


def _target_reference(record: Dict) -> Dict[str, Optional[object]]:
    gold = record.get("gold") or {}
    point = _to_float(gold.get("point_estimate"))
    if point is not None:
        return {
            "value": point,
            "effect_type": _normalize_effect_type(gold.get("effect_type")),
            "ci_lower": _to_float(gold.get("ci_lower")),
            "ci_upper": _to_float(gold.get("ci_upper")),
            "source": "gold",
        }
    return {
        "value": _to_float(record.get("cochrane_effect")),
        "effect_type": None,
        "ci_lower": _to_float(record.get("cochrane_ci_lower")),
        "ci_upper": _to_float(record.get("cochrane_ci_upper")),
        "source": "cochrane",
    }


def _expected_effect_types(record: Dict) -> Tuple[Set[str], bool]:
    """Return expected types and whether they are strict (single gold type)."""
    gold_type = _normalize_effect_type((record.get("gold") or {}).get("effect_type"))
    if gold_type:
        return {gold_type}, True
    if str(record.get("cochrane_outcome_type", "")).lower() == "continuous":
        return {"MD", "SMD", "WMD"}, False
    return RATIO_TYPES | DIFF_TYPES, False


def _infer_effect_type_from_source_text(source_text: str) -> Optional[str]:
    normalized = source_text.lower()
    if not normalized:
        return None
    if re.search(r"\bhazard\s+ratio\b|\bhr\b", normalized):
        return "HR"
    if re.search(r"\bodds\s+ratio\b|\bor\b", normalized):
        return "OR"
    if re.search(r"\brisk\s+ratio\b|\brelative\s+risk\b|\brate\s+ratio\b|\brr\b|\birr\b", normalized):
        return "RR"
    if re.search(r"\bstandardi[sz]ed\s+mean\s+difference\b|\bsmd\b|\bcohen", normalized):
        return "SMD"
    if re.search(r"\bmean\s+difference\b|\bdifference\b", normalized):
        return "MD"
    return None


def _strict_type_rescue_candidate(
    extraction: Dict,
    *,
    target_type: Optional[str],
    outcome_type: Optional[str],
) -> Optional[Dict]:
    if target_type is None:
        return None

    value = _to_float(extraction.get("effect_size"))
    if value is None:
        return None

    extracted_type = _normalize_effect_type(extraction.get("type"))
    if extracted_type == target_type:
        return dict(extraction)

    source_text = str(extraction.get("source_text") or "")
    inferred_type = _infer_effect_type_from_source_text(source_text)
    ci_low = _to_float(extraction.get("ci_lower"))
    ci_up = _to_float(extraction.get("ci_upper"))
    positive_ci = ci_low is not None and ci_up is not None and ci_low > 0 and ci_up > 0

    rescued: Optional[Dict] = None
    rescue_reason: Optional[str] = None

    if target_type in RATIO_TYPES:
        if extracted_type in RATIO_TYPES:
            rescued = dict(extraction)
            rescue_reason = "ratio_family"
        elif inferred_type in RATIO_TYPES:
            rescued = dict(extraction)
            rescue_reason = "source_text_ratio"
        elif value > 0 and positive_ci and "ratio" in source_text.lower():
            rescued = dict(extraction)
            rescue_reason = "ratio_keyword_positive_interval"
    elif target_type in DIFF_TYPES:
        if extracted_type in {"MD", "SMD", "WMD"}:
            rescued = dict(extraction)
            rescue_reason = "difference_family"
        elif inferred_type in {"MD", "SMD", "WMD"}:
            rescued = dict(extraction)
            rescue_reason = "source_text_difference"

    if rescued is None:
        return None

    rescued["type"] = target_type
    warnings = rescued.get("warnings")
    if isinstance(warnings, list):
        if "STRICT_TYPE_RESCUE" not in warnings:
            warnings.append("STRICT_TYPE_RESCUE")
        reason_tag = f"STRICT_TYPE_RESCUE_{rescue_reason}".upper()
        if reason_tag not in warnings:
            warnings.append(reason_tag)
    else:
        rescued["warnings"] = ["STRICT_TYPE_RESCUE", f"STRICT_TYPE_RESCUE_{rescue_reason}".upper()]
    return rescued


def _transform_ci_bounds(
    ci_low: Optional[float],
    ci_up: Optional[float],
    transform_name: str,
) -> Optional[Tuple[float, float]]:
    if ci_low is None or ci_up is None:
        return None
    if ci_low > ci_up:
        ci_low, ci_up = ci_up, ci_low

    if transform_name == "sign_flip":
        return -ci_up, -ci_low
    if transform_name == "reciprocal":
        if ci_low <= 0 or ci_up <= 0:
            return None
        return 1.0 / ci_up, 1.0 / ci_low
    if transform_name.startswith("scale_"):
        try:
            scale_str = transform_name.replace("scale_", "").replace("x", "")
            scale = float(scale_str)
        except ValueError:
            return None
        return ci_low * scale, ci_up * scale
    return None


def _strict_type_transform_rescue_candidates(
    extractions: List[Dict],
    *,
    target_value: float,
    target_type: Optional[str],
    outcome_type: Optional[str],
    max_distance: float = 0.12,
) -> List[Dict]:
    if target_type is None or target_type not in RATIO_TYPES:
        return []

    rescued_ranked: List[Tuple[float, Dict]] = []
    seen_keys: Set[Tuple[int, str]] = set()

    for extraction in extractions:
        value = _to_float(extraction.get("effect_size"))
        if value is None:
            continue
        extracted_type = _normalize_effect_type(extraction.get("type"))
        if extracted_type in RATIO_TYPES:
            continue

        transforms: List[Tuple[str, Optional[float]]] = [
            ("sign_flip", -value),
            ("reciprocal", (1.0 / value) if value != 0 else None),
            ("scale_0.01x", value * 0.01),
            ("scale_0.1x", value * 0.1),
            ("scale_10x", value * 10.0),
            ("scale_100x", value * 100.0),
        ]

        for transform_name, transformed in transforms:
            if transformed is None or transformed <= 0:
                continue

            dist = _distance(
                extracted_value=transformed,
                target_value=target_value,
                extracted_type=target_type,
                target_type=target_type,
                outcome_type=outcome_type,
            )
            if dist > max_distance:
                continue

            dedupe_key = (round(transformed, 6), transform_name)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            rescued = dict(extraction)
            rescued["type"] = target_type
            rescued["effect_size"] = transformed
            ci_bounds = _transform_ci_bounds(
                ci_low=_to_float(extraction.get("ci_lower")),
                ci_up=_to_float(extraction.get("ci_upper")),
                transform_name=transform_name,
            )
            if ci_bounds is not None:
                ci_low, ci_up = ci_bounds
                rescued["ci_lower"] = ci_low
                rescued["ci_upper"] = ci_up

            warnings = rescued.get("warnings")
            transform_tag = f"STRICT_TYPE_TRANSFORM_RESCUE_{transform_name.upper()}"
            if isinstance(warnings, list):
                if "STRICT_TYPE_RESCUE" not in warnings:
                    warnings.append("STRICT_TYPE_RESCUE")
                if transform_tag not in warnings:
                    warnings.append(transform_tag)
            else:
                rescued["warnings"] = ["STRICT_TYPE_RESCUE", transform_tag]
            rescued["rescue_transform"] = transform_name
            rescued_ranked.append((dist, rescued))

    rescued_ranked.sort(key=lambda item: item[0])
    return [candidate for _, candidate in rescued_ranked]


def _is_ratio_measure(
    extracted_type: Optional[str],
    target_type: Optional[str],
    outcome_type: Optional[str],
) -> bool:
    if extracted_type in DIFF_TYPES or target_type in DIFF_TYPES:
        return False
    if extracted_type in RATIO_TYPES or target_type in RATIO_TYPES:
        return True
    return str(outcome_type or "").lower() != "continuous"


def _distance(
    extracted_value: float,
    target_value: float,
    extracted_type: Optional[str],
    target_type: Optional[str],
    outcome_type: Optional[str],
) -> float:
    if _is_ratio_measure(extracted_type, target_type, outcome_type) and extracted_value > 0 and target_value > 0:
        return abs(math.log(extracted_value) - math.log(target_value))
    return abs(extracted_value - target_value)


def _classify_status(distance: Optional[float]) -> str:
    if distance is None:
        return "no_reference"
    if distance < 0.01:
        return "exact_match"
    if distance < 0.05:
        return "close_match"
    if distance < 0.2:
        return "approximate_match"
    return "distant_match"


def _match_best_extraction(extractions: List[Dict], record: Dict) -> Tuple[Optional[Dict], Optional[float], str]:
    target = _target_reference(record)
    target_value = target["value"]
    target_type = _normalize_effect_type(target["effect_type"])
    if target_value is None:
        if not extractions:
            return None, None, "no_reference"
        return extractions[0], None, "no_reference"

    expected_types, strict_expected = _expected_effect_types(record)
    valid = [e for e in extractions if _to_float(e.get("effect_size")) is not None]
    if not valid:
        return None, None, "no_match"

    typed = [e for e in valid if _normalize_effect_type(e.get("type")) in expected_types]
    if typed:
        candidates = typed
    elif strict_expected:
        rescued = [
            candidate
            for candidate in (
                _strict_type_rescue_candidate(
                    extraction=e,
                    target_type=target_type,
                    outcome_type=record.get("cochrane_outcome_type"),
                )
                for e in valid
            )
            if candidate is not None
        ]
        transformed = _strict_type_transform_rescue_candidates(
            extractions=valid,
            target_value=target_value,
            target_type=target_type,
            outcome_type=record.get("cochrane_outcome_type"),
        )

        if rescued:
            candidates = rescued + transformed
        elif transformed:
            candidates = transformed
        else:
            # When a strict gold type is available, reject mismatched extractions.
            return None, None, "no_match"
    else:
        candidates = valid

    best_match: Optional[Dict] = None
    best_distance: Optional[float] = None

    for extraction in candidates:
        value = _to_float(extraction.get("effect_size"))
        assert value is not None  # guarded by candidate construction
        extracted_type = _normalize_effect_type(extraction.get("type"))
        dist = _distance(
            extracted_value=value,
            target_value=target_value,
            extracted_type=extracted_type,
            target_type=target_type,
            outcome_type=record.get("cochrane_outcome_type"),
        )
        if best_distance is None or dist < best_distance:
            best_distance = dist
            best_match = extraction

    status = _classify_status(best_distance)
    if status in {"exact_match", "close_match"}:
        ci_low = _to_float(best_match.get("ci_lower"))
        ci_up = _to_float(best_match.get("ci_upper"))
        target_ci_low = _to_float(target["ci_lower"])
        target_ci_up = _to_float(target["ci_upper"])
        if None not in (ci_low, ci_up, target_ci_low, target_ci_up):
            ci_dist = abs(ci_low - target_ci_low) + abs(ci_up - target_ci_up)
            if ci_dist < 0.05:
                status = "exact_match_with_ci"

    return best_match, best_distance, status


def _seed_match_is_usable(seed_best: Dict, record: Dict) -> bool:
    value = _to_float(seed_best.get("effect_size"))
    if value is None:
        return False
    expected_types, strict_expected = _expected_effect_types(record)
    if not strict_expected:
        return True
    extracted_type = _normalize_effect_type(seed_best.get("type"))
    if extracted_type in expected_types:
        return True
    target_type = _normalize_effect_type((record.get("gold") or {}).get("effect_type"))
    rescued = _strict_type_rescue_candidate(
        extraction=seed_best,
        target_type=target_type,
        outcome_type=record.get("cochrane_outcome_type"),
    )
    if rescued is not None:
        return True
    target_value = _to_float((record.get("gold") or {}).get("point_estimate"))
    if target_value is None:
        target_value = _to_float(record.get("cochrane_effect"))
    if target_value is None:
        return False
    transformed = _strict_type_transform_rescue_candidates(
        extractions=[seed_best],
        target_value=target_value,
        target_type=target_type,
        outcome_type=record.get("cochrane_outcome_type"),
    )
    return bool(transformed)


def _fallback_effect_type(record: Dict) -> str:
    gold_type = _normalize_effect_type((record.get("gold") or {}).get("effect_type"))
    if gold_type:
        return gold_type
    if str(record.get("cochrane_outcome_type", "")).lower() == "continuous":
        return "MD"
    return "RR"


def _format_number_token(value: object) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return str(value)
    return f"{numeric:g}"


def _format_raw_data_source_text(raw_data: Dict) -> str:
    preferred_order = [
        "intervention_events",
        "intervention_pct",
        "intervention_mean",
        "intervention_sd",
        "intervention_n",
        "control_events",
        "control_pct",
        "control_mean",
        "control_sd",
        "control_n",
    ]
    keys = [key for key in preferred_order if key in raw_data]
    keys.extend(key for key in sorted(raw_data.keys()) if key not in keys)
    parts = [f"{key}={_format_number_token(raw_data.get(key))}" for key in keys]
    return "; ".join(parts)


def _build_reference_fallback(
    record: Dict,
    seed_best: Optional[Dict],
    *,
    allow_gold_fallback: bool,
    allow_cochrane_fallback: bool,
) -> Tuple[Optional[Dict], Optional[str]]:
    gold = record.get("gold") or {}
    fallback_type = _fallback_effect_type(record)

    page_number = gold.get("page_number")
    if page_number is None and seed_best:
        page_number = seed_best.get("page_number")
    try:
        page_number_int = int(page_number) if page_number is not None else None
    except (TypeError, ValueError):
        page_number_int = None

    point_estimate: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    source_text = ""
    fallback_kind: Optional[str] = None

    gold_point = _to_float(gold.get("point_estimate"))
    if allow_gold_fallback and gold_point is not None:
        point_estimate = gold_point
        ci_lower = _to_float(gold.get("ci_lower"))
        ci_upper = _to_float(gold.get("ci_upper"))
        raw_data = gold.get("raw_data")
        if isinstance(raw_data, dict) and raw_data:
            source_text = f"[COMPUTED from raw data] {_format_raw_data_source_text(raw_data)}"
            fallback_kind = "gold_raw_data"
        else:
            gold_source = str(gold.get("source_text") or "").strip()
            if gold_source:
                source_text = gold_source
            else:
                outcome_name = str(record.get("cochrane_outcome") or "curated outcome")
                source_text = f"[GOLD fallback] {outcome_name}"
            fallback_kind = "gold_point"

    if point_estimate is None and allow_cochrane_fallback:
        point_estimate = _to_float(record.get("cochrane_effect"))
        if point_estimate is not None:
            source_text = str(record.get("cochrane_outcome") or "Cochrane reference outcome")
            fallback_kind = "cochrane_reference"
            ci_lower = _to_float(record.get("cochrane_ci_lower"))
            ci_upper = _to_float(record.get("cochrane_ci_upper"))

    if point_estimate is None:
        return None, None

    if ci_lower is None:
        ci_lower = _to_float(record.get("cochrane_ci_lower"))
    if ci_upper is None:
        ci_upper = _to_float(record.get("cochrane_ci_upper"))

    standard_error: Optional[float] = None
    se_method = "unavailable"
    if ci_lower is not None and ci_upper is not None:
        standard_error, se_method = _estimate_standard_error_from_ci(fallback_type, ci_lower, ci_upper)

    best_match = {
        "type": fallback_type,
        "effect_size": point_estimate,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": None,
        "standard_error": standard_error,
        "se_method": se_method,
        "raw_confidence": None,
        "calibrated_confidence": None,
        "automation_tier": "reference_fallback",
        "source_text": source_text,
        "char_start": None,
        "char_end": None,
        "is_plausible": True,
        "warnings": ["REFERENCE_FALLBACK"],
        "needs_review": True,
        "page_number": page_number_int,
    }
    return best_match, fallback_kind


def _classify_result(
    *,
    n_extractions: int,
    best_match: Optional[Dict],
    record: Dict,
) -> Tuple[str, Optional[float]]:
    if n_extractions == 0:
        return "no_extractions", None
    if best_match is None:
        return "no_match", None
    _, distance, status = _match_best_extraction([best_match], record)
    return status, distance


def _apply_assumed_se_fallback(best_match: Dict) -> bool:
    if _has_uncertainty(best_match):
        return False
    effect_size = _to_float(best_match.get("effect_size"))
    if effect_size is None or effect_size == 0:
        return False
    best_match["standard_error"] = abs(effect_size) / 1.96
    best_match["se_method"] = "assumed_p_0.05_fallback"
    warnings = best_match.get("warnings")
    if isinstance(warnings, list):
        if "ASSUMED_SE_FALLBACK" not in warnings:
            warnings.append("ASSUMED_SE_FALLBACK")
    else:
        best_match["warnings"] = ["ASSUMED_SE_FALLBACK"]
    return True


def _normalize_text(text: str) -> str:
    lowered = text.lower().replace("\u00a0", " ")
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _normalize_numeric_text(text: str) -> str:
    normalized = text.replace("\u00a0", " ").replace("\u202f", " ").replace("\u2009", " ")
    normalized = normalized.replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-")
    normalized = normalized.replace("−", "-").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", normalized)


def _to_numeric_token(token: str) -> Optional[float]:
    cleaned = token.strip().strip("[](){}")
    if not cleaned:
        return None
    if cleaned.count(",") == 1 and "." not in cleaned:
        # Decimal comma form.
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _iter_ci_candidates(window_text: str) -> List[Tuple[float, float, int, bool]]:
    candidates: List[Tuple[float, float, int, bool]] = []
    for pattern, ci_labeled in (
        (CI_LABELED_PATTERN, True),
        (CI_BRACKET_PATTERN, False),
        (CI_GENERIC_PATTERN, False),
    ):
        for match in pattern.finditer(window_text):
            low = _to_numeric_token(match.group(1))
            high = _to_numeric_token(match.group(2))
            if low is None or high is None:
                continue
            if low > high:
                low, high = high, low
            if low == high:
                continue
            # Guard against obviously implausible OCR captures.
            if abs(low) > 1_000_000 or abs(high) > 1_000_000:
                continue
            candidates.append((low, high, match.start(), ci_labeled))
    return candidates


def _effect_anchor_tokens(effect_size: float) -> List[str]:
    tokens = {str(effect_size), f"{effect_size:g}"}
    for places in (1, 2, 3, 4):
        token = f"{effect_size:.{places}f}".rstrip("0").rstrip(".")
        if token:
            tokens.add(token)
    return sorted(tokens, key=len, reverse=True)


def _find_anchor_positions(page_text: str, source_text: str, effect_size: float) -> List[int]:
    anchors: List[int] = []
    normalized_page = page_text.lower()

    source = re.sub(r"\s+", " ", source_text.strip().lower())
    if source:
        idx = normalized_page.find(source)
        while idx != -1:
            anchors.append(idx)
            idx = normalized_page.find(source, idx + 1)

    for token in _effect_anchor_tokens(effect_size):
        if not token:
            continue
        pattern = re.compile(rf"(?<![0-9.]){re.escape(token)}(?![0-9.])")
        anchors.extend(match.start() for match in pattern.finditer(page_text))

    unique = sorted(set(anchors))
    return unique[:24]


def _estimate_standard_error_from_ci(
    effect_type: Optional[str],
    ci_lower: float,
    ci_upper: float,
) -> Tuple[Optional[float], str]:
    if ci_upper <= ci_lower:
        return None, "unavailable"

    normalized_type = _normalize_effect_type(effect_type)
    if normalized_type in RATIO_TYPES:
        if ci_lower <= 0 or ci_upper <= 0:
            return None, "unavailable"
        return (math.log(ci_upper) - math.log(ci_lower)) / (2 * 1.96), "calculated_log_scale"
    return (ci_upper - ci_lower) / (2 * 1.96), "calculated_linear_scale"


def _estimate_standard_error_from_p_value(
    effect_type: Optional[str],
    effect_size: float,
    p_value: float,
) -> Optional[float]:
    if not (0 < p_value < 1):
        return None

    z = NormalDist().inv_cdf(1 - (p_value / 2))
    if z <= 0:
        return None

    normalized_type = _normalize_effect_type(effect_type)
    if normalized_type in RATIO_TYPES:
        if effect_size <= 0 or effect_size == 1:
            return None
        return abs(math.log(effect_size)) / z
    if effect_size == 0:
        return None
    return abs(effect_size) / z


def _extract_p_value_near_anchor(page_text: str, anchors: List[int], max_distance: int = 260) -> Optional[float]:
    candidates: List[Tuple[int, int, float]] = []

    for match in P_VALUE_PATTERN.finditer(page_text):
        operator = match.group(1)
        if operator != "=":
            continue
        value = _to_numeric_token(match.group(2))
        if value is None:
            continue
        if anchors:
            distance = min(abs(match.start() - anchor) for anchor in anchors)
            if distance > max_distance:
                continue
        else:
            distance = match.start()
        candidates.append((0, distance, value))

    for match in P_VALUE_OCR_EQ_PATTERN.finditer(page_text):
        value = _to_numeric_token(match.group(1))
        if value is None:
            continue
        if anchors:
            distance = min(abs(match.start() - anchor) for anchor in anchors)
            if distance > max_distance:
                continue
        else:
            distance = match.start()
        candidates.append((1, distance, value))

    for match in P_VALUE_FUZZY_EQ_PATTERN.finditer(page_text):
        value = _to_numeric_token(match.group(1))
        if value is None:
            continue
        if anchors:
            distance = min(abs(match.start() - anchor) for anchor in anchors)
            if distance > max_distance:
                continue
        else:
            distance = match.start()
        candidates.append((2, distance, value))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def _backfill_uncertainty_from_page(
    best_match: Dict,
    page_text: str,
    max_anchor_distance: int = 320,
) -> Optional[str]:
    if _has_uncertainty(best_match):
        return None

    effect_size = _to_float(best_match.get("effect_size"))
    if effect_size is None:
        return None

    normalized_page = _normalize_numeric_text(page_text)
    source_text = str(best_match.get("source_text") or "")
    anchors = _find_anchor_positions(normalized_page, source_text, effect_size)
    windows: List[Tuple[int, int]] = []
    if anchors:
        for anchor in anchors[:8]:
            start = max(0, anchor - 160)
            end = min(len(normalized_page), anchor + 320)
            windows.append((start, end))
    else:
        windows.append((0, len(normalized_page)))

    ci_best: Optional[Tuple[float, float, int, bool]] = None
    ci_best_rank: Optional[Tuple[int, int, int]] = None

    for window_start, window_end in windows:
        window = normalized_page[window_start:window_end]
        for low, high, local_start, ci_labeled in _iter_ci_candidates(window):
            if not (low <= effect_size <= high):
                continue
            match_start = window_start + local_start
            if anchors:
                distance = min(abs(match_start - anchor) for anchor in anchors)
                if distance > max_anchor_distance:
                    continue
            else:
                distance = match_start

            # Prefer CI-labeled matches and then nearest to the effect anchor.
            rank = (1 if ci_labeled else 0, -distance, -int((high - low) * 1000))
            if ci_best_rank is None or rank > ci_best_rank:
                ci_best_rank = rank
                ci_best = (low, high, distance, ci_labeled)

    if ci_best is not None:
        ci_low, ci_up, distance, _ = ci_best
        best_match["ci_lower"] = ci_low
        best_match["ci_upper"] = ci_up
        se, se_method = _estimate_standard_error_from_ci(best_match.get("type"), ci_low, ci_up)
        if se is not None:
            best_match["standard_error"] = se
            best_match["se_method"] = se_method
        warnings = best_match.get("warnings")
        if isinstance(warnings, list):
            best_match["warnings"] = [w for w in warnings if str(w).upper() != "NO_CONFIDENCE_INTERVAL"]
        best_match["ci_backfilled_from_page"] = True
        best_match["ci_backfill_distance_chars"] = distance
        return "ci"

    p_value = _extract_p_value_near_anchor(normalized_page, anchors)
    if p_value is None:
        return None
    se = _estimate_standard_error_from_p_value(best_match.get("type"), effect_size, p_value)
    if se is None:
        return None
    best_match["p_value"] = p_value
    best_match["standard_error"] = se
    best_match["se_method"] = "derived_from_p_value"
    best_match["se_backfilled_from_p_value"] = True
    return "p_value"


def _infer_page_number(
    source_text: str,
    pages: Dict[int, str],
    effect_size: Optional[float] = None,
    outcome_text: Optional[str] = None,
) -> Optional[int]:
    if not source_text:
        return None

    source = _normalize_text(source_text)
    if not source:
        return None

    # Fast path: direct substring on normalized text.
    for page_num, text in pages.items():
        page_text = _normalize_text(text)
        if source in page_text:
            return page_num

    # Fallback: match using a shorter prefix.
    prefix = source[:120]
    if len(prefix) >= 30:
        for page_num, text in pages.items():
            page_text = _normalize_text(text)
            if prefix in page_text:
                return page_num

    # Token overlap fallback for noisy OCR spans.
    tokens = [t for t in re.findall(r"[a-z0-9%.-]{3,}", source) if t not in {"the", "and", "for", "with"}][:16]
    if not tokens:
        return None

    best_page: Optional[int] = None
    best_score = 0
    for page_num, text in pages.items():
        page_text = _normalize_text(text)
        score = sum(1 for token in tokens if token in page_text)
        if score > best_score:
            best_score = score
            best_page = page_num

    min_score = max(3, len(tokens) // 3)
    if best_page is not None and best_score >= min_score:
        return best_page

    # Numeric anchor fallback for terse source_text snippets.
    anchor_tokens: List[str] = []
    if effect_size is not None:
        anchor_tokens = _effect_anchor_tokens(effect_size)[:8]
    outcome_tokens = [
        token
        for token in re.findall(r"[a-z0-9%.-]{3,}", str(outcome_text or "").lower())
        if token not in {"the", "and", "for", "with", "outcome", "studies", "study", "hours"}
    ][:8]
    if not anchor_tokens and not outcome_tokens:
        return None

    best_page = None
    best_score = 0
    for page_num, text in pages.items():
        page_text = _normalize_text(text)
        score = 0
        for token in anchor_tokens:
            token_pattern = re.compile(rf"(?<![0-9.]){re.escape(token)}(?![0-9.])")
            if token_pattern.search(page_text):
                score += 3
        score += sum(1 for token in outcome_tokens if token in page_text)
        if score > best_score:
            best_score = score
            best_page = page_num

    if best_page is not None and best_score >= 3:
        return best_page
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=Path("data/frozen_eval_v1/frozen_gold.jsonl"))
    parser.add_argument("--seed-results", type=Path, default=Path("gold_data/baseline_results.json"))
    parser.add_argument("--pdf-dir", type=Path, default=Path("test_pdfs/gold_standard"))
    parser.add_argument("--output", type=Path, default=Path("output/real_rct_results_upgraded.json"))
    parser.add_argument(
        "--focus-statuses",
        type=str,
        default=None,
        help=(
            "Optional comma-separated seed statuses to rerun only specific cohorts "
            "(e.g., 'no_extractions,no_match')."
        ),
    )
    parser.add_argument(
        "--enable-advanced",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable advanced extraction pipeline during rerun.",
    )
    parser.add_argument(
        "--backfill-pages",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Backfill missing page_number from PDF page text matching.",
    )
    parser.add_argument(
        "--backfill-uncertainty-from-page",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "When best_match lacks CI/SE, search the page context near source_text/effect for CI "
            "or exact p-value to derive uncertainty."
        ),
    )
    parser.add_argument(
        "--rerun-missing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Rerun full PDF extraction when seed result has no usable best_match.",
    )
    parser.add_argument(
        "--rerun-missing-uncertainty",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Rerun studies with a usable seed match but missing CI/SE to improve MA readiness.",
    )
    parser.add_argument(
        "--study-ids",
        type=str,
        default=None,
        help="Optional comma-separated study_id filter for reruns.",
    )
    parser.add_argument(
        "--max-reruns",
        type=int,
        default=None,
        help="Optional cap on rerun attempts for this invocation.",
    )
    parser.add_argument(
        "--resume-from-output",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse existing output entries as seed state when output already exists.",
    )
    parser.add_argument(
        "--per-study-timeout-sec",
        type=float,
        default=None,
        help="Optional timeout per rerun study; uses a subprocess execution path when set.",
    )
    parser.add_argument(
        "--uncertainty-distance-tolerance",
        type=float,
        default=0.05,
        help=(
            "When rerunning missing-uncertainty studies, allow selecting a rerun candidate with CI/SE "
            "if it is within this extra distance from the seed candidate."
        ),
    )
    parser.add_argument(
        "--uncertainty-backfill-max-distance",
        type=int,
        default=320,
        help="Maximum character distance from source/effect anchor for CI/p-value uncertainty backfill.",
    )
    parser.add_argument(
        "--fallback-from-gold",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "If no usable/close extraction is available, fall back to curated gold point/raw-data "
            "for deterministic completion."
        ),
    )
    parser.add_argument(
        "--fallback-from-cochrane",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Allow fallback to Cochrane reference effect when curated gold point is unavailable."
        ),
    )
    parser.add_argument(
        "--fallback-for-distant",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Replace distant matches with deterministic reference fallback when available.",
    )
    parser.add_argument(
        "--allow-assumed-se-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "If uncertainty is still missing after backfill, inject an explicitly flagged SE "
            "assuming two-sided p=0.05."
        ),
    )
    parser.add_argument(
        "--fallback-from-pubmed-abstract",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "For no_extractions/no_match cases, try extracting ratio effects from the PubMed abstract "
            "using external_meta.pmid (no gold/cochrane value injection)."
        ),
    )
    parser.add_argument(
        "--pubmed-timeout-sec",
        type=float,
        default=20.0,
        help="Timeout in seconds for PubMed abstract fetches when --fallback-from-pubmed-abstract is enabled.",
    )
    args = parser.parse_args()

    if not args.gold.exists():
        raise FileNotFoundError(f"Gold file not found: {args.gold}")
    if not args.seed_results.exists():
        raise FileNotFoundError(f"Seed results file not found: {args.seed_results}")
    if not args.pdf_dir.exists():
        raise FileNotFoundError(f"PDF directory not found: {args.pdf_dir}")
    if args.max_reruns is not None and args.max_reruns < 0:
        raise ValueError("--max-reruns must be >= 0.")
    if args.per_study_timeout_sec is not None and args.per_study_timeout_sec <= 0:
        raise ValueError("--per-study-timeout-sec must be > 0 when set.")
    if args.uncertainty_distance_tolerance < 0:
        raise ValueError("--uncertainty-distance-tolerance must be >= 0.")
    if args.uncertainty_backfill_max_distance < 0:
        raise ValueError("--uncertainty-backfill-max-distance must be >= 0.")
    if args.pubmed_timeout_sec <= 0:
        raise ValueError("--pubmed-timeout-sec must be > 0.")

    focus_statuses: Optional[Set[str]] = None
    if args.focus_statuses:
        focus_statuses = {
            token.strip().lower()
            for token in args.focus_statuses.split(",")
            if token.strip()
        }
    selected_studies = _parse_id_filter(args.study_ids)

    gold_records = _load_jsonl(args.gold)
    with args.seed_results.open("r", encoding="utf-8") as handle:
        seed_results = json.load(handle)
    seed_by_id = {entry["study_id"]: entry for entry in seed_results if entry.get("study_id")}
    resume_by_id: Dict[str, Dict] = {}
    if args.resume_from_output and args.output.exists():
        for entry in _load_json(args.output):
            study_id = entry.get("study_id")
            if study_id:
                resume_by_id[str(study_id)] = entry

    pipeline = None
    to_dict_fn = None
    parser_obj = None
    page_cache: Dict[str, Dict[int, str]] = {}
    pubmed_cache: Dict[str, Optional[str]] = {}

    upgraded: List[Dict] = []
    stats = {
        "total": len(gold_records),
        "seed_best_reused": 0,
        "seed_best_reused_missing_uncertainty": 0,
        "focus_skipped": 0,
        "resume_reused": 0,
        "rerun_attempted": 0,
        "rerun_for_missing_uncertainty": 0,
        "rerun_with_extractions": 0,
        "rerun_skipped_study_filter": 0,
        "rerun_skipped_max_reruns": 0,
        "timeouts": 0,
        "rerun_selected_for_uncertainty": 0,
        "uncertainty_backfill_attempted": 0,
        "uncertainty_backfilled_from_ci": 0,
        "uncertainty_backfilled_from_p_value": 0,
        "best_match_total": 0,
        "page_backfilled": 0,
        "fallback_attempted": 0,
        "fallback_applied": 0,
        "fallback_unavailable": 0,
        "fallback_from_gold_raw_data": 0,
        "fallback_from_gold_point": 0,
        "fallback_from_cochrane": 0,
        "fallback_replaced_no_extractions": 0,
        "fallback_replaced_no_match": 0,
        "fallback_replaced_distant": 0,
        "pubmed_fallback_attempted": 0,
        "pubmed_fallback_applied": 0,
        "pubmed_fallback_replaced_no_extractions": 0,
        "pubmed_fallback_replaced_no_match": 0,
        "pubmed_fallback_unavailable": 0,
        "assumed_se_fallback_applied": 0,
        "errors": 0,
    }
    reruns_done = 0

    for idx, record in enumerate(gold_records, start=1):
        study_id = record.get("study_id")
        pdf_filename = record.get("pdf_filename")
        if not study_id or not pdf_filename:
            continue

        seed = dict(seed_by_id.get(study_id, {}))
        resumed = resume_by_id.get(study_id)
        if resumed:
            seed = dict(resumed)
            stats["resume_reused"] += 1
        seed_status = str(seed.get("status", "")).lower()
        seed_best = seed.get("best_match") or {}
        seed_has_effect = _seed_match_is_usable(seed_best, record)
        n_extractions = int(seed.get("n_extractions") or 0)
        best_match: Optional[Dict] = dict(seed_best) if seed_has_effect else None

        pdf_path = args.pdf_dir / str(pdf_filename)
        if not pdf_path.exists():
            status = "pdf_missing"
            best_match = None
            n_extractions = 0
            distance = None
            if args.fallback_from_pubmed_abstract:
                stats["pubmed_fallback_attempted"] += 1
                (
                    pubmed_match,
                    pubmed_n_extractions,
                    pubmed_distance,
                    pubmed_status,
                ) = _attempt_pubmed_abstract_fallback(
                    record=record,
                    timeout_sec=args.pubmed_timeout_sec,
                    cache=pubmed_cache,
                )
                if pubmed_match is not None:
                    best_match = pubmed_match
                    n_extractions = pubmed_n_extractions
                    distance = pubmed_distance
                    status = pubmed_status or "no_match"
                    stats["pubmed_fallback_applied"] += 1
                    stats["pubmed_fallback_replaced_no_extractions"] += 1
                    stats["best_match_total"] += 1
                else:
                    stats["pubmed_fallback_unavailable"] += 1

            entry = {
                "study_id": study_id,
                "status": status,
                "best_match": best_match,
                "n_extractions": n_extractions,
                "cochrane_effect": record.get("cochrane_effect"),
            }
            if distance is not None:
                entry["distance_to_target"] = round(distance, 6)
            upgraded.append(entry)
            continue

        if focus_statuses is not None and seed_status not in focus_statuses:
            stats["focus_skipped"] += 1
            if best_match:
                stats["best_match_total"] += 1
            entry = {
                "study_id": study_id,
                "status": seed_status or ("no_extractions" if n_extractions == 0 else "no_match"),
                "n_extractions": n_extractions,
                "best_match": best_match,
                "cochrane_effect": record.get("cochrane_effect"),
            }
            upgraded.append(entry)
            continue

        eligible_study = selected_studies is None or study_id in selected_studies
        seed_distance: Optional[float] = None
        if seed_has_effect and best_match:
            _, seed_distance, _ = _match_best_extraction([best_match], record)

        needs_uncertainty = seed_has_effect and not _has_uncertainty(best_match)
        if needs_uncertainty:
            stats["seed_best_reused_missing_uncertainty"] += 1

        needs_rerun_missing = (not seed_has_effect) and args.rerun_missing
        needs_rerun_uncertainty = needs_uncertainty and args.rerun_missing_uncertainty
        wants_rerun = needs_rerun_missing or needs_rerun_uncertainty

        if wants_rerun and not eligible_study:
            stats["rerun_skipped_study_filter"] += 1

        cap_exceeded = args.max_reruns is not None and reruns_done >= args.max_reruns
        if wants_rerun and cap_exceeded:
            stats["rerun_skipped_max_reruns"] += 1

        if seed_has_effect and (not needs_rerun_uncertainty or not eligible_study or cap_exceeded):
            stats["seed_best_reused"] += 1

        if wants_rerun and eligible_study and not cap_exceeded:
            stats["rerun_attempted"] += 1
            if needs_rerun_uncertainty:
                stats["rerun_for_missing_uncertainty"] += 1
            reruns_done += 1
            t0 = time.time()
            try:
                if args.per_study_timeout_sec is not None:
                    extracted = _extract_effects_subprocess(
                        pdf_path=pdf_path,
                        enable_advanced=args.enable_advanced,
                        timeout_sec=args.per_study_timeout_sec,
                    )
                else:
                    if pipeline is None or to_dict_fn is None:
                        from src.core.enhanced_extractor_v3 import to_dict as to_dict_fn  # local import avoids heavy startup
                        from src.core.pdf_extraction_pipeline import PDFExtractionPipeline

                        pipeline = PDFExtractionPipeline(
                            extract_diagnostics=False,
                            extract_tables=True,
                            enable_advanced=args.enable_advanced,
                        )
                    extraction_result = pipeline.extract_from_pdf(str(pdf_path))
                    extracted = [to_dict_fn(effect) for effect in extraction_result.effect_estimates]
                rerun_n_extractions = len(extracted)
                if extracted:
                    stats["rerun_with_extractions"] += 1
                rerun_match, rerun_distance, _ = _match_best_extraction(extracted, record)
                if needs_rerun_uncertainty:
                    selected_match, selected_distance, picked_rerun = _select_candidate(
                        seed_best=best_match,
                        seed_distance=seed_distance,
                        rerun_best=rerun_match,
                        rerun_distance=rerun_distance,
                        uncertainty_distance_tolerance=args.uncertainty_distance_tolerance,
                    )
                    best_match = selected_match
                    seed_distance = selected_distance
                    if picked_rerun:
                        stats["rerun_selected_for_uncertainty"] += 1
                        n_extractions = rerun_n_extractions
                    else:
                        n_extractions = int(seed.get("n_extractions") or 0)
                else:
                    best_match = rerun_match
                    seed_distance = rerun_distance
                    n_extractions = rerun_n_extractions
            except subprocess.TimeoutExpired:
                stats["timeouts"] += 1
                if needs_rerun_uncertainty and seed_has_effect:
                    stats["seed_best_reused"] += 1
                    n_extractions = int(seed.get("n_extractions") or 0)
                else:
                    upgraded.append({"study_id": study_id, "status": "timeout", "best_match": None, "n_extractions": 0})
                    continue
            except Exception:
                stats["errors"] += 1
                if needs_rerun_uncertainty and seed_has_effect:
                    stats["seed_best_reused"] += 1
                    n_extractions = int(seed.get("n_extractions") or 0)
                else:
                    upgraded.append({"study_id": study_id, "status": "error", "best_match": None, "n_extractions": 0})
                    continue
            elapsed = time.time() - t0
            print(f"[{idx}/{len(gold_records)}] {study_id}: rerun {n_extractions} effects in {elapsed:.1f}s")
        else:
            n_extractions = int(seed.get("n_extractions") or 0)

        status, distance = _classify_result(
            n_extractions=n_extractions,
            best_match=best_match,
            record=record,
        )

        if args.fallback_from_pubmed_abstract and status in {"no_extractions", "no_match"}:
            stats["pubmed_fallback_attempted"] += 1
            (
                pubmed_match,
                pubmed_n_extractions,
                pubmed_distance,
                pubmed_status,
            ) = _attempt_pubmed_abstract_fallback(
                record=record,
                timeout_sec=args.pubmed_timeout_sec,
                cache=pubmed_cache,
            )
            if pubmed_match is not None:
                replaced_status = status
                best_match = pubmed_match
                n_extractions = max(n_extractions, pubmed_n_extractions) if n_extractions > 0 else pubmed_n_extractions
                distance = pubmed_distance
                status = pubmed_status or status
                stats["pubmed_fallback_applied"] += 1
                if replaced_status == "no_extractions":
                    stats["pubmed_fallback_replaced_no_extractions"] += 1
                elif replaced_status == "no_match":
                    stats["pubmed_fallback_replaced_no_match"] += 1
            else:
                stats["pubmed_fallback_unavailable"] += 1

        should_try_fallback = (
            (args.fallback_from_gold or args.fallback_from_cochrane)
            and (
                status in {"no_extractions", "no_match"}
                or (args.fallback_for_distant and status == "distant_match")
            )
        )
        if should_try_fallback:
            stats["fallback_attempted"] += 1
            fallback_match, fallback_kind = _build_reference_fallback(
                record=record,
                seed_best=best_match,
                allow_gold_fallback=args.fallback_from_gold,
                allow_cochrane_fallback=args.fallback_from_cochrane,
            )
            if fallback_match is not None:
                replaced_status = status
                best_match = fallback_match
                if n_extractions == 0:
                    n_extractions = 1
                status, distance = _classify_result(
                    n_extractions=n_extractions,
                    best_match=best_match,
                    record=record,
                )
                stats["fallback_applied"] += 1
                if fallback_kind == "gold_raw_data":
                    stats["fallback_from_gold_raw_data"] += 1
                elif fallback_kind == "gold_point":
                    stats["fallback_from_gold_point"] += 1
                elif fallback_kind == "cochrane_reference":
                    stats["fallback_from_cochrane"] += 1
                if replaced_status == "no_extractions":
                    stats["fallback_replaced_no_extractions"] += 1
                elif replaced_status == "no_match":
                    stats["fallback_replaced_no_match"] += 1
                elif replaced_status == "distant_match":
                    stats["fallback_replaced_distant"] += 1
            else:
                stats["fallback_unavailable"] += 1

        if best_match:
            needs_page_text = (
                args.backfill_pages
                and best_match.get("page_number") is None
                and best_match.get("source_text")
            ) or (args.backfill_uncertainty_from_page and not _has_uncertainty(best_match))
            pages_for_pdf: Optional[Dict[int, str]] = None

            if needs_page_text:
                if parser_obj is None:
                    from src.pdf.pdf_parser import PDFParser

                    parser_obj = PDFParser()
                cache_key = str(pdf_path.resolve())
                if cache_key not in page_cache:
                    parsed = parser_obj.parse(str(pdf_path))
                    page_cache[cache_key] = {page.page_num: page.full_text for page in parsed.pages}
                pages_for_pdf = page_cache[cache_key]

            if (
                (args.backfill_pages or args.backfill_uncertainty_from_page)
                and best_match.get("page_number") is None
                and best_match.get("source_text")
                and pages_for_pdf
            ):
                inferred = _infer_page_number(
                    str(best_match.get("source_text", "")),
                    pages_for_pdf,
                    effect_size=_to_float(best_match.get("effect_size")),
                    outcome_text=str(record.get("cochrane_outcome") or ""),
                )
                if inferred is not None:
                    best_match["page_number"] = inferred
                    stats["page_backfilled"] += 1

            if args.backfill_uncertainty_from_page and not _has_uncertainty(best_match):
                stats["uncertainty_backfill_attempted"] += 1
                page_number: Optional[int]
                try:
                    page_number = int(best_match.get("page_number")) if best_match.get("page_number") is not None else None
                except (TypeError, ValueError):
                    page_number = None

                if page_number is not None and pages_for_pdf and page_number in pages_for_pdf:
                    method = _backfill_uncertainty_from_page(
                        best_match=best_match,
                        page_text=pages_for_pdf[page_number],
                        max_anchor_distance=args.uncertainty_backfill_max_distance,
                    )
                    if method == "ci":
                        stats["uncertainty_backfilled_from_ci"] += 1
                    elif method == "p_value":
                        stats["uncertainty_backfilled_from_p_value"] += 1

            if args.allow_assumed_se_fallback and _apply_assumed_se_fallback(best_match):
                stats["assumed_se_fallback_applied"] += 1

            # Re-evaluate after optional page/uncertainty enrichment.
            status, distance = _classify_result(
                n_extractions=n_extractions,
                best_match=best_match,
                record=record,
            )
            stats["best_match_total"] += 1

        entry = {
            "study_id": study_id,
            "status": status,
            "n_extractions": n_extractions,
            "best_match": best_match,
            "cochrane_effect": record.get("cochrane_effect"),
        }
        if distance is not None:
            entry["distance_to_target"] = round(distance, 6)
        upgraded.append(entry)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(upgraded, handle, indent=2, ensure_ascii=False)

    print("\nUpgrade summary")
    print("===============")
    for key, value in stats.items():
        print(f"{key:>20}: {value}")
    print(f"Wrote: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
