# External No-Tune Validation

## Goal
Run external PDF validation without tuning, without gold/cochrane fallback injection, and with a reproducible frozen cohort artifact.

## Scripts
- `scripts/prepare_external_no_tune_eval.py`
- `scripts/run_external_no_tune_eval.py`

## Default Input
- `data/ground_truth/external_validation_ground_truth.jsonl`

Current source composition in this repo:
- 39 trials total
- 37 `NEJM`
- 1 `Lancet`
- 1 `AJP`

## One-Command Run
```bash
python3 scripts/run_external_no_tune_eval.py
```

## Build A 40-Trial NEJM+Lancet Cohort
```bash
python3 scripts/run_external_no_tune_eval.py \
  --source module \
  --journal-allowlist Lancet,NEJM \
  --max-trials 40 \
  --cohort-dir data/external_no_tune_40_v1 \
  --pdf-dir test_pdfs/external_no_tune_40_v1/pdfs \
  --results-output output/external_no_tune_40_v1_results.json \
  --metrics-output output/external_no_tune_40_v1_metrics.json \
  --summary-output output/external_no_tune_40_v1_summary.json \
  --report-output output/external_no_tune_40_v1_report.md
```

## Optional PMCID Integrity Gate
Use this to drop rows where the PMCID metadata does not match the trial DOI/PMID.

```bash
python3 scripts/run_external_no_tune_eval.py \
  --source module \
  --journal-allowlist Lancet,NEJM \
  --max-trials 60 \
  --validate-pdf-content \
  --cohort-dir data/external_no_tune_metadata_validated \
  --pdf-dir test_pdfs/external_no_tune_40_v1/pdfs
```

Current finding on `external_no_tune_40_v2`:
- PMCID metadata audit: `output/external_no_tune_40_v2_pmcid_audit.json`
- Local PDFs with PMCID metadata matching trial DOI+PMID: 2 / 40

## Key No-Tune Controls
The runner executes extraction with:
- `--no-fallback-from-gold`
- `--no-fallback-from-cochrane`
- `--no-fallback-for-distant`
- `--no-allow-assumed-se-fallback`
- `--no-resume-from-output`

## Optional PubMed Abstract Recovery
For PMCID/PDF failures (for example, PMCID points to a different paper), you can
enable abstract-only recovery using the trial PMID:

```bash
python3 scripts/run_external_no_tune_eval.py \
  --skip-prepare \
  --cohort-dir data/external_no_tune_40_v2 \
  --pdf-dir test_pdfs/external_no_tune_40_v1/pdfs \
  --fallback-from-pubmed-abstract \
  --results-output output/external_no_tune_40_v6_results.json \
  --metrics-output output/external_no_tune_40_v6_metrics.json \
  --summary-output output/external_no_tune_40_v6_summary.json \
  --report-output output/external_no_tune_40_v6_report.md
```

## Main Artifacts
- `data/external_no_tune_v1/manifest.jsonl`
- `data/external_no_tune_v1/frozen_gold.jsonl`
- `data/external_no_tune_v1/protocol_lock.json`
- `output/external_no_tune_v1_results.json`
- `output/external_no_tune_v1_metrics.json`
- `output/external_no_tune_v1_summary.json`
- `output/external_no_tune_v1_report.md`

## Notes
- `prepare_external_no_tune_eval.py` selects one primary target effect per trial (prioritizing `abstract` source type when available).
- By default, only trials with locally available PDFs are included in `frozen_gold.jsonl` (`--require-local-pdf`).
