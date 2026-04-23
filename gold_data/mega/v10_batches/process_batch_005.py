#!/usr/bin/env python3
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""Process batch 005 - extract effect estimates from trial papers."""

import json
import re
import sys
from pathlib import Path

def extract_outcome_data(entry):
    """Extract effect estimates for all outcomes in an entry."""
    study_id = entry.get("study_id", "")
    outcomes = entry.get("outcomes", [])
    abstract = entry.get("abstract", "")
    results_text = entry.get("results_text", "")

    # Combine text for searching
    full_text = f"{abstract}\n\n{results_text}"

    results = []

    for outcome in outcomes:
        outcome_name = outcome.get("outcome", "")

        result = {
            "study_id": study_id,
            "outcome": outcome_name,
            "found": False,
            "effect_type": None,
            "point_estimate": None,
            "ci_lower": None,
            "ci_upper": None,
            "raw_data": None,
            "source_quote": "",
            "reasoning": ""
        }

        # Search for this outcome in the text
        outcome_lower = outcome_name.lower()

        # Common patterns for effect estimates
        # Pattern 1: OR/RR/HR = X.XX (95% CI: Y.YY-Z.ZZ)
        or_pattern = r'(?:OR|RR|HR|odds ratio|risk ratio|hazard ratio)[:\s=]+([0-9.]+)\s*(?:\(95%\s*CI[:\s]+([0-9.]+)\s*[-–to]+\s*([0-9.]+)\))?'

        # Pattern 2: MD/SMD = X.XX (95% CI: Y.YY, Z.ZZ)
        md_pattern = r'(?:MD|SMD|mean difference)[:\s=]+([−-]?[0-9.]+)\s*(?:\(95%\s*CI[:\s]+([−-]?[0-9.]+)\s*[,to]+\s*([−-]?[0-9.]+)\))?'

        # Pattern 3: X/N vs Y/N format (raw binary data)
        raw_binary_pattern = r'(\d+)/(\d+)\s+(?:vs|versus|\(|compared)\s*(\d+)/(\d+)'

        # Pattern 4: mean (SD) format for continuous
        mean_sd_pattern = r'mean\s*(?:\(SD\)|±)\s*([−-]?[0-9.]+)\s*\(([0-9.]+)\)'

        # Search in context windows around outcome mentions
        sentences = re.split(r'[.!?]\s+', full_text)
        relevant_sentences = []

        for i, sent in enumerate(sentences):
            if outcome_lower in sent.lower() or any(word in sent.lower() for word in ['mortality', 'death', 'survival', 'response', 'adverse']):
                # Include context (previous and next sentence)
                context_start = max(0, i-1)
                context_end = min(len(sentences), i+2)
                context = ' '.join(sentences[context_start:context_end])
                relevant_sentences.append(context)

        search_text = ' '.join(relevant_sentences) if relevant_sentences else full_text

        # Try to find OR/RR/HR
        or_match = re.search(or_pattern, search_text, re.IGNORECASE)
        if or_match:
            effect_val = float(or_match.group(1))
            ci_low = float(or_match.group(2)) if or_match.group(2) else None
            ci_high = float(or_match.group(3)) if or_match.group(3) else None

            # Determine effect type from context
            match_text = or_match.group(0)
            if 'hazard' in match_text.lower():
                effect_type = 'HR'
            elif 'risk ratio' in match_text.lower() or match_text.upper().startswith('RR'):
                effect_type = 'RR'
            else:
                effect_type = 'OR'

            result["found"] = True
            result["effect_type"] = effect_type
            result["point_estimate"] = effect_val
            result["ci_lower"] = ci_low
            result["ci_upper"] = ci_high
            result["source_quote"] = match_text[:200]
            result["reasoning"] = f"Found {effect_type} with CI in text near outcome mention"

        # Try to find MD/SMD
        md_match = re.search(md_pattern, search_text, re.IGNORECASE)
        if md_match and not result["found"]:
            effect_val = float(md_match.group(1).replace('−', '-'))
            ci_low = float(md_match.group(2).replace('−', '-')) if md_match.group(2) else None
            ci_high = float(md_match.group(3).replace('−', '-')) if md_match.group(3) else None

            match_text = md_match.group(0)
            effect_type = 'SMD' if 'SMD' in match_text else 'MD'

            result["found"] = True
            result["effect_type"] = effect_type
            result["point_estimate"] = effect_val
            result["ci_lower"] = ci_low
            result["ci_upper"] = ci_high
            result["source_quote"] = match_text[:200]
            result["reasoning"] = f"Found {effect_type} with CI in text"

        # Try to find raw binary data
        raw_match = re.search(raw_binary_pattern, search_text)
        if raw_match and not result["found"]:
            exp_events = int(raw_match.group(1))
            exp_n = int(raw_match.group(2))
            ctrl_events = int(raw_match.group(3))
            ctrl_n = int(raw_match.group(4))

            result["found"] = True
            result["effect_type"] = "OR"  # Can calculate OR from raw data
            result["raw_data"] = {
                "exp_events": exp_events,
                "exp_n": exp_n,
                "ctrl_events": ctrl_events,
                "ctrl_n": ctrl_n
            }
            result["source_quote"] = raw_match.group(0)[:200]
            result["reasoning"] = "Found raw binary outcome data (events/N per arm)"

        if not result["found"]:
            result["reasoning"] = f"Could not find effect estimate or raw data for outcome '{outcome_name}' in provided text"

        results.append(result)

    return results

def main():
    batch_path = Path("C:/Users/user/rct-extractor-v2/gold_data/mega/v10_batches/batch_005.jsonl")
    output_path = Path("C:/Users/user/rct-extractor-v2/gold_data/mega/v10_results/results_005.jsonl")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    total_outcomes = 0
    found_outcomes = 0

    with open(batch_path, 'r', encoding='utf-8') as fin, \
         open(output_path, 'w', encoding='utf-8') as fout:

        for line in fin:
            entry = json.loads(line.strip())
            results = extract_outcome_data(entry)

            for result in results:
                fout.write(json.dumps(result) + '\n')
                total_outcomes += 1
                if result["found"]:
                    found_outcomes += 1

            processed += 1
            print(f"Processed entry {processed}: {entry.get('study_id', 'unknown')} - {len(results)} outcomes")

    print(f"\n=== SUMMARY ===")
    print(f"Processed {processed} entries")
    print(f"Total outcomes: {total_outcomes}")
    print(f"Found: {found_outcomes} ({100*found_outcomes/total_outcomes:.1f}%)")
    print(f"Output: {output_path}")

if __name__ == "__main__":
    main()
