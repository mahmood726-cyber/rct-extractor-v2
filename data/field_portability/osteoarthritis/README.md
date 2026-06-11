# Osteoarthritis field bundle

Real-PDF accuracy evaluation corpus for the `osteoarthritis` specialty. PDFs/jsonl
gitignored (large/transient); code tracked. Gold harvested by the
extractor-independent `build_gold_from_abstracts.py` (verbatim guard), scored on
the full PDF body; non-RCT papers excluded by `_looks_non_rct`. See
`docs/PDF_ACCURACY_OSTEOARTHRITIS.md`.

## Reproduce
```bash
python scripts/pdf_eval/acquire_epmc_gold.py --specialty osteoarthritis \
    --query '(osteoarthritis AND (knee OR hip OR WOMAC OR OARSI))' \
    --target 22 --max-probe 1000 --out data/pdf_eval/gold_osteoarthritis.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_osteoarthritis.jsonl \
    --out data/pdf_eval/eval_osteoarthritis.json --preprocess
```
