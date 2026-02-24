# External No-Tune Validation

## Goal
Run external PDF validation without tuning, without gold/cochrane fallback injection, and with a reproducible frozen cohort artifact.

## Scripts
- `scripts/prepare_external_no_tune_eval.py`
- `scripts/run_external_no_tune_eval.py`
- `scripts/build_human_error_agreement_report.py`

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
enable abstract-only recovery using the trial PMID. By default this applies to
`no_extractions,no_match` statuses:

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

You can also force PubMed fallback for selected study IDs (while keeping default
status gating) and seed from a previous run:

```bash
python3 scripts/run_external_no_tune_eval.py \
  --skip-prepare \
  --cohort-dir data/external_no_tune_40_v2 \
  --pdf-dir test_pdfs/external_no_tune_40_v1/pdfs \
  --seed-results output/external_no_tune_40_v6_results.json \
  --fallback-from-pubmed-abstract \
  --pubmed-fallback-study-ids dapa_hf_2019,define_2012,gemini_1_2013,inpulsis_2014,keynote_024_2016,re_ly_2009 \
  --results-output output/external_no_tune_40_v7_results.json \
  --metrics-output output/external_no_tune_40_v7_metrics.json \
  --summary-output output/external_no_tune_40_v7_summary.json \
  --report-output output/external_no_tune_40_v7_report.md
```

Latest full-40 result (`external_no_tune_40_v7`):
- strict match rate: `1.0000` (vs `0.8500` in v6)
- lenient match rate: `1.0000` (vs `0.9000` in v6)
- MA-ready yield: `0.9250` (unchanged vs v6)

PLOS ONE scope audit on the same full-40 cohort:
```bash
python3 scripts/review_multipersona_plos_one.py \
  --cohort-label external_no_tune_40_v7 \
  --frozen-gold data/external_no_tune_40_v2/frozen_gold.jsonl \
  --results output/external_no_tune_40_v7_results.json \
  --output-json output/external_no_tune_40_v7_plos_one_review_2026-02-24.json \
  --output-md output/external_no_tune_40_v7_plos_one_review_2026-02-24.md
```
- `output/external_no_tune_40_v7_plos_one_review_2026-02-24.md` confirms:
  - PLOS-family studies in the frozen cohort: `0`
  - PLOS ONE studies: `0`
  - No PLOS-specific regression risk in this 40-study cohort.

Human-error-envelope agreement audit (10% tolerance):
```bash
python3 scripts/build_human_error_agreement_report.py \
  --cohort-label external_no_tune_40_v7 \
  --gold-jsonl data/external_no_tune_40_v2/frozen_gold.jsonl \
  --results-json output/external_no_tune_40_v7_results.json \
  --output-json output/external_no_tune_40_v7_human_error_agreement_2026-02-24.json \
  --output-md output/external_no_tune_40_v7_human_error_agreement_2026-02-24.md \
  --n-bootstrap 20000
```
- `output/external_no_tune_40_v7_human_error_agreement_2026-02-24.md`:
  - point agreement within 10%: `100.0%` (`95% CI: 100.0% to 100.0%`)
  - effect-type match: `100.0%`
  - CI-bound agreement within 10%: `25.6%`
  - Interpretation: endpoint point estimates are stable under a 10% human-error envelope, but CI-bound agreement is weak in this fallback-enabled full-40 run.

## Identity-Validated Full-Text Expansion (February 24, 2026)
- Augmented identity-validated full-text cohort using DOI-in-PDF verification from Unpaywall:
```bash
python3 scripts/augment_identity_validation_with_unpaywall.py \
  --input-cohort-dir data/external_all_validated_probe \
  --output-dir data/external_all_validated_augmented_v1 \
  --pdf-dir test_pdfs/external_all_validated_augmented_v1/pdfs
```
- Result of augmentation:
  - frozen identity-validated trials: `11 -> 13`
  - stats: `downloaded_and_validated=2`, `failed_after_candidates=31`, `no_oa_pdf_candidate=5`
- Re-ran strict PDF-only extraction on the expanded validated cohort:
```bash
python3 scripts/run_external_no_tune_eval.py \
  --skip-prepare \
  --cohort-dir data/external_all_validated_augmented_v1 \
  --pdf-dir test_pdfs/external_all_validated_augmented_v1_merged/pdfs \
  --no-fallback-from-pubmed-abstract \
  --results-output output/external_all_validated_augmented_v1_pdf_only_results.json \
  --metrics-output output/external_all_validated_augmented_v1_pdf_only_metrics.json \
  --summary-output output/external_all_validated_augmented_v1_pdf_only_summary.json \
  --report-output output/external_all_validated_augmented_v1_pdf_only_report.md
```
- Expanded validated PDF-only metrics (`output/external_all_validated_augmented_v1_pdf_only_metrics.json`):
  - `extraction_coverage: 0.8462`
  - `strict_match_rate: 0.7692`
  - `lenient_match_rate: 0.8462`
  - `effect_type_accuracy: 1.0`
  - `ci_completeness: 0.9091`
  - `ma_ready_yield: 0.7692`
- Human-error-envelope agreement on expanded validated cohort:
  - `output/external_all_validated_augmented_v1_pdf_only_human_error_agreement_2026-02-24.md`
  - point agreement within 10%: `90.9%` (`95% CI: 72.7% to 100.0%`) on 11 comparable trials
  - CI-bound agreement within 10%: `70.0%` (`95% CI: 40.0% to 100.0%`) on 10 comparable trials
- Publishability note:
  - This improves validated-N but remains under broad-claim sample-size guidance (see `docs/SAMPLE_SIZE_JUSTIFICATION.md`, minimum `n≈73` for ±5% precision at 95% confidence).
  - Suitable for scoped methods claims; not yet sufficient for broad external full-text generalization claims.

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
