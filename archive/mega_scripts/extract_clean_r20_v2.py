"""
Extract outcome data from clean_batch_r20.json following strict rules.
Manual extraction based on careful reading of each entry.
"""

import json
import re
import sys
import io

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def extract_petrella_2017(entry):
    """Manual extraction for Petrella 2017 - weight loss study."""
    # From results_text: "intervention group lost 3.6 kg (95% confidence interval, −5.26 to −1.90 kg) more than the comparator group"
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': True,
        'effect_type': 'MD',
        'point_estimate': -3.6,  # Weight loss (intervention lost MORE, so negative)
        'ci_lower': -5.26,
        'ci_upper': -1.90,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': 'intervention group lost 3.6 kg (95% confidence interval, −5.26 to −1.90 kg) more than the comparator group (P < 0.001)',
        'reasoning': 'Direct MD with 95% CI found in results_text'
    }

def extract_cadigan_2019(entry):
    """Manual extraction for Cadigan 2019 - alcohol consumption."""
    # From results_text:
    # "TXT PFI condition reporting less alcohol consumption when tailgating (M = 5.67, SD = 4.18) than those in the TXT ED condition (M = 7.08, SD = 4.27)"
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': True,
        'effect_type': 'MD',
        'point_estimate': None,  # Can compute: 5.67 - 7.08 = -1.41
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': 5.67,
        'intervention_sd': 4.18,
        'intervention_n_cont': None,  # Not clearly stated in this section
        'control_mean': 7.08,
        'control_sd': 4.27,
        'control_n_cont': None,
        'source_quote': 'TXT PFI condition reporting less alcohol consumption when tailgating (M = 5.67, SD = 4.18) than those in the TXT ED condition (M = 7.08, SD = 4.27)',
        'reasoning': 'Means and SDs for both groups found in results_text (drinks consumed)'
    }

def extract_hunt_2014(entry):
    """Manual extraction for Hunt 2014 - FFIT weight loss."""
    # From results_text: "mean weight loss in men in the intervention group was 5·56 kg (95% CI 4·70–6·43)
    # and 0·58 kg (0·04–1·12) in the comparison group"
    # "mean difference in weight loss between groups adjusted for baseline weight and club was 4·94 kg (3·95–5·94, p<0·0001)"
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': True,
        'effect_type': 'MD',
        'point_estimate': -4.94,  # More weight loss in intervention (negative)
        'ci_lower': -5.94,
        'ci_upper': -3.95,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': -5.56,
        'intervention_sd': None,  # CI given, not SD
        'intervention_n_cont': None,
        'control_mean': -0.58,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': 'mean difference in weight loss between groups adjusted for baseline weight and club was 4·94 kg (3·95–5·94, p<0·0001)',
        'reasoning': 'Direct adjusted MD with 95% CI found in results_text; also raw means with CIs'
    }

def extract_ziemssen_2017(entry):
    """Manual extraction for Ziemssen 2017 - SAEs."""
    # From abstract/results: "One serious adverse event (SAE) of perichondritis was reported, which was unrelated to laquinimod (0.9 mg)."
    # "Twenty-eight patients received placebo and 84 received laquinimod"
    # SAEs: laquinimod 1/84, placebo 0/28
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': True,
        'effect_type': 'RR',  # Binary outcome
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': 1,
        'intervention_n': 84,
        'control_events': 0,
        'control_n': 28,
        'intervention_mean': None,
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': 'Twenty-eight patients received placebo and 84 received laquinimod ranging from 0.9 to 2.7 mg. No deaths occurred. One serious adverse event (SAE) of perichondritis was reported',
        'reasoning': 'Event counts found: 1 SAE in laquinimod group (n=84), 0 in placebo (n=28)'
    }

def extract_cormick_2020(entry):
    """Manual extraction for Cormick 2020 - Body weight."""
    # From results_text: "women allocated to calcium had a mean weight increase of 1.1 (SD ±5.5) kg,
    # whereas those allocated to placebo had a mean increase of 1.5 (SD ±6.1) kg,
    # a mean difference of −0.4 kg (95% CI −0.4 (−1.4 to 0.6); P = .408)"
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': True,
        'effect_type': 'MD',
        'point_estimate': -0.4,
        'ci_lower': -1.4,
        'ci_upper': 0.6,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': 1.1,
        'intervention_sd': 5.5,
        'intervention_n_cont': 230,  # From results: "230 allocated to calcium"
        'control_mean': 1.5,
        'control_sd': 6.1,
        'control_n_cont': 227,  # "227 allocated to placebo"
        'source_quote': 'women allocated to calcium had a mean weight increase of 1.1 (SD ±5.5) kg, whereas those allocated to placebo had a mean increase of 1.5 (SD ±6.1) kg',
        'reasoning': 'Means, SDs, and MD with 95% CI found in results_text'
    }

def extract_riedt_2005(entry):
    """Manual extraction for Riedt 2005 - Body weight."""
    # From results_text: Weight loss mentioned but need to find specific numbers
    # "WL NL-Ca group lost more trochanter BMD (−4.2 ± 4.1%) and BMC (−4.8 ± 7.1%) than the WL Hi-Ca group (−1.4 ± 5.6% and −1.1 ± 8.1%"
    # Outcome is "Body weight" but results focus on BMD
    # Not clear body weight data is reported
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': '',
        'reasoning': 'Body weight outcome specified but only BMD data found in results section'
    }

def extract_kerksick_2020(entry):
    """Manual extraction for Kerksick 2020 - Body weight."""
    # From results_text: "losses of body mass (CTL −0.4 ± 2.4; LCHC −5.1 ± 4.2; LCHP −3.8 ± 4.2 kg)"
    # Three groups, not clear which is "intervention" vs "control"
    # Outcome is "Body weight", data is body mass change
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': '',
        'reasoning': 'Three-arm study (CTL, LCHC, LCHP); unclear which is intervention vs control from outcome specification'
    }

def extract_riedt_2007(entry):
    """Manual extraction for Riedt 2007 - Body weight."""
    # From results_text: "WL groups lost 7.2±3.3% of initial body weight"
    # But need absolute weight, not percentage
    # No comparison to control group found in visible text
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': '',
        'reasoning': 'Only percentage weight loss given (7.2±3.3%), no absolute weight data or control comparison'
    }

def extract_shapses_2004(entry):
    """Manual extraction for Shapses 2004 - Body weight."""
    # From results_text: "body weight, placebo –6.2 ± 0.7 vs. Ca –7.0 ± 0.7 kg"
    # This looks like mean ± SE
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': True,
        'effect_type': 'MD',
        'point_estimate': None,  # Difference: -7.0 - (-6.2) = -0.8 kg
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': -7.0,
        'intervention_sd': 0.7,  # Likely SE, not SD
        'intervention_n_cont': None,
        'control_mean': -6.2,
        'control_sd': 0.7,
        'control_n_cont': None,
        'source_quote': 'body weight, placebo –6.2 ± 0.7 vs. Ca –7.0 ± 0.7 kg',
        'reasoning': 'Means with ± values (likely SE) for both groups; weight change data'
    }

def extract_zemel_2009(entry):
    """Manual extraction for Zemel 2009 - Body weight."""
    # From abstract: "HD: -4.43 ± 0.53 kg; LC: -2.69 ± 0.53 kg; HC: -2.23 ± 0.73kg, p < 0.025"
    # Three groups: HD (high dairy), LC (low calcium), HC (high calcium)
    # Not clear which is "intervention" vs "control"
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': '',
        'reasoning': 'Three-arm study (HD, LC, HC); unclear which is intervention vs control from outcome specification'
    }

def extract_he_2020(entry):
    """Manual extraction for He 2020 - Mortality."""
    # From results_text: "However, patients in the RIC group exhibited a significant lower level of hs-CRP compared with the control group (P = 0.048)"
    # This is hs-CRP, not mortality
    # Need to check if mortality data is in the text
    # "Forty-nine patients (24 in the RIC group and 25 in the sham-RIC group) were recruited"
    # No mortality data found
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': '',
        'reasoning': 'Outcome is "Mortality during follow-up" but no mortality data found in abstract/results_text'
    }

def extract_poalelungi_2021(entry):
    """Manual extraction for Poalelungi 2021 - Mortality."""
    # Outcome is "Mortality during follow-up (for all studies)"
    # No mortality data visible in results_text
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': '',
        'reasoning': 'Outcome is "Mortality during follow-up" but no mortality data found in results_text'
    }

def extract_che_2019(entry):
    """Manual extraction for Che 2019 - Recurrence of ischemic stroke."""
    # From results_text: "One case of hemorrhagic transformation was observed in the RIPC group"
    # "Thirty patients (15 RIPC and 15 Control) were recruited"
    # Hemorrhagic transformation: 1/15 RIPC, ?/15 Control
    # Not clear if 0 in control
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': '',
        'reasoning': 'Outcome is "Recurrence of ischemic stroke" but only hemorrhagic transformation mentioned (1 in RIPC, unclear in control)'
    }

def extract_meng_2015(entry):
    """Manual extraction for Meng 2015 - Recurrence of ischemic stroke."""
    # From results_text, need to find stroke recurrence data
    # "Thirty patients in the BAIPC group and 28 patients in the sham BAIPC group finished the whole study"
    # Need to find recurrence events
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': False,
        'effect_type': 'NONE',
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': None,
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': None,
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': '',
        'reasoning': 'Outcome is "Recurrence of ischemic stroke" but recurrence event counts not found in visible results_text'
    }

def extract_nayak_2021(entry):
    """Manual extraction for Nayak 2021 - Overall survival."""
    # From results_text: "For cohort A, PFS-6 was 26.0% [95% CI, 16.3–41.5], median overall survival (OS) was 8.8 months (95% CI, 7.7–14.2)"
    # "For cohort B, PFS-6 was 6.7% (95% CI, 1.7–25.4), median OS was 10.3 months (95% CI, 8.5–12.5)"
    # This is survival time, not HR
    return {
        'study_id': entry['study_id'],
        'outcome': entry.get('outcome', ''),
        'found': True,
        'effect_type': 'MD',  # Actually survival time, but using MD as proxy
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'intervention_events': None,
        'intervention_n': None,
        'control_events': None,
        'control_n': None,
        'intervention_mean': 8.8,  # Cohort A median OS in months
        'intervention_sd': None,
        'intervention_n_cont': None,
        'control_mean': 10.3,  # Cohort B median OS in months
        'control_sd': None,
        'control_n_cont': None,
        'source_quote': 'For cohort A, median overall survival (OS) was 8.8 months (95% CI, 7.7–14.2). For cohort B, median OS was 10.3 months (95% CI, 8.5–12.5)',
        'reasoning': 'Median OS for two cohorts found (8.8 vs 10.3 months); not intervention vs control but two treatment cohorts'
    }

def main():
    # Load input data
    input_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_batch_r20.json'
    output_path = r'C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_r20.json'

    with open(input_path, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    print(f"Processing {len(entries)} entries...")

    # Map study_id to extraction function
    # Note: Cadigan has \xa0 (non-breaking space) in the JSON
    extractors = {
        'Petrella 2017_2017': extract_petrella_2017,
        'Cadigan 2019_2019': extract_cadigan_2019,
        'Cadigan\xa02019_2019': extract_cadigan_2019,  # Handle non-breaking space
        'Hunt 2014_2014': extract_hunt_2014,
        'Ziemssen 2017_2017': extract_ziemssen_2017,
        'Cormick 2020_2020': extract_cormick_2020,
        'Riedt 2005_2005': extract_riedt_2005,
        'Kerksick 2020_2020': extract_kerksick_2020,
        'Riedt 2007_2007': extract_riedt_2007,
        'Shapses 2004_2004': extract_shapses_2004,
        'Zemel 2009_2009': extract_zemel_2009,
        'He 2020_2020': extract_he_2020,
        'Poalelungi 2021_2021': extract_poalelungi_2021,
        'Che 2019_2019': extract_che_2019,
        'Meng 2015_2015': extract_meng_2015,
        'Nayak 2021_2021': extract_nayak_2021,
    }

    # Verify all extractors exist
    for study_id in [e['study_id'] for e in entries]:
        if study_id not in extractors:
            print(f"WARNING: No extractor for {study_id}")
            extractors[study_id] = lambda e: {
                'study_id': e['study_id'],
                'outcome': e.get('outcome', ''),
                'found': False,
                'effect_type': 'NONE',
                'point_estimate': None,
                'ci_lower': None,
                'ci_upper': None,
                'intervention_events': None,
                'intervention_n': None,
                'control_events': None,
                'control_n': None,
                'intervention_mean': None,
                'intervention_sd': None,
                'intervention_n_cont': None,
                'control_mean': None,
                'control_sd': None,
                'control_n_cont': None,
                'source_quote': '',
                'reasoning': f'No extractor defined for {study_id}'
            }

    results = []
    for i, entry in enumerate(entries, 1):
        study_id = entry['study_id']
        print(f"\n[{i}/{len(entries)}] Processing: {study_id}")

        extractor = extractors.get(study_id)
        if extractor:
            result = extractor(entry)
        else:
            result = {
                'study_id': study_id,
                'outcome': entry.get('outcome', ''),
                'found': False,
                'effect_type': 'NONE',
                'reasoning': f'No extractor defined for {study_id}'
            }

        results.append(result)

        if result['found']:
            print(f"  ✓ Found {result['effect_type']}")
            if result['point_estimate'] is not None:
                print(f"    Estimate: {result['point_estimate']} ({result['ci_lower']}, {result['ci_upper']})")
            elif result['intervention_mean'] is not None:
                print(f"    Int mean: {result['intervention_mean']}, Control mean: {result['control_mean']}")
            elif result['intervention_events'] is not None:
                print(f"    Int events: {result['intervention_events']}/{result['intervention_n']}, Control: {result['control_events']}/{result['control_n']}")
            print(f"    Quote: {result['source_quote'][:80]}...")
        else:
            print(f"  ✗ Not found: {result['reasoning']}")

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n\nResults written to: {output_path}")
    print(f"Found: {sum(1 for r in results if r['found'])}/{len(results)}")


if __name__ == '__main__':
    main()
