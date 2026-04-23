# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""Analyze (cid:X) artifacts in no-extraction PDFs to understand what they represent."""
import json, sys, io, os, re
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, "C:/Users/user/rct-extractor-v2")
from src.pdf.pdf_parser import PDFParser

PDF_DIR = "C:/Users/user/rct-extractor-v2/gold_data/mega/pdfs"
EVAL_FILE = "C:/Users/user/rct-extractor-v2/gold_data/mega/mega_eval_v3.jsonl"

# Build PMCID -> filename lookup
pmcid_to_file = {}
for fname in os.listdir(PDF_DIR):
    if fname.endswith(".pdf"):
        for part in fname.replace(".pdf", "").split("_"):
            if part.startswith("PMC") and part[3:].isdigit():
                pmcid_to_file[part] = fname
                break

results = []
with open(EVAL_FILE, encoding='utf-8') as f:
    for line in f:
        results.append(json.loads(line))

no_ext = [r for r in results if r['status'] == 'no_extraction']

# Analyze CID contexts
cid_contexts = Counter()
cid_surrounding = []
parser = PDFParser()

checked = 0
for entry in no_ext[:100]:
    pmcid = entry.get('pmcid')
    fname = pmcid_to_file.get(pmcid)
    if not fname:
        continue

    try:
        result = parser.parse(os.path.join(PDF_DIR, fname))
        text = "\n".join(p.full_text for p in result.pages if p.full_text)
    except Exception:
        continue

    # Find all (cid:X) occurrences with surrounding context
    for m in re.finditer(r'(.{0,20})\(cid:(\d+)\)(.{0,20})', text):
        before, cid_num, after = m.group(1), m.group(2), m.group(3)
        cid_contexts[int(cid_num)] += 1

        # Classify by surrounding context
        before_clean = before.replace('\n', '|').strip()
        after_clean = after.replace('\n', '|').strip()
        cid_surrounding.append((int(cid_num), before_clean[-15:], after_clean[:15], pmcid))

    checked += 1

print(f"Checked {checked} papers")
print(f"\n=== CID value frequency ===")
for cid_val, count in cid_contexts.most_common(30):
    print(f"  (cid:{cid_val}): {count} occurrences")

print(f"\n=== Context examples by CID value ===")
shown = Counter()
for cid_val, before, after, pmcid in cid_surrounding:
    if shown[cid_val] < 3:
        shown[cid_val] += 1
        # Try to infer what character it represents
        inference = "?"
        if re.match(r'\d', before[-1:]) and re.match(r'\d', after[:1]):
            inference = "BETWEEN_DIGITS (dash?)"
        elif before.endswith(' ') or after.startswith(' '):
            inference = "NEAR_SPACE"
        elif re.match(r'[a-zA-Z]', before[-1:]) and re.match(r'[a-zA-Z]', after[:1]):
            inference = "BETWEEN_LETTERS (ligature?)"
        elif re.match(r'[a-zA-Z]', before[-1:]) and re.match(r'\d', after[:1]):
            inference = "LETTER_DIGIT"

        print(f"  (cid:{cid_val}) in {pmcid}: ...{before}[CID]{after}... [{inference}]")
