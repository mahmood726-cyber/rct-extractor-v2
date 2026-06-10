# Multiple sclerosis field bundle

Real-PDF accuracy evaluation corpus for the `multiple_sclerosis` specialty. PDFs/
jsonl are gitignored (large/transient); code is tracked. Gold harvested by the
extractor-independent `scripts/pdf_eval/build_gold_from_abstracts.py` (verbatim
guard) and scored on the full PDF body. See `docs/PDF_ACCURACY_MULTIPLE_SCLEROSIS.md`.

## Reproduce
```bash
python scripts/pdf_eval/acquire_epmc_gold.py --specialty multiple_sclerosis \
    --query '"multiple sclerosis"' --target 22 --max-probe 1000 \
    --out data/pdf_eval/gold_multiple_sclerosis.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_multiple_sclerosis.jsonl \
    --out data/pdf_eval/eval_multiple_sclerosis.json --preprocess
```
