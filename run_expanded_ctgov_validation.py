"""
Expanded ClinicalTrials.gov External Validation for RCT Extractor v2

Validates extractor against author-submitted results from ClinicalTrials.gov
using a larger sample of NCT IDs from multiple sources.

Target: 300+ studies with complete HR/OR/RR results

Uses CTgov API v2: https://clinicaltrials.gov/api/v2/studies
"""
import sys
import json
import re
import time
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import urllib.request
import urllib.parse
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.extractor import NumericParser
from src.benchmark.statistics import clopper_pearson_ci

# CTgov API endpoint
CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"


def fetch_ctgov_study(nct_id: str, retries: int = 3) -> Optional[Dict]:
    """Fetch study data from ClinicalTrials.gov API with retry logic"""
    for attempt in range(retries):
        try:
            url = f"{CTGOV_API}/{nct_id}?fields=protocolSection,resultsSection"

            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'RCT-Extractor-Validation/2.0')

            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # Study not found
            if attempt < retries - 1:
                time.sleep(1)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
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

        # Look for statistical analyses
        analyses = outcome.get('analyses', [])
        for analysis in analyses:
            stat_method = analysis.get('statisticalMethod', '')
            param_value = analysis.get('paramValue', '')
            ci_lower = analysis.get('ciLowerLimit', '')
            ci_upper = analysis.get('ciUpperLimit', '')

            # Determine measure type from statistical method
            measure_type = None
            stat_lower = stat_method.lower()

            if 'hazard' in stat_lower or 'cox' in stat_lower:
                measure_type = 'HR'
            elif 'odds' in stat_lower:
                measure_type = 'OR'
            elif 'risk ratio' in stat_lower or 'relative risk' in stat_lower:
                measure_type = 'RR'
            elif 'risk difference' in stat_lower:
                measure_type = 'RD'
            elif 'mean difference' in stat_lower or 'difference in means' in stat_lower:
                measure_type = 'MD'

            if measure_type and param_value:
                try:
                    result = {
                        'measure_type': measure_type,
                        'value': float(param_value),
                        'ci_low': float(ci_lower) if ci_lower else None,
                        'ci_high': float(ci_upper) if ci_upper else None,
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

    templates = {
        'HR': "The hazard ratio was {value} (95% CI, {ci_low} to {ci_high})",
        'OR': "The odds ratio was {value} (95% CI, {ci_low} to {ci_high})",
        'RR': "The relative risk was {value} (95% CI, {ci_low} to {ci_high})",
        'RD': "The risk difference was {value} (95% CI, {ci_low} to {ci_high})",
        'MD': "The mean difference was {value} (95% CI, {ci_low} to {ci_high})",
    }

    if ci_low and ci_high:
        return templates.get(measure_type, '').format(
            value=value, ci_low=ci_low, ci_high=ci_high
        )

    # Without CI
    templates_no_ci = {
        'HR': f"The hazard ratio was {value}",
        'OR': f"The odds ratio was {value}",
        'RR': f"The relative risk was {value}",
        'RD': f"The risk difference was {value}",
        'MD': f"The mean difference was {value}",
    }
    return templates_no_ci.get(measure_type, '')


def check_match(extracted: float, expected: float, tolerance: float = 0.05) -> bool:
    """Check if values match within tolerance"""
    if extracted is None or expected is None:
        return False
    if expected == 0:
        return abs(extracted) < tolerance
    return abs(extracted - expected) / abs(expected) <= tolerance


def load_nct_ids_from_multiple_sources() -> List[str]:
    """Load NCT IDs from multiple sources"""
    nct_ids = set()

    # Source 1: Gold standard files
    gold_dir = Path(__file__).parent / 'data' / 'gold'
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
                        nct_ids.add(nct_id)
                except json.JSONDecodeError:
                    pass

    # Source 2: ctgov-search-strategies NCT list
    nct_list_file = Path("C:/Users/user/Downloads/ctgov-search-strategies/data/nct_ids_list.txt")
    if nct_list_file.exists():
        with open(nct_list_file, 'r') as f:
            for line in f:
                nct_id = line.strip()
                if nct_id.startswith('NCT'):
                    nct_ids.add(nct_id)

    # Source 3: Cochrane NCT IDs
    cochrane_file = Path("C:/Users/user/Downloads/ctgov-search-strategies/data/cochrane_nct_ids.csv")
    if cochrane_file.exists():
        with open(cochrane_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                nct_id = row.get('nct_id', '')
                if nct_id.startswith('NCT'):
                    nct_ids.add(nct_id)

    return sorted(list(nct_ids))


def main():
    print("=" * 70)
    print("RCT EXTRACTOR v2 - EXPANDED CTGOV VALIDATION")
    print("=" * 70)
    print("\nTarget: 300+ studies with complete effect estimate results")
    print("Note: CTgov reports only ~33% of HR values found in publications")

    # Load NCT IDs from multiple sources
    nct_ids = load_nct_ids_from_multiple_sources()
    print(f"\nLoaded {len(nct_ids)} unique NCT IDs from all sources")

    # Track results
    results_by_type = defaultdict(lambda: {'correct': 0, 'total': 0})
    total_results = 0
    correct_extractions = 0
    studies_with_results = 0
    studies_without_results = 0
    api_errors = 0

    # Detailed tracking
    all_outcomes = []

    print("\n" + "-" * 70)
    print("Fetching data from ClinicalTrials.gov API...")
    print("-" * 70)

    batch_size = 50
    for batch_start in range(0, len(nct_ids), batch_size):
        batch_end = min(batch_start + batch_size, len(nct_ids))
        batch = nct_ids[batch_start:batch_end]

        print(f"\nProcessing batch {batch_start//batch_size + 1}/{(len(nct_ids)-1)//batch_size + 1} "
              f"(NCT IDs {batch_start+1}-{batch_end} of {len(nct_ids)})...")

        for i, nct_id in enumerate(batch):
            # Progress indicator
            if (batch_start + i + 1) % 10 == 0:
                print(f"  Progress: {batch_start + i + 1}/{len(nct_ids)} studies processed...")

            study_data = fetch_ctgov_study(nct_id)

            if study_data is None:
                api_errors += 1
                continue

            results = extract_ctgov_results(study_data)

            if not results:
                studies_without_results += 1
                continue

            studies_with_results += 1

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

                is_correct = check_match(extracted_value, expected_value)

                if is_correct:
                    correct_extractions += 1
                    results_by_type[measure_type]['correct'] += 1

                results_by_type[measure_type]['total'] += 1

                all_outcomes.append({
                    'nct_id': nct_id,
                    'measure_type': measure_type,
                    'expected': expected_value,
                    'extracted': extracted_value,
                    'correct': is_correct,
                    'outcome': result.get('outcome_title', '')[:50]
                })

            # Rate limiting
            time.sleep(0.3)

    # Summary
    print("\n" + "=" * 70)
    print("EXPANDED CTGOV VALIDATION SUMMARY")
    print("=" * 70)

    print(f"""
Studies Queried: {len(nct_ids)}
  - With results: {studies_with_results} ({studies_with_results/len(nct_ids)*100:.1f}%)
  - Without results: {studies_without_results}
  - API errors: {api_errors}

Expected coverage: ~33% of studies have CTgov results
Actual coverage: {studies_with_results/len(nct_ids)*100:.1f}%
""")

    if total_results > 0:
        accuracy = correct_extractions / total_results
        ci_low, ci_high = clopper_pearson_ci(correct_extractions, total_results)

        print(f"""
Extraction Validation:
  - Total outcomes tested: {total_results}
  - Correctly extracted: {correct_extractions}
  - Accuracy: {accuracy*100:.1f}% ({correct_extractions}/{total_results})
  - 95% CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%]
""")

        print("\nResults by Measure Type:")
        print("-" * 50)
        print(f"{'Measure':<10} {'Correct':<10} {'Total':<10} {'Accuracy':<10}")
        print("-" * 50)

        for measure_type in ['HR', 'OR', 'RR', 'RD', 'MD']:
            data = results_by_type[measure_type]
            if data['total'] > 0:
                acc = data['correct'] / data['total'] * 100
                print(f"{measure_type:<10} {data['correct']:<10} {data['total']:<10} {acc:.1f}%")

        print("-" * 50)

        # Show any failures for debugging
        failures = [o for o in all_outcomes if not o['correct']]
        if failures:
            print(f"\nFailures ({len(failures)} total):")
            for f in failures[:10]:  # Show first 10
                print(f"  {f['nct_id']} {f['measure_type']}: expected={f['expected']}, got={f['extracted']}")
            if len(failures) > 10:
                print(f"  ... and {len(failures) - 10} more")

    # Save detailed results
    output_file = Path(__file__).parent / 'output' / 'expanded_ctgov_validation.json'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'studies_queried': len(nct_ids),
                'studies_with_results': studies_with_results,
                'total_outcomes': total_results,
                'correct_extractions': correct_extractions,
                'accuracy': correct_extractions / total_results if total_results > 0 else 0,
            },
            'by_type': dict(results_by_type),
            'outcomes': all_outcomes
        }, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
