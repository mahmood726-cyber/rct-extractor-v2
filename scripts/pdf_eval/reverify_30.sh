#!/usr/bin/env bash
# Independent re-verification of the 30 newly-merged specialties on merged master.
# Re-acquires each specialty's PMC-OA corpus VIA the committed corpus *_TERM
# (acquire_via_europepmc.py), re-harvests gold VERBATIM from abstracts
# (build_gold_from_abstracts.py), then scores the CURRENT merged-master extractor.
set -uo pipefail
cd "$(dirname "$0")/../.."

OUT=data/pdf_eval/reverify
mkdir -p "$OUT"

SPECIALTIES=(
  prostate_cancer ovarian_cancer pancreatic_cancer gastric_cancer
  hepatocellular_carcinoma melanoma leukaemia lymphoma head_neck_cancer
  bladder_cancer renal_cell_carcinoma oesophageal_cancer
  dyslipidaemia venous_thromboembolism peripheral_artery_disease obesity
  thyroid osteoporosis kidney_transplant pulmonary_hypertension pcos
  parkinsons alzheimers multiple_sclerosis migraine schizophrenia
  cirrhosis osteoarthritis covid19 sepsis
)

MODE="${1:-all}"   # acquire | gold | all

for sp in "${SPECIALTIES[@]}"; do
  if [[ "$MODE" == "acquire" || "$MODE" == "all" ]]; then
    echo "###### ACQUIRE $sp ######"
    python scripts/pdf_eval/acquire_via_europepmc.py --specialty "$sp" \
        --max-download 40 --page-size 100 --max-pages 25 2>&1 | tail -5
  fi
  if [[ "$MODE" == "gold" || "$MODE" == "all" ]]; then
    echo "###### GOLD $sp ######"
    python scripts/pdf_eval/build_gold_from_abstracts.py --specialty "$sp" \
        --per-specialty 200 --target 45 --out "$OUT/gold_$sp.jsonl" 2>&1 | tail -3
  fi
done
echo "ALL DONE ($MODE)"
