#!/usr/bin/env bash
# Score the CURRENT master extractor on the re-harvested gold for a named set of
# specialties and emit the per-specialty pdf_raw table + scope audit.
# Assumes reverify_targets.sh (acquire|gold) has already produced
# data/pdf_eval/reverify/gold_<sp>.jsonl for each specialty.
#
# Usage: scripts/pdf_eval/reverify_score.sh <tag> sp1 sp2 ...
#   <tag> names the output bundle, e.g. "primary9" or "spotcheck".
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT=data/pdf_eval/reverify

TAG="${1:?tag required}"; shift
SPECIALTIES=("$@")
[[ ${#SPECIALTIES[@]} -eq 0 ]] && { echo "no specialties" >&2; exit 2; }

# 1. merge per-specialty gold into one file for this tag
MERGED="$OUT/gold_${TAG}.jsonl"
: > "$MERGED"
for sp in "${SPECIALTIES[@]}"; do
  if [[ -s "$OUT/gold_$sp.jsonl" ]]; then
    cat "$OUT/gold_$sp.jsonl" >> "$MERGED"
  else
    echo "  !! missing or empty gold_$sp.jsonl" >&2
  fi
done
echo "merged $(wc -l < "$MERGED") gold papers -> $MERGED"

# 2. score the master extractor on the full PDF body (pdf_raw)
python scripts/pdf_eval/run_pdf_eval.py \
    --gold "$MERGED" --out "$OUT/eval_${TAG}.json"

# 3. per-specialty aggregate table
python scripts/pdf_eval/reverify_aggregate_targets.py \
    "$OUT/eval_${TAG}.json" "$OUT/summary_${TAG}.json"

# 4. scope-exclusion audit + miss classification
python scripts/pdf_eval/reverify_scope_audit.py \
    "$OUT/eval_${TAG}.json" "$OUT/gold_${TAG}.jsonl" "$OUT/scope_${TAG}.json"

echo "DONE scoring $TAG"
