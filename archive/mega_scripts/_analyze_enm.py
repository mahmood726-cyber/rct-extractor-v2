# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""Analyze extracted_no_match cases: what did we extract vs what Cochrane expects?"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

results = []
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/mega_eval_v3.jsonl', encoding='utf-8') as f:
    for line in f:
        results.append(json.loads(line))

enm = [r for r in results if r['status'] == 'extracted_no_match']
print(f"Extracted-no-match: {len(enm)} papers")

# Analyze the relationship between extracted and cochrane values
import math

closest_ratios = []  # ratio of closest extracted to any cochrane value
type_mismatches = 0
missing_type = 0
close_30pct = 0
close_50pct = 0

for entry in enm:
    extracted = entry['extracted']
    cochrane = entry['cochrane']

    # Find closest pair
    best_ratio = float('inf')
    best_pair = None
    for ext in extracted:
        ext_val = ext['point_estimate']
        if ext_val is None:
            continue
        for coch in cochrane:
            coch_val = coch['effect']
            if coch_val is None or coch_val == 0:
                continue

            # Try direct ratio
            ratio = abs(ext_val - coch_val) / abs(coch_val)
            if ratio < best_ratio:
                best_ratio = ratio
                best_pair = (ext, coch, 'direct', ratio)

            # Try reciprocal (for ratio types)
            if ext_val != 0:
                recip_ratio = abs(1/ext_val - coch_val) / abs(coch_val)
                if recip_ratio < best_ratio:
                    best_ratio = recip_ratio
                    best_pair = (ext, coch, 'reciprocal', recip_ratio)

            # Try sign-flip (for difference types)
            flip_ratio = abs(-ext_val - coch_val) / abs(coch_val)
            if flip_ratio < best_ratio:
                best_ratio = flip_ratio
                best_pair = (ext, coch, 'signflip', flip_ratio)

    if best_pair:
        ext, coch, method, ratio = best_pair
        closest_ratios.append((ratio, method, entry['pmcid'], ext['point_estimate'], coch['effect'],
                               ext.get('effect_type', '?'), coch.get('data_type', '?')))
        if ratio <= 0.30:
            close_30pct += 1
        if ratio <= 0.50:
            close_50pct += 1

# Sort by ratio
closest_ratios.sort()

print(f"\nClosest match distribution:")
print(f"  <= 5%:  {sum(1 for r in closest_ratios if r[0] <= 0.05)}")
print(f"  <= 10%: {sum(1 for r in closest_ratios if r[0] <= 0.10)}")
print(f"  <= 15%: {sum(1 for r in closest_ratios if r[0] <= 0.15)}")
print(f"  <= 20%: {sum(1 for r in closest_ratios if r[0] <= 0.20)}")
print(f"  <= 25%: {sum(1 for r in closest_ratios if r[0] <= 0.25)}")
print(f"  <= 30%: {close_30pct}")
print(f"  <= 50%: {close_50pct}")
print(f"  > 50%:  {sum(1 for r in closest_ratios if r[0] > 0.50)}")

# Show the near-misses (26-50% range) - these might be convertible with better matching
print(f"\n=== Near-misses (26-50% off) - potential with better matching ===")
count = 0
for ratio, method, pmcid, ext_val, coch_val, ext_type, coch_type in closest_ratios:
    if 0.25 < ratio <= 0.50:
        print(f"  {pmcid}: ext={ext_val:.4f} ({ext_type}) vs coch={coch_val:.4f} ({coch_type}) | {method} ratio={ratio:.3f}")
        count += 1
        if count >= 30:
            break

# Show the method distribution for close matches
print(f"\n=== Method distribution for matches <= 30% ===")
from collections import Counter
method_counts = Counter()
for ratio, method, *_ in closest_ratios:
    if ratio <= 0.30:
        method_counts[method] += 1
for method, count in method_counts.most_common():
    print(f"  {method}: {count}")

# === Analyze: how many have MULTIPLE extracted values? ===
print(f"\n=== Extracted value count distribution ===")
ext_counts = Counter(len(r['extracted']) for r in enm)
for k in sorted(ext_counts.keys()):
    print(f"  {k} extractions: {ext_counts[k]} papers")

# === Analyze: what types are we extracting vs what Cochrane expects? ===
print(f"\n=== Extracted types vs Cochrane types ===")
type_pairs = Counter()
for entry in enm:
    for ext in entry['extracted']:
        ext_type = ext.get('effect_type', 'unknown')
        for coch in entry['cochrane']:
            coch_type = coch.get('data_type', 'unknown')
            type_pairs[(ext_type, coch_type)] += 1

for (et, ct), count in type_pairs.most_common(20):
    print(f"  ext={et:8s} vs coch={ct:12s}: {count}")

# === Look at the >50% cases - what's happening? ===
print(f"\n=== Worst mismatches (>500% off) ===")
count = 0
for ratio, method, pmcid, ext_val, coch_val, ext_type, coch_type in closest_ratios:
    if ratio > 5.0:
        print(f"  {pmcid}: ext={ext_val:.4f} ({ext_type}) vs coch={coch_val:.4f} ({coch_type}) | ratio={ratio:.1f}x")
        count += 1
        if count >= 15:
            break
