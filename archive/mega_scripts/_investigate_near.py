"""Investigate extracted_no_match cases that are very close (<= 5%) to a Cochrane value."""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

results = []
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/mega_eval_v3.jsonl', encoding='utf-8') as f:
    for line in f:
        results.append(json.loads(line))

enm = [r for r in results if r['status'] == 'extracted_no_match']

print("=== Papers within 5% of Cochrane value but NOT matching ===\n")

for entry in enm:
    extracted = entry['extracted']
    cochrane = entry['cochrane']

    for ext in extracted:
        ext_val = ext['point_estimate']
        if ext_val is None:
            continue
        for coch in cochrane:
            coch_val = coch['effect']
            if coch_val is None or coch_val == 0:
                continue

            methods = []
            # Direct
            ratio = abs(ext_val - coch_val) / abs(coch_val)
            if ratio <= 0.05:
                methods.append(('direct', ratio))

            # Reciprocal
            if ext_val != 0:
                recip_ratio = abs(1/ext_val - coch_val) / abs(coch_val)
                if recip_ratio <= 0.05:
                    methods.append(('reciprocal', recip_ratio))

            # Sign-flip
            flip_ratio = abs(-ext_val - coch_val) / abs(coch_val)
            if flip_ratio <= 0.05:
                methods.append(('signflip', flip_ratio))

            for method, r in methods:
                coch_type = coch.get('data_type') or 'None'
                ext_type = str(ext.get('effect_type', '?'))
                print(f"  {entry['pmcid']} | {method} ({r:.4f})")
                print(f"    ext: {ext_val:.4f} ({ext_type})")
                print(f"    coch: {coch_val:.4f} ({coch_type}) | outcome: {coch['outcome'][:60]}")
                print(f"    study: {entry.get('first_author', '?')} {entry.get('year', '?')}")
                print()

# Now look at how the matching currently works: what tiers exist
print("\n=== Current matching tiers (from v6.1) ===")
print("Tier 1: direct_5pct (same value within 5%)")
print("Tier 1.5: reciprocal_10pct, reciprocal_15pct")
print("Tier 1.6: signflip_10pct, signflip_15pct")
print("Tier 2: cross_*_5pct (computed OR/RR/RD from raw data)")
print("Tier 3: direct_10pct")
print("Tier 3.5: direct_15pct_sametype")
print("Tier 3.6: direct_15pct_nulltype")
print("Tier 3.7: cross_*_15pct")
print("Tier 3.8: direct_20pct_sametype")
print("Tier 3.9: direct_25pct_sametype")
print("Tier 4: computed_*_10pct")

# Analyze: type distribution of extracted vs cochrane for these close matches
print("\n=== Type analysis for all extracted_no_match ===")
from collections import Counter
type_pairs = Counter()
for entry in enm:
    ext_types = set(str(ext.get('effect_type', 'unknown')) for ext in entry['extracted'])
    coch_types = set(str(coch.get('data_type', 'unknown')) for coch in entry['cochrane'])
    for et in ext_types:
        for ct in coch_types:
            type_pairs[(et, ct)] += 1

for (et, ct), count in type_pairs.most_common(20):
    print(f"  ext={et:30s} vs coch={str(ct):12s}: {count}")

# Specific question: how many have data_type=None in cochrane?
null_types = sum(1 for entry in enm
                 if all(coch.get('data_type') is None for coch in entry['cochrane']))
some_null = sum(1 for entry in enm
                if any(coch.get('data_type') is None for coch in entry['cochrane']))
print(f"\nCochrane entries with ALL data_type=None: {null_types}/{len(enm)}")
print(f"Cochrane entries with ANY data_type=None: {some_null}/{len(enm)}")
