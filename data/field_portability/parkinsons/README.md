# Parkinson's disease field bundle

Real-PDF accuracy evaluation corpus for the `parkinsons` specialty.

- PDFs (`rct_trial_pdfs/`), `*.jsonl`, `*.json`, `*.log` here are large/transient
  and gitignored. The code (specialty module, arm-data, tests, corpus builder)
  is tracked under `rct_extractor/_engine/specialties/` and `scripts/parkinsons/`.
- Gold + accuracy: see `docs/PDF_ACCURACY_PARKINSONS.md`. Gold tuples are
  harvested by the extractor-independent `scripts/pdf_eval/build_gold_from_abstracts.py`
  (verbatim-substring guard) and scored on the full PDF body.

## Reproduce

```bash
# 1. acquire real PMC-OA RCT PDFs + gold from EuropePMC (NCBI eutils DNS-blocked
#    on the build host; EuropePMC source, identical gold method, scored on PDF body)
python scripts/pdf_eval/acquire_epmc_gold.py --specialty parkinsons \
    --query '"parkinson disease" OR "parkinson'"'"'s disease"' \
    --target 22 --max-probe 900 --out data/pdf_eval/gold_parkinsons.jsonl
# 2. score the shipped extractor on the full PDF body
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_parkinsons.jsonl \
    --out data/pdf_eval/eval_parkinsons.json --preprocess
```
