<!-- sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files. -->

# Independent Adjudication Checklist

## Scope
- Benchmark: `cardiology_meta_linked_ahmad_m_trials_v1`
- Rows: `126`
- Goal: final gold labels created from independent dual annotation + adjudicator resolution.

## Current Status
- `adjudication_template.jsonl` reset to clean baseline (all `gold.included = null`).
- Manual prefill snapshot preserved at:
  - `adjudication_template.manual_snapshot_20260225T131507Z.jsonl`

## File Paths
- Annotator A: `blinded_template_annotator_a.jsonl`
- Annotator B: `blinded_template_annotator_b.jsonl`
- Final adjudication target: `adjudication_template.jsonl`
- Cohort: `benchmark_cohort.jsonl`
- Model seed (adjudicator reference only): `model_seed_adjudicator_only.jsonl`

## Protocol Gates
- [ ] A and B complete all rows (`included` non-null for each row).
- [ ] For `included=true`: `effect_type` and `point_estimate` are non-null.
- [ ] For `included=true`: `source_text` is non-empty.
- [ ] Unresolved rows are manually adjudicated into `adjudication_template.jsonl`.
- [ ] Final adjudication file has exactly one row per `benchmark_id` (126 total).

## Step 1: Complete Dual Annotation
- [ ] Annotator A completed all 126 rows.
- [ ] Annotator B completed all 126 rows.

## Step 2: Build Consensus + Unresolved Packet
- [ ] Run:

```bash
python scripts/build_unresolved_adjudication_packet.py --benchmark-dir C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1
```

- [ ] Review output summary:
  - `adjudication_unresolved/summary.json`
- [ ] Review unresolved packet:
  - `adjudication_unresolved/unresolved_packet.jsonl`

## Step 3: Manual Adjudication of Unresolved Rows
- [ ] Adjudicator resolves all rows in `unresolved_packet.jsonl`.
- [ ] Final labels entered into `adjudication_template.jsonl`.

## Step 4: Strict Freeze Evaluation
- [ ] Run strict freeze (no preview flag):

```bash
python scripts/evaluate_cardiology_linked_benchmark.py --benchmark-cohort-jsonl C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/benchmark_cohort.jsonl --system-results-jsonl C:/Users/user/rct-extractor-v2/output/cardiology_oa_full_v1_fast/results.jsonl --adjudicated-jsonl C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/adjudication_template.jsonl --output-json C:/Users/user/rct-extractor-v2/output/cardiology_oa_full_v1_fast/cardiology_meta_linked_ahmad_m_trials_v1_benchmark_eval.json --output-md C:/Users/user/rct-extractor-v2/output/cardiology_oa_full_v1_fast/cardiology_meta_linked_ahmad_m_trials_v1_benchmark_eval.md
```

- [ ] Confirm `gold_rows_unresolved = 0` in eval JSON.
- [ ] Confirm no placeholder/null labels remain.

## Optional Fast QA Commands
- Count non-null `included` in A/B/final:

```bash
python scripts/check_adjudication_completeness.py --benchmark-dir C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1
```
