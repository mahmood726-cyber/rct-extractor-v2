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
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project to path
PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
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
    """Load matched entries that have downloaded PDFs."""
    entries = []
    with open(MEGA_MATCHED_FILE) as f:
        for line in f:
            e = json.loads(line)
            if not e.get("pmcid"):
                continue
            safe_name = e["study_id"].replace(" ", "_").replace("/", "_")
            pdf_path = PDF_DIR / f"{safe_name}_{e['pmcid']}.pdf"
            if pdf_path.exists():
                e["pdf_path"] = str(pdf_path)
                entries.append(e)
    return entries


def extract_from_pdf(pdf_path):
    """Run the extraction pipeline on a PDF."""
    try:
        from src.core.pdf_extraction_pipeline import PDFExtractionPipeline
        pipeline = PDFExtractionPipeline()
        result = pipeline.extract_from_pdf(pdf_path)
        if result and result.effect_estimates:
            return [{
                "effect_type": str(e.effect_type) if hasattr(e, 'effect_type') else str(getattr(e, 'type', '')),
                "point_estimate": getattr(e, 'point_estimate', None) or getattr(e, 'value', None),
                "ci_lower": getattr(e, 'ci_lower', None),
                "ci_upper": getattr(e, 'ci_upper', None),
                "confidence": getattr(e, 'calibrated_confidence', None) or getattr(e, 'confidence', None),
            } for e in result.effect_estimates]
        return []
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


def values_match(extracted, cochrane, tolerance=0.05):
    """Check if extracted value matches Cochrane value within relative tolerance."""
    if extracted is None or cochrane is None:
        return False
    try:
        ext = float(extracted)
        coch = float(cochrane)
        if coch == 0:
            return abs(ext) < 0.01
        return abs(ext - coch) / abs(coch) <= tolerance
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
        if or_result:
            results["OR"] = or_result

        rr_result = compute_rr(a, n1, c, n2)
        if rr_result:
            results["RR"] = rr_result

        rd_result = compute_rd(a, n1, c, n2)
        if rd_result:
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
            if md_result:
                results["MD"] = md_result

            smd_result = compute_smd(m1, sd1, n1, m2, sd2, n2)
            if smd_result:
                results["SMD"] = smd_result

    return results


def is_same_type(ext_type, data_type):
    """Check if extracted effect type is compatible with Cochrane data type."""
    if data_type == "binary" and ext_type in RATIO_TYPES:
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


def rematch_existing():
    """Re-apply matching logic to existing eval results without re-extracting.

    Reads mega_eval_v2.jsonl, applies updated matching tiers, writes mega_eval_v3.jsonl.
    """
    print("=== REMATCH MODE: Re-applying matching logic to existing results ===")

    EVAL_V3_FILE = MEGA_DIR / "mega_eval_v3.jsonl"

    results = []
    with open(MEGA_EVAL_FILE) as f:
        for line in f:
            results.append(json.loads(line))
    print(f"Loaded {len(results)} existing results")

    counts = {
        "match": 0, "extracted_no_match": 0, "no_extraction": 0,
        "no_cochrane_ref": 0, "error": 0,
    }
    method_counts = {}
    new_matches = []  # Track newly matched studies

    with open(EVAL_V3_FILE, "w") as out_f:
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
    print(f"REMATCH SUMMARY (v3 matching)")
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
    summary_file = MEGA_DIR / "mega_eval_v3_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {EVAL_V3_FILE}")
    print(f"Saved: {summary_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate extractor v2 on mega gold PDFs")
    parser.add_argument("--batch", type=int, default=100, help="Number of PDFs to evaluate")
    parser.add_argument("--resume", action="store_true", help="Skip already evaluated")
    parser.add_argument("--rematch", action="store_true",
                        help="Re-apply matching logic to existing results without re-extracting")
    args = parser.parse_args()

    if args.rematch:
        rematch_existing()
        return

    entries = load_entries_with_pdfs()
    print(f"PDFs available: {len(entries)}")

    # Load existing evaluations
    already_evaluated = set()
    if args.resume and MEGA_EVAL_FILE.exists():
        with open(MEGA_EVAL_FILE) as f:
            for line in f:
                ev = json.loads(line)
                already_evaluated.add(ev["study_id"])
        print(f"Already evaluated: {len(already_evaluated)}")

    to_evaluate = [e for e in entries if e["study_id"] not in already_evaluated]
    n = min(args.batch, len(to_evaluate))
    print(f"To evaluate: {n}")
    print("=" * 70)

    counts = {
        "match": 0, "extracted_no_match": 0, "no_extraction": 0,
        "no_cochrane_ref": 0, "error": 0,
    }
    method_counts = {}

    # Write results incrementally (append mode)
    mode = "a" if args.resume else "w"
    eval_file = open(MEGA_EVAL_FILE, mode)

    for i, entry in enumerate(to_evaluate[:n]):
        try:
            result = evaluate_entry(entry)
            result["study_id"] = entry["study_id"]
            result["first_author"] = entry.get("first_author", "")
            result["year"] = entry.get("year", 0)
            result["pmcid"] = entry.get("pmcid", "")

            status = result["status"]
            counts[status] = counts.get(status, 0) + 1

            if result.get("match_method"):
                mm = result["match_method"]
                method_counts[mm] = method_counts.get(mm, 0) + 1

            # Write immediately
            eval_file.write(json.dumps(result) + "\n")
            eval_file.flush()

            if (i + 1) % 10 == 0 or status == "match":
                match_info = ""
                if result.get("match"):
                    m = result["match"]
                    match_info = f" ext={m['extracted']} coch={m['cochrane']} [{m.get('method','')}]"
                print(f"  [{i+1}/{n}] {entry['study_id'][:30]:30s} {status:20s}{match_info}")
                sys.stdout.flush()

        except Exception as e:
            counts["error"] += 1
            eval_file.write(json.dumps({
                "study_id": entry["study_id"],
                "status": "error",
                "error": str(e),
            }) + "\n")
            eval_file.flush()

    eval_file.close()

    # Summary
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

    # Save summary
    summary = {
        "total_evaluated": total_evaluated,
        "with_cochrane_ref": with_cochrane,
        "counts": counts,
        "method_counts": method_counts,
        "match_rate": counts["match"] / max(with_cochrane, 1),
        "extraction_rate": (counts["match"] + counts["extracted_no_match"]) / max(with_cochrane, 1),
    }
    with open(MEGA_EVAL_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {MEGA_EVAL_FILE}")


if __name__ == "__main__":
    main()
