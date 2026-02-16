"""Split v10 batch into sub-batches for parallel Claude Code subagent processing."""
import json
import os

MEGA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gold_data', 'mega')
INPUT = os.path.join(MEGA_DIR, 'llm_batch_v10.jsonl')
BATCH_DIR = os.path.join(MEGA_DIR, 'v10_batches')
os.makedirs(BATCH_DIR, exist_ok=True)

BATCH_SIZE = 15

entries = []
with open(INPUT, encoding='utf-8') as f:
    for line in f:
        entries.append(json.loads(line.strip()))

n_batches = (len(entries) + BATCH_SIZE - 1) // BATCH_SIZE
print(f"Total entries: {len(entries)}")
print(f"Batch size: {BATCH_SIZE}")
print(f"Number of batches: {n_batches}")

for i in range(n_batches):
    batch = entries[i*BATCH_SIZE:(i+1)*BATCH_SIZE]
    batch_file = os.path.join(BATCH_DIR, f'batch_{i+1:03d}.jsonl')
    with open(batch_file, 'w', encoding='utf-8') as f:
        for e in batch:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    print(f"  batch_{i+1:03d}.jsonl: {len(batch)} entries")

# Also create results directory
RESULTS_DIR = os.path.join(MEGA_DIR, 'v10_results')
os.makedirs(RESULTS_DIR, exist_ok=True)
print(f"\nBatch dir: {BATCH_DIR}")
print(f"Results dir: {RESULTS_DIR}")
