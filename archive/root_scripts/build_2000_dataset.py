"""
Build 2000-Case Gold Standard Dataset from ClinicalTrials.gov

Fetches effect estimates from CTgov and creates gold standard test cases.
"""
import sys
import json
import time
import random
from pathlib import Path
from typing import Dict, List, Optional, Set
import urllib.request

sys.path.insert(0, str(Path(__file__).parent / 'src'))

CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"


def generate_nct_ids(count: int = 5000) -> List[str]:
    """Generate NCT IDs from various ranges"""
    random.seed(42)
    nct_ids = []

    # Sample heavily from ranges known to have results
    ranges = [
        (100000, 500000, count // 10),
        (500000, 1000000, count // 10),
        (1000000, 2000000, count // 5),
        (2000000, 3000000, count // 5),
        (3000000, 4000000, count // 5),
        (4000000, 5000000, count // 5),
        (5000000, 6000000, count // 10),
    ]

    for start, end, n in ranges:
        sampled = random.sample(range(start, end), min(n, end - start))
        for num in sampled:
            nct_ids.append(f"NCT{num:08d}")

    return nct_ids


def fetch_study(nct_id: str) -> Optional[Dict]:
    """Fetch study from CTgov API"""
    try:
        url = f"{CTGOV_API}/{nct_id}"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'RCT-Extractor-DataBuilder/2.0')

        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except:
        return None


def extract_effects(study_data: Dict) -> List[Dict]:
    """Extract effect estimates from study"""
    results = []

    if not study_data:
        return results

    # Get study info
    protocol = study_data.get('protocolSection', {})
    id_module = protocol.get('identificationModule', {})
    nct_id = id_module.get('nctId', '')
    title = id_module.get('briefTitle', '')[:100]

    results_section = study_data.get('resultsSection', {})
    if not results_section:
        return results

    outcome_measures = results_section.get('outcomeMeasuresModule', {})
    outcome_list = outcome_measures.get('outcomeMeasures', [])

    for outcome in outcome_list:
        outcome_title = outcome.get('title', '')[:80]

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
            elif 'mean difference' in stat_lower:
                measure_type = 'MD'

            if measure_type and param_value:
                try:
                    value = float(param_value)
                    ci_low = float(ci_lower) if ci_lower else None
                    ci_high = float(ci_upper) if ci_upper else None

                    # Create text variations
                    if ci_low is not None and ci_high is not None:
                        text_templates = [
                            f"The {measure_type.lower()} was {value} (95% CI, {ci_low} to {ci_high})",
                            f"{measure_type}: {value} (95% CI {ci_low}-{ci_high})",
                            f"hazard ratio of {value} (95% confidence interval, {ci_low} to {ci_high})" if measure_type == 'HR' else f"{measure_type}: {value} ({ci_low}-{ci_high})",
                        ]
                        text = random.choice(text_templates)
                    else:
                        text = f"The {measure_type.lower()} was {value}"

                    results.append({
                        'nct_id': nct_id,
                        'trial_name': title,
                        'outcome': outcome_title,
                        'text': text,
                        'expected': {
                            'measure_type': measure_type,
                            measure_type.lower(): value,
                            'ci_low': ci_low,
                            'ci_high': ci_high,
                        },
                        'source': 'ctgov_api'
                    })
                except ValueError:
                    continue

    return results


def main():
    print("=" * 70)
    print("BUILDING 2000-CASE GOLD STANDARD DATASET")
    print("=" * 70)

    target = 2000

    # Load existing cases first
    gold_dir = Path(__file__).parent / 'data' / 'gold'
    existing_cases = []
    existing_ncts = set()

    for jsonl_file in gold_dir.glob("*.jsonl"):
        if 'ctgov_expanded' not in jsonl_file.stem:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            case = json.loads(line)
                            existing_cases.append(case)
                            if 'nct_id' in case:
                                existing_ncts.add(case['nct_id'])
                        except:
                            pass

    print(f"\nExisting cases: {len(existing_cases)}")
    print(f"Need to add: {target - len(existing_cases)}")

    # Generate NCT IDs
    nct_ids = generate_nct_ids(8000)
    random.shuffle(nct_ids)

    print(f"Generated {len(nct_ids)} NCT IDs to check")

    # Fetch and build
    new_cases = []
    studies_checked = 0
    studies_with_effects = 0

    print("\n" + "-" * 70)
    print("Fetching from ClinicalTrials.gov...")
    print("-" * 70)

    for nct_id in nct_ids:
        if len(existing_cases) + len(new_cases) >= target:
            break

        if nct_id in existing_ncts:
            continue

        studies_checked += 1

        if studies_checked % 200 == 0:
            print(f"  Progress: {studies_checked} checked, {len(new_cases)} new cases found "
                  f"(total: {len(existing_cases) + len(new_cases)})")

        study_data = fetch_study(nct_id)
        effects = extract_effects(study_data)

        if effects:
            studies_with_effects += 1
            for effect in effects:
                if len(existing_cases) + len(new_cases) >= target:
                    break
                new_cases.append(effect)
                existing_ncts.add(nct_id)

        time.sleep(0.12)

    print(f"\n  Studies checked: {studies_checked}")
    print(f"  Studies with effect estimates: {studies_with_effects}")
    print(f"  New cases collected: {len(new_cases)}")

    # Save new cases
    output_file = gold_dir / 'ctgov_expanded_2000.jsonl'

    with open(output_file, 'w', encoding='utf-8') as f:
        for case in new_cases:
            f.write(json.dumps(case, ensure_ascii=False) + '\n')

    print(f"\nSaved {len(new_cases)} new cases to: {output_file}")

    # Summary
    total = len(existing_cases) + len(new_cases)
    print("\n" + "=" * 70)
    print("DATASET SUMMARY")
    print("=" * 70)
    print(f"  Existing cases: {len(existing_cases)}")
    print(f"  New CTgov cases: {len(new_cases)}")
    print(f"  Total cases: {total}")
    print(f"  Target: {target}")
    print(f"  Status: {'COMPLETE' if total >= target else 'INCOMPLETE'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
