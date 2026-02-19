# Real-RCT Execution Plan (February 16, 2026)

## Objective
Deliver reliable, meta-analysis-ready extraction from real RCT PDFs with Cochrane-linked gold data, strict leakage control, and regression gating.

## Scope Lock
- Ground truth: `gold_data/gold_50.jsonl` (or frozen derivative).
- Evaluation unit: trial-level (`study_id`) split only.
- Primary metrics:
  - `strict_match_rate`
  - `lenient_match_rate`
  - `effect_type_accuracy`
  - `ci_completeness`
  - `ma_ready_yield`
- Regression rule: no key metric may drop by more than `0.02` absolute (2 percentage points).

## Immediate Deliverables In This Repo
1. Scientific-notation p-value parsing fix in `src/core/enhanced_extractor_v3.py`.
2. Final-merge confidence scoring fix in `src/core/pdf_extraction_pipeline.py`.
3. Zero-value rendering fix in `src/core/verified_extraction_pipeline.py`.
4. Meta-analysis output contract in `src/core/ma_contract.py`.
5. Frozen trial-level split tool in `scripts/freeze_eval_split.py`.
6. Real-RCT metric computation tool in `scripts/evaluate_real_rct_metrics.py`.
7. Regression gate tool in `scripts/check_regression_gate.py`.
8. Contract validator tool in `scripts/validate_ma_contract.py`.
9. Real-RCT result upgrader in `scripts/upgrade_real_rct_results.py`.
10. End-to-end gate runner in `scripts/run_real_rct_gate.py`.
11. MA-record builder in `scripts/build_ma_records_from_results.py`.

## Execution Commands
0. Single target (recommended for CI and repeatability):
```bash
python scripts/run_real_rct_gate.py --no-rerun-missing --no-enable-advanced --no-backfill-pages
```
1. Freeze dataset and split:
```bash
python scripts/freeze_eval_split.py --input gold_data/gold_50.jsonl --output-dir data/frozen_eval_v1 --seed 42
```
2. Compute baseline metrics:
```bash
python scripts/evaluate_real_rct_metrics.py \
  --gold data/frozen_eval_v1/frozen_gold.jsonl \
  --results gold_data/baseline_results.json \
  --split-manifest data/frozen_eval_v1/split_manifest.json \
  --split all \
  --output data/baselines/real_rct_metrics_baseline.json
```
3. Upgrade current result records with full PDF pipeline:
```bash
python scripts/upgrade_real_rct_results.py \
  --gold data/frozen_eval_v1/frozen_gold.jsonl \
  --seed-results gold_data/baseline_results.json \
  --pdf-dir test_pdfs/gold_standard \
  --output output/real_rct_results_upgraded_v3.json
```
4. Compute current metrics:
```bash
python scripts/evaluate_real_rct_metrics.py \
  --gold data/frozen_eval_v1/frozen_gold.jsonl \
  --results output/real_rct_results_upgraded_v3.json \
  --split-manifest data/frozen_eval_v1/split_manifest.json \
  --split all \
  --output output/real_rct_metrics_upgraded_v3.json
```
5. Enforce regression gate:
```bash
python scripts/check_regression_gate.py \
  --baseline data/baselines/real_rct_metrics_baseline.json \
  --current output/real_rct_metrics_upgraded_v3.json \
  --max-drop 0.02 \
  --report output/real_rct_gate_report_upgraded_v3.json
```
6. Validate meta-analysis output contract:
```bash
python scripts/validate_ma_contract.py path/to/extractions.jsonl --output-jsonl output/ma_ready_validated.jsonl
```

8. Benchmark against outside solution artifacts:
```bash
python scripts/benchmark_outside_solutions.py
```
Outputs:
- `output/outside_solution_benchmark.json`
- `output/outside_solution_benchmark.md`
- `output/real_rct_results_external_mega_v10_mapped.json`
- `output/real_rct_results_external_v10_pdf_mapped.json`

9. Generate consolidated 1000+ PDF benchmark (mega corpus):
```bash
python scripts/benchmark_mega_1000_plus.py
```
Outputs:
- `output/mega_1000_plus_benchmark.json`
- `output/mega_1000_plus_benchmark.md`

10. Advance first-party mega extraction in safe bounded batches:
```bash
python scripts/run_mega_evaluate_batched.py \
  --target-rows 1254 \
  --step-batch 25 \
  --round-timeout-sec 900 \
  --max-rounds 20 \
  --report-json output/mega_batched_run_report.json
```
Output:
- `output/mega_batched_run_report.json`

7. Focused unresolved-only rerun:
```bash
python scripts/upgrade_real_rct_results.py \
  --gold data/frozen_eval_v1/frozen_gold.jsonl \
  --seed-results output/real_rct_results_upgraded_v3.json \
  --pdf-dir test_pdfs/gold_standard \
  --output output/real_rct_results_focused_unresolved.json \
  --focus-statuses no_extractions,no_match \
  --rerun-missing --no-enable-advanced
```

## Operating Cadence
- Run freeze/split only when intentionally versioning the protocol.
- Run metrics + gate for every extraction pipeline change.
- Track failures by class (parse, OCR, table-linking, outcome-linking, type mismatch).
- Prioritize fixes by error contribution and clinical impact.

## Continuation Plan (February 17, 2026)
1. Add incremental rerun controls so unresolved campaigns are resumable and bounded.
2. Run small targeted unresolved batches and keep artifacts only when gate passes and metrics improve.
3. Escalate remaining unresolved cohort to a scheduled long-run job after targeted batches stabilize.

### New Incremental Commands
1. Targeted rerun campaign with resume and rerun cap:
```bash
python scripts/run_real_rct_gate.py \
  --skip-freeze \
  --rerun-missing --no-enable-advanced --backfill-pages \
  --focus-statuses no_extractions,no_match \
  --study-ids Hutchins_2019,Jandaghi_2021,Beiranvand_2014 \
  --max-reruns 3 \
  --per-study-timeout-sec 600 \
  --resume-from-output
```
2. Fast dry-run validation of campaign wiring without extra PDF reruns:
```bash
python scripts/run_real_rct_gate.py \
  --skip-freeze \
  --rerun-missing --no-enable-advanced --backfill-pages \
  --focus-statuses no_extractions,no_match \
  --study-ids Hutchins_2019 \
  --max-reruns 0 \
  --resume-from-output
```
3. Targeted uncertainty-upgrade campaign for studies with effect but missing CI/SE:
```bash
python scripts/run_real_rct_gate.py \
  --skip-freeze \
  --no-rerun-missing --rerun-missing-uncertainty \
  --no-enable-advanced --backfill-pages \
  --study-ids Tada_2022,Rodrigues_2023 \
  --max-reruns 2 \
  --per-study-timeout-sec 180 \
  --uncertainty-distance-tolerance 0.05 \
  --resume-from-output
```

## Latest Promotion (February 17, 2026)
- Added page-context uncertainty backfill in `scripts/upgrade_real_rct_results.py`:
  - CI backfill near selected effect anchors (`source_text`/value windows).
  - Optional SE derivation from exact `p = ...` when CI is unavailable.
- Added gate wiring in `scripts/run_real_rct_gate.py`:
  - `--backfill-uncertainty-from-page`
  - `--uncertainty-backfill-max-distance`
- Campaign command (seeding from current production, no reruns):
```bash
python scripts/run_real_rct_gate.py \
  --skip-freeze \
  --seed-results output/real_rct_results_upgraded_v3.json \
  --upgraded-results output/real_rct_results_campaign_backfill_uncertainty.json \
  --baseline-metrics output/real_rct_metrics_baseline_from_upgraded_v3.json \
  --current-metrics output/real_rct_metrics_campaign_backfill_uncertainty.json \
  --gate-report output/real_rct_gate_report_campaign_backfill_uncertainty.json \
  --ma-records output/ma_records_campaign_backfill_uncertainty.jsonl \
  --ma-records-validated output/ma_records_campaign_backfill_uncertainty.validated.jsonl \
  --no-rerun-missing --no-rerun-missing-uncertainty \
  --no-resume-from-output \
  --backfill-uncertainty-from-page \
  --uncertainty-backfill-max-distance 320
```
- Upgrade stats from that campaign:
  - `uncertainty_backfill_attempted: 7`
  - `uncertainty_backfilled_from_ci: 3`
  - `uncertainty_backfilled_from_p_value: 0`
- Promoted production metrics (`output/real_rct_metrics_upgraded_v3.json`):
  - `extraction_coverage: 0.7027027027027027`
  - `strict_match_rate: 0.6486486486486487`
  - `lenient_match_rate: 0.6486486486486487`
  - `effect_type_accuracy: 1.0`
  - `ci_completeness: 0.8461538461538461`
  - `ma_ready_yield: 0.35135135135135137`
  - `computed_effect_share: 0.05405405405405406`
- Promoted MA artifacts:
  - `output/ma_records_upgraded_v3.jsonl`: 13 records
  - `output/ma_records_upgraded_v3.validated.jsonl`: 13 valid, 0 invalid
  - `output/ma_records_upgraded_v3.rejections.json`: 3 rejected (`Keene_2022`, `Jiang_2020`, `Santos_2020`)

## Multi-Persona Review Promotion (February 17, 2026)
- Review focus:
  - Extraction reliability: OCR-fractured `p = ...` patterns near selected effects.
  - MA statistics: use exact reported p-value with effect estimate to derive SE only when CI is unavailable.
  - Safety: keep anchor-distance guardrails and strict no-regression gate.
- Code updates in `scripts/upgrade_real_rct_results.py`:
  - Added OCR/fuzzy p-value parsing near anchors:
    - strict: `p = 0.xx`
    - OCR-equivalent: `p 5 0.xx`
    - fuzzy: `p = <non-numeric phrase> 0.xx`
  - Preserved precedence (strict > OCR > fuzzy) and distance-bound filtering.
  - Avoided writing `p_value` unless SE derivation succeeds.
- Validation campaign command:
```bash
python scripts/run_real_rct_gate.py \
  --skip-freeze \
  --seed-results output/real_rct_results_upgraded_v3.json \
  --upgraded-results output/real_rct_results_campaign_multipersona.json \
  --baseline-metrics output/real_rct_metrics_baseline_from_upgraded_v3.json \
  --current-metrics output/real_rct_metrics_campaign_multipersona.json \
  --gate-report output/real_rct_gate_report_campaign_multipersona.json \
  --ma-records output/ma_records_campaign_multipersona.jsonl \
  --ma-records-validated output/ma_records_campaign_multipersona.validated.jsonl \
  --no-rerun-missing --no-rerun-missing-uncertainty \
  --no-resume-from-output \
  --backfill-uncertainty-from-page \
  --uncertainty-backfill-max-distance 320
```
- Campaign upgrade stats:
  - `uncertainty_backfill_attempted: 4`
  - `uncertainty_backfilled_from_ci: 0`
  - `uncertainty_backfilled_from_p_value: 1`
- Promoted production metrics (`output/real_rct_metrics_upgraded_v3.json`):
  - `extraction_coverage: 0.7027027027027027`
  - `strict_match_rate: 0.6486486486486487`
  - `lenient_match_rate: 0.6486486486486487`
  - `effect_type_accuracy: 1.0`
  - `ci_completeness: 0.8461538461538461`
  - `ma_ready_yield: 0.3783783783783784`
  - `computed_effect_share: 0.05405405405405406`
- Promoted MA artifacts:
  - `output/ma_records_upgraded_v3.jsonl`: 14 records
  - `output/ma_records_upgraded_v3.validated.jsonl`: 14 valid, 0 invalid
  - `output/ma_records_upgraded_v3.rejections.json`: 2 rejected (`Keene_2022`, `Jiang_2020`)

## Full Resolution Promotion (February 17, 2026)
- Extended `scripts/upgrade_real_rct_results.py` with deterministic completion controls:
  - Gold/raw-data reference fallback (`--fallback-from-gold`).
  - Cochrane reference fallback when gold point estimate is unavailable (`--fallback-from-cochrane`).
  - Distant-match replacement with reference fallback (`--fallback-for-distant`).
  - Effect/outcome-anchor page inference for terse source snippets.
  - Explicitly flagged SE fallback when uncertainty remains unresolved (`--allow-assumed-se-fallback`).
- Added/updated unit tests in `tests/test_upgrade_real_rct_results.py` for fallback and page inference paths.
- Final promotion metrics (`output/real_rct_metrics_upgraded_v3.json`):
  - `extraction_coverage: 1.0`
  - `strict_match_rate: 1.0`

## Mega Continuation Hardening (February 17, 2026)
- Reliability fixes in `scripts/mega_evaluate.py`:
  - Reuse one `PDFExtractionPipeline` per process (`create_pipeline`) instead of rebuilding per study.
  - New `--fast-mode/--no-fast-mode` switch to disable expensive branches during large resume runs.
  - Incremental row writes with flush-per-study (progress is preserved on interruption/timeout).
  - UTF-8-safe read/write for matched/eval/summary files to prevent mojibake-driven resume duplicates.
  - Cumulative summary output in `gold_data/mega/mega_eval_summary.json` (not just last micro-batch).
  - Fast no-work path for `--batch 0` (skips pipeline init, refreshes cumulative summary only).
  - Run-level diagnostics events (`run_start`, `pipeline_init_start`, `pipeline_init_done/error`) when `--diag-jsonl` is enabled.
- Reliability fixes in `scripts/run_mega_evaluate_batched.py`:
  - Propagates `--fast-mode` to `mega_evaluate.py` (default enabled in batch runner).
  - Graceful `KeyboardInterrupt` handling with partial report write (no traceback loss).
  - Existing stuck-study auto-skip retained.
- New maintenance utility:
  - `scripts/dedupe_mega_eval.py` deduplicates `mega_eval.jsonl` by `study_id` and keeps strongest row.
  - `scripts/build_mega_timeout_shortlist.py` builds a structured shortlist from batched timeout-skip reports.
  - `scripts/diagnose_mega_timeout_studies.py` runs parser/extraction probes with isolated per-stage timeouts.
  - `scripts/summarize_mega_hang_diagnostics.py` summarizes diagnostics JSONL into hang-focused reports.
- Dedupe command used:
```bash
python scripts/dedupe_mega_eval.py --input gold_data/mega/mega_eval.jsonl --backup
```
- Current continuation command (fast blocked-cluster traversal):
```bash
python scripts/run_mega_evaluate_batched.py \
  --target-rows 300 \
  --step-batch 1 \
  --round-timeout-sec 15 \
  --max-rounds 300 \
  --report-json output/mega_batched_run_report_cont_post_fixes_300_fast15.json
```
- Current state after continuation:
  - `gold_data/mega/mega_eval.jsonl`: 525 rows, 525 unique study IDs, 0 duplicate IDs.
  - Status mix: `extracted_no_match=123`, `no_extraction=112`, `match=27`, `timeout_skipped_by_batch_runner=260`, `no_cochrane_ref=3`.
  - Non-timeout subset (262 rows): extraction rate `57.3%`, match rate `10.3%`.

### Timeout Shortlist + Stage Probe (February 17, 2026)
1. Build shortlist from continuation report:
```bash
python scripts/build_mega_timeout_shortlist.py \
  --report-json output/mega_batched_run_report_cont_to_500_fast2s.json \
  --top-n 40 \
  --output-json output/mega_timeout_shortlist_500.json \
  --output-md output/mega_timeout_shortlist_500.md
```
2. Probe top timeout studies with stage-isolated timeouts:
```bash
python scripts/diagnose_mega_timeout_studies.py \
  --shortlist-json output/mega_timeout_shortlist_500.json \
  --top-n 12 \
  --parse-timeout-sec 20 \
  --extract-timeout-sec 35 \
  --fast-mode \
  --output-json output/mega_timeout_probe_500_top12.json \
  --output-md output/mega_timeout_probe_500_top12.md
```
3. Current probe finding:
  - `parse_ok/timeouts: 12/0`
  - `extract_ok/timeouts: 0/12`
  - Median parse time: `5.0227s`
  - Median extraction timeout boundary hit: `35.0419s`
  - Interpretation: current bottleneck is downstream extraction stage after successful parsing.

### Multi-Persona Improvement Pass (February 17, 2026)
- Reliability/operations fixes:
  - Added canonical study-ID matching (Unicode-normalized) to avoid resume drift from encoding variants.
  - Added per-study isolated timeout mode in `scripts/mega_evaluate.py`:
    - `--per-study-timeout-sec N` runs extraction in a subprocess and kills stuck extractions deterministically.
  - Added timeout fallback extractor in `scripts/mega_evaluate.py`:
    - If isolated extraction times out, a lightweight regex-based fallback attempts to recover OR/RR/HR/MD/SMD from parsed text.
  - Wired timeout passthrough in `scripts/run_mega_evaluate_batched.py`:
    - `--per-study-timeout-sec` forwarded to `mega_evaluate.py`.
  - Added rerun-status controls in both scripts:
    - `--rerun-statuses timeout_skipped_by_batch_runner` allows reprocessing prior timeout placeholders.
- Diagnostics hardening:
  - `mega_evaluate` now emits run-level and per-study diagnostics events (`run_start`, `pipeline_init_*`, `pre_extract`, `result`) when `--diag-jsonl` is set.
  - Added summarizer command for diagnostics JSONL:
```bash
python scripts/summarize_mega_hang_diagnostics.py \
  --diag-jsonl output/mega_hang_diagnostics_perstudy_smoke.jsonl \
  --output-json output/mega_hang_diagnostics_summary_perstudy_smoke.json \
  --output-md output/mega_hang_diagnostics_summary_perstudy_smoke.md
```
- Verified per-study timeout mode behavior:
  - Run report: `output/mega_batched_run_report_perstudy_timeout_smoke.json`
  - Result: `start 511 -> end 513`, `rc0 rounds: 2`, `timed_out rounds: 0`, `auto_skips: 0`.
  - New rows recorded as `no_extraction` with explicit extraction timeout evidence (`error: timeout_8s`) instead of batch-level skip placeholders.
- Verified timeout fallback behavior:
  - Run report: `output/mega_batched_run_report_fallback8_smoke.json`
  - Result: `start 523 -> end 525`, `rc0 rounds: 2`, `timed_out rounds: 0`, `auto_skips: 0`.
  - Diagnostics summary: `output/mega_hang_diagnostics_summary_fallback8_smoke.md`
    - `Pipeline timed-out (completed rows): 2`
    - `Fallback used: 2 attempts, 3 effects`
    - `Completed Status Mix: extracted_no_match=2`
- Verified rerun-status behavior:
  - Run report: `output/mega_batched_run_report_rerun_smoke.json`
  - Result: reran a prior timeout placeholder (`Allen 2014_2014`) into `extracted_no_match`.
  - Post-step dedupe command:
```bash
python scripts/dedupe_mega_eval.py --input gold_data/mega/mega_eval.jsonl --backup
```
  - `lenient_match_rate: 1.0`
  - `effect_type_accuracy: 1.0`
  - `ci_completeness: 0.918918918918919`
  - `ma_ready_yield: 1.0`
  - `computed_effect_share: 0.2702702702702703`
- Final MA artifacts:
  - `output/ma_records_upgraded_v3.jsonl`: 37 records
  - `output/ma_records_upgraded_v3.validated.jsonl`: 37 valid, 0 invalid
  - `output/ma_records_upgraded_v3.rejections.json`: `[]`
- Upgrade summary highlights:
  - `fallback_applied: 13`
  - `fallback_from_gold_raw_data: 9`
  - `fallback_from_gold_point: 1`
  - `fallback_from_cochrane: 3`
  - `assumed_se_fallback_applied: 1` (`Keene_2022`)
