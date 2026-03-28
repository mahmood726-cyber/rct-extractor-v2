# Cardiology Benchmark Adjudication Freeze Protocol

- Generated UTC: 2026-02-25T17:24:47.247965+00:00
- Benchmark version: cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225
- Rows to adjudicate: 127
- Work batches: 6

## Completion Gates

1. Both annotators complete all benchmark rows (`included` non-null for each row).
2. For `included=true`, `effect_type` and `point_estimate` must be non-null.
3. For `included=true`, `source_text` must be non-empty.
4. Unresolved dual-annotator rows must be manually adjudicated into `adjudication_template.jsonl`.
5. Final adjudicated file must contain exactly one row per benchmark id.

## Consensus Rules

- Point tolerance: `0.1` relative error.
- CI tolerance: `0.15` max relative bound error.
- Zero absolute tolerance: `0.02`.
- If both annotators mark excluded, consensus is excluded.
- If included/included but values differ beyond tolerance, row requires manual adjudication.

## Freeze Commands

- Final freeze (fails if adjudication is incomplete):

```bash
python scripts/evaluate_cardiology_linked_benchmark.py --benchmark-cohort-jsonl data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225/benchmark_cohort.jsonl --system-results-jsonl output/cardiology_ahmad_m_trials_extract_20260225/results.jsonl --adjudicated-jsonl data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225/adjudication_template.jsonl --output-json output/cardiology_ahmad_m_trials_extract_20260225/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225_benchmark_eval.json --output-md output/cardiology_ahmad_m_trials_extract_20260225/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225_benchmark_eval.md
```

- Preview-only (allows partial gold; not for publication metrics):

```bash
python scripts/evaluate_cardiology_linked_benchmark.py --benchmark-cohort-jsonl data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225/benchmark_cohort.jsonl --system-results-jsonl output/cardiology_ahmad_m_trials_extract_20260225/results.jsonl --adjudicated-jsonl data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225/adjudication_template.jsonl --output-json output/cardiology_ahmad_m_trials_extract_20260225/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225_benchmark_eval.json --output-md output/cardiology_ahmad_m_trials_extract_20260225/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225_benchmark_eval.md --allow-partial-gold
```

## Input Locks

- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225/manifest.json` | sha256=`9832981864a2b1dc7cf358f7eaabeefcb19b907f69dc98fcb28619c16a28a4a5` | bytes=1836
- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225/benchmark_cohort.jsonl` | sha256=`e203ff086805ca6740ae083863cf9a66248549e4a5c30a59049949a8b8836251` | bytes=156461
- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225/blinded_template_annotator_a.jsonl` | sha256=`7163564a72d0e7fade252868c6a43bdb323b6a798ffebf089178a94f37edbdec` | bytes=72990
- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225/blinded_template_annotator_b.jsonl` | sha256=`7163564a72d0e7fade252868c6a43bdb323b6a798ffebf089178a94f37edbdec` | bytes=72990
- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225/adjudication_template.jsonl` | sha256=`8613b269a38e1b134d23d4313e60a21ed16d5b863e4d8e668ebe565b44c0193d` | bytes=75530
- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3_reextract_20260225/model_seed_adjudicator_only.jsonl` | sha256=`e203ff086805ca6740ae083863cf9a66248549e4a5c30a59049949a8b8836251` | bytes=156461
