#!/usr/bin/env python
"""
Analyze 'extracted_no_match' entries from mega_eval_v9_2.jsonl
Diagnoses WHY extracted values fail to match any Cochrane reference.
"""

import json
import sys
import io
import math
from collections import Counter, defaultdict

# Windows cp1252 safety
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

EVAL_FILE = r"C:\Users\user\rct-extractor-v2\gold_data\mega\mega_eval_v9_2.jsonl"

RATIO_TYPES = {"OR", "RR", "HR", "IRR", "RRR"}
DIFF_TYPES = {"MD", "SMD", "RD", "ARD"}

# Distance buckets
BUCKETS = [
    ("within_35pct", 0.35),
    ("within_50pct", 0.50),
    ("within_100pct", 1.00),
    ("within_200pct", 2.00),
    ("within_500pct", 5.00),
]


def clean_effect_type(et):
    """EffectType.OR -> OR"""
    if et and "." in et:
        return et.split(".")[-1]
    return et or "?"


def is_ratio(et):
    return clean_effect_type(et) in RATIO_TYPES


def is_diff(et):
    return clean_effect_type(et) in DIFF_TYPES


def compute_all_distances(extracted_list, cochrane_list):
    """
    For every (extracted, cochrane) pair compute:
      - direct rel_distance
      - reciprocal rel_distance (for ratio types)
      - sign-flipped rel_distance
    Returns sorted list of (rel_dist, ext_val, coch_val, ext_type, data_type, outcome, method)
    """
    results = []
    for ext in extracted_list:
        pe = ext.get("point_estimate")
        if pe is None:
            continue
        et = clean_effect_type(ext.get("effect_type"))
        for coch in cochrane_list:
            cv = coch.get("effect")
            if cv is None:
                continue
            dt = coch.get("data_type")
            outcome = coch.get("outcome", "")

            # Direct distance
            denom = abs(cv) if abs(cv) > 1e-9 else 1e-9
            rd = abs(pe - cv) / denom
            results.append((rd, pe, cv, et, dt, outcome, "direct"))

            # Reciprocal (ratio types)
            if et in RATIO_TYPES and pe != 0:
                recip = 1.0 / pe
                rd_recip = abs(recip - cv) / denom
                results.append((rd_recip, recip, cv, et, dt, outcome, "reciprocal"))

            # Sign-flipped
            rd_sign = abs(-pe - cv) / denom
            results.append((rd_sign, -pe, cv, et, dt, outcome, "sign_flip"))

            # Absolute value match (both positive)
            rd_abs = abs(abs(pe) - abs(cv)) / max(abs(cv), 1e-9)
            results.append((rd_abs, abs(pe), cv, et, dt, outcome, "abs_match"))

    results.sort(key=lambda x: x[0])
    return results


def categorize_failure(entry, all_dists):
    """
    Categorize why the match failed.
    Returns (category, explanation)
    """
    if not all_dists:
        return "no_comparison", "No valid extracted values or no cochrane values"

    best_rd, best_ext, best_coch, best_et, best_dt, best_outcome, best_method = all_dists[0]

    # Check type mismatch
    ext_is_ratio = best_et in RATIO_TYPES
    coch_is_binary = best_dt == "binary"
    coch_is_continuous = best_dt == "continuous"

    # Type mismatch: diff type extracted, but cochrane is binary (expects ratio)
    if best_et in DIFF_TYPES and coch_is_binary:
        return "type_mismatch_diff_vs_binary", f"Extracted {best_et} but Cochrane expects binary (ratio type)"

    # Type mismatch: ratio type extracted, but cochrane is continuous (expects diff)
    if ext_is_ratio and coch_is_continuous:
        return "type_mismatch_ratio_vs_continuous", f"Extracted {best_et} but Cochrane expects continuous (diff type)"

    # Close miss (within 50% on the best pairing)
    if best_rd <= 0.50:
        return "close_miss", f"Best distance {best_rd:.3f} ({best_method}) -- just beyond tolerance"

    # Moderate miss
    if best_rd <= 1.0:
        return "moderate_miss", f"Best distance {best_rd:.3f} ({best_method}) -- within 2x but not close"

    # Check if multiple cochrane outcomes and the extracted value doesn't match ANY
    # This could be 'wrong outcome'
    n_coch = len(entry.get("cochrane", []))
    n_ext = len(entry.get("extracted", []))

    # Wild miss
    if best_rd > 5.0:
        return "wildly_off", f"Best distance {best_rd:.1f} ({best_method}) -- completely different value"

    # Default: wrong outcome or adjusted vs unadjusted
    return "wrong_value", f"Best distance {best_rd:.3f} ({best_method}) -- likely different outcome/analysis"


def compute_bias_direction(entry):
    """
    Is the extracted value systematically higher or lower than cochrane?
    For ratio types, compare on log scale. For diff types, compare directly.
    Returns 'higher', 'lower', or 'mixed'
    """
    cm = entry.get("closest_miss")
    if not cm:
        return None
    ext_val = cm.get("extracted")
    coch_val = cm.get("cochrane")
    if ext_val is None or coch_val is None:
        return None

    et = clean_effect_type(cm.get("ext_type"))
    if et in RATIO_TYPES:
        # Compare on log scale
        if ext_val > 0 and coch_val > 0:
            if math.log(ext_val) > math.log(coch_val):
                return "higher"
            else:
                return "lower"
    else:
        if ext_val > coch_val:
            return "higher"
        else:
            return "lower"
    return None


def main():
    with open(EVAL_FILE) as f:
        entries = [json.loads(line) for line in f]

    enm_entries = [e for e in entries if e["status"] == "extracted_no_match"]
    total = len(entries)
    n_enm = len(enm_entries)

    print("=" * 90)
    print(f"ANALYSIS OF 'extracted_no_match' ENTRIES")
    print(f"Total entries: {total}, extracted_no_match: {n_enm}")
    print("=" * 90)

    # =========================================================================
    # 1. Compute distances for all entries
    # =========================================================================
    print("\n" + "=" * 90)
    print("SECTION 1: DISTANCE ANALYSIS (best possible distance per entry)")
    print("=" * 90)

    entry_analysis = []
    for entry in enm_entries:
        all_dists = compute_all_distances(entry["extracted"], entry["cochrane"])
        category, explanation = categorize_failure(entry, all_dists)
        bias = compute_bias_direction(entry)

        # Also get closest_miss from the eval file itself
        cm = entry.get("closest_miss", {})
        cm_rd = cm.get("rel_distance") if cm else None

        # Best distance considering all methods
        best_rd = all_dists[0][0] if all_dists else None
        best_method = all_dists[0][6] if all_dists else None

        entry_analysis.append({
            "entry": entry,
            "all_dists": all_dists,
            "best_rd": best_rd,
            "best_method": best_method,
            "cm_rd": cm_rd,
            "category": category,
            "explanation": explanation,
            "bias": bias,
        })

    # Distribution of ORIGINAL closest_miss rel_distance
    cm_distances = [ea["cm_rd"] for ea in entry_analysis if ea["cm_rd"] is not None]
    cm_distances.sort()

    print(f"\nOriginal closest_miss rel_distance (from eval file, direct only):")
    print(f"  Count: {len(cm_distances)}, Missing: {n_enm - len(cm_distances)}")
    if cm_distances:
        print(f"  Min: {cm_distances[0]:.4f}")
        print(f"  25th: {cm_distances[len(cm_distances)//4]:.4f}")
        print(f"  Median: {cm_distances[len(cm_distances)//2]:.4f}")
        print(f"  75th: {cm_distances[3*len(cm_distances)//4]:.4f}")
        print(f"  Max: {cm_distances[-1]:.4f}")

    # Distribution of BEST distance (including reciprocal, sign-flip, abs)
    best_distances = [ea["best_rd"] for ea in entry_analysis if ea["best_rd"] is not None]
    best_distances.sort()

    print(f"\nBest possible distance (including reciprocal/sign-flip/abs methods):")
    print(f"  Count: {len(best_distances)}, Missing: {n_enm - len(best_distances)}")
    if best_distances:
        print(f"  Min: {best_distances[0]:.4f}")
        print(f"  25th: {best_distances[len(best_distances)//4]:.4f}")
        print(f"  Median: {best_distances[len(best_distances)//2]:.4f}")
        print(f"  75th: {best_distances[3*len(best_distances)//4]:.4f}")
        print(f"  Max: {best_distances[-1]:.4f}")

    # =========================================================================
    # 2. Histogram of relative distances
    # =========================================================================
    print("\n" + "=" * 90)
    print("SECTION 2: DISTANCE HISTOGRAM")
    print("=" * 90)

    print("\n--- Original rel_distance (direct comparison only) ---")
    buckets_cm = Counter()
    for d in cm_distances:
        placed = False
        for label, thresh in BUCKETS:
            if d <= thresh:
                buckets_cm[label] += 1
                placed = True
                break
        if not placed:
            buckets_cm["over_500pct"] += 1

    cumulative = 0
    for label, thresh in BUCKETS:
        c = buckets_cm.get(label, 0)
        cumulative += c
        pct = 100.0 * cumulative / len(cm_distances) if cm_distances else 0
        bar = "#" * c
        print(f"  {label:>16s}: {c:4d}  (cumul {cumulative:4d}, {pct:5.1f}%)  {bar}")
    c = buckets_cm.get("over_500pct", 0)
    cumulative += c
    pct = 100.0 * cumulative / len(cm_distances) if cm_distances else 0
    print(f"  {'over_500pct':>16s}: {c:4d}  (cumul {cumulative:4d}, {pct:5.1f}%)")

    print("\n--- Best possible distance (all methods) ---")
    buckets_best = Counter()
    for d in best_distances:
        placed = False
        for label, thresh in BUCKETS:
            if d <= thresh:
                buckets_best[label] += 1
                placed = True
                break
        if not placed:
            buckets_best["over_500pct"] += 1

    cumulative = 0
    for label, thresh in BUCKETS:
        c = buckets_best.get(label, 0)
        cumulative += c
        pct = 100.0 * cumulative / len(best_distances) if best_distances else 0
        bar = "#" * c
        print(f"  {label:>16s}: {c:4d}  (cumul {cumulative:4d}, {pct:5.1f}%)  {bar}")
    c = buckets_best.get("over_500pct", 0)
    cumulative += c
    pct = 100.0 * cumulative / len(best_distances) if best_distances else 0
    print(f"  {'over_500pct':>16s}: {c:4d}  (cumul {cumulative:4d}, {pct:5.1f}%)")

    # NEW: fine-grained 35% tier analysis
    print("\n--- Fine-grained near-miss analysis (best possible distance) ---")
    fine_buckets = [
        ("0-10%", 0.10),
        ("10-15%", 0.15),
        ("15-20%", 0.20),
        ("20-25%", 0.25),
        ("25-30%", 0.30),
        ("30-35%", 0.35),
        ("35-40%", 0.40),
        ("40-50%", 0.50),
    ]
    prev_thresh = 0
    for label, thresh in fine_buckets:
        c = sum(1 for d in best_distances if prev_thresh < d <= thresh)
        bar = "#" * c
        print(f"  {label:>10s}: {c:4d}  {bar}")
        prev_thresh = thresh

    # =========================================================================
    # 3. Failure categories
    # =========================================================================
    print("\n" + "=" * 90)
    print("SECTION 3: FAILURE CATEGORIZATION")
    print("=" * 90)

    cat_counts = Counter()
    for ea in entry_analysis:
        cat_counts[ea["category"]] += 1

    print(f"\n{'Category':<40s} {'Count':>5s} {'Pct':>6s}")
    print("-" * 55)
    for cat, c in cat_counts.most_common():
        pct = 100.0 * c / n_enm
        print(f"  {cat:<38s} {c:5d} {pct:5.1f}%")

    # Detailed type mismatch analysis
    print("\n--- Type mismatch detail ---")
    type_mismatch_combos = Counter()
    for ea in entry_analysis:
        if "type_mismatch" in ea["category"]:
            e = ea["entry"]
            cm = e.get("closest_miss", {})
            et = clean_effect_type(cm.get("ext_type"))
            dt = cm.get("data_type", "None")
            type_mismatch_combos[f"{et} -> {dt}"] += 1
    for combo, c in type_mismatch_combos.most_common():
        print(f"  {combo}: {c}")

    # =========================================================================
    # 4. Representative examples (20)
    # =========================================================================
    print("\n" + "=" * 90)
    print("SECTION 4: 20 REPRESENTATIVE EXAMPLES")
    print("=" * 90)

    # Pick examples from each category
    cat_examples = defaultdict(list)
    for ea in entry_analysis:
        cat_examples[ea["category"]].append(ea)

    shown = 0
    for cat in ["close_miss", "type_mismatch_diff_vs_binary", "type_mismatch_ratio_vs_continuous",
                 "moderate_miss", "wrong_value", "wildly_off", "no_comparison"]:
        examples = cat_examples.get(cat, [])
        # Sort by best_rd so we see the most interesting ones
        examples.sort(key=lambda x: x["best_rd"] if x["best_rd"] is not None else 999)
        take = min(max(1, 20 - shown), len(examples), 4)  # up to 4 per category
        for ea in examples[:take]:
            if shown >= 20:
                break
            shown += 1
            e = ea["entry"]
            cm = e.get("closest_miss", {})
            extracted_summary = []
            for ext in e["extracted"]:
                et = clean_effect_type(ext.get("effect_type"))
                pe = ext.get("point_estimate")
                ci_lo = ext.get("ci_lower")
                ci_hi = ext.get("ci_upper")
                conf = ext.get("confidence", 0)
                if pe is not None:
                    ci_str = f" [{ci_lo}, {ci_hi}]" if ci_lo is not None else ""
                    extracted_summary.append(f"{et}={pe:.4g}{ci_str} (conf={conf:.2f})")
                else:
                    extracted_summary.append(f"{et}=None")

            cochrane_summary = []
            for coch in e["cochrane"]:
                oc = coch.get("outcome", "")[:60]
                ef = coch.get("effect")
                dt = coch.get("data_type", "?")
                ci_lo = coch.get("ci_lower")
                ci_hi = coch.get("ci_upper")
                cochrane_summary.append(f"{oc} | {dt} | effect={ef} [{ci_lo}, {ci_hi}]")

            print(f"\n  [{shown}] {e['study_id']}  -- CATEGORY: {ea['category']}")
            print(f"      N_extracted: {e['n_extracted']}, N_cochrane: {e['n_cochrane']}")
            print(f"      Best rel_distance: {ea['best_rd']:.4f} (via {ea['best_method']})" if ea['best_rd'] else "      Best rel_distance: N/A")
            print(f"      Original closest_miss rel_dist: {ea['cm_rd']:.4f}" if ea['cm_rd'] else "      Original closest_miss: N/A")
            print(f"      Explanation: {ea['explanation']}")
            print(f"      Extracted:")
            for es in extracted_summary:
                print(f"        - {es}")
            print(f"      Cochrane:")
            for cs in cochrane_summary:
                print(f"        - {cs}")
        if shown >= 20:
            break

    # =========================================================================
    # 5. Pattern analysis
    # =========================================================================
    print("\n" + "=" * 90)
    print("SECTION 5: PATTERN ANALYSIS")
    print("=" * 90)

    # 5a. Failure rate by data_type
    print("\n--- 5a. Failure rate by Cochrane data_type ---")
    # Need to compare against overall data_type distribution
    all_data_types = Counter()
    enm_data_types = Counter()
    for e in entries:
        for coch in e.get("cochrane", []):
            dt = coch.get("data_type", "None")
            all_data_types[dt] += 1
            if e["status"] == "extracted_no_match":
                enm_data_types[dt] += 1

    print(f"  {'Data Type':<15s} {'All':>6s} {'ENM':>6s} {'ENM Rate':>10s}")
    print("  " + "-" * 40)
    for dt in sorted(all_data_types.keys(), key=lambda x: str(x)):
        a = all_data_types[dt]
        e = enm_data_types.get(dt, 0)
        rate = 100.0 * e / a if a > 0 else 0
        print(f"  {str(dt):<15s} {a:6d} {e:6d} {rate:9.1f}%")

    # 5b. Failure rate by extracted effect type
    print("\n--- 5b. ENM rate by extracted effect type ---")
    all_ext_types = Counter()
    enm_ext_types = Counter()
    for e in entries:
        if e.get("n_extracted", 0) > 0:
            for ext in e.get("extracted", []):
                et = clean_effect_type(ext.get("effect_type"))
                all_ext_types[et] += 1
                if e["status"] == "extracted_no_match":
                    enm_ext_types[et] += 1

    print(f"  {'Effect Type':<10s} {'All':>6s} {'ENM':>6s} {'ENM Rate':>10s}")
    print("  " + "-" * 35)
    for et in sorted(all_ext_types.keys(), key=lambda x: -all_ext_types[x]):
        a = all_ext_types[et]
        e = enm_ext_types.get(et, 0)
        rate = 100.0 * e / a if a > 0 else 0
        print(f"  {et:<10s} {a:6d} {e:6d} {rate:9.1f}%")

    # 5c. Bias direction
    print("\n--- 5c. Systematic bias direction ---")
    bias_counts = Counter()
    for ea in entry_analysis:
        b = ea["bias"]
        bias_counts[b if b else "unknown"] += 1
    for b, c in bias_counts.most_common():
        pct = 100.0 * c / n_enm
        print(f"  {b:<10s}: {c:4d} ({pct:.1f}%)")

    # 5d. Bias by effect type
    print("\n--- 5d. Bias direction by extracted effect type ---")
    bias_by_type = defaultdict(Counter)
    for ea in entry_analysis:
        cm = ea["entry"].get("closest_miss", {})
        et = clean_effect_type(cm.get("ext_type")) if cm else "?"
        b = ea["bias"] if ea["bias"] else "unknown"
        bias_by_type[et][b] += 1

    for et in sorted(bias_by_type.keys(), key=lambda x: -sum(bias_by_type[x].values())):
        counts = bias_by_type[et]
        total_et = sum(counts.values())
        h = counts.get("higher", 0)
        l = counts.get("lower", 0)
        u = counts.get("unknown", 0)
        print(f"  {et:<6s}: higher={h:3d} lower={l:3d} unknown={u:3d}  (total={total_et})")

    # 5e. Number of extractions vs match rate
    print("\n--- 5e. N_extracted distribution for ENM vs matched ---")
    n_ext_match = Counter()
    n_ext_enm = Counter()
    for e in entries:
        ne = e.get("n_extracted", 0)
        if ne == 0:
            continue
        bucket = "1" if ne == 1 else ("2-3" if ne <= 3 else ("4-6" if ne <= 6 else "7+"))
        if e["status"] == "match":
            n_ext_match[bucket] += 1
        elif e["status"] == "extracted_no_match":
            n_ext_enm[bucket] += 1

    print(f"  {'N_ext':<8s} {'Matched':>8s} {'ENM':>8s} {'ENM %':>8s}")
    print("  " + "-" * 35)
    for bucket in ["1", "2-3", "4-6", "7+"]:
        m = n_ext_match.get(bucket, 0)
        e = n_ext_enm.get(bucket, 0)
        total_b = m + e
        pct = 100.0 * e / total_b if total_b > 0 else 0
        print(f"  {bucket:<8s} {m:8d} {e:8d} {pct:7.1f}%")

    # 5f. Category breakdown with avg distance
    print("\n--- 5f. Category stats (avg best distance) ---")
    cat_dists = defaultdict(list)
    for ea in entry_analysis:
        if ea["best_rd"] is not None:
            cat_dists[ea["category"]].append(ea["best_rd"])

    print(f"  {'Category':<40s} {'N':>5s} {'Median':>8s} {'Mean':>10s} {'Min':>8s} {'Max':>10s}")
    print("  " + "-" * 85)
    for cat in sorted(cat_dists.keys(), key=lambda x: -len(cat_dists[x])):
        dists = sorted(cat_dists[cat])
        n = len(dists)
        med = dists[n // 2]
        mean = sum(dists) / n
        print(f"  {cat:<40s} {n:5d} {med:8.3f} {mean:10.3f} {dists[0]:8.4f} {dists[-1]:10.1f}")

    # 5g. Potential recoverable matches (could be rescued with wider tiers)
    print("\n--- 5g. POTENTIALLY RECOVERABLE (best distance <= 0.50) ---")
    recoverable = [ea for ea in entry_analysis if ea["best_rd"] is not None and ea["best_rd"] <= 0.50]
    recoverable.sort(key=lambda x: x["best_rd"])

    print(f"  Total potentially recoverable: {len(recoverable)} / {n_enm} ({100*len(recoverable)/n_enm:.1f}%)")
    print(f"\n  Method that achieves best distance:")
    method_counts = Counter()
    for ea in recoverable:
        method_counts[ea["best_method"]] += 1
    for m, c in method_counts.most_common():
        print(f"    {m}: {c}")

    print(f"\n  Top 15 closest misses that could be recovered:")
    for i, ea in enumerate(recoverable[:15]):
        e = ea["entry"]
        ad = ea["all_dists"][0] if ea["all_dists"] else None
        if ad:
            rd, ext_v, coch_v, et, dt, outcome, method = ad
            print(f"    {i+1:2d}. {e['study_id']:<30s} dist={rd:.4f} method={method:<12s} "
                  f"ext={ext_v:.4g} coch={coch_v:.4g} {et}->{dt}")

    # 5h. Entries with NO closest_miss (all extracted values are None?)
    print("\n--- 5h. Entries with no closest_miss ---")
    no_cm = [ea for ea in entry_analysis if ea["best_rd"] is None]
    print(f"  Count: {len(no_cm)}")
    for ea in no_cm[:5]:
        e = ea["entry"]
        print(f"    {e['study_id']}: extracted={[(clean_effect_type(x.get('effect_type')), x.get('point_estimate')) for x in e['extracted']]}")

    # 5i. How many could have matched if we computed effect from raw_data?
    print("\n--- 5i. Entries where Cochrane has raw_data ---")
    has_raw = 0
    no_raw = 0
    for ea in entry_analysis:
        e = ea["entry"]
        any_raw = any(c.get("raw_data") for c in e.get("cochrane", []))
        if any_raw:
            has_raw += 1
        else:
            no_raw += 1
    print(f"  With raw_data: {has_raw}, Without: {no_raw}")

    # For those with raw_data, check if computing OR/RR/MD from raw would help
    print("\n  Checking if recomputed effects from raw_data match extractions...")
    recompute_matches = 0
    recompute_close = 0
    for ea in entry_analysis:
        e = ea["entry"]
        for coch in e.get("cochrane", []):
            rd = coch.get("raw_data")
            if not rd:
                continue
            dt = coch.get("data_type")
            computed = []
            if dt == "binary" and all(k in rd for k in ["exp_cases", "exp_n", "ctrl_cases", "ctrl_n"]):
                ec, en, cc, cn = rd["exp_cases"], rd["exp_n"], rd["ctrl_cases"], rd["ctrl_n"]
                # Compute OR
                a, b, c_val, d = ec, en - ec, cc, cn - cc
                if b > 0 and c_val > 0 and d > 0 and a > 0:
                    or_val = (a * d) / (b * c_val)
                    computed.append(("OR", or_val))
                # Compute RR
                if en > 0 and cn > 0 and cc > 0:
                    rr_val = (ec / en) / (cc / cn)
                    computed.append(("RR", rr_val))
                # Compute RD
                if en > 0 and cn > 0:
                    rd_val = (ec / en) - (cc / cn)
                    computed.append(("RD", rd_val))
            elif dt == "continuous" and all(k in rd for k in ["exp_mean", "exp_sd", "exp_n", "ctrl_mean", "ctrl_sd", "ctrl_n"]):
                md_val = rd["exp_mean"] - rd["ctrl_mean"]
                computed.append(("MD", md_val))
                # SMD (Cohen's d)
                en, cn = rd["exp_n"], rd["ctrl_n"]
                sp = math.sqrt(((en - 1) * rd["exp_sd"]**2 + (cn - 1) * rd["ctrl_sd"]**2) / (en + cn - 2))
                if sp > 0:
                    smd_val = md_val / sp
                    computed.append(("SMD", smd_val))

            # Check if any computed value matches any extracted value
            for ext in e.get("extracted", []):
                pe = ext.get("point_estimate")
                if pe is None:
                    continue
                for comp_type, comp_val in computed:
                    if comp_val == 0 and pe == 0:
                        recompute_matches += 1
                    elif abs(comp_val) > 1e-9:
                        rel = abs(pe - comp_val) / abs(comp_val)
                        if rel <= 0.10:
                            recompute_matches += 1
                        elif rel <= 0.35:
                            recompute_close += 1

    print(f"  Recomputed raw_data matches (<=10%): {recompute_matches}")
    print(f"  Recomputed raw_data close (10-35%): {recompute_close}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 90)
    print("SUMMARY: WHY DO 202 EXTRACTED_NO_MATCH ENTRIES FAIL?")
    print("=" * 90)

    # Count type mismatches
    n_type_mm = sum(1 for ea in entry_analysis if "type_mismatch" in ea["category"])
    n_close = sum(1 for ea in entry_analysis if ea["category"] == "close_miss")
    n_moderate = sum(1 for ea in entry_analysis if ea["category"] == "moderate_miss")
    n_wrong = sum(1 for ea in entry_analysis if ea["category"] == "wrong_value")
    n_wild = sum(1 for ea in entry_analysis if ea["category"] == "wildly_off")
    n_nocomp = sum(1 for ea in entry_analysis if ea["category"] == "no_comparison")

    # How many recoverable with wider tiers
    n_recov_35 = sum(1 for ea in entry_analysis if ea["best_rd"] is not None and ea["best_rd"] <= 0.35)
    n_recov_50 = sum(1 for ea in entry_analysis if ea["best_rd"] is not None and ea["best_rd"] <= 0.50)

    print(f"""
  1. TYPE MISMATCH: {n_type_mm} entries ({100*n_type_mm/n_enm:.1f}%)
     Extractor found a ratio (OR/RR/HR) but Cochrane expects continuous (MD),
     or extractor found MD but Cochrane expects binary (OR). These are
     fundamentally incompatible extractions.

  2. CLOSE MISS: {n_close} entries ({100*n_close/n_enm:.1f}%)
     Best distance <= 50%. These could potentially be recovered with
     slightly wider tolerance tiers or new matching methods.

  3. MODERATE MISS: {n_moderate} entries ({100*n_moderate/n_enm:.1f}%)
     Best distance 50-100%. Possibly correct outcome but different
     statistical method, adjustment, or subgroup.

  4. WRONG VALUE/OUTCOME: {n_wrong} entries ({100*n_wrong/n_enm:.1f}%)
     Best distance 100-500%. Likely extracted from a completely different
     outcome, subgroup, or timepoint than what Cochrane indexed.

  5. WILDLY OFF: {n_wild} entries ({100*n_wild/n_enm:.1f}%)
     Best distance > 500%. Extraction is for something completely unrelated
     to any Cochrane reference outcome.

  6. NO COMPARISON: {n_nocomp} entries ({100*n_nocomp/n_enm:.1f}%)
     All extracted values are None (extraction found effect type but no number).

  RECOVERY POTENTIAL:
     - Could recover with 35% tiers (reciprocal/sign/abs): {n_recov_35}
     - Could recover with 50% tiers (reciprocal/sign/abs): {n_recov_50}
     - True hard failures (>50% best distance): {n_enm - n_recov_50}
""")


if __name__ == "__main__":
    main()
