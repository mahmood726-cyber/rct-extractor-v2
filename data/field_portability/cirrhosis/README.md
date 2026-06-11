# Cirrhosis / decompensated liver disease field bundle

Real-PDF accuracy evaluation corpus for the `cirrhosis` specialty. PDFs/jsonl
gitignored (large/transient); code tracked. Gold harvested by the
extractor-independent `build_gold_from_abstracts.py` (verbatim guard), scored on
the full PDF body; non-RCT papers excluded by `_looks_non_rct`. See
`docs/PDF_ACCURACY_CIRRHOSIS.md`.

## Reproduce
```bash
python scripts/pdf_eval/acquire_epmc_gold.py --specialty cirrhosis \
    --query '(cirrhosis OR "portal hypertension" OR "hepatic encephalopathy" OR variceal OR hepatorenal)' \
    --target 22 --max-probe 1400 --out data/pdf_eval/gold_cirrhosis.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_cirrhosis.jsonl \
    --out data/pdf_eval/eval_cirrhosis.json --preprocess
```
