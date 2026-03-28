#!/usr/bin/env bash
set -euo pipefail

# Oncology Demo runbook (bash)

python scripts/build_author_meta_benchmark_subset.py \
  --benchmark-cohort-jsonl <seed_benchmark_cohort_jsonl> \
  --output-dir data/benchmarks/oncology_demo_meta_linked_v1 \
  --author-full-name "Surname Given" \
  --author-meta-pmids-file data/field_portability/oncology_demo/author_meta_pmids.json \
  --require-meta \
  --no-require-cardiology

python scripts/extract_pdf_corpus.py \
  --input-dir data/field_portability/oncology_demo/rct_trial_pdfs \
  --output-jsonl output/oncology_demo_extract_v1/results.jsonl \
  --summary-json output/oncology_demo_extract_v1/summary.json \
  --summary-md output/oncology_demo_extract_v1/report.md \
  --recursive \
  --workers 2

python scripts/apply_ai_validators_to_results.py \
  --input-jsonl output/oncology_demo_extract_v1/results.jsonl \
  --output-jsonl output/oncology_demo_extract_v1/results_ai_validated_balanced.jsonl \
  --summary-json output/oncology_demo_extract_v1/results_ai_validated_balanced_summary.json \
  --validator-mode balanced

python scripts/apply_dual_llm_borderline_validators.py \
  --input-jsonl output/oncology_demo_extract_v1/results_ai_validated_balanced.jsonl \
  --output-jsonl output/oncology_demo_extract_v1/results_ai_validated_balanced_dual_rules.jsonl \
  --summary-json output/oncology_demo_extract_v1/results_ai_validated_balanced_dual_rules_summary.json \
  --audit-jsonl output/oncology_demo_extract_v1/results_ai_validated_balanced_dual_rules_audit.jsonl \
  --provider-a rules_a \
  --provider-b rules_b \
  --max-candidates 120 \
  --min-agreement-confidence 0.65 \
  --conflict-policy keep
