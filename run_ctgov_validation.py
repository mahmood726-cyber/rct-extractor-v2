"""
ClinicalTrials.gov External Validation for RCT Extractor v2

Validates extractor against author-submitted results from ClinicalTrials.gov
Note: CTgov reports only ~33% of HR values found in publications

Uses CTgov API v2: https://clinicaltrials.gov/api/v2/studies
"""
import sys
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request
import urllib.parse

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.extractor import NumericParser
from src.benchmark.statistics import clopper_pearson_ci

# CTgov API endpoint
CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"


def fetch_ctgov_study(nct_id: str) -> Optional[Dict]:
    """Fetch study data from ClinicalTrials.gov API"""
    try:
        url = f"{CTGOV_API}/{nct_id}?fields=protocolSection,resultsSection"

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'RCT-Extractor-Validation/2.0')

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"  Error fetching {nct_id}: {e}")
        return None


def extract_ctgov_results(study_data: Dict) -> List[Dict]:
    """Extract outcome results from CTgov study data"""
    results = []

    if not study_data:
        return results

    results_section = study_data.get('resultsSection', {})
    outcome_measures = results_section.get('outcomeMeasuresModule', {})
    outcome_list = outcome_measures.get('outcomeMeasures', [])

    for outcome in outcome_list:
        title = outcome.get('title', '')
        description = outcome.get('description', '')
        param_type = outcome.get('paramType', '')

        # Look for statistical analyses
        analyses = outcome.get('analyses', [])
        for analysis in analyses:
            stat_method = analysis.get('statisticalMethod', '')
            param_value = analysis.get('paramValue', '')
            ci_lower = analysis.get('ciLowerLimit', '')
            ci_upper = analysis.get('ciUpperLimit', '')
            ci_pct = analysis.get('ciPctValue', '')

            # Determine measure type from statistical method
            measure_type = None
            if 'hazard' in stat_method.lower() or 'cox' in stat_method.lower():
                measure_type = 'HR'
            elif 'odds' in stat_method.lower():
                measure_type = 'OR'
            elif 'risk ratio' in stat_method.lower() or 'relative risk' in stat_method.lower():
                measure_type = 'RR'
            elif 'risk difference' in stat_method.lower():
                measure_type = 'RD'
            elif 'mean difference' in stat_method.lower():
                measure_type = 'MD'

            if measure_type and param_value:
                try:
                    result = {
                        'measure_type': measure_type,
                        'value': float(param_value),
                        'ci_low': float(ci_lower) if ci_lower else None,
                        'ci_high': float(ci_upper) if ci_upper else None,
                        'ci_pct': ci_pct,
                        'outcome_title': title,
                        'stat_method': stat_method
                    }
                    results.append(result)
                except ValueError:
                    continue

    return results


def create_text_from_ctgov(result: Dict) -> str:
    """Create synthetic text from CTgov result for extraction testing"""
    measure_type = result['measure_type']
    value = result['value']
    ci_low = result.get('ci_low')
    ci_high = result.get('ci_high')

    if measure_type == 'HR':
        if ci_low and ci_high:
            return f"The hazard ratio was {value} (95% CI, {ci_low} to {ci_high})"
        return f"The hazard ratio was {value}"
    elif measure_type == 'OR':
        if ci_low and ci_high:
            return f"The odds ratio was {value} (95% CI, {ci_low} to {ci_high})"
        return f"The odds ratio was {value}"
    elif measure_type == 'RR':
        if ci_low and ci_high:
            return f"The relative risk was {value} (95% CI, {ci_low} to {ci_high})"
        return f"The relative risk was {value}"
    elif measure_type == 'RD':
        if ci_low and ci_high:
            return f"The risk difference was {value} (95% CI, {ci_low} to {ci_high})"
        return f"The risk difference was {value}"
    elif measure_type == 'MD':
        if ci_low and ci_high:
            return f"The mean difference was {value} (95% CI, {ci_low} to {ci_high})"
        return f"The mean difference was {value}"

    return ""


def check_match(extracted: float, expected: float, tolerance: float = 0.05) -> bool:
    """Check if values match within tolerance"""
    if extracted is None or expected is None:
        return False
    if expected == 0:
        return abs(extracted) < tolerance
    return abs(extracted - expected) / abs(expected) <= tolerance


def load_nct_ids_from_gold() -> List[str]:
    """Load NCT IDs from gold standard files"""
    gold_dir = Path(__file__).parent / 'data' / 'gold'
    nct_ids = []

    for jsonl_file in gold_dir.glob("*.jsonl"):
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    nct_id = data.get('nct_id')
                    if nct_id and nct_id.startswith('NCT'):
                        nct_ids.append(nct_id)
                except json.JSONDecodeError:
                    pass

    return list(set(nct_ids))


def main():
    print("=" * 70)
    print("RCT EXTRACTOR v2 - CLINICALTRIALS.GOV EXTERNAL VALIDATION")
    print("=" * 70)
    print("\nNote: CTgov reports only ~33% of effect estimates from publications")
    print("This validation uses author-submitted data as gold standard")

    # Load NCT IDs from gold standard
    nct_ids = load_nct_ids_from_gold()
    print(f"\nFound {len(nct_ids)} unique NCT IDs in gold standard")

    # Limit for demo (can be removed for full validation)
    sample_size = min(20, len(nct_ids))
    nct_ids = nct_ids[:sample_size]
    print(f"Testing sample of {sample_size} trials")

    # Fetch and validate
    total_results = 0
    correct_extractions = 0
    studies_with_results = 0
    studies_without_results = 0

    print("\n" + "-" * 70)
    print("Fetching data from ClinicalTrials.gov...")
    print("-" * 70)

    for i, nct_id in enumerate(nct_ids):
        print(f"\n[{i+1}/{len(nct_ids)}] {nct_id}...", end=" ")

        study_data = fetch_ctgov_study(nct_id)

        if not study_data:
            print("API error")
            continue

        results = extract_ctgov_results(study_data)

        if not results:
            studies_without_results += 1
            print("No results reported")
            continue

        studies_with_results += 1
        print(f"Found {len(results)} outcome(s)")

        for result in results:
            total_results += 1

            # Create synthetic text and extract
            text = create_text_from_ctgov(result)
            measure_type = result['measure_type']
            expected_value = result['value']

            # Extract using our system
            extracted_value = None
            if measure_type == 'HR':
                ext_result = NumericParser.parse_hazard_ratio(text)
                if ext_result:
                    extracted_value = ext_result.get('hr')
            elif measure_type == 'OR':
                ext_result = NumericParser.parse_odds_ratio(text)
                if ext_result:
                    extracted_value = ext_result.get('or')
            elif measure_type == 'RR':
                ext_result = NumericParser.parse_relative_risk(text)
                if ext_result:
                    extracted_value = ext_result.get('rr')
            elif measure_type == 'RD':
                ext_result = NumericParser.parse_risk_difference(text)
                if ext_result:
                    extracted_value = ext_result.get('rd')
            elif measure_type == 'MD':
                ext_result = NumericParser.parse_mean_difference(text)
                if ext_result:
                    extracted_value = ext_result.get('md')

            if check_match(extracted_value, expected_value):
                correct_extractions += 1
                status = "OK"
            else:
                status = f"MISMATCH (expected {expected_value}, got {extracted_value})"

            print(f"    {measure_type}: {expected_value} -> {status}")

        # Rate limiting
        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("CTGOV EXTERNAL VALIDATION SUMMARY")
    print("=" * 70)

    print(f"""
Studies Queried: {len(nct_ids)}
  - With results: {studies_with_results}
  - Without results: {studies_without_results}
  - API errors: {len(nct_ids) - studies_with_results - studies_without_results}

Results Coverage: {studies_with_results/len(nct_ids)*100:.1f}% of studies have results
  (Expected: ~33% of publications have CTgov results)

Extraction Validation:
  - Total outcomes tested: {total_results}
  - Correctly extracted: {correct_extractions}
  - Accuracy: {correct_extractions/total_results*100:.1f}% ({correct_extractions}/{total_results})
""")

    if total_results > 0:
        ci_low, ci_high = clopper_pearson_ci(correct_extractions, total_results)
        print(f"  - 95% CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%]")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
