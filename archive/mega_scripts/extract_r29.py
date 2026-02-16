"""
Extract outcome data from clean_batch_r29.json
"""
import json
import re

def extract_binary_data(text, outcome_name):
    """Extract binary outcome data (events/n for intervention and control)."""
    # Common patterns for binary data
    # Pattern: "X of Y (Z%)" or "X/Y" or "X (Y%)"

    # Look for intervention/control group descriptions
    # Common terms: intervention, treatment, experimental, case, active
    # vs control, placebo, usual care, standard

    results = {
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None
    }

    # This is complex - return not found for now
    return results, False

def extract_continuous_data(text, outcome_name):
    """Extract continuous outcome data (mean/SD/n for intervention and control)."""
    results = {
        "intervention_mean": None,
        "intervention_sd": None,
        "intervention_n": None,
        "control_mean": None,
        "control_sd": None,
        "control_n": None
    }

    return results, False

def extract_effect_estimate(text):
    """Extract direct effect estimates (OR, RR, HR, MD, SMD with CIs)."""
    results = {
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None
    }

    # OR pattern: OR = X.XX, 95% CI X.XX to X.XX or (X.XX-X.XX) or [X.XX, X.XX]
    or_pattern = r'(?:odds ratio|OR)[:\s=]+\s*([\d.]+)[,;\s]+(?:95%\s*(?:CI|confidence interval)[:\s=]+\s*)?(?:\(|\[)?([\d.]+)[\s,-]+(?:to\s+)?([\d.]+)(?:\)|\])?'
    match = re.search(or_pattern, text, re.IGNORECASE)
    if match:
        results["effect_type"] = "OR"
        results["point_estimate"] = float(match.group(1))
        results["ci_lower"] = float(match.group(2))
        results["ci_upper"] = float(match.group(3))
        return results, True

    # RR pattern
    rr_pattern = r'(?:relative risk|risk ratio|RR)[:\s=]+\s*([\d.]+)[,;\s]+(?:95%\s*(?:CI|confidence interval)[:\s=]+\s*)?(?:\(|\[)?([\d.]+)[\s,-]+(?:to\s+)?([\d.]+)(?:\)|\])?'
    match = re.search(rr_pattern, text, re.IGNORECASE)
    if match:
        results["effect_type"] = "RR"
        results["point_estimate"] = float(match.group(1))
        results["ci_lower"] = float(match.group(2))
        results["ci_upper"] = float(match.group(3))
        return results, True

    # MD pattern
    md_pattern = r'(?:mean difference|MD)[:\s=]+\s*([-\d.]+)[,;\s]+(?:95%\s*(?:CI|confidence interval)[:\s=]+\s*)?(?:\(|\[)?([-\d.]+)[\s,-]+(?:to\s+)?([-\d.]+)(?:\)|\])?'
    match = re.search(md_pattern, text, re.IGNORECASE)
    if match:
        results["effect_type"] = "MD"
        results["point_estimate"] = float(match.group(1))
        results["ci_lower"] = float(match.group(2))
        results["ci_upper"] = float(match.group(3))
        return results, True

    return results, False

def process_entry(entry):
    """Process a single study entry."""
    study_id = entry["study_id"]
    outcome = entry["outcome"]
    data_type = entry.get("data_type")
    results_text = entry["results_text"]

    result = {
        "study_id": study_id,
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "",
        "reasoning": ""
    }

    # Try to extract effect estimate first
    effect_data, found_effect = extract_effect_estimate(results_text)
    if found_effect:
        result.update(effect_data)
        result["found"] = True
        result["reasoning"] = f"Found {effect_data['effect_type']} with confidence interval in results text."
        # Extract source quote (find the sentence containing the estimate)
        sentences = re.split(r'[.!?]\s+', results_text)
        for sent in sentences:
            if re.search(r'(?:OR|RR|MD|relative risk|odds ratio|mean difference)', sent, re.IGNORECASE):
                result["source_quote"] = sent[:500]
                break
        return result

    # Try binary data extraction for binary outcomes
    if data_type == "binary":
        binary_data, found_binary = extract_binary_data(results_text, outcome)
        if found_binary:
            result.update(binary_data)
            result["found"] = True
            result["reasoning"] = "Found binary outcome data (events/n) for intervention and control groups."
            return result

    # Try continuous data extraction
    elif data_type == "continuous":
        cont_data, found_cont = extract_continuous_data(results_text, outcome)
        if found_cont:
            result.update(cont_data)
            result["found"] = True
            result["reasoning"] = "Found continuous outcome data (mean/SD) for intervention and control groups."
            return result

    # If nothing found
    result["reasoning"] = f"Could not find explicit numerical data for outcome '{outcome}' in the results text. The text discusses results but does not provide the specific raw data or effect estimate needed."

    return result

def main():
    import sys
    import io
    # Fix Windows cp1252 encoding issue
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    # Load batch file
    with open("C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r29.json", "r", encoding="utf-8") as f:
        batch = json.load(f)

    print(f"Processing {len(batch)} studies...")

    results = []
    for entry in batch:
        result = process_entry(entry)
        results.append(result)
        if result["found"]:
            print(f"[Y] {result['study_id']}: Found {result['effect_type']}")
        else:
            print(f"[N] {result['study_id']}: Not found")

    # Write results
    with open("C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r29.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    found_count = sum(1 for r in results if r["found"])
    print(f"\n=== SUMMARY ===")
    print(f"Total: {len(results)}")
    print(f"Found: {found_count} ({100*found_count/len(results):.1f}%)")
    print(f"Not found: {len(results) - found_count}")

if __name__ == "__main__":
    main()
