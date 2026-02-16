"""Analyze PDF text quality issues causing extraction failures."""
import json, sys, io, os, re
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, "C:/Users/user/rct-extractor-v2")
from src.pdf.pdf_parser import PDFParser

EVAL_FILE = "C:/Users/user/rct-extractor-v2/gold_data/mega/mega_eval_v3.jsonl"
PDF_DIR = "C:/Users/user/rct-extractor-v2/gold_data/mega/pdfs"

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
print(f"Analyzing text quality of {len(no_ext)} no_extraction papers (sampling 150)")

# Quality metrics
cid_count = 0          # has (cid:X) control codes
merged_words = 0       # long "words" suggesting missing spaces
very_short = 0         # very little text extracted
reversed_text = 0      # RTL or reversed text
avg_word_lengths = []
issue_details = Counter()
fixable_papers = []

parser = PDFParser()

for i, entry in enumerate(no_ext[:150]):
    pmcid = entry.get('pmcid')
    fname = pmcid_to_file.get(pmcid)
    if not fname:
        continue

    try:
        result = parser.parse(os.path.join(PDF_DIR, fname))
        text = "\n".join(p.full_text for p in result.pages if p.full_text)
    except Exception:
        issue_details['parse_error'] += 1
        continue

    if not text or len(text) < 100:
        very_short += 1
        issue_details['very_short_text'] += 1
        continue

    issues = []

    # Check for (cid:X) artifacts
    cid_matches = re.findall(r'\(cid:\d+\)', text)
    if cid_matches:
        cid_count += 1
        issues.append(f'cid_artifacts({len(cid_matches)})')

    # Check for merged words (words > 30 chars not URLs/DOIs)
    words = text.split()
    long_words = [w for w in words if len(w) > 30 and '/' not in w and '.' not in w[:5]]
    if len(long_words) > 10:
        merged_words += 1
        issues.append(f'merged_words({len(long_words)})')

    # Check average word length (normal is 4-7; >10 suggests missing spaces)
    if words:
        avg_len = sum(len(w) for w in words) / len(words)
        avg_word_lengths.append(avg_len)
        if avg_len > 10:
            issues.append(f'high_avg_word_len({avg_len:.1f})')

    # Check for reversed text (common in some PDF encodings)
    if re.search(r'[a-z]{3,}\s+[a-z]{3,}\s+[a-z]{3,}', text[:500]) is None:
        # First 500 chars don't have normal English word sequences
        if re.search(r'[a-zA-Z]', text[:500]):
            issues.append('possible_encoding_issue')

    # Check for column overlap (text from two columns merged on same line)
    lines = text.split('\n')
    wide_lines = [l for l in lines if len(l) > 200]
    if len(wide_lines) > 20:
        issues.append(f'wide_lines({len(wide_lines)})')

    for issue in issues:
        issue_details[issue.split('(')[0]] += 1

    if issues:
        fixable_papers.append((pmcid, issues))

    if (i + 1) % 50 == 0:
        print(f"  Checked {i+1}/150...", flush=True)

print(f"\n=== Text Quality Results (150 no_extraction papers) ===")
print(f"  (cid:X) artifacts: {cid_count}")
print(f"  Merged words (>30 chars): {merged_words}")
print(f"  Very short text (<100 chars): {very_short}")
print(f"  Parse errors: {issue_details.get('parse_error', 0)}")

if avg_word_lengths:
    import statistics
    print(f"\n  Avg word length: mean={statistics.mean(avg_word_lengths):.1f}, "
          f"median={statistics.median(avg_word_lengths):.1f}, "
          f"max={max(avg_word_lengths):.1f}")
    high_avg = sum(1 for a in avg_word_lengths if a > 8)
    print(f"  Papers with avg word length > 8: {high_avg}")

print(f"\n  Issue counts:")
for issue, count in issue_details.most_common():
    print(f"    {issue}: {count}")

print(f"\n  Papers with any text issue: {len(fixable_papers)}")

# Show examples of each issue type
print(f"\n=== Example papers with issues ===")
shown = Counter()
for pmcid, issues in fixable_papers:
    for issue in issues:
        itype = issue.split('(')[0]
        if shown[itype] < 2:
            shown[itype] += 1
            try:
                result = parser.parse(os.path.join(PDF_DIR, pmcid_to_file[pmcid]))
                text = "\n".join(p.full_text for p in result.pages if p.full_text)
                # Show first 300 chars of text
                sample = text[:400].replace('\n', ' | ')
                print(f"\n  [{itype}] {pmcid}:")
                print(f"    {sample[:300]}...")
            except Exception:
                pass
