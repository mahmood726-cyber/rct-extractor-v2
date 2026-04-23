#!/usr/bin/env python3
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
# -*- coding: utf-8 -*-
"""
Manual extraction for batch 009 - carefully examine each entry
"""
import json
import sys
import io

# Set UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Read all entries
batch_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_009.jsonl'
output_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_009.jsonl'

entries = []
with open(batch_file, 'r', encoding='utf-8') as f:
    for line in f:
        entries.append(json.loads(line))

print(f"Processing {len(entries)} entries\n", file=sys.stderr)

# Manual extraction results for each study
results = []

# Entry 1: Lin 2014_2014 - ADHD trial, mentions BP increases but no numeric values
for outcome in entries[0]['outcomes']:
    results.append({
        'study_id': 'Lin 2014_2014',
        'outcome': outcome['outcome'],
        'found': False,
        'effect_type': None,
        'point_estimate': None,
        'ci_lower': None,
        'ci_upper': None,
        'raw_data': {},
        'source_quote': 'Compared with placebo, edivoxetine treatment was associated with statistically significant increases in blood pressure and pulse (p < 0.050)',
        'reasoning': 'Text mentions increases in blood pressure and pulse but provides no numeric values for the changes'
    })

# Entries 2-15: Process similarly
# Let me print each entry to examine the text carefully
for idx, entry in enumerate(entries):
    print(f"\n{'='*80}", file=sys.stderr)
    print(f"ENTRY {idx+1}: {entry['study_id']}", file=sys.stderr)
    print(f"{'='*80}", file=sys.stderr)
    print(f"Outcomes: {[o['outcome'] for o in entry['outcomes']]}", file=sys.stderr)
    print(f"\nAbstract ({len(entry.get('abstract', ''))} chars):", file=sys.stderr)
    print(entry.get('abstract', '')[:800], file=sys.stderr)
    print(f"\nResults ({len(entry.get('results_text', ''))} chars):", file=sys.stderr)
    print(entry.get('results_text', '')[:800], file=sys.stderr)
    print(file=sys.stderr)

# Don't write results yet - just examine the data first
