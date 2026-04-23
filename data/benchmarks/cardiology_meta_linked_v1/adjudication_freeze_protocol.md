<!-- sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files. -->

# Cardiology Benchmark Adjudication Freeze Protocol

- Generated UTC: 2026-02-25T10:29:02.754894+00:00
- Benchmark version: cardiology_meta_linked_v1_full533
- Rows to adjudicate: 533
- Work batches: 14

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

```bash
python scripts/evaluate_cardiology_linked_benchmark.py --benchmark-cohort-jsonl data/benchmarks/cardiology_meta_linked_v1/benchmark_cohort.jsonl --system-results-jsonl output/cardiology_oa_full_v1_fast/results_linkage_boosted_snapshot.jsonl --adjudicated-jsonl data/benchmarks/cardiology_meta_linked_v1/adjudication_template.jsonl --output-json output/cardiology_oa_full_v1_fast/cardiology_linked_benchmark_eval.json --output-md output/cardiology_oa_full_v1_fast/cardiology_linked_benchmark_eval.md
```

## Input Locks

- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_v1/manifest.json` | sha256=`63e657a87339fd845e363a4cbf202753c32675bcb1fc8f120709ca3f91b7a06a` | bytes=1444
- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_v1/benchmark_cohort.jsonl` | sha256=`50d4799ddff4d945cd3eb89f7225facd2999143dd2f4abc30cda32f65f84ad05` | bytes=382142
- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_v1/blinded_template_annotator_a.jsonl` | sha256=`c4ec7e4482ec65824083fa0e409bc8ba39e660052fe8e3faf7e1f4e2286d3806` | bytes=228659
- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_v1/blinded_template_annotator_b.jsonl` | sha256=`c4ec7e4482ec65824083fa0e409bc8ba39e660052fe8e3faf7e1f4e2286d3806` | bytes=228659
- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_v1/adjudication_template.jsonl` | sha256=`e157f7f4a011cb5924ff0b8fea27fa3ba468470f1bb03225eeda77ea52e358fc` | bytes=239319
- `C:/Users/user/rct-extractor-v2/data/benchmarks/cardiology_meta_linked_v1/model_seed_adjudicator_only.jsonl` | sha256=`50d4799ddff4d945cd3eb89f7225facd2999143dd2f4abc30cda32f65f84ad05` | bytes=382142
