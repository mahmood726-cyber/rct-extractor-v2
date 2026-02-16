#!/usr/bin/env python3
"""
Process clean_batch_r4.json and extract outcome data
Manual extraction with clear reasoning for each study
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
import re

def find_numbers_in_text(text):
    """Helper to find all numbers in text for debugging"""
    return re.findall(r'\d+\.?\d*', text)

def search_keywords(text, keywords):
    """Search for keyword occurrences in text"""
    results = []
    lines = text.split('\n')
    for i, line in enumerate(lines, 1):
        if any(kw.lower() in line.lower() for kw in keywords):
            results.append((i, line.strip()))
    return results

# Load batch
with open('clean_batch_r4.json', encoding='utf-8') as f:
    batch = json.load(f)

print(f"Processing {len(batch)} studies from clean_batch_r4.json\n")

# I'll manually extract each study
results = []

# Study 1: Locatelli 2014_2014 - Death (all causes)
print("="*80)
print("STUDY 1: Locatelli 2014_2014")
print("Outcome: Death (all causes)")
print("="*80)
text1 = batch[0]['results_text']
death_mentions = search_keywords(text1, ['death', 'mortality', 'died', 'fatal', 'survival'])
print(f"Death-related mentions: {len(death_mentions)}")
for line_num, line in death_mentions:
    print(f"  Line {line_num}: {line}")
print("\nConclusion: No death outcome data reported in results_text")
print("The text only mentions death in the background/introduction context.")

results.append({
    'study_id': 'Locatelli 2014_2014',
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
    'reasoning': 'No death/mortality outcome data found in results_text. Text only discusses phosphorus and cholesterol outcomes. Death mentioned only in background/rationale context.'
})

# Study 2: Buesing 2015_2015 - Walking velocity
print("\n" + "="*80)
print("STUDY 2: Buesing 2015_2015")
print("Outcome: Walking velocity (metres per second) at end of intervention phase")
print("="*80)
text2 = batch[1]['results_text']
velocity_mentions = search_keywords(text2, ['velocity', 'walking', 'speed', 'gait', 'm/s', 'metre'])
print(f"Walking velocity mentions: {len(velocity_mentions)}")
for line_num, line in velocity_mentions[:10]:  # First 10
    print(f"  Line {line_num}: {line}")

# Continue for all studies...
# For now, let me create a comprehensive script

print("\n" + "="*80)
print("Creating comprehensive extraction file...")
print("="*80)

# Save what we have so far
with open('clean_results_r4_partial.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(results)} results to clean_results_r4_partial.json")
print("\nTo continue extraction, I need to review each study's results_text carefully.")
print("This requires reading the full text for each of the 15 studies.")
