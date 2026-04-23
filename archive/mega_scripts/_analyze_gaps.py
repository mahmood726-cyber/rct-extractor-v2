# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""Quick analysis of pattern gap findings."""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

labeled_ci = []
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/pattern_gap_analysis.jsonl', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        has_label = any(p.startswith('label_') for p in d['patterns'])
        has_ci = any(p in d['patterns'] for p in ['has_CI', 'paren_CI', 'bracket_CI', 'to_CI', 'comma_CI'])
        if has_label and has_ci:
            labeled_ci.append(d)

print(f'Total labeled+CI contexts: {len(labeled_ci)}')
print(f'  no_extraction: {len([c for c in labeled_ci if c["status"] == "no_extraction"])}')
print(f'  extracted_no_match: {len([c for c in labeled_ci if c["status"] == "extracted_no_match"])}')

print()
print('=== NO_EXTRACTION with label+CI (missed entirely) ===')
seen = set()
for c in labeled_ci:
    if c['status'] != 'no_extraction':
        continue
    if c['pmcid'] in seen:
        continue
    seen.add(c['pmcid'])
    labels = [p for p in c['patterns'] if p.startswith('label_')]
    ci_types = [p for p in c['patterns'] if p in ['has_CI', 'paren_CI', 'bracket_CI', 'to_CI', 'comma_CI']]
    print(f'\n  {c["pmcid"]} | cochrane={c["cochrane_val"]:.4f} ({c["data_type"]}) | {labels} {ci_types}')
    ctx = c['context'][:350].replace('\n', ' ')
    print(f'    {ctx}')

print()
print('=== EXTRACTED_NO_MATCH with label+CI (extracted wrong value) ===')
seen = set()
for c in labeled_ci:
    if c['status'] != 'extracted_no_match':
        continue
    if c['pmcid'] in seen:
        continue
    seen.add(c['pmcid'])
    labels = [p for p in c['patterns'] if p.startswith('label_')]
    ci_types = [p for p in c['patterns'] if p in ['has_CI', 'paren_CI', 'bracket_CI', 'to_CI', 'comma_CI']]
    print(f'\n  {c["pmcid"]} | cochrane={c["cochrane_val"]:.4f} ({c["data_type"]}) | {labels} {ci_types}')
    ctx = c['context'][:350].replace('\n', ' ')
    print(f'    {ctx}')

# Also show the most promising: no_extraction + labeled (no CI requirement)
print()
print('=== NO_EXTRACTION with label only (no CI) ===')
no_ext_label_only = []
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/pattern_gap_analysis.jsonl', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        has_label = any(p.startswith('label_') for p in d['patterns'])
        has_ci = any(p in d['patterns'] for p in ['has_CI', 'paren_CI', 'bracket_CI', 'to_CI', 'comma_CI'])
        if has_label and not has_ci and d['status'] == 'no_extraction':
            no_ext_label_only.append(d)

seen = set()
for c in no_ext_label_only[:15]:
    if c['pmcid'] in seen:
        continue
    seen.add(c['pmcid'])
    labels = [p for p in c['patterns'] if p.startswith('label_')]
    print(f'\n  {c["pmcid"]} | cochrane={c["cochrane_val"]:.4f} ({c["data_type"]}) | {labels}')
    ctx = c['context'][:350].replace('\n', ' ')
    print(f'    {ctx}')
