# Schizophrenia field bundle

Real-PDF accuracy evaluation corpus for the `schizophrenia` specialty. PDFs/jsonl
gitignored (large/transient); code tracked. Gold harvested by the
extractor-independent `build_gold_from_abstracts.py` (verbatim guard), scored on
the full PDF body. See `docs/PDF_ACCURACY_SCHIZOPHRENIA.md`.

## Reproduce
```bash
python scripts/pdf_eval/acquire_epmc_gold.py --specialty schizophrenia \
    --query 'schizophrenia' --target 22 --max-probe 1300 \
    --out data/pdf_eval/gold_schizophrenia.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_schizophrenia.jsonl \
    --out data/pdf_eval/eval_schizophrenia.json --preprocess
```
