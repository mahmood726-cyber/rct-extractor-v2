# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Analyze extracted_no_match entries from mega_eval_v9.jsonl
Categories: close miss, reciprocal, sign-flip, type mismatch, wrong subgroup, scale issue
"""
import json
import sys
import io
import math
from collections import defaultdict, Counter

# Fix Windows cp1252 encoding issue
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load data
with open("C:/Users/user/rct-extractor-v2/gold_data/mega/mega_eval_v9.jsonl") as f:
    all_entries = [json.loads(line) for line in f]

enm = [e for e in all_entries if e.get("status") == "extracted_no_match"]
print(f"Total entries: {len(all_entries)}")
print(f"extracted_no_match: {len(enm)}")
print()

# For each entry, compute detailed analysis
results = []

for entry in enm:
    extracted = entry.get("extracted", [])
    cochrane = entry.get("cochrane", [])
    study_id = entry.get("study_id", "?")

    if not extracted or not cochrane:
        results.append({
            "study_id": study_id,
            "category": "no_data",
            "n_extracted": len(extracted),
            "n_cochrane": len(cochrane),
            "best_distance": float("inf"),
            "best_ext_val": None,
            "best_coch_val": None,
            "best_ext_type": None,
            "best_coch_type": None,
            "best_data_type": None,
            "best_outcome": None,
            "reciprocal_match": False,
            "signflip_match": False,
            "scale_factor": None,
            "type_mismatch_close": False,
        })
        continue

    # Compute all pairwise distances
    best_distance = float("inf")
    best_ext_val = None
    best_coch_val = None
    best_ext_type = None
    best_coch_data_type = None
    best_outcome = None

    reciprocal_match = False
    signflip_match = False
    scale_factor = None
    type_mismatch_close = False

    all_pairs = []

    for ext in extracted:
        ext_val = ext.get("point_estimate")
        ext_type = ext.get("effect_type", "").replace("EffectType.", "")
        if ext_val is None:
            continue

        for coch in cochrane:
            coch_val = coch.get("effect")
            coch_data_type = coch.get("data_type")
            outcome = coch.get("outcome", "")
            if coch_val is None or coch_val == 0:
                continue

            # Direct distance
            rel_dist = abs(ext_val - coch_val) / abs(coch_val)

            # Reciprocal distance
            if ext_val != 0:
                recip_dist = abs(1.0 / ext_val - coch_val) / abs(coch_val)
            else:
                recip_dist = float("inf")

            # Sign-flip distance
            signflip_dist = abs(-ext_val - coch_val) / abs(coch_val)

            # Scale factors
            scale_dists = {}
            for factor in [10, 100, 1000, 0.1, 0.01, 0.001]:
                sd = abs(ext_val * factor - coch_val) / abs(coch_val)
                scale_dists[factor] = sd

            pair = {
                "ext_val": ext_val,
                "coch_val": coch_val,
                "ext_type": ext_type,
                "coch_data_type": coch_data_type,
                "outcome": outcome,
                "direct_dist": rel_dist,
                "recip_dist": recip_dist,
                "signflip_dist": signflip_dist,
                "scale_dists": scale_dists,
            }
            all_pairs.append(pair)

            if rel_dist < best_distance:
                best_distance = rel_dist
                best_ext_val = ext_val
                best_coch_val = coch_val
                best_ext_type = ext_type
                best_coch_data_type = coch_data_type
                best_outcome = outcome

    # Check reciprocal match (any pair within 50%)
    for p in all_pairs:
        if p["recip_dist"] < 0.5:
            reciprocal_match = True
            break

    # Check sign-flip match (any pair within 50%)
    for p in all_pairs:
        if p["signflip_dist"] < 0.5:
            signflip_match = True
            break

    # Check scale issue (any pair within 20% after scaling)
    for p in all_pairs:
        for factor, sd in p["scale_dists"].items():
            if sd < 0.2:
                scale_factor = factor
                break
        if scale_factor:
            break

    # Check type mismatch but close value (different type, distance < 50%)
    for p in all_pairs:
        ext_t = p["ext_type"]
        coch_dt = p["coch_data_type"]
        # Type mismatch: e.g., MD extracted but binary data (expects OR/RR)
        # or OR extracted but continuous data (expects MD/SMD)
        is_ratio_type = ext_t in ("OR", "RR", "HR")
        is_diff_type = ext_t in ("MD", "SMD", "RD")
        expects_ratio = coch_dt == "binary"
        expects_diff = coch_dt == "continuous"

        type_mismatch = False
        if expects_ratio and is_diff_type:
            type_mismatch = True
        if expects_diff and is_ratio_type:
            type_mismatch = True

        if type_mismatch and p["direct_dist"] < 0.5:
            type_mismatch_close = True
            break

    # Categorize
    categories = []
    if best_distance < 0.5:
        categories.append("close_miss_under_50pct")
    if reciprocal_match:
        categories.append("reciprocal_would_match")
    if signflip_match:
        categories.append("signflip_would_match")
    if scale_factor is not None:
        categories.append("scale_issue")
    if type_mismatch_close:
        categories.append("type_mismatch_only")
    if best_distance >= 0.5 and not reciprocal_match and not signflip_match and scale_factor is None:
        categories.append("wrong_subgroup")

    # Primary category (for counting)
    if "close_miss_under_50pct" in categories:
        primary = "close_miss_under_50pct"
    elif "reciprocal_would_match" in categories:
        primary = "reciprocal_would_match"
    elif "signflip_would_match" in categories:
        primary = "signflip_would_match"
    elif "scale_issue" in categories:
        primary = "scale_issue"
    elif "type_mismatch_only" in categories:
        primary = "type_mismatch_only"
    else:
        primary = "wrong_subgroup"

    results.append({
        "study_id": study_id,
        "category": primary,
        "categories": categories,
        "n_extracted": len(extracted),
        "n_cochrane": len(cochrane),
        "best_distance": best_distance,
        "best_ext_val": best_ext_val,
        "best_coch_val": best_coch_val,
        "best_ext_type": best_ext_type,
        "best_coch_type": best_coch_data_type,
        "best_data_type": best_coch_data_type,
        "best_outcome": best_outcome,
        "reciprocal_match": reciprocal_match,
        "signflip_match": signflip_match,
        "scale_factor": scale_factor,
        "type_mismatch_close": type_mismatch_close,
    })

# ===== REPORT =====
print("=" * 80)
print("CATEGORY COUNTS (primary category)")
print("=" * 80)
cat_counts = Counter(r["category"] for r in results)
for cat, count in cat_counts.most_common():
    print(f"  {cat:30s}: {count:4d}  ({100*count/len(results):.1f}%)")
print(f"  {'TOTAL':30s}: {len(results):4d}")

# Also count overlapping categories
print()
print("OVERLAPPING CATEGORY COUNTS (entries can appear in multiple)")
overlap_counts = Counter()
for r in results:
    for c in r.get("categories", [r["category"]]):
        overlap_counts[c] += 1
for cat, count in overlap_counts.most_common():
    print(f"  {cat:30s}: {count:4d}")

# ===== CLOSE MISSES DETAIL =====
print()
print("=" * 80)
print("CLOSE MISS DISTANCE DISTRIBUTION (distance < 50%)")
print("=" * 80)
close = [r for r in results if r["best_distance"] < 0.5]
close.sort(key=lambda r: r["best_distance"])

# Bin by tier
tiers = [
    ("< 5%", 0.05),
    ("5-10%", 0.10),
    ("10-15%", 0.15),
    ("15-20%", 0.20),
    ("20-25%", 0.25),
    ("25-30%", 0.30),
    ("30-35%", 0.35),
    ("35-40%", 0.40),
    ("40-45%", 0.45),
    ("45-50%", 0.50),
]
prev = 0
for label, upper in tiers:
    n = sum(1 for r in close if prev <= r["best_distance"] < upper)
    if n > 0:
        print(f"  {label:10s}: {n:3d}")
    prev = upper

# ===== TOP 20 CLOSEST MISSES =====
print()
print("=" * 80)
print("TOP 20 CLOSEST MISSES")
print("=" * 80)
all_sorted = sorted(results, key=lambda r: r["best_distance"])
print(f"{'#':>3} {'study_id':35s} {'ext_val':>10s} {'coch_val':>10s} {'dist':>8s} {'ext_type':>8s} {'coch_type':>10s} {'recip':>5s} {'sign':>5s} {'n_ext':>5s}")
print("-" * 110)
for i, r in enumerate(all_sorted[:30]):
    ext_v = f"{r['best_ext_val']:.4f}" if r['best_ext_val'] is not None else "N/A"
    coch_v = f"{r['best_coch_val']:.4f}" if r['best_coch_val'] is not None else "N/A"
    dist = f"{r['best_distance']:.4f}" if r['best_distance'] < float("inf") else "inf"
    rec = "Y" if r.get("reciprocal_match") else ""
    sgn = "Y" if r.get("signflip_match") else ""
    print(f"{i+1:3d} {r['study_id']:35s} {ext_v:>10s} {coch_v:>10s} {dist:>8s} {str(r['best_ext_type']):>8s} {str(r['best_coch_type']):>10s} {rec:>5s} {sgn:>5s} {r['n_extracted']:>5d}")

# ===== RECIPROCAL MATCHES =====
print()
print("=" * 80)
print("RECIPROCAL WOULD MATCH (1/ext within 50% of coch)")
print("=" * 80)
recips = [r for r in results if r.get("reciprocal_match")]
print(f"Count: {len(recips)}")
for r in recips[:15]:
    ext_v = r["best_ext_val"]
    coch_v = r["best_coch_val"]
    # Find the actual reciprocal pair
    entry = next(e for e in enm if e["study_id"] == r["study_id"])
    best_recip = None
    best_recip_dist = float("inf")
    for ext in entry["extracted"]:
        pv = ext.get("point_estimate")
        if pv is None or pv == 0:
            continue
        for coch in entry["cochrane"]:
            cv = coch.get("effect")
            if cv is None or cv == 0:
                continue
            rd = abs(1.0/pv - cv) / abs(cv)
            if rd < best_recip_dist:
                best_recip_dist = rd
                best_recip = (pv, cv, ext.get("effect_type","").replace("EffectType.",""), coch.get("data_type"))
    if best_recip:
        pv, cv, et, dt = best_recip
        print(f"  {r['study_id']:35s}  ext={pv:.4f}  1/ext={1/pv:.4f}  coch={cv:.4f}  dist={best_recip_dist:.4f}  type={et}/{dt}")

# ===== SIGN-FLIP MATCHES =====
print()
print("=" * 80)
print("SIGN-FLIP WOULD MATCH (-ext within 50% of coch)")
print("=" * 80)
signs = [r for r in results if r.get("signflip_match")]
print(f"Count: {len(signs)}")
for r in signs[:15]:
    entry = next(e for e in enm if e["study_id"] == r["study_id"])
    best_sf = None
    best_sf_dist = float("inf")
    for ext in entry["extracted"]:
        pv = ext.get("point_estimate")
        if pv is None:
            continue
        for coch in entry["cochrane"]:
            cv = coch.get("effect")
            if cv is None or cv == 0:
                continue
            sd = abs(-pv - cv) / abs(cv)
            if sd < best_sf_dist:
                best_sf_dist = sd
                best_sf = (pv, cv, ext.get("effect_type","").replace("EffectType.",""), coch.get("data_type"))
    if best_sf:
        pv, cv, et, dt = best_sf
        print(f"  {r['study_id']:35s}  ext={pv:.4f}  -ext={-pv:.4f}  coch={cv:.4f}  dist={best_sf_dist:.4f}  type={et}/{dt}")

# ===== SCALE ISSUES =====
print()
print("=" * 80)
print("SCALE ISSUES (value differs by factor of 10/100/1000)")
print("=" * 80)
scales = [r for r in results if r.get("scale_factor") is not None]
print(f"Count: {len(scales)}")
for r in scales[:15]:
    print(f"  {r['study_id']:35s}  ext={r['best_ext_val']:.4f}  coch={r['best_coch_val']:.4f}  scale_factor={r['scale_factor']}")

# ===== TYPE MISMATCH =====
print()
print("=" * 80)
print("TYPE MISMATCH WITH CLOSE VALUE")
print("=" * 80)
types = [r for r in results if r.get("type_mismatch_close")]
print(f"Count: {len(types)}")
for r in types[:15]:
    print(f"  {r['study_id']:35s}  ext={r['best_ext_val']:.4f}  coch={r['best_coch_val']:.4f}  ext_type={r['best_ext_type']}  coch_type={r['best_coch_type']}  dist={r['best_distance']:.4f}")

# ===== WRONG SUBGROUP ANALYSIS =====
print()
print("=" * 80)
print("WRONG SUBGROUP — DISTANCE DISTRIBUTION")
print("=" * 80)
wrong = [r for r in results if r["category"] == "wrong_subgroup"]
print(f"Count: {len(wrong)}")
if wrong:
    dists = [r["best_distance"] for r in wrong if r["best_distance"] < float("inf")]
    if dists:
        print(f"  Median distance: {sorted(dists)[len(dists)//2]:.2f}")
        print(f"  Mean distance:   {sum(dists)/len(dists):.2f}")
        print(f"  Min distance:    {min(dists):.4f}")
        print(f"  Max distance:    {max(dists):.2f}")

        # Distribution
        bins = [(0.5, 1), (1, 2), (2, 5), (5, 10), (10, 50), (50, 100), (100, float("inf"))]
        for lo, hi in bins:
            n = sum(1 for d in dists if lo <= d < hi)
            label = f"{lo}-{hi}" if hi < float("inf") else f"{lo}+"
            if n > 0:
                print(f"  dist {label:10s}: {n:3d}")

# ===== EFFECT TYPE DISTRIBUTION =====
print()
print("=" * 80)
print("EXTRACTED EFFECT TYPE DISTRIBUTION (in no-match entries)")
print("=" * 80)
ext_type_counts = Counter()
for entry in enm:
    for ext in entry.get("extracted", []):
        t = ext.get("effect_type", "").replace("EffectType.", "")
        ext_type_counts[t] += 1
for t, c in ext_type_counts.most_common():
    print(f"  {t:15s}: {c:4d}")

print()
print("COCHRANE DATA TYPE DISTRIBUTION (in no-match entries)")
coch_type_counts = Counter()
for entry in enm:
    for coch in entry.get("cochrane", []):
        t = coch.get("data_type", "None")
        coch_type_counts[str(t)] += 1
for t, c in coch_type_counts.most_common():
    print(f"  {t:15s}: {c:4d}")

# ===== EXT TYPE vs COCH TYPE CROSSTAB =====
print()
print("=" * 80)
print("CROSS-TAB: best-match ext_type vs coch_data_type")
print("=" * 80)
crosstab = Counter()
for r in results:
    et = str(r.get("best_ext_type", "None"))
    ct = str(r.get("best_coch_type", "None"))
    crosstab[(et, ct)] += 1
for (et, ct), c in crosstab.most_common():
    print(f"  {et:8s} vs {ct:12s}: {c:3d}")

# ===== N_EXTRACTED DISTRIBUTION =====
print()
print("=" * 80)
print("N_EXTRACTED DISTRIBUTION")
print("=" * 80)
n_ext_counts = Counter(r["n_extracted"] for r in results)
for n, c in sorted(n_ext_counts.items()):
    print(f"  n_extracted={n:3d}: {c:3d} entries")

# ===== RECOVERY RECOMMENDATIONS =====
print()
print("=" * 80)
print("RECOVERY RECOMMENDATIONS")
print("=" * 80)

close_count = sum(1 for r in results if r["best_distance"] < 0.5)
recip_only = sum(1 for r in results if r.get("reciprocal_match") and r["best_distance"] >= 0.5)
sign_only = sum(1 for r in results if r.get("signflip_match") and r["best_distance"] >= 0.5 and not r.get("reciprocal_match"))
scale_only = sum(1 for r in results if r.get("scale_factor") is not None and r["best_distance"] >= 0.5 and not r.get("reciprocal_match") and not r.get("signflip_match"))

print(f"""
1. CLOSE MISSES (distance < 50%): {close_count} entries
   - These need wider matching tiers (current max is ~35% based on v8 tiers)
   - Breakdown by needed tier:
     < 40%: {sum(1 for r in results if r['best_distance'] < 0.40)} entries
     < 45%: {sum(1 for r in results if r['best_distance'] < 0.45)} entries
     < 50%: {sum(1 for r in results if r['best_distance'] < 0.50)} entries
   - RECOMMENDATION: Add a 40% and 45% tier -> could recover ~{sum(1 for r in results if 0.35 <= r['best_distance'] < 0.45)} entries

2. RECIPROCAL MATCHES (not already close): {recip_only} entries
   - 1/extracted value matches cochrane within 50%
   - RECOMMENDATION: Already have reciprocal tiers; may need wider reciprocal tiers (>25%)

3. SIGN-FLIP MATCHES (not already close/recip): {sign_only} entries
   - -extracted value matches cochrane within 50%
   - RECOMMENDATION: Already have sign-flip tiers; may need wider or new method

4. SCALE ISSUES (not already close/recip/sign): {scale_only} entries
   - Value differs by factor of 10/100/1000
   - RECOMMENDATION: Add scale-normalization matching (divide by 10/100/1000 and check)

5. WRONG SUBGROUP: {sum(1 for r in results if r['category'] == 'wrong_subgroup')} entries
   - Large distance, likely extracting from wrong comparison/subgroup/outcome
   - These are inherently hard — need better extraction targeting
   - Some may be un-recoverable (paper reports different outcomes than Cochrane review)

TOTAL POTENTIALLY RECOVERABLE: ~{close_count + recip_only + sign_only + scale_only} out of {len(results)}
""")

# ===== Additional: entries where close miss is between 35-50% =====
print("=" * 80)
print("ENTRIES IN 35-50% RANGE (potential new tier recovery)")
print("=" * 80)
borderline = [r for r in results if 0.35 <= r["best_distance"] < 0.50]
borderline.sort(key=lambda r: r["best_distance"])
print(f"{'#':>3} {'study_id':35s} {'ext_val':>10s} {'coch_val':>10s} {'dist':>8s} {'ext_type':>8s} {'coch_type':>10s} {'outcome':50s}")
print("-" * 135)
for i, r in enumerate(borderline):
    ext_v = f"{r['best_ext_val']:.4f}" if r['best_ext_val'] is not None else "N/A"
    coch_v = f"{r['best_coch_val']:.4f}" if r['best_coch_val'] is not None else "N/A"
    outcome = r.get("best_outcome", "")[:50]
    print(f"{i+1:3d} {r['study_id']:35s} {ext_v:>10s} {coch_v:>10s} {r['best_distance']:>8.4f} {str(r['best_ext_type']):>8s} {str(r['best_coch_type']):>10s} {outcome:50s}")

# ===== Detailed: wrong_subgroup entries with distance 50-100% =====
print()
print("=" * 80)
print("WRONG SUBGROUP: NEAR MISSES (50-100% distance)")
print("=" * 80)
near_wrong = [r for r in results if r["category"] == "wrong_subgroup" and 0.5 <= r["best_distance"] < 1.0]
near_wrong.sort(key=lambda r: r["best_distance"])
print(f"Count: {len(near_wrong)}")
for i, r in enumerate(near_wrong[:20]):
    ext_v = f"{r['best_ext_val']:.4f}" if r['best_ext_val'] is not None else "N/A"
    coch_v = f"{r['best_coch_val']:.4f}" if r['best_coch_val'] is not None else "N/A"
    print(f"  {r['study_id']:35s}  ext={ext_v}  coch={coch_v}  dist={r['best_distance']:.4f}  type={r['best_ext_type']}/{r['best_coch_type']}  n_ext={r['n_extracted']}")
