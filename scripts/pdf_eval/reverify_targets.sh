#!/usr/bin/env bash
# Parameterized re-verification driver (generalises reverify_30.sh).
# Re-acquires each named specialty's PMC-OA corpus VIA its committed corpus *_TERM
# (acquire_via_europepmc.py), re-harvests gold VERBATIM from abstracts
# (build_gold_from_abstracts.py), then the caller scores the CURRENT master
# extractor with run_pdf_eval.py. Pass specialties as args; no hardcoded list.
#
# Usage:
#   scripts/pdf_eval/reverify_targets.sh [acquire|gold|all] sp1 sp2 ...
set -uo pipefail
cd "$(dirname "$0")/../.."

OUT=data/pdf_eval/reverify
mkdir -p "$OUT"

MODE="${1:-all}"
shift || true
SPECIALTIES=("$@")

if [[ ${#SPECIALTIES[@]} -eq 0 ]]; then
  echo "no specialties given" >&2; exit 2
fi

for sp in "${SPECIALTIES[@]}"; do
  if [[ "$MODE" == "acquire" || "$MODE" == "all" ]]; then
    echo "###### ACQUIRE $sp ######"
    # AWS S3 OA mirror: EuropePMC render PDF endpoint returns 500 and the NCBI
    # OA FTP package tree was retired (2026-06-13); the AWS bucket serves the
    # same real PMC-OA PDFs. Corpus query / gold source / scoring surface unchanged.
    python scripts/pdf_eval/acquire_via_s3.py --specialty "$sp" \
        --max-download 40 --page-size 100 --max-pages 25 2>&1 | tail -6
  fi
  if [[ "$MODE" == "gold" || "$MODE" == "all" ]]; then
    echo "###### GOLD $sp ######"
    python scripts/pdf_eval/build_gold_from_abstracts.py --specialty "$sp" \
        --per-specialty 200 --target 45 --out "$OUT/gold_$sp.jsonl" 2>&1 | tail -3
  fi
done
echo "ALL DONE ($MODE)"
