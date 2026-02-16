import json
import re

# Load batch data
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r25.json', encoding='utf-8') as f:
    batch_data = json.load(f)

results = []

for entry in batch_data:
    study_id = entry['study_id']
    outcome = entry['outcome']
    data_type = entry['data_type']
    results_text = entry['results_text']
    abstract = entry.get('abstract', '')

    result = {
        'study_id': study_id,
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
        'control_mean': None,
        'control_sd': None,
        'source_quote': '',
        'reasoning': ''
    }

    # Process based on study_id and outcome
    print(f"\n{'='*80}")
    print(f"Processing: {study_id}")
    print(f"Outcome: {outcome}")
    print(f"Data type: {data_type}")
    print(f"Results text length: {len(results_text)}")

    results.append(result)

# Save results
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r25.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n\nProcessed {len(results)} entries")
