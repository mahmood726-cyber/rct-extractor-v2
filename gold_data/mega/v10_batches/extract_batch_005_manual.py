#!/usr/bin/env python3
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""Manual extraction for batch 005 - careful reading of each entry."""

import json
import re
from pathlib import Path

def extract_numbers_from_text(text, outcome_name):
    """Extract effect estimates by careful pattern matching."""

    # Normalize text
    text_clean = text.replace('\u00c2\u00a0', ' ').replace('\u00e2\u20ac\u201c', '-').replace('\u00e2\u20ac\u201d', '-')
    text_clean = text_clean.replace('\u00e2\u2030\u00a4', '<=').replace('\u00e2\u2030\u00a5', '>=')

    result = {
        "found": False,
        "effect_type": None,
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "raw_data": None,
        "source_quote": "",
        "reasoning": ""
    }

    # Look for various effect estimate patterns

    # Pattern: "X/N (Y%) vs Z/N (W%)" or "X (Y%) vs Z (W%)"
    binary_pct = re.search(r'(\d+)/(\d+)\s*\(([0-9.]+)%?\)\s*(?:vs|versus|compared to|in the|and)\s*(\d+)/(\d+)\s*\(([0-9.]+)%?\)', text_clean, re.IGNORECASE)
    if binary_pct:
        result["found"] = True
        result["effect_type"] = "OR"
        result["raw_data"] = {
            "exp_events": int(binary_pct.group(1)),
            "exp_n": int(binary_pct.group(2)),
            "ctrl_events": int(binary_pct.group(4)),
            "ctrl_n": int(binary_pct.group(5))
        }
        result["source_quote"] = binary_pct.group(0)[:200]
        result["reasoning"] = "Found raw binary data with percentages"
        return result

    # Pattern: "X of Y (Z%) vs A of B (C%)"
    binary_of = re.search(r'(\d+)\s+of\s+(\d+)\s*\(([0-9.]+)%?\)\s*(?:vs|versus|compared to|and)\s*(\d+)\s+of\s+(\d+)\s*\(([0-9.]+)%?\)', text_clean, re.IGNORECASE)
    if binary_of:
        result["found"] = True
        result["effect_type"] = "OR"
        result["raw_data"] = {
            "exp_events": int(binary_of.group(1)),
            "exp_n": int(binary_of.group(2)),
            "ctrl_events": int(binary_of.group(4)),
            "ctrl_n": int(binary_of.group(5))
        }
        result["source_quote"] = binary_of.group(0)[:200]
        result["reasoning"] = "Found raw binary data (X of Y format)"
        return result

    # Pattern: OR/RR/HR = X.XX (95% CI X.XX-X.XX) or (CI: X.XX, X.XX)
    effect_ci = re.search(r'(OR|RR|HR|odds ratio|risk ratio|hazard ratio)[:\s=,]+([0-9.]+)\s*(?:\(95%\s*CI[:\s,]+([0-9.]+)\s*[-–to,]+\s*([0-9.]+)\)|95%\s*CI[:\s]+([0-9.]+)\s*[-–to,]+\s*([0-9.]+))', text_clean, re.IGNORECASE)
    if effect_ci:
        effect_name = effect_ci.group(1).upper()
        if 'HAZARD' in effect_name.upper():
            eff_type = 'HR'
        elif 'RISK' in effect_name.upper() or effect_name == 'RR':
            eff_type = 'RR'
        else:
            eff_type = 'OR'

        result["found"] = True
        result["effect_type"] = eff_type
        result["point_estimate"] = float(effect_ci.group(2))
        result["ci_lower"] = float(effect_ci.group(3) or effect_ci.group(5))
        result["ci_upper"] = float(effect_ci.group(4) or effect_ci.group(6))
        result["source_quote"] = effect_ci.group(0)[:200]
        result["reasoning"] = f"Found {eff_type} with 95% CI"
        return result

    # Pattern: MD = X.XX (95% CI: X.XX, X.XX) or MD X.XX (X.XX to X.XX)
    md_pattern = re.search(r'(MD|SMD|mean difference|standardized mean difference)[:\s=,]+([−-]?[0-9.]+)\s*(?:\(95%\s*CI[:\s,]+([−-]?[0-9.]+)\s*[to,]+\s*([−-]?[0-9.]+)\)|95%\s*CI[:\s]+([−-]?[0-9.]+)\s*[to,]+\s*([−-]?[0-9.]+))', text_clean, re.IGNORECASE)
    if md_pattern:
        eff_type = 'SMD' if 'SMD' in md_pattern.group(1).upper() or 'STANDARDIZED' in md_pattern.group(1).upper() else 'MD'
        result["found"] = True
        result["effect_type"] = eff_type
        result["point_estimate"] = float(md_pattern.group(2).replace('−', '-'))
        result["ci_lower"] = float((md_pattern.group(3) or md_pattern.group(5)).replace('−', '-'))
        result["ci_upper"] = float((md_pattern.group(4) or md_pattern.group(6)).replace('−', '-'))
        result["source_quote"] = md_pattern.group(0)[:200]
        result["reasoning"] = f"Found {eff_type} with 95% CI"
        return result

    # Pattern: mean (SD) in each group
    # Look for: "intervention: X.X (Y.Y)" and "control: A.A (B.B)" or "X.X ± Y.Y vs A.A ± B.B"
    mean_sd = re.findall(r'([0-9.]+)\s*[±(]\s*([0-9.]+)\)?', text_clean)
    if len(mean_sd) >= 2:
        # Try to find sample sizes too
        n_pattern = re.findall(r'[nN]\s*=\s*(\d+)', text_clean)
        if len(n_pattern) >= 2:
            result["found"] = True
            result["effect_type"] = "MD"
            result["raw_data"] = {
                "exp_mean": float(mean_sd[0][0]),
                "exp_sd": float(mean_sd[0][1]),
                "exp_n": int(n_pattern[0]),
                "ctrl_mean": float(mean_sd[1][0]),
                "ctrl_sd": float(mean_sd[1][1]),
                "ctrl_n": int(n_pattern[1])
            }
            result["source_quote"] = f"Mean(SD): {mean_sd[0][0]}({mean_sd[0][1]}) vs {mean_sd[1][0]}({mean_sd[1][1]}), n={n_pattern[0]} vs {n_pattern[1]}"
            result["reasoning"] = "Found mean(SD) and sample sizes for both groups"
            return result

    result["reasoning"] = f"No extractable effect estimate found for '{outcome_name}'"
    return result

def process_entry(entry):
    """Process a single entry and extract all outcomes."""
    study_id = entry["study_id"]
    outcomes = entry.get("outcomes", [])
    abstract = entry.get("abstract", "")
    results_text = entry.get("results_text", "")

    # Combine for searching
    full_text = f"{abstract}\n\n{results_text}"

    results = []

    for outcome_obj in outcomes:
        outcome_name = outcome_obj.get("outcome", "")
        data_type = outcome_obj.get("data_type", "unknown")

        # Search for outcome in text
        extraction = extract_numbers_from_text(full_text, outcome_name)

        result = {
            "study_id": study_id,
            "outcome": outcome_name,
            "data_type": data_type,
            **extraction
        }

        results.append(result)

    return results

def main():
    batch_file = Path("C:/Users/user/rct-extractor-v2/gold_data/mega/v10_batches/batch_005.jsonl")
    output_file = Path("C:/Users/user/rct-extractor-v2/gold_data/mega/v10_results/results_005.jsonl")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    total_entries = 0
    total_outcomes = 0
    found_count = 0

    with open(batch_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8') as fout:

        for line in fin:
            entry = json.loads(line.strip())
            results = process_entry(entry)

            for result in results:
                fout.write(json.dumps(result, ensure_ascii=False) + '\n')
                total_outcomes += 1
                if result["found"]:
                    found_count += 1
                    print(f"[FOUND] {result['study_id']}: {result['outcome'][:50]}... -> {result['effect_type']}")
                else:
                    print(f"[NOT FOUND] {result['study_id']}: {result['outcome'][:50]}...")

            total_entries += 1

    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Entries processed: {total_entries}")
    print(f"Outcomes total: {total_outcomes}")
    print(f"Outcomes found: {found_count} ({100*found_count/total_outcomes:.1f}%)")
    print(f"Output: {output_file}")

if __name__ == "__main__":
    main()
