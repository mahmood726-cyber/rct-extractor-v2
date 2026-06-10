# Sepsis / septic shock field bundle

Real-PDF accuracy evaluation corpus for the `sepsis` specialty. PDFs/jsonl
gitignored (large/transient); code tracked. Gold harvested by the
extractor-independent `build_gold_from_abstracts.py` (verbatim guard), scored on
the full PDF body; non-RCT papers excluded by `_looks_non_rct`. See
`docs/PDF_ACCURACY_SEPSIS.md`.

## Reproduce
```bash
python scripts/pdf_eval/acquire_epmc_gold.py --specialty sepsis \
    --query '(sepsis OR "septic shock") AND (mortality OR vasopressor OR hydrocortisone OR antibiotic OR "renal replacement")' \
    --target 22 --max-probe 1300 --out data/pdf_eval/gold_sepsis.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_sepsis.jsonl \
    --out data/pdf_eval/eval_sepsis.json --preprocess
```
