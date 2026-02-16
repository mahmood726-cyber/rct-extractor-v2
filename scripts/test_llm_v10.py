"""Quick test: run LLM v10 extraction on 3 entries to verify pipeline."""
import io
import json
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, io.UnsupportedOperation):
    pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MEGA_DIR = Path(__file__).resolve().parent.parent / "gold_data" / "mega"
EVAL_INPUT_FILE = MEGA_DIR / "mega_eval_v9_3.jsonl"

print("Loading v9.3 results...", flush=True)
results = []
retry = []
with open(EVAL_INPUT_FILE, encoding='utf-8') as f:
    for line in f:
        r = json.loads(line.strip())
        results.append(r)
        if r.get("status") in ("no_extraction", "extracted_no_match"):
            retry.append(r)

print(f"Total: {len(results)}, Retry: {len(retry)}", flush=True)
print(f"  no_extraction: {sum(1 for r in retry if r['status'] == 'no_extraction')}", flush=True)
print(f"  extracted_no_match: {sum(1 for r in retry if r['status'] == 'extracted_no_match')}", flush=True)

# Load entries with PDFs
from scripts.mega_evaluate_v2 import load_entries_with_pdfs, llm_guided_worker, infer_data_type
print("Loading entries with PDFs...", flush=True)
all_entries = load_entries_with_pdfs()
entry_by_id = {e["study_id"]: e for e in all_entries}
print(f"Entries with PDFs: {len(all_entries)}", flush=True)

# Test with 3 entries
test_entries = []
for r in retry[:10]:
    sid = r.get("study_id", "")
    if sid in entry_by_id:
        test_entries.append((entry_by_id[sid], r))
    if len(test_entries) >= 3:
        break

print(f"\nTesting {len(test_entries)} entries:", flush=True)
for entry, existing in test_entries:
    sid = entry["study_id"]
    old_status = existing["status"]
    print(f"\n--- {sid} (was: {old_status}) ---", flush=True)

    # Show Cochrane outcomes
    for comp in entry.get("comparisons", [])[:3]:
        print(f"  Outcome: {comp.get('outcome', '?')}, data_type: {comp.get('data_type', '?')}, effect: {comp.get('cochrane_effect', '?')}", flush=True)

    t0 = time.time()
    result = llm_guided_worker((entry, existing))
    elapsed = time.time() - t0

    if result is None:
        print(f"  Result: None ({elapsed:.1f}s)", flush=True)
    else:
        new_status = result.get("status", "?")
        llm_count = result.get("llm_extractions", 0)
        match_info = ""
        if result.get("match") and isinstance(result["match"], dict):
            m = result["match"]
            match_info = f" ext={m.get('extracted',0):.4f} coch={m.get('cochrane',0):.4f} [{m.get('method','')}]"
        print(f"  Result: {old_status} -> {new_status}, llm_extractions={llm_count}{match_info} ({elapsed:.1f}s)", flush=True)

print("\n=== Test complete ===", flush=True)
