# COVID-19 field bundle

Real-PDF accuracy evaluation corpus for the `covid19` specialty. PDFs/jsonl
gitignored (large/transient); code tracked. Gold harvested by the
extractor-independent `build_gold_from_abstracts.py` (verbatim guard), scored on
the full PDF body; non-RCT papers excluded by `_looks_non_rct`. See
`docs/PDF_ACCURACY_COVID19.md`.

## Reproduce
```bash
python scripts/pdf_eval/acquire_epmc_gold.py --specialty covid19 \
    --query '("covid-19" OR "sars-cov-2") AND (treatment OR vaccine OR antiviral OR mortality)' \
    --target 22 --max-probe 1200 --out data/pdf_eval/gold_covid19.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_covid19.jsonl \
    --out data/pdf_eval/eval_covid19.json --preprocess
```
