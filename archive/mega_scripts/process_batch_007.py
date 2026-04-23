#!/usr/bin/env python3
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Process batch_007.jsonl and extract effect estimates from each entry.
"""

import json
import re
import sys

def extract_effect_estimate(study_id, outcome_name, data_type, abstract, results_text):
    """
    Extract effect estimate for a specific outcome from the text.

    Returns dict with:
    - found: bool
    - effect_type: str (OR, RR, HR, MD, SMD, RD, etc.)
    - point_estimate: float
    - ci_lower: float
    - ci_upper: float
    - raw_data: dict (if available)
    - source_quote: str
    - reasoning: str
    """

    # Combine abstract and results for searching
    full_text = f"{abstract}\n\n{results_text}"

    # Normalize outcome name for searching (case-insensitive, flexible matching)
    outcome_lower = outcome_name.lower()

    # Common patterns for effect estimates
    # Pattern for OR/RR/HR with CI: "OR 1.45 (95% CI 1.12-1.89)" or "OR=1.45, 95%CI: 1.12 to 1.89"
    effect_pattern = r'(OR|RR|HR|IRR|ARD|GMR|relative risk|odds ratio|hazard ratio)[:\s=]+(\d+\.?\d*)\s*(?:\([^)]*?(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)[^)]*?\)|,?\s*95%\s*CI[:\s]+(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*))'

    # Pattern for MD/SMD: "MD -0.5 (95% CI -0.8 to -0.2)" or "mean difference -0.5 (-0.8, -0.2)"
    md_pattern = r'(MD|SMD|mean difference|standardized mean difference)[:\s=]+(-?\d+\.?\d*)\s*(?:\([^)]*?(-?\d+\.?\d*)\s*[-–to,]+\s*(-?\d+\.?\d*)[^)]*?\)|,?\s*95%\s*CI[:\s]+(-?\d+\.?\d*)\s*[-–to]+\s*(-?\d+\.?\d*))'

    # Pattern for risk difference: "RD 0.05 (0.01 to 0.09)"
    rd_pattern = r'(RD|risk difference)[:\s=]+(-?\d+\.?\d*)\s*(?:\([^)]*?(-?\d+\.?\d*)\s*[-–to]+\s*(-?\d+\.?\d*)[^)]*?\))'

    # Pattern for raw binary data: "15/100 vs 20/100" or "15 of 100 in treatment, 20 of 100 in control"
    binary_pattern = r'(\d+)\s*[/of]+\s*(\d+).*?(?:vs|versus|compared to|control).*?(\d+)\s*[/of]+\s*(\d+)'

    # Pattern for continuous data: "mean (SD): 5.2 (1.3) vs 4.8 (1.1)" or "5.2 ± 1.3 vs 4.8 ± 1.1"
    continuous_pattern = r'(?:mean|Mean)[:\s]*(?:\(SD\)[:\s]*)?(-?\d+\.?\d*)\s*(?:\(|±)\s*(-?\d+\.?\d*)\s*\)?.*?(?:vs|versus).*?(-?\d+\.?\d*)\s*(?:\(|±)\s*(-?\d+\.?\d*)'

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

    # Search for outcome mention in text (get context window)
    outcome_match_positions = []
    for match in re.finditer(re.escape(outcome_name.lower()), full_text.lower()):
        outcome_match_positions.append(match.start())

    # If outcome not found by exact match, try key terms
    if not outcome_match_positions:
        key_terms = outcome_name.lower().split()
        for i, char in enumerate(full_text.lower()):
            if any(full_text.lower()[i:i+len(term)] == term for term in key_terms if len(term) > 3):
                outcome_match_positions.append(i)
                break

    if not outcome_match_positions:
        result["reasoning"] = f"Outcome '{outcome_name}' not mentioned in text"
        return result

    # Extract context windows around outcome mentions (±500 chars)
    contexts = []
    for pos in outcome_match_positions[:3]:  # Check up to 3 mentions
        start = max(0, pos - 500)
        end = min(len(full_text), pos + 500)
        contexts.append(full_text[start:end])

    # Search each context for effect estimates
    for context in contexts:
        # Try effect estimate patterns (OR, RR, HR, etc.)
        match = re.search(effect_pattern, context, re.IGNORECASE)
        if match:
            effect_abbrev = match.group(1).upper()
            if effect_abbrev == "RELATIVE RISK":
                effect_abbrev = "RR"
            elif effect_abbrev == "ODDS RATIO":
                effect_abbrev = "OR"
            elif effect_abbrev == "HAZARD RATIO":
                effect_abbrev = "HR"

            point = float(match.group(2))
            # CI could be in groups 3,4 or 5,6
            if match.group(3) and match.group(4):
                ci_low = float(match.group(3))
                ci_high = float(match.group(4))
            elif match.group(5) and match.group(6):
                ci_low = float(match.group(5))
                ci_high = float(match.group(6))
            else:
                continue

            result["found"] = True
            result["effect_type"] = effect_abbrev
            result["point_estimate"] = point
            result["ci_lower"] = ci_low
            result["ci_upper"] = ci_high
            result["source_quote"] = match.group(0)[:200]
            result["reasoning"] = f"Found {effect_abbrev} with 95% CI in text near outcome mention"
            return result

        # Try MD/SMD pattern
        match = re.search(md_pattern, context, re.IGNORECASE)
        if match:
            effect_name = match.group(1).upper()
            if "STANDARDIZED" in effect_name:
                effect_abbrev = "SMD"
            else:
                effect_abbrev = "MD"

            point = float(match.group(2))
            if match.group(3) and match.group(4):
                ci_low = float(match.group(3))
                ci_high = float(match.group(4))
            elif match.group(5) and match.group(6):
                ci_low = float(match.group(5))
                ci_high = float(match.group(6))
            else:
                continue

            result["found"] = True
            result["effect_type"] = effect_abbrev
            result["point_estimate"] = point
            result["ci_lower"] = ci_low
            result["ci_upper"] = ci_high
            result["source_quote"] = match.group(0)[:200]
            result["reasoning"] = f"Found {effect_abbrev} with 95% CI in text near outcome mention"
            return result

        # Try RD pattern
        match = re.search(rd_pattern, context, re.IGNORECASE)
        if match:
            point = float(match.group(2))
            ci_low = float(match.group(3))
            ci_high = float(match.group(4))

            result["found"] = True
            result["effect_type"] = "RD"
            result["point_estimate"] = point
            result["ci_lower"] = ci_low
            result["ci_upper"] = ci_high
            result["source_quote"] = match.group(0)[:200]
            result["reasoning"] = "Found risk difference with 95% CI in text near outcome mention"
            return result

        # Try raw binary data
        if data_type == "binary" or "dropout" in outcome_name.lower() or "adverse" in outcome_name.lower():
            match = re.search(binary_pattern, context, re.IGNORECASE)
            if match:
                exp_events = int(match.group(1))
                exp_n = int(match.group(2))
                ctrl_events = int(match.group(3))
                ctrl_n = int(match.group(4))

                result["found"] = True
                result["effect_type"] = "RAW_BINARY"
                result["raw_data"] = {
                    "exp_events": exp_events,
                    "exp_n": exp_n,
                    "ctrl_events": ctrl_events,
                    "ctrl_n": ctrl_n
                }
                result["source_quote"] = match.group(0)[:200]
                result["reasoning"] = "Found raw binary data (events/N per arm)"
                return result

        # Try raw continuous data
        if data_type == "continuous":
            match = re.search(continuous_pattern, context, re.IGNORECASE)
            if match:
                exp_mean = float(match.group(1))
                exp_sd = float(match.group(2))
                ctrl_mean = float(match.group(3))
                ctrl_sd = float(match.group(4))

                result["found"] = True
                result["effect_type"] = "RAW_CONTINUOUS"
                result["raw_data"] = {
                    "exp_mean": exp_mean,
                    "exp_sd": exp_sd,
                    "ctrl_mean": ctrl_mean,
                    "ctrl_sd": ctrl_sd
                }
                result["source_quote"] = match.group(0)[:200]
                result["reasoning"] = "Found raw continuous data (mean, SD per arm)"
                return result

    result["reasoning"] = f"Outcome '{outcome_name}' mentioned but no extractable effect estimate found in surrounding text"
    return result


def main():
    batch_file = r"C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_007.jsonl"
    output_file = r"C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_007.jsonl"

    results = []

    with open(batch_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            entry = json.loads(line)

            study_id = entry['study_id']
            outcomes = entry.get('outcomes', [])
            abstract = entry.get('abstract', '')
            results_text = entry.get('results_text', '')

            print(f"Processing {study_id} ({len(outcomes)} outcomes)...", file=sys.stderr)

            # Extract for each outcome
            for outcome_obj in outcomes:
                outcome_name = outcome_obj['outcome']
                data_type = outcome_obj.get('data_type')

                extraction = extract_effect_estimate(
                    study_id,
                    outcome_name,
                    data_type,
                    abstract,
                    results_text
                )
                results.append(extraction)

    # Write results
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')

    print(f"\nProcessed {len(results)} outcome extractions", file=sys.stderr)
    print(f"Found: {sum(1 for r in results if r['found'])}/{len(results)}", file=sys.stderr)
    print(f"Results written to {output_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
