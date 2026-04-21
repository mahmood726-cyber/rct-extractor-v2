"""
Compute effect estimates for COUNTS_ONLY gold standard entries.

For each entry with raw_data, uses the effect_calculator to compute
the same effect that Cochrane would compute from raw 2×2 tables or means/SDs.

Compares computed values against Cochrane's values and fills gold.* fields.
"""
import io
import json
import math
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(__file__).resolve().parents[1]
GOLD_FILE = PROJECT_DIR / "gold_data" / "gold_50.jsonl"

sys.path.insert(0, str(PROJECT_DIR))
from src.core.effect_calculator import compute_effect_from_raw_data


# Map study_id → inferred effect type based on Cochrane value analysis
# Some entries labeled "binary" actually have continuous data (means/SDs)
EFFECT_TYPE_OVERRIDES = {
    "Bomyea_2015": "SMD",      # -0.67 is clearly a standardized mean difference
    "Marigold_2005": "MD",     # 1.0 is raw mean difference (49.1-48.1)
    "Jandaghi_2021": "MD",     # 2.3 is MD (different outcome than what we extracted)
    "Habib_2017": "RR",        # 1.28 is a risk ratio from percentages
    # Others: infer from cochrane_outcome_type
}


def infer_effect_type(entry):
    """Infer what effect type Cochrane computed."""
    sid = entry["study_id"]
    if sid in EFFECT_TYPE_OVERRIDES:
        return EFFECT_TYPE_OVERRIDES[sid]

    ctype = entry.get("cochrane_outcome_type", "binary")
    cochrane_val = entry.get("cochrane_effect")
    gold = entry.get("gold", {})
    raw = gold.get("raw_data", {})

    # If we have means/SDs, it's continuous (regardless of cochrane label)
    if "intervention_mean" in raw or "intervention_change" in raw:
        return "MD"

    # If we have events/N or pct/N, check Cochrane value for hints
    if cochrane_val is not None:
        # OR values are typically 0.1-10, centered on 1
        # RR values are also centered on 1
        # Hard to distinguish OR/RR without more context → default to OR for binary
        pass

    return "OR" if ctype == "binary" else "MD"


def main():
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    stats = {"computed": 0, "match": 0, "mismatch": 0, "no_raw": 0, "skipped": 0}

    print("=" * 70)
    print("COMPUTING EFFECTS FOR COUNTS_ONLY ENTRIES")
    print("=" * 70)

    for entry in entries:
        cat = entry.get("category", "")
        if cat != "COUNTS_ONLY":
            continue

        sid = entry["study_id"]
        gold = entry.get("gold", {})
        raw = gold.get("raw_data")
        cochrane_val = entry.get("cochrane_effect")

        if not raw:
            print(f"\n  {sid}: NO RAW DATA — skipping")
            stats["no_raw"] += 1
            continue

        # Infer effect type
        etype = infer_effect_type(entry)

        # Compute effect
        result = compute_effect_from_raw_data(raw, entry.get("cochrane_outcome_type", "binary"),
                                               cochrane_effect_type=etype)

        if result is None:
            print(f"\n  {sid}: COMPUTATION FAILED")
            stats["skipped"] += 1
            continue

        stats["computed"] += 1

        # Compare with Cochrane
        cochrane_match = ""
        if cochrane_val is not None:
            diff = abs(result.point_estimate - cochrane_val)
            if cochrane_val != 0:
                pct_diff = abs(diff / cochrane_val) * 100
            else:
                pct_diff = diff * 100

            if pct_diff < 5:
                cochrane_match = f" MATCH (diff={pct_diff:.1f}%)"
                stats["match"] += 1
            else:
                cochrane_match = f" MISMATCH (computed={result.point_estimate:.4f} vs cochrane={cochrane_val}, diff={pct_diff:.1f}%)"
                stats["mismatch"] += 1

        print(f"\n  {sid}:")
        print(f"    Effect: {result.effect_type} = {result.point_estimate:.4f} "
              f"[{result.ci_lower:.4f}, {result.ci_upper:.4f}]")
        print(f"    Method: {result.method}")
        if cochrane_match:
            print(f"    Cochrane: {cochrane_match}")

        # Fill gold.* fields
        gold["effect_type"] = result.effect_type
        gold["point_estimate"] = round(result.point_estimate, 4)
        gold["ci_lower"] = round(result.ci_lower, 4)
        gold["ci_upper"] = round(result.ci_upper, 4)
        gold["source"] = "computed"
        gold["method"] = result.method
        if result.notes:
            existing_notes = gold.get("notes", "")
            gold["notes"] = existing_notes + f" | COMPUTED: {result.notes}"
        else:
            existing_notes = gold.get("notes", "")
            if "COMPUTED" not in existing_notes:
                gold["notes"] = existing_notes + " | COMPUTED from raw data"

        entry["gold"] = gold

    # Save
    with open(GOLD_FILE, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    print(f"\n{'=' * 70}")
    print(f"COMPUTATION SUMMARY")
    print(f"{'=' * 70}")
    print(f"Computed:     {stats['computed']}")
    print(f"  Match:      {stats['match']} (within 5% of Cochrane)")
    print(f"  Mismatch:   {stats['mismatch']} (different outcome/scale)")
    print(f"No raw data:  {stats['no_raw']}")
    print(f"Failed:       {stats['skipped']}")

    # Count total filled
    filled = sum(1 for e in entries
                 if not e.get("excluded") and e.get("gold", {}).get("point_estimate") is not None)
    usable = sum(1 for e in entries if not e.get("excluded"))
    print(f"\nTotal gold entries filled: {filled}/{usable} ({filled/usable*100:.0f}%)")


if __name__ == "__main__":
    main()
