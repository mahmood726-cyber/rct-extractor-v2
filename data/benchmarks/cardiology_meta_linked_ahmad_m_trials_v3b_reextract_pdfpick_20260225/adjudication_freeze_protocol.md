# Cardiology Benchmark Adjudication Freeze Protocol

- Generated UTC: 2026-02-25T17:26:52.399600+00:00
- Benchmark version: cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225
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
python scripts/evaluate_cardiology_linked_benchmark.py --benchmark-cohort-jsonl data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/benchmark_cohort.jsonl --system-results-jsonl output/cardiology_ahmad_m_trials_extract_20260225/results.jsonl --adjudicated-jsonl data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/adjudication_template.jsonl --output-json output/cardiology_ahmad_m_trials_extract_20260225/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225_benchmark_eval.json --output-md output/cardiology_ahmad_m_trials_extract_20260225/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225_benchmark_eval.md
```

- Preview-only (allows partial gold; not for publication metrics):

```bash
python scripts/evaluate_cardiology_linked_benchmark.py --benchmark-cohort-jsonl data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/benchmark_cohort.jsonl --system-results-jsonl output/cardiology_ahmad_m_trials_extract_20260225/results.jsonl --adjudicated-jsonl data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/adjudication_template.jsonl --output-json output/cardiology_ahmad_m_trials_extract_20260225/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225_benchmark_eval.json --output-md output/cardiology_ahmad_m_trials_extract_20260225/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225_benchmark_eval.md --allow-partial-gold
```

## Input Locks

- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/manifest.json` | sha256=`f72d5cfca8d1ab7903f4128bb93eab869d2ae9396b99dd4995e9afd880160789` | bytes=1845
- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/benchmark_cohort.jsonl` | sha256=`23c4e839fdb8bdc8b510a02ddd932b104adf37eca16c272f188de112cd96e3f9` | bytes=157981
- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/blinded_template_annotator_a.jsonl` | sha256=`ba59f6644cabdf2fd0fee3e0658331c4ed670ced4de3f460aa0da430777b5bf7` | bytes=73755
- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/blinded_template_annotator_b.jsonl` | sha256=`ba59f6644cabdf2fd0fee3e0658331c4ed670ced4de3f460aa0da430777b5bf7` | bytes=73755
- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/adjudication_template.jsonl` | sha256=`92101d128a31c2c8565db04ba646b68180dc05fcbd0e781ec8df76795fece47d` | bytes=76295
- `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/model_seed_adjudicator_only.jsonl` | sha256=`23c4e839fdb8bdc8b510a02ddd932b104adf37eca16c272f188de112cd96e3f9` | bytes=157981
