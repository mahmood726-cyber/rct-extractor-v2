# External No-Tune Validation

## Goal
Run external PDF validation without tuning, without gold/cochrane fallback injection, and with a reproducible frozen cohort artifact.

## Scripts
- `scripts/prepare_external_no_tune_eval.py`
- `scripts/run_external_no_tune_eval.py`
- `scripts/build_human_error_agreement_report.py`
- `scripts/augment_identity_validation_with_unpaywall.py`
- `scripts/bootstrap_real_rct_metrics.py`
- `scripts/build_ma_records_from_results.py`
- `scripts/validate_ma_contract.py`
- `scripts/build_published_meta_comparison_report.py`

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
- Improved augmentation pass with repository landing-page PDF discovery and balanced network settings:
```bash
python3 scripts/augment_identity_validation_with_unpaywall.py \
  --input-cohort-dir data/external_all_validated_probe \
  --output-dir data/external_all_validated_augmented_v2_balanced \
  --pdf-dir test_pdfs/external_all_validated_augmented_v2_balanced/pdfs \
  --request-timeout-sec 6 \
  --http-retries 1 \
  --max-landing-pages-per-study 2 \
  --max-links-per-landing-page 6 \
  --max-candidates-per-study 8
```
- Result of balanced v2 augmentation:
  - frozen identity-validated trials: `11 -> 17` (`+6 downloaded`, `+4 net` vs v1)
  - downloaded and DOI-validated additions vs v1: `clarity_2010`, `emperor_reduced_2020`, `fourier_2017`, `paradigm_hf_2014`
  - protocol: `data/external_all_validated_augmented_v2_balanced/protocol_lock.json`
- Re-ran strict PDF-only extraction on the balanced v2 cohort:
```bash
python3 scripts/run_external_no_tune_eval.py \
  --skip-prepare \
  --cohort-dir data/external_all_validated_augmented_v2_balanced \
  --pdf-dir test_pdfs/external_all_validated_augmented_v2_balanced_merged/pdfs \
  --no-fallback-from-pubmed-abstract \
  --results-output output/external_all_validated_augmented_v2_balanced_pdf_only_results.json \
  --metrics-output output/external_all_validated_augmented_v2_balanced_pdf_only_metrics.json \
  --summary-output output/external_all_validated_augmented_v2_balanced_pdf_only_summary.json \
  --report-output output/external_all_validated_augmented_v2_balanced_pdf_only_report.md
```
- Balanced v2 validated PDF-only metrics (`output/external_all_validated_augmented_v2_balanced_pdf_only_metrics.json`):
  - `extraction_coverage: 0.9412`
  - `strict_match_rate: 0.8824`
  - `lenient_match_rate: 0.9412`
  - `effect_type_accuracy: 1.0`
  - `ci_completeness: 0.9375`
  - `ma_ready_yield: 0.8824`
- Human-error-envelope agreement on balanced v2 cohort:
  - `output/external_all_validated_augmented_v2_balanced_pdf_only_human_error_agreement_2026-02-24.md`
  - point agreement within 10%: `93.8%` (`95% CI: 81.2% to 100.0%`) on 16 comparable trials
  - CI-bound agreement within 10%: `80.0%` (`95% CI: 60.0% to 100.0%`) on 15 comparable trials
- Publishability note:
  - This improves validated-N from 13 to 17 but remains under broad-claim sample-size guidance (see `docs/SAMPLE_SIZE_JUSTIFICATION.md`, minimum `n≈73` for ±5% precision at 95% confidence).
  - Suitable for scoped methods claims; not yet sufficient for broad external full-text generalization claims.

## Identity-Validated v3 Deep Extension (February 24, 2026)
- Added parser-timeout and cached-download reuse in `augment_identity_validation_with_unpaywall.py` to prevent malformed-PDF stalls and recover partial successful downloads.
- Built v3 deep cohort from v2 balanced baseline:
```bash
python3 scripts/augment_identity_validation_with_unpaywall.py \
  --input-cohort-dir data/external_all_validated_augmented_v2_balanced \
  --output-dir data/external_all_validated_augmented_v3_deep \
  --pdf-dir test_pdfs/external_all_validated_augmented_v3_deep/pdfs \
  --max-attempts 0 \
  --pdf-parse-timeout-sec 12
```
- v3 cohort outcome:
  - frozen identity-validated trials: `17 -> 19`
  - added studies: `improve_it_2015`, `improve_it_2015_pmc4590563`
  - protocol: `data/external_all_validated_augmented_v3_deep/protocol_lock.json`
- v3 strict PDF-only extraction:
```bash
python3 scripts/run_external_no_tune_eval.py \
  --skip-prepare \
  --cohort-dir data/external_all_validated_augmented_v3_deep \
  --pdf-dir test_pdfs/external_all_validated_augmented_v3_deep_merged/pdfs \
  --no-fallback-from-pubmed-abstract \
  --results-output output/external_all_validated_augmented_v3_deep_pdf_only_results.json \
  --metrics-output output/external_all_validated_augmented_v3_deep_pdf_only_metrics.json \
  --summary-output output/external_all_validated_augmented_v3_deep_pdf_only_summary.json \
  --report-output output/external_all_validated_augmented_v3_deep_pdf_only_report.md
```
- CI/error-targeted advanced rerun (5 studies: `actt_1_2020,checkmate_067_2015,dream_2006,cleopatra_2012,leader_2016`):
```bash
python3 scripts/run_external_no_tune_eval.py \
  --skip-prepare \
  --cohort-dir data/external_all_validated_augmented_v3_deep \
  --pdf-dir test_pdfs/external_all_validated_augmented_v3_deep_merged/pdfs \
  --seed-results output/external_all_validated_augmented_v3_deep_pdf_only_seed_ci_targeted.json \
  --study-ids actt_1_2020,checkmate_067_2015,dream_2006,cleopatra_2012,leader_2016 \
  --enable-advanced \
  --no-fallback-from-pubmed-abstract \
  --results-output output/external_all_validated_augmented_v3_deep_pdf_only_advfix_results.json \
  --metrics-output output/external_all_validated_augmented_v3_deep_pdf_only_advfix_metrics.json \
  --summary-output output/external_all_validated_augmented_v3_deep_pdf_only_advfix_summary.json \
  --report-output output/external_all_validated_augmented_v3_deep_pdf_only_advfix_report.md
```
- v3 metrics (`output/external_all_validated_augmented_v3_deep_pdf_only_advfix_metrics.json`):
  - `extraction_coverage: 0.9474`
  - `strict_match_rate: 0.8947`
  - `lenient_match_rate: 0.9474`
  - `effect_type_accuracy: 1.0`
  - `ci_completeness: 0.9444`
  - `ma_ready_yield: 0.8947`
- v3 human-error agreement:
  - `output/external_all_validated_augmented_v3_deep_pdf_only_advfix_human_error_agreement_2026-02-24.md`
  - point agreement within 10%: `94.4%` (`95% CI: 83.3% to 100.0%`) on 18 comparable trials
  - CI-bound agreement within 10%: `82.4%` (`95% CI: 64.7% to 100.0%`) on 17 comparable trials
- Frozen bootstrap and MA-contract artifacts:
  - `output/external_all_validated_augmented_v3_deep_pdf_only_advfix_bootstrap_95ci.json`
  - `output/external_all_validated_augmented_v3_deep_pdf_only_advfix_ma_records_validated.jsonl` (`16` valid records)
  - `output/external_all_validated_augmented_v3_deep_pdf_only_advfix_ma_records_rejections.json` (`2` rejections: `cleopatra_2012`, `dream_2006`)
- Published-meta comparison artifact:
  - `output/external_all_validated_augmented_v3_deep_pdf_only_advfix_published_meta_comparison_2026-02-24.md`
- Publishability note update:
  - validated full-text N improved further (`13 -> 19`) but remains below broad-claim precision target (`n~73` for +/-5% precision at 95% confidence; `docs/SAMPLE_SIZE_JUSTIFICATION.md`).

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
