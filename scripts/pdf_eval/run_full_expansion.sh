#!/usr/bin/env bash
# Orchestrate the full multi-specialty real-PDF eval AFTER PDFs are acquired.
#   before = extractor at HEAD WITHOUT the v6.4 patch (git stash the one file)
#   after  = extractor WITH the v6.4 patch
# Keeps the committed HIV+malaria gold (59 papers) and appends the new specialties.
set -euo pipefail
cd "$(dirname "$0")/../.."

NEW_SP="tuberculosis hepatitis typhoid pneumonia hypertension diabetes maternal_neonatal \
cholera meningitis schistosomiasis sickle_cell helminths cervical_cancer diarrhoeal malnutrition"
GOLD=data/pdf_eval/gold_abstract.jsonl
NEWGOLD=data/pdf_eval/_gold_new.jsonl

echo "== 1. harvest gold for new specialties =="
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty $NEW_SP \
    --per-specialty 200 --target 45 --out "$NEWGOLD"

echo "== 2. append to committed HIV+malaria gold (preserve their 145 tuples) =="
python - "$GOLD" "$NEWGOLD" <<'PY'
import sys, json
base, new = sys.argv[1], sys.argv[2]
keep = [l for l in open(base, encoding="utf-8") if l.strip()
        and json.loads(l)["specialty"] in ("hiv", "malaria")]
add = [l for l in open(new, encoding="utf-8") if l.strip()]
with open(base, "w", encoding="utf-8") as f:
    f.writelines(keep); f.writelines(add)
recs = [json.loads(l) for l in open(base, encoding="utf-8") if l.strip()]
from collections import Counter
c = Counter(r["specialty"] for r in recs)
t = sum(len(r["gold_effects"]) for r in recs)
print(f"  full gold: {len(recs)} papers, {t} tuples across {len(c)} specialties")
print("  ", dict(sorted(c.items())))
PY

echo "== 3. BEFORE: stash the v6.4 patch, eval =="
git stash push -- rct_extractor/_engine/core/enhanced_extractor_v3.py
python scripts/pdf_eval/run_pdf_eval.py --gold "$GOLD" \
    --out data/pdf_eval/eval_results_before.json --preprocess
git stash pop

echo "== 4. AFTER: with v6.4 patch, eval =="
python scripts/pdf_eval/run_pdf_eval.py --gold "$GOLD" \
    --out data/pdf_eval/eval_results_after.json --preprocess

echo "== 5. regenerate report =="
python scripts/pdf_eval/generate_report.py
rm -f "$NEWGOLD"
echo "DONE"
