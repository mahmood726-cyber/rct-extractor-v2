# Migraine field bundle

Real-PDF accuracy evaluation corpus for the `migraine` specialty. PDFs/jsonl are
gitignored (large/transient); code is tracked. Gold harvested by the
extractor-independent `build_gold_from_abstracts.py` (verbatim guard) and scored
on the full PDF body. See `docs/PDF_ACCURACY_MIGRAINE.md`.

## Reproduce
```bash
python scripts/pdf_eval/acquire_epmc_gold.py --specialty migraine \
    --query 'migraine' --target 22 --max-probe 1100 \
    --out data/pdf_eval/gold_migraine.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_migraine.jsonl \
    --out data/pdf_eval/eval_migraine.json --preprocess
```
