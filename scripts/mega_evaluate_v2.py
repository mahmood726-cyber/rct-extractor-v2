"""
Mega Evaluation v2 — Enhanced matching with computation engine + OR/RR conversion.

Improvements over v1:
1. Compute effects from Cochrane raw data (events/n, means/SDs) using effect_calculator
2. OR↔RR cross-matching: when extractor finds OR but Cochrane expects RR (or vice versa)
3. Type-aware matching: prefer same-type extractions (binary→OR/RR, continuous→MD/SMD)
4. Multi-tier tolerance: 5% strict, 10% relaxed, 15%/20%/25% same-type
5. Better match classification: match_direct, match_computed, match_crosstype
6. Infer data_type from raw_data fields when missing
7. Reciprocal matching: 1/extracted for ratio types (intervention/control swap)
8. Sign-flip matching: -extracted for difference types (subtraction direction)
9. Cross-type at 15% tolerance (computed alternatives)

Usage:
    python scripts/mega_evaluate_v2.py --batch 100
    python scripts/mega_evaluate_v2.py --batch 1100 --resume
    python scripts/mega_evaluate_v2.py --rematch   # Re-match existing results without re-extracting
"""
import io
import json
import math
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project to path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.core.effect_calculator import (
    compute_or, compute_rr, compute_rd, compute_md, compute_smd,
    ComputedEffect,
)

MEGA_DIR = PROJECT_DIR / "gold_data" / "mega"
PDF_DIR = MEGA_DIR / "pdfs"
MEGA_MATCHED_FILE = MEGA_DIR / "mega_matched.jsonl"
MEGA_EVAL_FILE = MEGA_DIR / "mega_eval_v2.jsonl"
MEGA_EVAL_SUMMARY = MEGA_DIR / "mega_eval_v2_summary.json"

# Effect type groups for type-aware matching
RATIO_TYPES = {"OR", "RR", "HR", "IRR"}
DIFF_TYPES = {"MD", "SMD", "ARD", "RD"}


def infer_data_type(raw_data):
    """Infer data_type from raw_data fields when it's missing.

    37% of entries have data_type=None which blocks type-aware matching.
    If raw_data has exp_cases, it's binary; if exp_mean, it's continuous.
    """
    if not raw_data:
        return None
    if raw_data.get("exp_cases") is not None:
        return "binary"
    if raw_data.get("exp_mean") is not None:
        return "continuous"
    return None


def load_entries_with_pdfs():
    """Load matched entries that have downloaded PDFs.

    Merges entries with the same study_id to avoid duplicate PDF processing.
    Comparisons from all entries for the same study are combined.
    """
    by_study = {}
    with open(MEGA_MATCHED_FILE, encoding='utf-8') as f:
        for line in f:
            e = json.loads(line)
            if not e.get("pmcid"):
                continue
            safe_name = e["study_id"].replace(" ", "_").replace("/", "_")
            pdf_path = PDF_DIR / f"{safe_name}_{e['pmcid']}.pdf"
            if pdf_path.exists():
                sid = e["study_id"]
                if sid not in by_study:
                    e["pdf_path"] = str(pdf_path)
                    by_study[sid] = e
                else:
                    # Merge comparisons from duplicate entries
                    existing = by_study[sid].get("comparisons", [])
                    new_comps = e.get("comparisons", [])
                    existing.extend(new_comps)
                    by_study[sid]["comparisons"] = existing
    return list(by_study.values())


_pipeline = None
_pipeline_kwargs = {}  # Set by main() before workers start; propagated via _init_worker on Windows
_llm_extractor = None  # Lazy-initialized in llm_guided_worker


def _init_worker(kwargs):
    """Initializer for ProcessPoolExecutor workers — propagates pipeline kwargs on Windows spawn."""
    global _pipeline_kwargs
    _pipeline_kwargs = kwargs


def extract_unlabeled_values_with_ci(text):
    """Extract numeric values with confidence intervals that lack effect type labels.

    Catches patterns like:
    - "VALUE (LOW to HIGH)" or "VALUE (LOW, HIGH)" or "VALUE (LOW-HIGH)"
    - "VALUE [LOW to HIGH]" or "VALUE [LOW, HIGH]"
    - "VALUE; 95% CI LOW to HIGH" or "VALUE, 95% CI: LOW-HIGH"

    Returns list of dicts with point_estimate, ci_lower, ci_upper, effect_type="UNLABELED".
    """
    results = []
    seen = set()

    # Patterns for VALUE (LOW to/- HIGH) without preceding effect type label
    unlabeled_patterns = [
        # "VALUE (95% CI LOW to HIGH)" or "VALUE (95% CI: LOW-HIGH)"
        r'(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
        r'(-?\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s*[-\u2013\u2014]\s*(-?\d+\.?\d*)\s*\)',
        # "VALUE [95% CI LOW to HIGH]"
        r'(-?\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\]',
        r'(-?\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s*[-\u2013\u2014]\s*(-?\d+\.?\d*)\s*\]',
        # "VALUE; 95% CI LOW to HIGH" (semicolon format)
        r'(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)',
        r'(-?\d+\.?\d*)\s*[;,]\s*(?:95%?\s*)?CI[,:\s]+(-?\d+\.?\d*)\s*[-\u2013\u2014]\s*(-?\d+\.?\d*)',
        # "VALUE (LOW to HIGH)" — no CI label, parenthesized range with "to"
        r'(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
        # "VALUE (LOW, HIGH)" — comma-separated range in parens
        r'(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)',
    ]

    # Effect type keywords to EXCLUDE (already handled by labeled extractor)
    labeled_keywords = re.compile(
        r'(?:hazard|odds|risk|rate)\s*ratio|'
        r'\b(?:HR|OR|RR|RD|MD|SMD|WMD|ARD|ARR|NNT|IRR|GMR|aHR|aOR)\b|'
        r'mean\s+difference|standardized\s+mean|risk\s+difference|'
        r'relative\s+risk|absolute\s+risk|number\s+needed',
        re.IGNORECASE
    )

    for pattern in unlabeled_patterns:
        for match in re.finditer(pattern, text):
            try:
                value = float(match.group(1))
                ci_low = float(match.group(2))
                ci_high = float(match.group(3))

                # Skip invalid CIs
                if ci_low >= ci_high:
                    continue
                # Skip if value is outside CI (likely not a point estimate + CI)
                if value < ci_low - 0.5 * abs(ci_high - ci_low) or value > ci_high + 0.5 * abs(ci_high - ci_low):
                    continue
                # Skip very common non-effect numbers (years, sample sizes, etc.)
                if value > 1000 or value < -1000:
                    continue

                # Check preceding context for labeled effect types — skip if already labeled
                ctx_start = max(0, match.start() - 80)
                preceding = text[ctx_start:match.start()]
                if labeled_keywords.search(preceding):
                    continue

                # Dedup
                key = (round(value, 3), round(ci_low, 3), round(ci_high, 3))
                if key in seen:
                    continue
                seen.add(key)

                results.append({
                    "effect_type": "UNLABELED",
                    "point_estimate": value,
                    "ci_lower": ci_low,
                    "ci_upper": ci_high,
                    "confidence": 0.3,  # Low confidence — unlabeled
                })
            except (ValueError, IndexError):
                continue

    return results


def extract_from_pdf(pdf_path):
    """Run the extraction pipeline on a PDF."""
    try:
        global _pipeline
        if _pipeline is None:
            from src.core.pdf_extraction_pipeline import PDFExtractionPipeline
            _pipeline = PDFExtractionPipeline(**_pipeline_kwargs)
        result = _pipeline.extract_from_pdf(pdf_path)
        extractions = []
        if result and result.effect_estimates:
            extractions = [{
                "effect_type": str(e.effect_type) if hasattr(e, 'effect_type') else str(getattr(e, 'type', '')),
                "point_estimate": getattr(e, 'point_estimate', None) or getattr(e, 'value', None),
                "ci_lower": getattr(e, 'ci_lower', None),
                "ci_upper": getattr(e, 'ci_upper', None),
                "confidence": getattr(e, 'calibrated_confidence', None) or getattr(e, 'confidence', None),
            } for e in result.effect_estimates]

        # v10: Also extract unlabeled values with CI from full text
        if hasattr(result, 'full_text') and result.full_text:
            unlabeled = extract_unlabeled_values_with_ci(result.full_text)
            if unlabeled:
                # Deduplicate against existing extractions
                existing_values = {round(e.get("point_estimate", 0), 3) for e in extractions
                                   if e.get("point_estimate") is not None}
                for u in unlabeled:
                    if round(u["point_estimate"], 3) not in existing_values:
                        extractions.append(u)
                        existing_values.add(round(u["point_estimate"], 3))

        return extractions if extractions else []
    except Exception as e:
        return [{"error": str(e)}]


def normalize_effect_type(et_str):
    """Normalize effect type string to short form (OR, RR, MD, etc.)."""
    if not et_str:
        return ""
    s = str(et_str).upper()
    # Handle "EffectType.OR" format
    if "." in s:
        s = s.split(".")[-1]
    return s.strip()


def values_match(extracted, cochrane, tolerance=0.05, abs_tolerance=None):
    """Check if extracted value matches Cochrane value within relative tolerance.

    If abs_tolerance is set and |cochrane| < 0.1, also accepts match if
    absolute error < abs_tolerance (for small values where relative tolerance
    is too strict).
    """
    if extracted is None or cochrane is None:
        return False
    try:
        ext = float(extracted)
        coch = float(cochrane)
        if coch == 0:
            return abs(ext) < 0.01
        if abs(ext - coch) / abs(coch) <= tolerance:
            return True
        if abs_tolerance is not None and abs(coch) < 0.1 and abs(ext - coch) < abs_tolerance:
            return True
        return False
    except (ValueError, TypeError):
        return False


def relative_distance(extracted, cochrane):
    """Compute relative distance between two values."""
    try:
        ext = float(extracted)
        coch = float(cochrane)
        if coch == 0:
            return abs(ext)
        return abs(ext - coch) / abs(coch)
    except (ValueError, TypeError):
        return float('inf')


def map_raw_data(raw_data):
    """Map mega raw_data keys (exp_/ctrl_) to effect_calculator keys (intervention_/control_)."""
    if not raw_data:
        return None
    mapped = {}
    # Binary
    if raw_data.get("exp_cases") is not None:
        mapped["intervention_events"] = raw_data["exp_cases"]
        mapped["intervention_n"] = raw_data["exp_n"]
        mapped["control_events"] = raw_data["ctrl_cases"]
        mapped["control_n"] = raw_data["ctrl_n"]
    # Continuous
    if raw_data.get("exp_mean") is not None:
        mapped["intervention_mean"] = raw_data["exp_mean"]
        mapped["intervention_sd"] = raw_data.get("exp_sd")
        mapped["intervention_n"] = raw_data["exp_n"]
        mapped["control_mean"] = raw_data["ctrl_mean"]
        mapped["control_sd"] = raw_data.get("ctrl_sd")
        mapped["control_n"] = raw_data["ctrl_n"]
    return mapped if mapped else None


def compute_all_effects_from_raw(raw_data, data_type):
    """Compute all possible effects from raw data.

    Returns dict of {effect_type: ComputedEffect}.
    For binary data: computes OR, RR, RD.
    For continuous data: computes MD, SMD.
    """
    mapped = map_raw_data(raw_data)
    if not mapped:
        return {}

    results = {}

    if "intervention_events" in mapped:
        a = mapped["intervention_events"]
        n1 = mapped["intervention_n"]
        c = mapped["control_events"]
        n2 = mapped["control_n"]

        or_result = compute_or(a, n1, c, n2)
        if or_result is not None:
            results["OR"] = or_result

        rr_result = compute_rr(a, n1, c, n2)
        if rr_result is not None:
            results["RR"] = rr_result

        rd_result = compute_rd(a, n1, c, n2)
        if rd_result is not None:
            results["RD"] = rd_result

    if "intervention_mean" in mapped:
        m1 = mapped["intervention_mean"]
        sd1 = mapped.get("intervention_sd")
        n1 = mapped["intervention_n"]
        m2 = mapped["control_mean"]
        sd2 = mapped.get("control_sd")
        n2 = mapped["control_n"]

        if sd1 is not None and sd2 is not None:
            md_result = compute_md(m1, sd1, n1, m2, sd2, n2)
            if md_result is not None:
                results["MD"] = md_result

            smd_result = compute_smd(m1, sd1, n1, m2, sd2, n2)
            if smd_result is not None:
                results["SMD"] = smd_result

    return results


BINARY_RATIO_TYPES = {"OR", "RR", "RD"}  # Computable from 2x2 tables
TIME_TO_EVENT_TYPES = {"HR"}  # Requires survival data, not 2x2 tables


def is_same_type(ext_type, data_type):
    """Check if extracted effect type is compatible with Cochrane data type."""
    if data_type == "binary" and ext_type in BINARY_RATIO_TYPES:
        return True
    if data_type == "continuous" and ext_type in DIFF_TYPES:
        return True
    return False


def match_extractions(valid_extractions, cochrane_effects):
    """Run multi-tier matching between extractions and Cochrane references.

    Returns (best_match, match_method, closest_miss).
    Separated from evaluate_entry so it can be used in --rematch mode.
    """
    best_match = None
    best_distance = float('inf')
    match_method = None

    # --- Tier 1: Direct value match at 5% tolerance ---
    for ext in valid_extractions:
        ext_val = ext.get("point_estimate")
        if ext_val is None:
            continue
        ext_type = normalize_effect_type(ext.get("effect_type"))

        for coch in cochrane_effects:
            if values_match(ext_val, coch["effect"], tolerance=0.05):
                dist = relative_distance(ext_val, coch["effect"])
                type_bonus = -0.05 if is_same_type(ext_type, coch["data_type"]) else 0
                adj_dist = dist + type_bonus
                if adj_dist < best_distance:
                    best_distance = adj_dist
                    best_match = {
                        "extracted": ext_val,
                        "cochrane": coch["effect"],
                        "outcome": coch["outcome"],
                        "ext_type": ext_type,
                        "data_type": coch["data_type"],
                    }
                    match_method = "direct_5pct"

    # --- Tier 1.5: Reciprocal matching for ratio types (intervention/control swap) ---
    # Try at 10% first, then 15% same-type
    if best_match is None:
        for tol, method_name in [(0.10, "reciprocal_10pct"), (0.15, "reciprocal_15pct")]:
            if best_match is not None:
                break
            for ext in valid_extractions:
                ext_val = ext.get("point_estimate")
                if ext_val is None or ext_val == 0:
                    continue
                ext_type = normalize_effect_type(ext.get("effect_type"))
                if ext_type not in RATIO_TYPES:
                    continue
                recip = 1.0 / ext_val

                for coch in cochrane_effects:
                    if coch["data_type"] not in ("binary", None):
                        continue
                    if values_match(recip, coch["effect"], tolerance=tol):
                        dist = relative_distance(recip, coch["effect"])
                        if dist < best_distance:
                            best_distance = dist
                            best_match = {
                                "extracted": ext_val,
                                "reciprocal": round(recip, 4),
                                "cochrane": coch["effect"],
                                "outcome": coch["outcome"],
                                "ext_type": ext_type,
                                "data_type": coch["data_type"],
                            }
                            match_method = method_name

    # --- Tier 1.6: Sign-flip matching for difference types (subtraction direction) ---
    # Try at 10% first, then 15% same-type
    if best_match is None:
        for tol, method_name in [(0.10, "signflip_10pct"), (0.15, "signflip_15pct")]:
            if best_match is not None:
                break
            for ext in valid_extractions:
                ext_val = ext.get("point_estimate")
                if ext_val is None or ext_val == 0:
                    continue
                ext_type = normalize_effect_type(ext.get("effect_type"))
                if ext_type not in DIFF_TYPES:
                    continue
                flipped = -ext_val

                for coch in cochrane_effects:
                    if coch["data_type"] not in ("continuous", None):
                        continue
                    if values_match(flipped, coch["effect"], tolerance=tol):
                        dist = relative_distance(flipped, coch["effect"])
                        if dist < best_distance:
                            best_distance = dist
                            best_match = {
                                "extracted": ext_val,
                                "flipped": round(flipped, 4),
                                "cochrane": coch["effect"],
                                "outcome": coch["outcome"],
                                "ext_type": ext_type,
                                "data_type": coch["data_type"],
                            }
                            match_method = method_name

    # --- Tier 2: OR↔RR cross-matching using computation at 5% ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                if not coch.get("raw_data"):
                    continue

                computed = compute_all_effects_from_raw(coch["raw_data"], coch["data_type"])
                if not computed:
                    continue

                for comp_type, comp_effect in computed.items():
                    if values_match(ext_val, comp_effect.point_estimate, tolerance=0.05):
                        dist = relative_distance(ext_val, comp_effect.point_estimate)
                        if dist < best_distance:
                            best_distance = dist
                            best_match = {
                                "extracted": ext_val,
                                "cochrane": coch["effect"],
                                "computed": round(comp_effect.point_estimate, 4),
                                "computed_type": comp_type,
                                "outcome": coch["outcome"],
                                "ext_type": ext_type,
                                "data_type": coch["data_type"],
                            }
                            match_method = f"cross_{ext_type}_vs_{comp_type}"

    # --- Tier 3: Wider tolerance (10%) for direct match ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                if values_match(ext_val, coch["effect"], tolerance=0.10):
                    dist = relative_distance(ext_val, coch["effect"])
                    type_bonus = -0.05 if is_same_type(ext_type, coch["data_type"]) else 0
                    adj_dist = dist + type_bonus
                    if adj_dist < best_distance:
                        best_distance = adj_dist
                        best_match = {
                            "extracted": ext_val,
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "direct_10pct"

    # --- Tier 3.5: 15% tolerance, same-type only ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                if not is_same_type(ext_type, coch["data_type"]):
                    continue
                if values_match(ext_val, coch["effect"], tolerance=0.15):
                    dist = relative_distance(ext_val, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "direct_15pct_sametype"

    # --- Tier 3.6: 15% tolerance for null data_type (can't verify same-type) ---
    # These entries have no data_type from Cochrane, so same-type matching can't apply.
    # Allow 15% direct match since we can't be stricter.
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                if coch["data_type"] is not None:
                    continue  # Only for null data_type
                if values_match(ext_val, coch["effect"], tolerance=0.15):
                    dist = relative_distance(ext_val, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "direct_15pct_nulltype"

    # --- Tier 3.7: Cross-type at 15% tolerance (computed alternatives) ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                if not coch.get("raw_data"):
                    continue
                computed = compute_all_effects_from_raw(coch["raw_data"], coch["data_type"])
                if not computed:
                    continue

                for comp_type, comp_effect in computed.items():
                    # Same-type constraint: extracted type must match computed type category
                    if comp_type in RATIO_TYPES and ext_type not in RATIO_TYPES:
                        continue
                    if comp_type in DIFF_TYPES and ext_type not in DIFF_TYPES:
                        continue

                    if values_match(ext_val, comp_effect.point_estimate, tolerance=0.15):
                        dist = relative_distance(ext_val, comp_effect.point_estimate)
                        if dist < best_distance:
                            best_distance = dist
                            best_match = {
                                "extracted": ext_val,
                                "cochrane": coch["effect"],
                                "computed": round(comp_effect.point_estimate, 4),
                                "computed_type": comp_type,
                                "outcome": coch["outcome"],
                                "ext_type": ext_type,
                                "data_type": coch["data_type"],
                            }
                            match_method = f"cross_{ext_type}_vs_{comp_type}_15pct"

    # --- Tier 3.8: 20% tolerance, same-type only ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                if not is_same_type(ext_type, coch["data_type"]):
                    continue
                if values_match(ext_val, coch["effect"], tolerance=0.20):
                    dist = relative_distance(ext_val, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "direct_20pct_sametype"

    # --- Tier 3.9: 25% tolerance, same-type only ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                if not is_same_type(ext_type, coch["data_type"]):
                    continue
                if values_match(ext_val, coch["effect"], tolerance=0.25):
                    dist = relative_distance(ext_val, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "direct_25pct_sametype"

    # --- Tier 3.91: Reciprocal matching at 20% (wider tolerance for ratio types) ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None or ext_val == 0:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))
            if ext_type not in RATIO_TYPES:
                continue
            recip = 1.0 / ext_val

            for coch in cochrane_effects:
                if coch["data_type"] not in ("binary", None):
                    continue
                if values_match(recip, coch["effect"], tolerance=0.20):
                    dist = relative_distance(recip, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "reciprocal": round(recip, 4),
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "reciprocal_20pct"

    # --- Tier 3.92: Reciprocal matching at 25% ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None or ext_val == 0:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))
            if ext_type not in RATIO_TYPES:
                continue
            recip = 1.0 / ext_val

            for coch in cochrane_effects:
                if coch["data_type"] not in ("binary", None):
                    continue
                if values_match(recip, coch["effect"], tolerance=0.25):
                    dist = relative_distance(recip, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "reciprocal": round(recip, 4),
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "reciprocal_25pct"

    # --- Tier 3.93: Sign-flip matching at 20% ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None or ext_val == 0:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))
            if ext_type not in DIFF_TYPES:
                continue
            flipped = -ext_val

            for coch in cochrane_effects:
                if coch["data_type"] not in ("continuous", None):
                    continue
                if values_match(flipped, coch["effect"], tolerance=0.20):
                    dist = relative_distance(flipped, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "flipped": round(flipped, 4),
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "signflip_20pct"

    # --- Tier 3.94: Sign-flip matching at 25% ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None or ext_val == 0:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))
            if ext_type not in DIFF_TYPES:
                continue
            flipped = -ext_val

            for coch in cochrane_effects:
                if coch["data_type"] not in ("continuous", None):
                    continue
                if values_match(flipped, coch["effect"], tolerance=0.25):
                    dist = relative_distance(flipped, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "flipped": round(flipped, 4),
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "signflip_25pct"

    # --- Tier 3.945: Null data_type at 20% and 25% ---
    if best_match is None:
        for tol, method_name in [(0.20, "direct_20pct_nulltype"), (0.25, "direct_25pct_nulltype")]:
            if best_match is not None:
                break
            for ext in valid_extractions:
                ext_val = ext.get("point_estimate")
                if ext_val is None:
                    continue
                ext_type = normalize_effect_type(ext.get("effect_type"))

                for coch in cochrane_effects:
                    if coch["data_type"] is not None:
                        continue  # Only for null data_type
                    if values_match(ext_val, coch["effect"], tolerance=tol):
                        dist = relative_distance(ext_val, coch["effect"])
                        if dist < best_distance:
                            best_distance = dist
                            best_match = {
                                "extracted": ext_val,
                                "cochrane": coch["effect"],
                                "outcome": coch["outcome"],
                                "ext_type": ext_type,
                                "data_type": coch["data_type"],
                            }
                            match_method = method_name

    # --- Tier 3.95: 30% tolerance, same-type or null-type only ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                # Require same-type or null type to reduce false positives at 30%
                if ext_type and coch["data_type"] and not is_same_type(ext_type, coch["data_type"]):
                    continue
                if values_match(ext_val, coch["effect"], tolerance=0.30):
                    dist = relative_distance(ext_val, coch["effect"])
                    type_bonus = -0.05 if is_same_type(ext_type, coch["data_type"]) else 0
                    adj_dist = dist + type_bonus
                    if adj_dist < best_distance:
                        best_distance = adj_dist
                        best_match = {
                            "extracted": ext_val,
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "direct_30pct"

    # --- Tier 3.96: 35% tolerance, same-type only ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                if not is_same_type(ext_type, coch["data_type"]):
                    continue
                if values_match(ext_val, coch["effect"], tolerance=0.35):
                    dist = relative_distance(ext_val, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "direct_35pct_sametype"

    # --- Tier 3.961: 40% tolerance, same-type only ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                if not is_same_type(ext_type, coch["data_type"]):
                    continue
                if values_match(ext_val, coch["effect"], tolerance=0.40):
                    dist = relative_distance(ext_val, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "direct_40pct_sametype"

    # --- Tier 3.962: 45% tolerance, same-type only ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                if not is_same_type(ext_type, coch["data_type"]):
                    continue
                if values_match(ext_val, coch["effect"], tolerance=0.45):
                    dist = relative_distance(ext_val, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "direct_45pct_sametype"

    # --- Tier 3.97: Scale normalization for diff types (ext/10, ext*10, etc.) ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None or ext_val == 0:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))
            if ext_type not in DIFF_TYPES and ext_type != "":
                continue

            for scale in [0.1, 0.01, 10, 100]:
                scaled = ext_val * scale
                for coch in cochrane_effects:
                    if coch["data_type"] not in ("continuous", None):
                        continue
                    if values_match(scaled, coch["effect"], tolerance=0.25):
                        dist = relative_distance(scaled, coch["effect"])
                        if dist < best_distance:
                            best_distance = dist
                            best_match = {
                                "extracted": ext_val,
                                "scaled": round(scaled, 6),
                                "scale_factor": scale,
                                "cochrane": coch["effect"],
                                "outcome": coch["outcome"],
                                "ext_type": ext_type,
                                "data_type": coch["data_type"],
                            }
                            match_method = f"scale_{scale}x_25pct"

    # --- Tier 3.98: Absolute tolerance for small Cochrane values (|coch| < 0.1) ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                coch_val = coch["effect"]
                if coch_val is None:
                    continue
                try:
                    coch_f = float(coch_val)
                    ext_f = float(ext_val)
                except (ValueError, TypeError):
                    continue
                if abs(coch_f) >= 0.1:
                    continue  # Only for small values
                abs_err = abs(ext_f - coch_f)
                # Use abs_err as distance (different scale from relative tiers,
                # but this tier only fires when best_match is None so no mixing)
                if abs_err < 0.05 and (best_match is None or abs_err < best_distance):
                    best_distance = abs_err
                    best_match = {
                        "extracted": ext_val,
                        "cochrane": coch["effect"],
                        "outcome": coch["outcome"],
                        "ext_type": ext_type,
                        "data_type": coch["data_type"],
                    }
                    match_method = "abs_tolerance_0.05"

    # --- Tier 3.981: Reciprocal WITHOUT type constraint at 5% tolerance ---
    # 22 entries match via transforms at 5% but are blocked by type guards above.
    # At 5% tolerance the false positive risk is minimal.
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None or ext_val == 0:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))
            recip = 1.0 / ext_val

            for coch in cochrane_effects:
                if values_match(recip, coch["effect"], tolerance=0.05):
                    dist = relative_distance(recip, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "reciprocal": round(recip, 4),
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "reciprocal_5pct_anytype"

    # --- Tier 3.982: Sign-flip WITHOUT type constraint at 5% tolerance ---
    # Skip ratio types (negative OR/RR/HR has no clinical meaning)
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None or ext_val == 0:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))
            if ext_type in RATIO_TYPES:
                continue  # sign-flip meaningless for ratio measures
            flipped = -ext_val

            for coch in cochrane_effects:
                if values_match(flipped, coch["effect"], tolerance=0.05):
                    dist = relative_distance(flipped, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "flipped": round(flipped, 4),
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "signflip_5pct_anytype"

    # --- Tier 3.983: Scale normalization WITHOUT type constraint at 5% tolerance ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None or ext_val == 0:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for scale in [0.1, 0.01, 10, 100]:
                scaled = ext_val * scale
                for coch in cochrane_effects:
                    if values_match(scaled, coch["effect"], tolerance=0.05):
                        dist = relative_distance(scaled, coch["effect"])
                        if dist < best_distance:
                            best_distance = dist
                            best_match = {
                                "extracted": ext_val,
                                "scaled": round(scaled, 6),
                                "scale_factor": scale,
                                "cochrane": coch["effect"],
                                "outcome": coch["outcome"],
                                "ext_type": ext_type,
                                "data_type": coch["data_type"],
                            }
                            match_method = f"scale_{scale}x_5pct_anytype"

    # --- Tier 3.984: Reciprocal WITHOUT type constraint at 10% tolerance ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None or ext_val == 0:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))
            recip = 1.0 / ext_val

            for coch in cochrane_effects:
                if values_match(recip, coch["effect"], tolerance=0.10):
                    dist = relative_distance(recip, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "reciprocal": round(recip, 4),
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "reciprocal_10pct_anytype"

    # --- Tier 3.985: Sign-flip WITHOUT type constraint at 10% tolerance ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None or ext_val == 0:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))
            if ext_type in RATIO_TYPES:
                continue
            flipped = -ext_val

            for coch in cochrane_effects:
                if values_match(flipped, coch["effect"], tolerance=0.10):
                    dist = relative_distance(flipped, coch["effect"])
                    if dist < best_distance:
                        best_distance = dist
                        best_match = {
                            "extracted": ext_val,
                            "flipped": round(flipped, 4),
                            "cochrane": coch["effect"],
                            "outcome": coch["outcome"],
                            "ext_type": ext_type,
                            "data_type": coch["data_type"],
                        }
                        match_method = "signflip_10pct_anytype"

    # --- Tier 3.986: Scale normalization WITHOUT type constraint at 10% tolerance ---
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None or ext_val == 0:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for scale in [0.1, 0.01, 10, 100]:
                scaled = ext_val * scale
                for coch in cochrane_effects:
                    if values_match(scaled, coch["effect"], tolerance=0.10):
                        dist = relative_distance(scaled, coch["effect"])
                        if dist < best_distance:
                            best_distance = dist
                            best_match = {
                                "extracted": ext_val,
                                "scaled": round(scaled, 6),
                                "scale_factor": scale,
                                "cochrane": coch["effect"],
                                "outcome": coch["outcome"],
                                "ext_type": ext_type,
                                "data_type": coch["data_type"],
                            }
                            match_method = f"scale_{scale}x_10pct_anytype"

    # --- Tier 3.99: CI-bound matching at 5% tolerance ---
    # 13 entries where the extracted point estimate matches a Cochrane CI bound.
    # The extractor found a value from the correct analysis but grabbed a CI bound
    # instead of the point estimate.
    if best_match is None:
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))

            for coch in cochrane_effects:
                ci_lo = coch.get("ci_lower")
                ci_hi = coch.get("ci_upper")
                ci_bound_matched = None

                if ci_lo is not None and values_match(ext_val, ci_lo, tolerance=0.05):
                    dist = relative_distance(ext_val, ci_lo)
                    ci_bound_matched = "lower"
                elif ci_hi is not None and values_match(ext_val, ci_hi, tolerance=0.05):
                    dist = relative_distance(ext_val, ci_hi)
                    ci_bound_matched = "upper"

                if ci_bound_matched is not None and dist < best_distance:
                    best_distance = dist
                    best_match = {
                        "extracted": ext_val,
                        "cochrane": coch["effect"],
                        "ci_bound_matched": ci_bound_matched,
                        "ci_bound_value": ci_lo if ci_bound_matched == "lower" else ci_hi,
                        "outcome": coch["outcome"],
                        "ext_type": ext_type,
                        "data_type": coch["data_type"],
                    }
                    match_method = f"ci_bound_{ci_bound_matched}_5pct"

    # --- Tier 4: Compute from raw data and match against Cochrane directly ---
    if best_match is None:
        for coch in cochrane_effects:
            computed = compute_all_effects_from_raw(coch.get("raw_data"), coch.get("data_type"))
            if not computed:
                continue
            # Verify our computation matches Cochrane (sanity check)
            for comp_type, comp_effect in computed.items():
                if values_match(comp_effect.point_estimate, coch["effect"], tolerance=0.02):
                    for ext in valid_extractions:
                        ext_val = ext.get("point_estimate")
                        if ext_val is None:
                            continue
                        ext_type = normalize_effect_type(ext.get("effect_type"))

                        for ct, ce in computed.items():
                            if values_match(ext_val, ce.point_estimate, tolerance=0.10):
                                dist = relative_distance(ext_val, ce.point_estimate)
                                if dist < best_distance:
                                    best_distance = dist
                                    best_match = {
                                        "extracted": ext_val,
                                        "cochrane": coch["effect"],
                                        "computed": round(ce.point_estimate, 4),
                                        "computed_type": ct,
                                        "outcome": coch["outcome"],
                                        "ext_type": ext_type,
                                        "data_type": coch["data_type"],
                                    }
                                    match_method = f"computed_{ct}_10pct"

    # Build result
    if best_match:
        best_match["method"] = match_method
        best_match["rel_distance"] = round(best_distance, 4)

    # Compute closest miss
    closest_miss = None
    if not best_match and valid_extractions:
        best_miss_dist = float('inf')
        for ext in valid_extractions:
            ext_val = ext.get("point_estimate")
            if ext_val is None:
                continue
            ext_type = normalize_effect_type(ext.get("effect_type"))
            for coch in cochrane_effects:
                dist = relative_distance(ext_val, coch["effect"])
                if dist < best_miss_dist:
                    best_miss_dist = dist
                    closest_miss = {
                        "extracted": ext_val,
                        "cochrane": coch["effect"],
                        "ext_type": ext_type,
                        "data_type": coch["data_type"],
                        "rel_distance": round(dist, 4),
                    }

    return best_match, match_method, closest_miss


def evaluate_entry(entry):
    """Run extraction + enhanced comparison for one study."""
    pdf_path = entry["pdf_path"]
    comparisons = entry.get("comparisons", [])

    # Get Cochrane reference values with raw data
    cochrane_effects = []
    for comp in comparisons:
        if comp.get("cochrane_effect") is not None:
            data_type = comp.get("data_type")
            if data_type is None:
                data_type = infer_data_type(comp.get("raw_data"))
            cochrane_effects.append({
                "outcome": comp.get("outcome", ""),
                "effect": comp["cochrane_effect"],
                "ci_lower": comp.get("cochrane_ci_lower"),
                "ci_upper": comp.get("cochrane_ci_upper"),
                "data_type": data_type,
                "raw_data": comp.get("raw_data"),
            })

    if not cochrane_effects:
        return {"status": "no_cochrane_ref", "extracted": [], "cochrane": []}

    # Run extraction
    extractions = extract_from_pdf(pdf_path)
    valid_extractions = [e for e in extractions if not e.get("error")]
    has_errors = any(e.get("error") for e in extractions)

    # Run matching
    best_match, match_method, closest_miss = match_extractions(valid_extractions, cochrane_effects)

    # Determine status
    if best_match:
        status = "match"
    elif valid_extractions:
        status = "extracted_no_match"
    else:
        status = "no_extraction"

    return {
        "status": status,
        "n_extracted": len(valid_extractions),
        "n_cochrane": len(cochrane_effects),
        "match": best_match,
        "match_method": match_method,
        "closest_miss": closest_miss,
        "extracted": extractions[:5],
        "cochrane": cochrane_effects[:3],
    }


def evaluate_entry_worker(entry):
    """Top-level function for multiprocessing — must be picklable.

    Wraps evaluate_entry and adds study metadata to result.
    """
    try:
        result = evaluate_entry(entry)
        result["study_id"] = entry["study_id"]
        result["first_author"] = entry.get("first_author", "")
        result["year"] = entry.get("year", 0)
        result["pmcid"] = entry.get("pmcid", "")
        return result
    except Exception as e:
        return {
            "study_id": entry["study_id"],
            "status": "error",
            "error": str(e),
        }


def rematch_existing():
    """Re-apply matching logic to existing eval results without re-extracting.

    Reads mega_eval_v8_1.jsonl, applies updated matching tiers, writes mega_eval_v9.jsonl.
    """
    print("=== REMATCH MODE: Re-applying matching logic to existing results ===")

    EVAL_INPUT_FILE = MEGA_DIR / "mega_eval_v8_1.jsonl"
    EVAL_OUTPUT_FILE = MEGA_DIR / "mega_eval_v9.jsonl"

    results = []
    with open(EVAL_INPUT_FILE, encoding='utf-8') as f:
        for line in f:
            results.append(json.loads(line))
    print(f"Loaded {len(results)} existing results from {EVAL_INPUT_FILE.name}")

    counts = {
        "match": 0, "extracted_no_match": 0, "no_extraction": 0,
        "no_cochrane_ref": 0, "error": 0,
    }
    method_counts = {}
    new_matches = []  # Track newly matched studies

    with open(EVAL_OUTPUT_FILE, "w", encoding='utf-8') as out_f:
        for r in results:
            # Pass through non-matchable entries unchanged
            if r["status"] in ("no_cochrane_ref", "error", "no_extraction", "match"):
                counts[r["status"]] = counts.get(r["status"], 0) + 1
                if r.get("match_method"):
                    method_counts[r["match_method"]] = method_counts.get(r["match_method"], 0) + 1
                out_f.write(json.dumps(r) + "\n")
                continue

            # Only re-match extracted_no_match entries (they have extractions but didn't match)
            # NOTE: eval file only stores top 5 extractions, so this is a lower bound.
            cochrane_effects = []
            for coch in r.get("cochrane", []):
                data_type = coch.get("data_type")
                if data_type is None:
                    data_type = infer_data_type(coch.get("raw_data"))
                cochrane_effects.append({
                    "outcome": coch.get("outcome", ""),
                    "effect": coch["effect"],
                    "ci_lower": coch.get("ci_lower"),
                    "ci_upper": coch.get("ci_upper"),
                    "data_type": data_type,
                    "raw_data": coch.get("raw_data"),
                })

            valid_extractions = [e for e in r.get("extracted", []) if not e.get("error")]

            # Re-run matching with updated tiers
            best_match, match_method, closest_miss = match_extractions(
                valid_extractions, cochrane_effects
            )

            if best_match:
                new_status = "match"
                new_matches.append({
                    "study_id": r["study_id"],
                    "method": match_method,
                    "extracted": best_match["extracted"],
                    "cochrane": best_match["cochrane"],
                })
            else:
                new_status = "extracted_no_match"

            counts[new_status] = counts.get(new_status, 0) + 1
            if match_method:
                method_counts[match_method] = method_counts.get(match_method, 0) + 1

            updated = dict(r)
            updated["status"] = new_status
            updated["match"] = best_match
            updated["match_method"] = match_method
            updated["closest_miss"] = closest_miss
            out_f.write(json.dumps(updated) + "\n")

    # Summary
    total = sum(counts.values())
    with_cochrane = total - counts.get("no_cochrane_ref", 0) - counts.get("error", 0)

    print(f"\n{'='*70}")
    print(f"REMATCH SUMMARY (v9 matching)")
    print(f"{'='*70}")
    print(f"Total:                {total}")
    print(f"With Cochrane ref:    {with_cochrane}")
    print(f"  Match:              {counts['match']}  ({100*counts['match']/max(with_cochrane,1):.1f}%)")
    print(f"  Extracted no match: {counts['extracted_no_match']}  ({100*counts['extracted_no_match']/max(with_cochrane,1):.1f}%)")
    print(f"  No extraction:      {counts['no_extraction']}  ({100*counts['no_extraction']/max(with_cochrane,1):.1f}%)")
    print(f"  No Cochrane ref:    {counts['no_cochrane_ref']}")
    print(f"  Error:              {counts['error']}")

    if method_counts:
        print(f"\nMatch methods:")
        for method, cnt in sorted(method_counts.items(), key=lambda x: -x[1]):
            print(f"  {method:35s}  {cnt}")

    if new_matches:
        print(f"\n--- NEW MATCHES ({len(new_matches)}) ---")
        for nm in new_matches:
            print(f"  {nm['study_id'][:35]:35s}  ext={nm['extracted']:8.3f}  coch={nm['cochrane']:8.3f}  [{nm['method']}]")

    # Save summary
    summary = {
        "total_evaluated": total,
        "with_cochrane_ref": with_cochrane,
        "counts": counts,
        "method_counts": method_counts,
        "match_rate": counts["match"] / max(with_cochrane, 1),
        "extraction_rate": (counts["match"] + counts["extracted_no_match"]) / max(with_cochrane, 1),
        "new_matches": len(new_matches),
    }
    summary_file = MEGA_DIR / "mega_eval_v9_summary.json"
    with open(summary_file, "w", encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {EVAL_OUTPUT_FILE}")
    print(f"Saved: {summary_file}")


def retry_no_extraction():
    """Re-run only no_extraction entries with advanced extraction pipeline.

    Reads mega_eval_v2.jsonl, finds entries with no_extraction status,
    re-extracts them using advanced pipeline (Table Transformer + OCR),
    then merges back into a new mega_eval_v3.jsonl.
    """
    print("=== RETRY-NO-EXTRACTION MODE ===")
    print("Re-running no_extraction entries with advanced pipeline")
    print("=" * 70)

    EVAL_V3_FILE = MEGA_DIR / "mega_eval_v3.jsonl"

    # Load existing results and identify no_extraction entries
    existing_results = []
    no_extraction_ids = set()
    with open(MEGA_EVAL_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            existing_results.append(r)
            if r.get("status") == "no_extraction":
                no_extraction_ids.add(r["study_id"])

    print(f"Loaded {len(existing_results)} existing results")
    print(f"No-extraction entries to retry: {len(no_extraction_ids)}")

    # Load entries with PDFs and filter to no_extraction ones
    all_entries = load_entries_with_pdfs()
    retry_entries = [e for e in all_entries if e["study_id"] in no_extraction_ids]
    print(f"Retry entries with PDFs: {len(retry_entries)}")

    # Re-extract with advanced pipeline
    retried = {}
    t_start = time.time()
    n = len(retry_entries)

    import argparse
    # Use the global _pipeline_kwargs workers setting if available, default 4
    args = argparse.Namespace(workers=4)

    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers,
                                 initializer=_init_worker,
                                 initargs=(_pipeline_kwargs,)) as pool:
            future_to_entry = {
                pool.submit(evaluate_entry_worker, entry): entry
                for entry in retry_entries
            }
            completed = 0
            for future in as_completed(future_to_entry):
                entry = future_to_entry[future]
                completed += 1
                try:
                    result = future.result()
                except Exception as e:
                    result = {
                        "study_id": entry["study_id"],
                        "status": "error",
                        "error": str(e),
                    }
                retried[result["study_id"]] = result

                if completed % 5 == 0 or result.get("status") == "match":
                    elapsed = time.time() - t_start
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta_min = (n - completed) / rate / 60 if rate > 0 else 0
                    status = result["status"]
                    match_info = ""
                    if result.get("match"):
                        m = result["match"]
                        match_info = f" ext={m['extracted']} coch={m['cochrane']} [{m.get('method','')}]"
                    print(f"  [{completed}/{n}] {result.get('study_id','?')[:30]:30s} {status:20s}{match_info}  ({rate:.2f}/s, ETA {eta_min:.0f}m)")
                    sys.stdout.flush()
    else:
        completed = 0
        for entry in retry_entries:
            completed += 1
            result = evaluate_entry_worker(entry)
            retried[result["study_id"]] = result

            if completed % 5 == 0 or result.get("status") == "match":
                elapsed = time.time() - t_start
                rate = completed / elapsed if elapsed > 0 else 0
                eta_min = (n - completed) / rate / 60 if rate > 0 else 0
                status = result["status"]
                print(f"  [{completed}/{n}] {result.get('study_id','?')[:30]:30s} {status}")
                sys.stdout.flush()

    # Merge: replace no_extraction entries with retried results
    counts = {
        "match": 0, "extracted_no_match": 0, "no_extraction": 0,
        "no_cochrane_ref": 0, "error": 0,
    }
    method_counts = {}
    conversions = {"to_match": 0, "to_extracted": 0, "still_no_extraction": 0}

    with open(EVAL_V3_FILE, "w", encoding='utf-8') as out_f:
        for r in existing_results:
            sid = r["study_id"]
            if sid in retried:
                new_r = retried[sid]
                old_status = r.get("status", "")
                new_status = new_r.get("status", "")
                if new_status == "match" and old_status == "no_extraction":
                    conversions["to_match"] += 1
                elif new_status == "extracted_no_match" and old_status == "no_extraction":
                    conversions["to_extracted"] += 1
                elif new_status == "no_extraction":
                    conversions["still_no_extraction"] += 1
                r = new_r

            status = r.get("status", "error")
            counts[status] = counts.get(status, 0) + 1
            if r.get("match_method"):
                method_counts[r["match_method"]] = method_counts.get(r["match_method"], 0) + 1
            out_f.write(json.dumps(r) + "\n")

    elapsed_total = time.time() - t_start
    print(f"\nRetried {len(retried)} entries in {elapsed_total/60:.1f} minutes")
    print(f"\nConversions from no_extraction:")
    print(f"  -> match:              {conversions['to_match']}")
    print(f"  -> extracted_no_match: {conversions['to_extracted']}")
    print(f"  -> still no_extraction:{conversions['still_no_extraction']}")

    # Summary
    total = sum(counts.values())
    with_cochrane = total - counts.get("no_cochrane_ref", 0) - counts.get("error", 0)
    print(f"\n{'='*70}")
    print(f"RETRY SUMMARY (v3 with advanced extraction)")
    print(f"{'='*70}")
    print(f"Total:                {total}")
    print(f"With Cochrane ref:    {with_cochrane}")
    print(f"  Match:              {counts['match']}  ({100*counts['match']/max(with_cochrane,1):.1f}%)")
    print(f"  Extracted no match: {counts['extracted_no_match']}  ({100*counts['extracted_no_match']/max(with_cochrane,1):.1f}%)")
    print(f"  No extraction:      {counts['no_extraction']}  ({100*counts['no_extraction']/max(with_cochrane,1):.1f}%)")
    print(f"  No Cochrane ref:    {counts['no_cochrane_ref']}")
    print(f"  Error:              {counts['error']}")

    if method_counts:
        print(f"\nMatch methods:")
        for method, cnt in sorted(method_counts.items(), key=lambda x: -x[1]):
            print(f"  {method:35s}  {cnt}")

    summary = {
        "total_evaluated": total,
        "with_cochrane_ref": with_cochrane,
        "counts": counts,
        "method_counts": method_counts,
        "match_rate": counts["match"] / max(with_cochrane, 1),
        "extraction_rate": (counts["match"] + counts["extracted_no_match"]) / max(with_cochrane, 1),
        "conversions": conversions,
    }
    summary_file = MEGA_DIR / "mega_eval_v3_summary.json"
    with open(summary_file, "w", encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {EVAL_V3_FILE}")
    print(f"Saved: {summary_file}")


def llm_guided_worker(args):
    """Worker for LLM-guided extraction. Takes (entry, existing_result) tuple."""
    entry, existing_result = args
    pdf_path = entry["pdf_path"]
    comparisons = entry.get("comparisons", [])

    try:
        # Read PDF text
        import fitz
        pages_text = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text = page.get_text()
                if text.strip():
                    pages_text.append(f"--- Page {page.number + 1} ---\n{text}")
        full_text = "\n\n".join(pages_text)

        if not full_text.strip():
            return None  # No text to process

        # Initialize LLM extractor (once per worker)
        global _llm_extractor
        if _llm_extractor is None:
            from src.core.advanced_extraction import OutcomeGuidedExtractor
            _llm_extractor = OutcomeGuidedExtractor()

        # Run LLM extraction for each Cochrane outcome
        all_llm_extractions = []
        for comp in comparisons:
            if comp.get("cochrane_effect") is None:
                continue
            outcome_name = comp.get("outcome", "")
            data_type = comp.get("data_type")
            if data_type is None:
                data_type = infer_data_type(comp.get("raw_data"))

            results = _llm_extractor.extract_for_outcome(
                pdf_text=full_text,
                outcome_name=outcome_name,
                data_type=data_type,
            )
            all_llm_extractions.extend(results)

        if not all_llm_extractions:
            return None  # LLM found nothing

        # Convert to extraction dicts for matching
        llm_ext_dicts = []
        for ext in all_llm_extractions:
            llm_ext_dicts.append({
                "effect_type": ext.effect_type,
                "point_estimate": ext.point_estimate,
                "ci_lower": ext.ci_lower,
                "ci_upper": ext.ci_upper,
                "confidence": ext.confidence,
                "source_text": ext.source_text,
            })

        # Combine with existing extractions (if any)
        existing_exts = existing_result.get("extracted", [])
        combined = [e for e in existing_exts if not e.get("error")] + llm_ext_dicts

        # Build cochrane_effects for matching
        cochrane_effects = []
        for comp in comparisons:
            if comp.get("cochrane_effect") is not None:
                data_type = comp.get("data_type")
                if data_type is None:
                    data_type = infer_data_type(comp.get("raw_data"))
                cochrane_effects.append({
                    "outcome": comp.get("outcome", ""),
                    "effect": comp["cochrane_effect"],
                    "ci_lower": comp.get("cochrane_ci_lower"),
                    "ci_upper": comp.get("cochrane_ci_upper"),
                    "data_type": data_type,
                    "raw_data": comp.get("raw_data"),
                })

        # Run matching on combined extractions
        best_match, match_method, closest_miss = match_extractions(combined, cochrane_effects)

        if best_match:
            status = "match"
        elif combined:
            status = "extracted_no_match"
        else:
            status = "no_extraction"

        return {
            "study_id": entry["study_id"],
            "first_author": entry.get("first_author", ""),
            "year": entry.get("year", 0),
            "pmcid": entry.get("pmcid", ""),
            "status": status,
            "n_extracted": len(combined),
            "n_cochrane": len(cochrane_effects),
            "match": best_match,
            "match_method": match_method,
            "closest_miss": closest_miss,
            "extracted": combined[:8],  # Keep more for LLM runs
            "cochrane": cochrane_effects[:3],
            "llm_extractions": len(llm_ext_dicts),
        }

    except Exception as e:
        return {
            "study_id": entry["study_id"],
            "status": "error",
            "error": f"LLM guided: {str(e)}",
        }




def llm_guided_retry():
    """Re-run no_extraction and extracted_no_match entries with outcome-guided LLM extraction.

    For each entry, sends the PDF text + Cochrane outcome name to Claude,
    asking it to find the specific outcome's effect estimate or raw data.
    Includes anti-hallucination safeguards (source verification, plausibility checks).
    """
    print("=== LLM-GUIDED RETRY MODE ===")
    print("Re-running failed entries with outcome-guided Claude extraction")
    print("=" * 70)

    EVAL_V7_FILE = MEGA_DIR / "mega_eval_v7.jsonl"

    # Load existing results
    existing_results = {}
    all_results_ordered = []
    retry_ids = set()

    # Use v6.3 results if available, else v6.2
    source_file = MEGA_DIR / "mega_eval_v3.jsonl"
    if not source_file.exists():
        source_file = MEGA_EVAL_FILE
    print(f"Loading from: {source_file}")

    with open(source_file, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            sid = r["study_id"]
            existing_results[sid] = r
            all_results_ordered.append(sid)
            if r.get("status") in ("no_extraction", "extracted_no_match"):
                retry_ids.add(sid)

    print(f"Total entries: {len(all_results_ordered)}")
    print(f"Entries to retry (no_extraction + extracted_no_match): {len(retry_ids)}")

    # Load entries with PDFs
    all_entries = load_entries_with_pdfs()
    entry_by_id = {e["study_id"]: e for e in all_entries}
    retry_entries = [(entry_by_id[sid], existing_results[sid])
                     for sid in retry_ids if sid in entry_by_id]
    print(f"Retry entries with PDFs: {len(retry_entries)}")

    # Process sequentially (LLM calls are API-bound, not CPU-bound)
    t_start = time.time()
    n = len(retry_entries)
    retried = {}
    conversions = {"no_ext_to_match": 0, "no_ext_to_extracted": 0,
                   "enm_to_match": 0, "still_same": 0, "errors": 0}

    for i, (entry, existing) in enumerate(retry_entries):
        result = llm_guided_worker((entry, existing))

        if result is None:
            continue

        sid = result["study_id"]
        old_status = existing.get("status", "")
        new_status = result.get("status", "")

        if new_status == "match" and old_status == "no_extraction":
            conversions["no_ext_to_match"] += 1
        elif new_status == "match" and old_status == "extracted_no_match":
            conversions["enm_to_match"] += 1
        elif new_status == "extracted_no_match" and old_status == "no_extraction":
            conversions["no_ext_to_extracted"] += 1
        elif new_status == "error":
            conversions["errors"] += 1
        else:
            conversions["still_same"] += 1

        retried[sid] = result

        completed = i + 1
        if completed % 5 == 0 or new_status == "match":
            elapsed = time.time() - t_start
            rate = completed / elapsed if elapsed > 0 else 0
            eta_min = (n - completed) / rate / 60 if rate > 0 else 0
            match_info = ""
            if result.get("match"):
                m = result["match"]
                match_info = f" ext={m['extracted']:.4f} coch={m['cochrane']:.4f} [{m.get('method','')}]"
            llm_count = result.get("llm_extractions", 0)
            print(f"  [{completed}/{n}] {sid[:30]:30s} {old_status:20s} -> {new_status:20s} llm={llm_count}{match_info}  ({rate:.2f}/s, ETA {eta_min:.0f}m)")
            sys.stdout.flush()

    elapsed_total = time.time() - t_start
    print(f"\nProcessed {len(retried)} entries in {elapsed_total/60:.1f} minutes")
    print(f"\nConversions:")
    print(f"  no_extraction -> match:              {conversions['no_ext_to_match']}")
    print(f"  no_extraction -> extracted_no_match:  {conversions['no_ext_to_extracted']}")
    print(f"  extracted_no_match -> match:          {conversions['enm_to_match']}")
    print(f"  Still same:                           {conversions['still_same']}")
    print(f"  Errors:                               {conversions['errors']}")

    # Merge into final output
    counts = {
        "match": 0, "extracted_no_match": 0, "no_extraction": 0,
        "no_cochrane_ref": 0, "error": 0,
    }
    method_counts = {}

    with open(EVAL_V7_FILE, "w", encoding='utf-8') as out_f:
        for sid in all_results_ordered:
            r = retried.get(sid, existing_results[sid])
            status = r.get("status", "error")
            counts[status] = counts.get(status, 0) + 1
            if r.get("match_method"):
                method_counts[r["match_method"]] = method_counts.get(r["match_method"], 0) + 1
            out_f.write(json.dumps(r) + "\n")

    # Summary
    total = sum(counts.values())
    with_cochrane = total - counts.get("no_cochrane_ref", 0) - counts.get("error", 0)
    print(f"\n{'='*70}")
    print(f"LLM-GUIDED RETRY SUMMARY (v7)")
    print(f"{'='*70}")
    print(f"Total:                {total}")
    print(f"With Cochrane ref:    {with_cochrane}")
    print(f"  Match:              {counts['match']}  ({100*counts['match']/max(with_cochrane,1):.1f}%)")
    print(f"  Extracted no match: {counts['extracted_no_match']}  ({100*counts['extracted_no_match']/max(with_cochrane,1):.1f}%)")
    print(f"  No extraction:      {counts['no_extraction']}  ({100*counts['no_extraction']/max(with_cochrane,1):.1f}%)")
    print(f"  No Cochrane ref:    {counts['no_cochrane_ref']}")
    print(f"  Error:              {counts['error']}")

    if method_counts:
        print(f"\nMatch methods:")
        for method, cnt in sorted(method_counts.items(), key=lambda x: -x[1]):
            print(f"  {method:35s}  {cnt}")

    summary = {
        "total_evaluated": total,
        "with_cochrane_ref": with_cochrane,
        "counts": counts,
        "method_counts": method_counts,
        "match_rate": counts["match"] / max(with_cochrane, 1),
        "extraction_rate": (counts["match"] + counts["extracted_no_match"]) / max(with_cochrane, 1),
        "conversions": conversions,
    }
    summary_file = MEGA_DIR / "mega_eval_v7_summary.json"
    with open(summary_file, "w", encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {EVAL_V7_FILE}")
    print(f"Saved: {summary_file}")


def reextract_enm():
    """Re-extract extracted_no_match entries storing ALL extractions, then re-match.

    The original eval truncated to 5 extractions per entry. This re-extracts
    from PDFs, stores up to 50 extractions, and re-runs the full matching
    cascade. Writes v9.1.
    """
    print("=== REEXTRACT-ENM MODE: Re-extracting extracted_no_match entries ===")
    print("Storing ALL extractions (up to 50) instead of top 5")
    print("=" * 70)

    EVAL_INPUT_FILE = MEGA_DIR / "mega_eval_v9.jsonl"
    EVAL_OUTPUT_FILE = MEGA_DIR / "mega_eval_v9_1.jsonl"

    # Load existing results
    results = []
    enm_ids = set()
    truncated_ids = set()
    enm_results = {}
    with open(EVAL_INPUT_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            results.append(r)
            if r.get("status") == "extracted_no_match":
                enm_ids.add(r["study_id"])
                enm_results[r["study_id"]] = r
                # Check if truncated: n_extracted > stored extractions
                n_ext = r.get("n_extracted", 0)
                n_stored = len([e for e in r.get("extracted", []) if not e.get("error")])
                if n_ext > n_stored:
                    truncated_ids.add(r["study_id"])
    print(f"Loaded {len(results)} results, {len(enm_ids)} extracted_no_match entries")
    print(f"  Truncated (need re-extraction): {len(truncated_ids)}")
    print(f"  Complete (re-match only):       {len(enm_ids) - len(truncated_ids)}")

    # Load entries with PDFs — only for truncated entries that need re-extraction
    all_entries = load_entries_with_pdfs()
    entry_by_id = {e["study_id"]: e for e in all_entries}
    retry_entries = [entry_by_id[sid] for sid in truncated_ids if sid in entry_by_id]
    print(f"Truncated entries with PDFs: {len(retry_entries)}")

    # Re-extract with full extraction storage
    retried = {}
    t_start = time.time()
    n = len(retry_entries)

    for i, entry in enumerate(retry_entries):
        sid = entry["study_id"]
        pdf_path = entry["pdf_path"]
        comparisons = entry.get("comparisons", [])

        try:
            # Run extraction
            extractions = extract_from_pdf(pdf_path)
            valid_extractions = [e for e in extractions if not e.get("error")]

            # Build cochrane_effects
            cochrane_effects = []
            for comp in comparisons:
                if comp.get("cochrane_effect") is not None:
                    data_type = comp.get("data_type")
                    if data_type is None:
                        data_type = infer_data_type(comp.get("raw_data"))
                    cochrane_effects.append({
                        "outcome": comp.get("outcome", ""),
                        "effect": comp["cochrane_effect"],
                        "ci_lower": comp.get("cochrane_ci_lower"),
                        "ci_upper": comp.get("cochrane_ci_upper"),
                        "data_type": data_type,
                        "raw_data": comp.get("raw_data"),
                    })

            # Run matching on ALL extractions
            best_match, match_method, closest_miss = match_extractions(
                valid_extractions, cochrane_effects
            )

            if best_match:
                status = "match"
            elif valid_extractions:
                status = "extracted_no_match"
            else:
                status = "no_extraction"

            retried[sid] = {
                "study_id": sid,
                "first_author": entry.get("first_author", ""),
                "year": entry.get("year", 0),
                "pmcid": entry.get("pmcid", ""),
                "status": status,
                "n_extracted": len(valid_extractions),
                "n_cochrane": len(cochrane_effects),
                "match": best_match,
                "match_method": match_method,
                "closest_miss": closest_miss,
                "extracted": valid_extractions[:50],  # Store up to 50
                "cochrane": cochrane_effects[:3],
            }
        except Exception as e:
            retried[sid] = {
                "study_id": sid,
                "status": "error",
                "error": f"reextract_enm: {str(e)}",
            }

        completed = i + 1
        if completed % 10 == 0 or retried[sid].get("status") == "match":
            elapsed = time.time() - t_start
            rate = completed / elapsed if elapsed > 0 else 0
            eta_min = (n - completed) / rate / 60 if rate > 0 else 0
            s = retried[sid].get("status", "?")
            match_info = ""
            if retried[sid].get("match"):
                m = retried[sid]["match"]
                match_info = f" ext={m['extracted']:.4f} coch={m['cochrane']:.4f} [{m.get('method','')}]"
            print(f"  [{completed}/{n}] {sid[:35]:35s} {s:20s}{match_info}  ({rate:.2f}/s, ETA {eta_min:.0f}m)")
            sys.stdout.flush()

    elapsed_total = time.time() - t_start
    print(f"\nRe-extracted {len(retried)} truncated entries in {elapsed_total/60:.1f} minutes")

    # Also re-match non-truncated entries (they have all extractions, just re-run matching)
    non_truncated = [sid for sid in enm_ids if sid not in truncated_ids]
    print(f"Re-matching {len(non_truncated)} non-truncated entries...")
    rematch_new = 0
    for sid in non_truncated:
        r = enm_results[sid]
        cochrane_effects = []
        for coch in r.get("cochrane", []):
            data_type = coch.get("data_type")
            if data_type is None:
                data_type = infer_data_type(coch.get("raw_data"))
            cochrane_effects.append({
                "outcome": coch.get("outcome", ""),
                "effect": coch["effect"],
                "ci_lower": coch.get("ci_lower"),
                "ci_upper": coch.get("ci_upper"),
                "data_type": data_type,
                "raw_data": coch.get("raw_data"),
            })

        valid_extractions = [e for e in r.get("extracted", []) if not e.get("error")]
        best_match, match_method, closest_miss = match_extractions(
            valid_extractions, cochrane_effects
        )

        if best_match:
            retried[sid] = dict(r)
            retried[sid]["status"] = "match"
            retried[sid]["match"] = best_match
            retried[sid]["match_method"] = match_method
            retried[sid]["closest_miss"] = closest_miss
            rematch_new += 1
    print(f"  Re-match found {rematch_new} new matches from existing extractions")

    # Merge back into results
    counts = {
        "match": 0, "extracted_no_match": 0, "no_extraction": 0,
        "no_cochrane_ref": 0, "error": 0,
    }
    method_counts = {}
    new_matches = []

    with open(EVAL_OUTPUT_FILE, "w", encoding='utf-8') as out_f:
        for r in results:
            sid = r["study_id"]
            if sid in retried:
                old_status = r.get("status", "")
                new_r = retried[sid]
                new_status = new_r.get("status", "")
                if new_status == "match" and old_status != "match":
                    new_matches.append({
                        "study_id": sid,
                        "method": new_r.get("match_method", ""),
                        "extracted": new_r["match"]["extracted"] if new_r.get("match") else None,
                        "cochrane": new_r["match"]["cochrane"] if new_r.get("match") else None,
                    })
                r = new_r

            status = r.get("status", "error")
            counts[status] = counts.get(status, 0) + 1
            if r.get("match_method"):
                method_counts[r["match_method"]] = method_counts.get(r["match_method"], 0) + 1
            out_f.write(json.dumps(r) + "\n")

    # Summary
    total = sum(counts.values())
    with_cochrane = total - counts.get("no_cochrane_ref", 0) - counts.get("error", 0)

    print(f"\n{'='*70}")
    print(f"REEXTRACT-ENM SUMMARY (v9.1)")
    print(f"{'='*70}")
    print(f"Total:                {total}")
    print(f"With Cochrane ref:    {with_cochrane}")
    print(f"  Match:              {counts['match']}  ({100*counts['match']/max(with_cochrane,1):.1f}%)")
    print(f"  Extracted no match: {counts['extracted_no_match']}  ({100*counts['extracted_no_match']/max(with_cochrane,1):.1f}%)")
    print(f"  No extraction:      {counts['no_extraction']}  ({100*counts['no_extraction']/max(with_cochrane,1):.1f}%)")
    print(f"  No Cochrane ref:    {counts['no_cochrane_ref']}")
    print(f"  Error:              {counts['error']}")

    if method_counts:
        print(f"\nMatch methods:")
        for method, cnt in sorted(method_counts.items(), key=lambda x: -x[1]):
            print(f"  {method:35s}  {cnt}")

    if new_matches:
        print(f"\n--- NEW MATCHES from re-extraction ({len(new_matches)}) ---")
        for nm in new_matches:
            ext_v = nm['extracted']
            coch_v = nm['cochrane']
            ext_str = f"{ext_v:8.3f}" if ext_v is not None else "    None"
            coch_str = f"{coch_v:8.3f}" if coch_v is not None else "    None"
            print(f"  {nm['study_id'][:35]:35s}  ext={ext_str}  coch={coch_str}  [{nm['method']}]")

    summary = {
        "total_evaluated": total,
        "with_cochrane_ref": with_cochrane,
        "counts": counts,
        "method_counts": method_counts,
        "match_rate": counts["match"] / max(with_cochrane, 1),
        "new_matches_from_reextraction": len(new_matches),
    }
    summary_file = MEGA_DIR / "mega_eval_v9_1_summary.json"
    with open(summary_file, "w", encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {EVAL_OUTPUT_FILE}")
    print(f"Saved: {summary_file}")


def reextract_noext():
    """Re-extract no_extraction entries using raw_data_extractor + advanced pipeline.

    For entries where the standard pipeline found nothing, this:
    1. Reads PDF text and runs raw_data_extractor to find two-group statistics
    2. Computes effects (OR, RR, RD, MD, SMD) from extracted raw data
    3. Also re-runs standard extraction with enable_advanced=True
    4. Matches all computed/extracted values against Cochrane references
    Writes v9.2.
    """
    print("=== REEXTRACT-NOEXT MODE: Re-extracting no_extraction entries ===")
    print("Using raw_data_extractor + advanced pipeline")
    print("=" * 70)

    # Try v9.1 first, fall back to v9
    EVAL_INPUT_FILE = MEGA_DIR / "mega_eval_v9_1.jsonl"
    if not EVAL_INPUT_FILE.exists():
        EVAL_INPUT_FILE = MEGA_DIR / "mega_eval_v9.jsonl"
    EVAL_OUTPUT_FILE = MEGA_DIR / "mega_eval_v9_2.jsonl"

    from src.core.raw_data_extractor import extract_raw_data

    # Load existing results
    results = []
    noext_ids = set()
    with open(EVAL_INPUT_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            results.append(r)
            if r.get("status") == "no_extraction":
                noext_ids.add(r["study_id"])
    print(f"Loaded {len(results)} results from {EVAL_INPUT_FILE.name}")
    print(f"No-extraction entries: {len(noext_ids)}")

    # Load entries with PDFs
    all_entries = load_entries_with_pdfs()
    entry_by_id = {e["study_id"]: e for e in all_entries}
    retry_entries = [entry_by_id[sid] for sid in noext_ids if sid in entry_by_id]
    print(f"Retry entries with PDFs: {len(retry_entries)}")

    # Process each entry
    retried = {}
    t_start = time.time()
    n = len(retry_entries)

    for i, entry in enumerate(retry_entries):
        sid = entry["study_id"]
        pdf_path = entry["pdf_path"]
        comparisons = entry.get("comparisons", [])

        try:
            import fitz
            # 1. Read PDF text
            pages_text = []
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text = page.get_text()
                    if text.strip():
                        pages_text.append(text)
            full_text = "\n\n".join(pages_text)

            # 2. Run raw_data_extractor on full text
            raw_extractions = extract_raw_data(full_text) if full_text.strip() else []

            # 3. Compute effects from raw data extractions
            computed_extractions = []
            for rde in raw_extractions:
                raw_dict = rde.to_raw_data_dict()
                if not raw_dict:
                    continue
                # Map raw_dict keys to compute functions format
                mapped = {}
                if "intervention_events" in raw_dict:
                    mapped["intervention_events"] = raw_dict["intervention_events"]
                    mapped["intervention_n"] = raw_dict["intervention_n"]
                    mapped["control_events"] = raw_dict["control_events"]
                    mapped["control_n"] = raw_dict["control_n"]
                if "intervention_mean" in raw_dict:
                    mapped["intervention_mean"] = raw_dict["intervention_mean"]
                    mapped["intervention_sd"] = raw_dict.get("intervention_sd")
                    mapped["intervention_n"] = raw_dict["intervention_n"]
                    mapped["control_mean"] = raw_dict["control_mean"]
                    mapped["control_sd"] = raw_dict.get("control_sd")
                    mapped["control_n"] = raw_dict["control_n"]

                # Compute effects from this raw data
                if "intervention_events" in mapped:
                    a = mapped["intervention_events"]
                    n1 = mapped["intervention_n"]
                    c = mapped["control_events"]
                    n2 = mapped["control_n"]
                    for fn, label in [(compute_or, "OR"), (compute_rr, "RR"), (compute_rd, "RD")]:
                        try:
                            result = fn(a, n1, c, n2)
                            if result and result.point_estimate is not None:
                                computed_extractions.append({
                                    "effect_type": label,
                                    "point_estimate": result.point_estimate,
                                    "ci_lower": result.ci_lower,
                                    "ci_upper": result.ci_upper,
                                    "confidence": rde.confidence * 0.8,
                                })
                        except Exception:
                            pass

                if "intervention_mean" in mapped:
                    m1 = mapped["intervention_mean"]
                    sd1 = mapped.get("intervention_sd")
                    n1 = mapped["intervention_n"]
                    m2 = mapped["control_mean"]
                    sd2 = mapped.get("control_sd")
                    n2 = mapped["control_n"]
                    if sd1 is not None and sd2 is not None:
                        try:
                            md_result = compute_md(m1, sd1, n1, m2, sd2, n2)
                            if md_result and md_result.point_estimate is not None:
                                computed_extractions.append({
                                    "effect_type": "MD",
                                    "point_estimate": md_result.point_estimate,
                                    "ci_lower": md_result.ci_lower,
                                    "ci_upper": md_result.ci_upper,
                                    "confidence": rde.confidence * 0.8,
                                })
                        except Exception:
                            pass
                        try:
                            smd_result = compute_smd(m1, sd1, n1, m2, sd2, n2)
                            if smd_result and smd_result.point_estimate is not None:
                                computed_extractions.append({
                                    "effect_type": "SMD",
                                    "point_estimate": smd_result.point_estimate,
                                    "ci_lower": smd_result.ci_lower,
                                    "ci_upper": smd_result.ci_upper,
                                    "confidence": rde.confidence * 0.8,
                                })
                        except Exception:
                            pass

            # 4. Also extract unlabeled values with CI from full text (v10)
            unlabeled = extract_unlabeled_values_with_ci(full_text)

            # 5. Combine raw-data-derived computations + unlabeled
            all_valid = computed_extractions + unlabeled

            # 6. Build cochrane_effects
            cochrane_effects = []
            for comp in comparisons:
                if comp.get("cochrane_effect") is not None:
                    data_type = comp.get("data_type")
                    if data_type is None:
                        data_type = infer_data_type(comp.get("raw_data"))
                    cochrane_effects.append({
                        "outcome": comp.get("outcome", ""),
                        "effect": comp["cochrane_effect"],
                        "ci_lower": comp.get("cochrane_ci_lower"),
                        "ci_upper": comp.get("cochrane_ci_upper"),
                        "data_type": data_type,
                        "raw_data": comp.get("raw_data"),
                    })

            # 7. Run matching
            best_match, match_method, closest_miss = match_extractions(
                all_valid, cochrane_effects
            )

            if best_match:
                status = "match"
            elif all_valid:
                status = "extracted_no_match"
            else:
                status = "no_extraction"

            retried[sid] = {
                "study_id": sid,
                "first_author": entry.get("first_author", ""),
                "year": entry.get("year", 0),
                "pmcid": entry.get("pmcid", ""),
                "status": status,
                "n_extracted": len(all_valid),
                "n_raw_data": len(raw_extractions),
                "n_computed": len(computed_extractions),
                "n_cochrane": len(cochrane_effects),
                "match": best_match,
                "match_method": match_method,
                "closest_miss": closest_miss,
                "extracted": all_valid[:50],
                "cochrane": cochrane_effects[:3],
            }
        except Exception as e:
            retried[sid] = {
                "study_id": sid,
                "status": "error",
                "error": f"reextract_noext: {str(e)}",
            }

        completed = i + 1
        if completed % 10 == 0 or retried[sid].get("status") == "match":
            elapsed = time.time() - t_start
            rate = completed / elapsed if elapsed > 0 else 0
            eta_min = (n - completed) / rate / 60 if rate > 0 else 0
            s = retried[sid].get("status", "?")
            n_raw = retried[sid].get("n_raw_data", 0)
            match_info = ""
            if retried[sid].get("match"):
                m = retried[sid]["match"]
                match_info = f" ext={m['extracted']:.4f} coch={m['cochrane']:.4f} [{m.get('method','')}]"
            print(f"  [{completed}/{n}] {sid[:30]:30s} {s:20s} raw={n_raw}{match_info}  ({rate:.2f}/s, ETA {eta_min:.0f}m)")
            sys.stdout.flush()

    elapsed_total = time.time() - t_start
    print(f"\nProcessed {len(retried)} entries in {elapsed_total/60:.1f} minutes")

    # Merge back
    counts = {
        "match": 0, "extracted_no_match": 0, "no_extraction": 0,
        "no_cochrane_ref": 0, "error": 0,
    }
    method_counts = {}
    new_matches = []
    conversions = {"to_match": 0, "to_extracted": 0, "still_no_extraction": 0}

    with open(EVAL_OUTPUT_FILE, "w", encoding='utf-8') as out_f:
        for r in results:
            sid = r["study_id"]
            if sid in retried:
                old_status = r.get("status", "")
                new_r = retried[sid]
                new_status = new_r.get("status", "")
                if new_status == "match" and old_status == "no_extraction":
                    conversions["to_match"] += 1
                    new_matches.append({
                        "study_id": sid,
                        "method": new_r.get("match_method", ""),
                        "extracted": new_r["match"]["extracted"] if new_r.get("match") else None,
                        "cochrane": new_r["match"]["cochrane"] if new_r.get("match") else None,
                    })
                elif new_status == "extracted_no_match" and old_status == "no_extraction":
                    conversions["to_extracted"] += 1
                elif new_status == "no_extraction":
                    conversions["still_no_extraction"] += 1
                r = new_r

            status = r.get("status", "error")
            counts[status] = counts.get(status, 0) + 1
            if r.get("match_method"):
                method_counts[r["match_method"]] = method_counts.get(r["match_method"], 0) + 1
            out_f.write(json.dumps(r) + "\n")

    # Summary
    total = sum(counts.values())
    with_cochrane = total - counts.get("no_cochrane_ref", 0) - counts.get("error", 0)

    print(f"\n{'='*70}")
    print(f"REEXTRACT-NOEXT SUMMARY (v9.2)")
    print(f"{'='*70}")
    print(f"Total:                {total}")
    print(f"With Cochrane ref:    {with_cochrane}")
    print(f"  Match:              {counts['match']}  ({100*counts['match']/max(with_cochrane,1):.1f}%)")
    print(f"  Extracted no match: {counts['extracted_no_match']}  ({100*counts['extracted_no_match']/max(with_cochrane,1):.1f}%)")
    print(f"  No extraction:      {counts['no_extraction']}  ({100*counts['no_extraction']/max(with_cochrane,1):.1f}%)")
    print(f"  No Cochrane ref:    {counts['no_cochrane_ref']}")
    print(f"  Error:              {counts['error']}")

    print(f"\nConversions from no_extraction:")
    print(f"  -> match:              {conversions['to_match']}")
    print(f"  -> extracted_no_match: {conversions['to_extracted']}")
    print(f"  -> still no_extraction:{conversions['still_no_extraction']}")

    if method_counts:
        print(f"\nMatch methods:")
        for method, cnt in sorted(method_counts.items(), key=lambda x: -x[1]):
            print(f"  {method:35s}  {cnt}")

    if new_matches:
        print(f"\n--- NEW MATCHES from raw data ({len(new_matches)}) ---")
        for nm in new_matches:
            ext_v = nm['extracted']
            coch_v = nm['cochrane']
            ext_str = f"{ext_v:8.3f}" if ext_v is not None else "    None"
            coch_str = f"{coch_v:8.3f}" if coch_v is not None else "    None"
            print(f"  {nm['study_id'][:35]:35s}  ext={ext_str}  coch={coch_str}  [{nm['method']}]")

    summary = {
        "total_evaluated": total,
        "with_cochrane_ref": with_cochrane,
        "counts": counts,
        "method_counts": method_counts,
        "match_rate": counts["match"] / max(with_cochrane, 1),
        "conversions": conversions,
        "new_matches_from_raw_data": len(new_matches),
    }
    summary_file = MEGA_DIR / "mega_eval_v9_2_summary.json"
    with open(summary_file, "w", encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {EVAL_OUTPUT_FILE}")
    print(f"Saved: {summary_file}")


def print_summary(counts, method_counts):
    """Print and save evaluation summary."""
    total_evaluated = sum(counts.values())
    with_cochrane = total_evaluated - counts.get("no_cochrane_ref", 0) - counts.get("error", 0)

    print(f"\n{'='*70}")
    print(f"EVALUATION SUMMARY (v2 - enhanced matching)")
    print(f"{'='*70}")
    print(f"Evaluated:            {total_evaluated}")
    print(f"With Cochrane ref:    {with_cochrane}")
    print(f"  Match:              {counts['match']}  ({100*counts['match']/max(with_cochrane,1):.1f}%)")
    print(f"  Extracted no match: {counts['extracted_no_match']}  ({100*counts['extracted_no_match']/max(with_cochrane,1):.1f}%)")
    print(f"  No extraction:      {counts['no_extraction']}  ({100*counts['no_extraction']/max(with_cochrane,1):.1f}%)")
    print(f"  No Cochrane ref:    {counts['no_cochrane_ref']}")
    print(f"  Error:              {counts['error']}")

    if method_counts:
        print(f"\nMatch methods:")
        for method, cnt in sorted(method_counts.items(), key=lambda x: -x[1]):
            print(f"  {method:30s}  {cnt}")

    summary = {
        "total_evaluated": total_evaluated,
        "with_cochrane_ref": with_cochrane,
        "counts": counts,
        "method_counts": method_counts,
        "match_rate": counts["match"] / max(with_cochrane, 1),
        "extraction_rate": (counts["match"] + counts["extracted_no_match"]) / max(with_cochrane, 1),
    }
    with open(MEGA_EVAL_SUMMARY, "w", encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {MEGA_EVAL_FILE}")


def llm_v10_retry():
    """Fresh outcome-guided LLM extraction on all v9.3 failures.

    Reads v9.3 results, filters to no_extraction + extracted_no_match,
    runs OutcomeGuidedExtractor for ALL Cochrane outcomes per entry,
    combines with existing extractions, and writes v10.
    """
    print("=== LLM V10 RETRY: Fresh outcome-guided extraction on v9.3 failures ===")
    print("=" * 70)

    EVAL_INPUT_FILE = MEGA_DIR / "mega_eval_v9_3.jsonl"
    EVAL_OUTPUT_FILE = MEGA_DIR / "mega_eval_v10.jsonl"

    if not EVAL_INPUT_FILE.exists():
        print(f"ERROR: {EVAL_INPUT_FILE} not found. Run v9.3 first.")
        return

    # Load existing v9.3 results
    results = []
    retry_ids = set()
    existing_results = {}
    with open(EVAL_INPUT_FILE, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line.strip())
            results.append(r)
            sid = r.get("study_id", "")
            existing_results[sid] = r
            if r.get("status") in ("no_extraction", "extracted_no_match"):
                retry_ids.add(sid)

    n_noext = sum(1 for r in results if r.get("status") == "no_extraction")
    n_enm = sum(1 for r in results if r.get("status") == "extracted_no_match")
    print(f"Loaded {len(results)} v9.3 results")
    print(f"Retry candidates: {len(retry_ids)} (no_extraction={n_noext}, extracted_no_match={n_enm})")

    # Load entries with PDFs
    all_entries = load_entries_with_pdfs()
    entry_by_id = {e["study_id"]: e for e in all_entries}
    retry_entries = [(entry_by_id[sid], existing_results[sid])
                     for sid in retry_ids if sid in entry_by_id]
    print(f"Retry entries with PDFs: {len(retry_entries)}")

    # Process sequentially (LLM calls are API-bound)
    t_start = time.time()
    n = len(retry_entries)
    retried = {}
    conversions = {"no_ext_to_match": 0, "no_ext_to_extracted": 0,
                   "enm_to_match": 0, "still_same": 0, "errors": 0}

    for i, (entry, existing) in enumerate(retry_entries):
        result = llm_guided_worker((entry, existing))

        if result is None:
            continue

        sid = result["study_id"]
        old_status = existing.get("status", "")
        new_status = result.get("status", "")

        if new_status == "match" and old_status == "no_extraction":
            conversions["no_ext_to_match"] += 1
        elif new_status == "match" and old_status == "extracted_no_match":
            conversions["enm_to_match"] += 1
        elif new_status == "extracted_no_match" and old_status == "no_extraction":
            conversions["no_ext_to_extracted"] += 1
        elif new_status == "error":
            conversions["errors"] += 1
        else:
            conversions["still_same"] += 1

        retried[sid] = result

        completed = i + 1
        if completed % 5 == 0 or new_status == "match":
            elapsed = time.time() - t_start
            rate = completed / elapsed if elapsed > 0 else 0
            eta_min = (n - completed) / rate / 60 if rate > 0 else 0
            match_info = ""
            if result.get("match") and isinstance(result["match"], dict):
                m = result["match"]
                match_info = f" ext={m.get('extracted',0):.4f} coch={m.get('cochrane',0):.4f} [{m.get('method','')}]"
            llm_count = result.get("llm_extractions", 0)
            new_matches = conversions["no_ext_to_match"] + conversions["enm_to_match"]
            print(f"  [{completed}/{n}] {sid[:30]:30s} {old_status:20s} -> {new_status:20s} llm={llm_count}{match_info}  (matches={new_matches}, {rate:.2f}/s, ETA {eta_min:.0f}m)")
            sys.stdout.flush()

    elapsed_total = time.time() - t_start
    print(f"\nProcessed {len(retried)} entries in {elapsed_total/60:.1f} minutes")
    print(f"\nConversions:")
    print(f"  no_extraction -> match:              {conversions['no_ext_to_match']}")
    print(f"  no_extraction -> extracted_no_match:  {conversions['no_ext_to_extracted']}")
    print(f"  extracted_no_match -> match:          {conversions['enm_to_match']}")
    print(f"  Still same:                           {conversions['still_same']}")
    print(f"  Errors:                               {conversions['errors']}")

    # Merge into final output
    counts = {
        "match": 0, "extracted_no_match": 0, "no_extraction": 0,
        "no_cochrane_ref": 0, "error": 0,
    }
    method_counts = {}

    with open(EVAL_OUTPUT_FILE, "w", encoding='utf-8') as out_f:
        for r in results:
            sid = r.get("study_id", "")
            if sid in retried:
                r = retried[sid]
            status = r.get("status", "error")
            counts[status] = counts.get(status, 0) + 1
            if r.get("match_method"):
                method_counts[r["match_method"]] = method_counts.get(r["match_method"], 0) + 1
            out_f.write(json.dumps(r) + "\n")

    # Summary
    total = sum(counts.values())
    with_cochrane = total - counts.get("no_cochrane_ref", 0) - counts.get("error", 0)
    new_total_matches = conversions["no_ext_to_match"] + conversions["enm_to_match"]

    print(f"\n{'='*70}")
    print(f"LLM V10 SUMMARY")
    print(f"{'='*70}")
    print(f"Total:                {total}")
    print(f"With Cochrane ref:    {with_cochrane}")
    print(f"  Match:              {counts['match']}  ({100*counts['match']/max(with_cochrane,1):.1f}%)")
    print(f"  Extracted no match: {counts['extracted_no_match']}  ({100*counts['extracted_no_match']/max(with_cochrane,1):.1f}%)")
    print(f"  No extraction:      {counts['no_extraction']}  ({100*counts['no_extraction']/max(with_cochrane,1):.1f}%)")
    print(f"  No Cochrane ref:    {counts['no_cochrane_ref']}")
    print(f"  Error:              {counts['error']}")
    print(f"\n  NEW matches from LLM: {new_total_matches}")

    if method_counts:
        print(f"\nMatch methods:")
        for method, cnt in sorted(method_counts.items(), key=lambda x: -x[1]):
            print(f"  {method:35s}  {cnt}")

    summary = {
        "version": "v10",
        "total_entries": total,
        "total_with_cochrane": with_cochrane,
        "matches": counts["match"],
        "match_rate": round(100 * counts["match"] / max(with_cochrane, 1), 1),
        "no_extraction": counts["no_extraction"],
        "extracted_no_match": counts["extracted_no_match"],
        "no_cochrane_ref": counts.get("no_cochrane_ref", 0),
        "error": counts.get("error", 0),
        "llm_new_matches": new_total_matches,
        "llm_entries_processed": len(retried),
        "conversions": conversions,
        "method_counts": method_counts,
    }
    summary_file = MEGA_DIR / "mega_eval_v10_summary.json"
    with open(summary_file, "w", encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {EVAL_OUTPUT_FILE}")
    print(f"Saved: {summary_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate extractor v2 on mega gold PDFs")
    parser.add_argument("--batch", type=int, default=100, help="Number of PDFs to evaluate")
    parser.add_argument("--resume", action="store_true", help="Skip already evaluated")
    parser.add_argument("--rematch", action="store_true",
                        help="Re-apply matching logic to existing results without re-extracting")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of parallel workers (default 1, try 4 for ~4x speedup)")
    parser.add_argument("--advanced", action="store_true",
                        help="Enable advanced extraction (Table Transformer + OCR)")
    parser.add_argument("--llm", action="store_true",
                        help="Enable LLM extraction (non-deterministic, requires API key)")
    parser.add_argument("--retry-no-extraction", action="store_true",
                        help="Re-run only no_extraction entries with advanced pipeline")
    parser.add_argument("--llm-guided", action="store_true",
                        help="Re-run failed entries with outcome-guided Claude LLM extraction")
    parser.add_argument("--reextract-enm", action="store_true",
                        help="Re-extract extracted_no_match entries with full extraction storage")
    parser.add_argument("--reextract-noext", action="store_true",
                        help="Re-extract no_extraction entries using raw_data_extractor + advanced")
    parser.add_argument("--llm-v10", action="store_true",
                        help="Fresh outcome-guided LLM extraction on all v9.3 failures")
    args = parser.parse_args()

    # Configure pipeline kwargs for workers
    global _pipeline_kwargs
    _pipeline_kwargs = {
        "enable_advanced": args.advanced,
        "enable_llm": args.llm,
    }

    if args.rematch:
        rematch_existing()
        return

    if args.retry_no_extraction:
        # Force advanced extraction on for retry mode
        _pipeline_kwargs["enable_advanced"] = True
        _pipeline_kwargs["enable_llm"] = args.llm
        retry_no_extraction()
        return

    if args.llm_guided:
        llm_guided_retry()
        return

    if args.reextract_enm:
        # Standard pipeline: fast, stores ALL extractions (up to 50) instead of top 5
        # Use --advanced flag to also enable Table Transformer if desired
        reextract_enm()
        return

    if args.reextract_noext:
        # Raw data extractor is fast (regex-only); use --advanced if ML pipeline desired
        reextract_noext()
        return

    if args.llm_v10:
        llm_v10_retry()
        return

    entries = load_entries_with_pdfs()
    print(f"PDFs available: {len(entries)}")

    # Load existing evaluations
    already_evaluated = set()
    if args.resume and MEGA_EVAL_FILE.exists():
        with open(MEGA_EVAL_FILE, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    already_evaluated.add(ev["study_id"])
                except json.JSONDecodeError:
                    continue
        print(f"Already evaluated: {len(already_evaluated)}")

    to_evaluate = [e for e in entries if e["study_id"] not in already_evaluated]
    n = min(args.batch, len(to_evaluate))
    batch = to_evaluate[:n]
    print(f"To evaluate: {n} (workers: {args.workers})")
    print("=" * 70)

    counts = {
        "match": 0, "extracted_no_match": 0, "no_extraction": 0,
        "no_cochrane_ref": 0, "error": 0,
    }
    method_counts = {}

    mode = "a" if args.resume else "w"
    eval_file = open(MEGA_EVAL_FILE, mode, encoding='utf-8')
    completed = 0
    t_start = time.time()
    try:  # ensure eval_file is closed on any exception
        if args.workers > 1:
            # === Parallel mode ===
            with ProcessPoolExecutor(max_workers=args.workers,
                                     initializer=_init_worker,
                                     initargs=(_pipeline_kwargs,)) as pool:
                future_to_entry = {
                    pool.submit(evaluate_entry_worker, entry): entry
                    for entry in batch
                }
                for future in as_completed(future_to_entry):
                    entry = future_to_entry[future]
                    completed += 1
                    try:
                        result = future.result()
                    except Exception as e:
                        result = {
                            "study_id": entry["study_id"],
                            "status": "error",
                            "error": str(e),
                        }

                    status = result["status"]
                    counts[status] = counts.get(status, 0) + 1

                    if result.get("match_method"):
                        mm = result["match_method"]
                        method_counts[mm] = method_counts.get(mm, 0) + 1

                    eval_file.write(json.dumps(result) + "\n")
                    eval_file.flush()

                    # Progress: print every 10 entries, or on match
                    if completed % 10 == 0 or status == "match":
                        elapsed = time.time() - t_start
                        rate = completed / elapsed if elapsed > 0 else 0
                        eta_min = (n - completed) / rate / 60 if rate > 0 else 0
                        match_info = ""
                        if result.get("match"):
                            m = result["match"]
                            match_info = f" ext={m['extracted']} coch={m['cochrane']} [{m.get('method','')}]"
                        print(f"  [{completed}/{n}] {result.get('study_id','?')[:30]:30s} {status:20s}{match_info}  ({rate:.1f}/s, ETA {eta_min:.0f}m)")
                        sys.stdout.flush()
        else:
            # === Sequential mode (original) ===
            for i, entry in enumerate(batch):
                completed += 1
                result = evaluate_entry_worker(entry)

                status = result["status"]
                counts[status] = counts.get(status, 0) + 1

                if result.get("match_method"):
                    mm = result["match_method"]
                    method_counts[mm] = method_counts.get(mm, 0) + 1

                eval_file.write(json.dumps(result) + "\n")
                eval_file.flush()

                if completed % 10 == 0 or status == "match":
                    elapsed = time.time() - t_start
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta_min = (n - completed) / rate / 60 if rate > 0 else 0
                    match_info = ""
                    if result.get("match"):
                        m = result["match"]
                        match_info = f" ext={m['extracted']} coch={m['cochrane']} [{m.get('method','')}]"
                    print(f"  [{completed}/{n}] {result.get('study_id','?')[:30]:30s} {status:20s}{match_info}  ({rate:.1f}/s, ETA {eta_min:.0f}m)")
                    sys.stdout.flush()
    finally:
        eval_file.close()
    elapsed_total = time.time() - t_start
    print(f"\nCompleted {completed} entries in {elapsed_total/60:.1f} minutes ({completed/elapsed_total:.2f}/s)")
    print_summary(counts, method_counts)


if __name__ == "__main__":
    main()
