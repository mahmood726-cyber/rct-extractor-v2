# Alzheimer's disease / dementia field bundle

Real-PDF accuracy evaluation corpus for the `alzheimers` specialty. PDFs/jsonl
are gitignored (large/transient); code is tracked. Gold tuples are harvested by
the extractor-independent `scripts/pdf_eval/build_gold_from_abstracts.py`
(verbatim guard) and scored on the full PDF body. See
`docs/PDF_ACCURACY_ALZHEIMERS.md`.

## Reproduce
```bash
python scripts/pdf_eval/acquire_epmc_gold.py --specialty alzheimers \
    --query '"alzheimer disease" OR "alzheimer'"'"'s disease" OR dementia' \
    --target 22 --max-probe 1000 --out data/pdf_eval/gold_alzheimers.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_alzheimers.jsonl \
    --out data/pdf_eval/eval_alzheimers.json --preprocess
```
