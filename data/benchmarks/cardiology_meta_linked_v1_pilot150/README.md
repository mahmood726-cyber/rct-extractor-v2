# Cardiology Meta-Linked Benchmark Pack

- Generated UTC: 2026-02-24T22:40:35.981499+00:00
- Benchmark version: cardiology_meta_linked_v1_pilot150
- Total selected rows: 150
- Linked PMIDs represented: 150

## Files

- Cohort rows: `benchmark_cohort.jsonl`
- Blinded template A: `blinded_template_annotator_a.jsonl`
- Blinded template B: `blinded_template_annotator_b.jsonl`
- Adjudication template: `adjudication_template.jsonl`
- Model seed (for adjudicator only): `model_seed_adjudicator_only.jsonl`

## Annotation Rules

- `annotation.included=true` only when a clear quantitative treatment effect is present.
- Fill `effect_type` using standard tags (HR, OR, RR, MD, SMD, ARD, ARR, RD, IRR, GMR, NNT, NNH).
- Record `point_estimate` and CI bounds exactly as reported; do not transform scales.
- Leave unknown fields as `null` and explain uncertainty in `notes`.
- Keep annotators blinded to model output (`model_seed` is adjudicator-only).

## Scoring Command

```bash
python scripts/evaluate_cardiology_linked_benchmark.py --benchmark-cohort-jsonl <cohort_jsonl> --system-results-jsonl output/cardiology_oa_full_v1_fast/results_linkage_boosted_snapshot.jsonl --annotator-a-jsonl <annotator_a_completed_jsonl> --annotator-b-jsonl <annotator_b_completed_jsonl> --output-json output/cardiology_oa_full_v1_fast/cardiology_linked_benchmark_eval.json --output-md output/cardiology_oa_full_v1_fast/cardiology_linked_benchmark_eval.md
```

