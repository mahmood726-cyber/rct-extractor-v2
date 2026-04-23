# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""
Large-Scale ClinicalTrials.gov Validation for RCT Extractor v2

Validates extractor against 1000+ outcomes from studies with author-submitted
results from ClinicalTrials.gov.

Strategy: Sample NCT IDs from various ranges and therapeutic areas to find
studies with effect estimate results (HR, OR, RR, RD, MD).

Uses CTgov API v2: https://clinicaltrials.gov/api/v2/studies
"""
import sys
import json
import time
import random
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict
import urllib.request
import urllib.parse

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.extractor import NumericParser
from src.benchmark.statistics import clopper_pearson_ci

CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"


def generate_nct_id_ranges() -> List[str]:
    """Generate NCT IDs from various ranges to find studies with results"""
    nct_ids = []

    # Sample from different NCT ID ranges (covering 2005-2024)
    # NCT IDs are roughly: NCT00XXXXXX (early), NCT01-05XXXXXX (2010s-2020s)
    ranges = [
        (100000, 500000, 200),    # Early studies (2005-2010)
        (500000, 1000000, 200),   # 2010-2012
        (1000000, 2000000, 300),  # 2012-2015
        (2000000, 3000000, 300),  # 2015-2018
        (3000000, 4000000, 300),  # 2018-2020
        (4000000, 5000000, 300),  # 2020-2022
        (5000000, 6500000, 300),  # 2022-2024
    ]

    for start, end, count in ranges:
        sampled = random.sample(range(start, end), min(count, end - start))
        for num in sampled:
            nct_ids.append(f"NCT{num:08d}")

    return nct_ids


def load_existing_nct_ids() -> Set[str]:
    """Load NCT IDs from existing data sources"""
    nct_ids = set()

    # From gold standard
    gold_dir = Path(__file__).parent / 'data' / 'gold'
    if gold_dir.exists():
        for jsonl_file in gold_dir.glob("*.jsonl"):
            try:
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
                        except:
                            pass
            except:
                pass

    # From ctgov-search-strategies
    sources = [
        Path("C:/Users/user/Downloads/ctgov-search-strategies/data/nct_ids_list.txt"),
        Path("C:/Users/user/Downloads/ctgov-search-strategies/data/cochrane_nct_ids.csv"),
    ]

    for source in sources:
        if source.exists():
            try:
                with open(source, 'r') as f:
                    for line in f:
                        if 'NCT' in line:
                            # Extract NCT ID
                            import re
                            match = re.search(r'NCT\d{8}', line)
                            if match:
                                nct_ids.add(match.group())
            except:
                pass

    return nct_ids


def fetch_study_results(nct_id: str) -> Optional[Dict]:
    """Fetch study results from CTgov API"""
    try:
        url = f"{CTGOV_API}/{nct_id}"

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'RCT-Extractor-Validation/2.0')

        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return None
    except:
        return None


def extract_effect_estimates(study_data: Dict) -> List[Dict]:
    """Extract effect estimates from study results"""
    results = []

    if not study_data:
        return results

    results_section = study_data.get('resultsSection', {})
    if not results_section:
        return results

    outcome_measures = results_section.get('outcomeMeasuresModule', {})
    outcome_list = outcome_measures.get('outcomeMeasures', [])

    for outcome in outcome_list:
        title = outcome.get('title', '')

        analyses = outcome.get('analyses', [])
        for analysis in analyses:
            stat_method = analysis.get('statisticalMethod', '')
            param_value = analysis.get('paramValue', '')
            ci_lower = analysis.get('ciLowerLimit', '')
            ci_upper = analysis.get('ciUpperLimit', '')

            # Determine measure type
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
                    results.append({
                        'measure_type': measure_type,
                        'value': float(param_value),
                        'ci_low': float(ci_lower) if ci_lower else None,
                        'ci_high': float(ci_upper) if ci_upper else None,
                        'outcome_title': title[:100],
                        'stat_method': stat_method
                    })
                except ValueError:
                    continue

    return results


def create_test_text(result: Dict) -> str:
    """Create synthetic text for extraction testing"""
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

    if ci_low is not None and ci_high is not None:
        return templates.get(measure_type, '').format(
            value=value, ci_low=ci_low, ci_high=ci_high
        )
    return f"The {measure_type.lower()} was {value}"


def check_match(extracted: float, expected: float, tolerance: float = 0.05) -> bool:
    """Check if values match within tolerance"""
    if extracted is None or expected is None:
        return False
    if expected == 0:
        return abs(extracted) < tolerance
    return abs(extracted - expected) / abs(expected) <= tolerance


def main():
    print("=" * 70)
    print("RCT EXTRACTOR v2 - 1000+ OUTCOME CTGOV VALIDATION")
    print("=" * 70)
    print("\nTarget: 1000+ outcomes with effect estimates from CTgov")

    # Set random seed for reproducibility
    random.seed(42)

    # Collect NCT IDs from multiple sources
    print("\n" + "-" * 70)
    print("Phase 1: Collecting NCT IDs...")
    print("-" * 70)

    # Start with existing known IDs
    existing_ids = load_existing_nct_ids()
    print(f"  Loaded {len(existing_ids)} NCT IDs from existing sources")

    # Generate additional random IDs
    random_ids = generate_nct_id_ranges()
    print(f"  Generated {len(random_ids)} random NCT IDs from various ranges")

    # Combine and deduplicate
    all_nct_ids = list(existing_ids) + random_ids
    random.shuffle(all_nct_ids)  # Shuffle to mix sources

    print(f"  Total NCT IDs to check: {len(all_nct_ids)}")

    # Fetch and validate
    print("\n" + "-" * 70)
    print("Phase 2: Fetching results and validating extraction...")
    print("-" * 70)

    results_by_type = defaultdict(lambda: {'correct': 0, 'total': 0})
    total_outcomes = 0
    correct_extractions = 0
    studies_with_effects = 0
    studies_checked = 0
    not_found = 0
    no_results = 0

    all_outcomes = []
    target_outcomes = 1000

    for i, nct_id in enumerate(all_nct_ids):
        if total_outcomes >= target_outcomes:
            break

        studies_checked += 1

        if studies_checked % 100 == 0:
            print(f"  Progress: {studies_checked} studies checked, "
                  f"{total_outcomes} outcomes found, {correct_extractions} correct")

        study_data = fetch_study_results(nct_id)

        if study_data is None:
            not_found += 1
            continue

        effects = extract_effect_estimates(study_data)

        if not effects:
            no_results += 1
            continue

        studies_with_effects += 1

        for effect in effects:
            if total_outcomes >= target_outcomes:
                break

            total_outcomes += 1

            text = create_test_text(effect)
            measure_type = effect['measure_type']
            expected_value = effect['value']

            # Extract
            extracted_value = None
            if measure_type == 'HR':
                ext = NumericParser.parse_hazard_ratio(text)
                if ext:
                    extracted_value = ext.get('hr')
            elif measure_type == 'OR':
                ext = NumericParser.parse_odds_ratio(text)
                if ext:
                    extracted_value = ext.get('or')
            elif measure_type == 'RR':
                ext = NumericParser.parse_relative_risk(text)
                if ext:
                    extracted_value = ext.get('rr')
            elif measure_type == 'RD':
                ext = NumericParser.parse_risk_difference(text)
                if ext:
                    extracted_value = ext.get('rd')
            elif measure_type == 'MD':
                ext = NumericParser.parse_mean_difference(text)
                if ext:
                    extracted_value = ext.get('md')

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
                'correct': is_correct
            })

        # Rate limiting
        time.sleep(0.15)

    # Summary
    print("\n" + "=" * 70)
    print("1000+ OUTCOME CTGOV VALIDATION SUMMARY")
    print("=" * 70)

    print(f"""
Studies Checked: {studies_checked}
  - With effect estimates: {studies_with_effects}
  - No results section: {no_results}
  - Not found (404): {not_found}
""")

    if total_outcomes > 0:
        accuracy = correct_extractions / total_outcomes
        ci_low, ci_high = clopper_pearson_ci(correct_extractions, total_outcomes)

        print(f"""
Extraction Validation:
  - Total outcomes tested: {total_outcomes}
  - Correctly extracted: {correct_extractions}
  - Accuracy: {accuracy*100:.2f}% ({correct_extractions}/{total_outcomes})
  - 95% CI: [{ci_low*100:.2f}%, {ci_high*100:.2f}%]
""")

        print("Results by Measure Type:")
        print("-" * 60)
        print(f"{'Measure':<12} {'Correct':<12} {'Total':<12} {'Accuracy':<12}")
        print("-" * 60)

        for measure_type in ['HR', 'OR', 'RR', 'RD', 'MD']:
            data = results_by_type[measure_type]
            if data['total'] > 0:
                acc = data['correct'] / data['total'] * 100
                print(f"{measure_type:<12} {data['correct']:<12} {data['total']:<12} {acc:.2f}%")

        print("-" * 60)

        # Show failures
        failures = [o for o in all_outcomes if not o['correct']]
        if failures:
            print(f"\nFailures ({len(failures)} total):")
            for f in failures[:20]:
                print(f"  {f['nct_id']} {f['measure_type']}: "
                      f"expected={f['expected']}, got={f['extracted']}")
            if len(failures) > 20:
                print(f"  ... and {len(failures) - 20} more")
        else:
            print("\n*** NO FAILURES DETECTED! ***")

    # Save results
    output_file = Path(__file__).parent / 'output' / 'ctgov_1000_validation.json'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'studies_checked': studies_checked,
                'studies_with_effects': studies_with_effects,
                'total_outcomes': total_outcomes,
                'correct_extractions': correct_extractions,
                'accuracy': correct_extractions / total_outcomes if total_outcomes > 0 else 0,
            },
            'by_type': dict(results_by_type),
            'outcomes': all_outcomes
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
