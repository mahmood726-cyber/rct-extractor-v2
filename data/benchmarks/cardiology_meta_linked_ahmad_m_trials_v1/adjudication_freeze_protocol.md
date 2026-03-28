# Cardiology Benchmark Adjudication Freeze Protocol

- Generated UTC: 2026-02-25T12:41:48.239699+00:00
- Benchmark version: cardiology_meta_linked_ahmad_m_trials_v1
- Rows to adjudicate: 126
- Work batches: 4

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
python scripts/evaluate_cardiology_linked_benchmark.py --benchmark-cohort-jsonl C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/benchmark_cohort.jsonl --system-results-jsonl C:/Users/user/rct-extractor-v2/output/cardiology_oa_full_v1_fast/results.jsonl --adjudicated-jsonl C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/adjudication_template.jsonl --output-json output/cardiology_oa_full_v1_fast/cardiology_meta_linked_ahmad_m_trials_v1_benchmark_eval.json --output-md output/cardiology_oa_full_v1_fast/cardiology_meta_linked_ahmad_m_trials_v1_benchmark_eval.md
```

- Preview-only (allows partial gold; not for publication metrics):

```bash
python scripts/evaluate_cardiology_linked_benchmark.py --benchmark-cohort-jsonl C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/benchmark_cohort.jsonl --system-results-jsonl C:/Users/user/rct-extractor-v2/output/cardiology_oa_full_v1_fast/results.jsonl --adjudicated-jsonl C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/adjudication_template.jsonl --output-json output/cardiology_oa_full_v1_fast/cardiology_meta_linked_ahmad_m_trials_v1_benchmark_eval.json --output-md output/cardiology_oa_full_v1_fast/cardiology_meta_linked_ahmad_m_trials_v1_benchmark_eval.md --allow-partial-gold
```

## Input Locks

- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/manifest.json` | sha256=`795d4cb856d975b80a2dfb9124dd54b0313a74109e1bcf0605b5f315c1bedcd3` | bytes=1937
- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/benchmark_cohort.jsonl` | sha256=`29cf5be28b258898798842a1d75598b217b3fa2ec9f15da8fdcc69a40a6e0662` | bytes=134812
- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/blinded_template_annotator_a.jsonl` | sha256=`84e5c752421adafa0177031c8283c09b79b827fab45482c56813ebe91aceaefd` | bytes=69996
- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/blinded_template_annotator_b.jsonl` | sha256=`84e5c752421adafa0177031c8283c09b79b827fab45482c56813ebe91aceaefd` | bytes=69996
- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/adjudication_template.jsonl` | sha256=`07eb77944955b5f685b9cadf1720e9be383e0675ba62199bd6645384212dcc87` | bytes=80791
- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v1/model_seed_adjudicator_only.jsonl` | sha256=`29cf5be28b258898798842a1d75598b217b3fa2ec9f15da8fdcc69a40a6e0662` | bytes=134812
