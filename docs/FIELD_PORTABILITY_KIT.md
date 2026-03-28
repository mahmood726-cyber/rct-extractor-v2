# Field Portability Kit

## Purpose
This project can be reused outside cardiology by keeping a fixed extraction core and swapping only field-specific inputs:
- corpus (PDF set)
- vocabulary/profile
- benchmark/adjudication pack

Goal: make specialty-level adaptation reproducible, auditable, and publication-ready.

## What To Ship On GitHub
Include these artifacts when the project is finalized:
1. Core extraction + validator scripts
   - `scripts/extract_pdf_corpus.py`
   - `scripts/apply_ai_validators_to_results.py`
   - `scripts/apply_dual_llm_borderline_validators.py`
2. Benchmark + adjudication workflow scripts
   - `scripts/build_author_meta_benchmark_subset.py`
   - `scripts/build_blinded_ensemble_pre_adjudication.py`
   - `scripts/build_ensemble_spotcheck_sheet.py`
   - `scripts/apply_ensemble_spotcheck_overrides.py`
   - `scripts/evaluate_cardiology_linked_benchmark.py`
3. Portability assets
   - `configs/field_profile.template.yaml`
   - `scripts/scaffold_field_portability_bundle.py`
   - this file (`docs/FIELD_PORTABILITY_KIT.md`)
4. Example completed field package (cardiology)
   - frozen benchmark manifest
   - adjudication template and overrides
   - final evaluation JSON/MD

## Field Adaptation Pattern
Use a constant pipeline, vary only field profile + corpus + adjudicated benchmark.

### Step 1: Scaffold a field bundle
```powershell
python scripts/scaffold_field_portability_bundle.py `
  --field-name "Oncology" `
  --field-slug "oncology"
```

This creates:
- `data/field_portability/oncology/field_profile.yaml`
- `data/field_portability/oncology/author_meta_pmids.json`
- `data/field_portability/oncology/commands.ps1`
- `data/field_portability/oncology/commands.sh`
- `data/field_portability/oncology/README.md`

### Step 2: Build field-linked benchmark subset
Run `build_author_meta_benchmark_subset.py` with your author and PMIDs.
For non-cardiology fields, use `--no-require-cardiology` and specify your own PubMed query (or PMIDs).

### Step 3: Extract + validate
Run deterministic extraction on field PDFs, then run validators in `balanced` mode.

### Step 4: Optional dual-validator audit
Use `apply_dual_llm_borderline_validators.py`:
- no-key mode: `rules_a + rules_b` (audit fallback)
- API mode: independent models (`openai + anthropic`)

### Step 5: Adjudication and freeze
Apply blinded ensemble + spot checks + overrides.
Freeze an adjudicated gold file before final claims.

### Step 6: Report publication metrics
Minimum report:
- extraction coverage on included gold
- false-positive extraction rate on excluded gold
- effect type match rate
- point/CI agreement rates

## Required Quality Bar (recommended)
For external publication claims, target all:
1. Independent adjudicated gold labels: `true`
2. Coverage on included rows: `>= 0.95`
3. FP extraction rate on excluded rows: `<= 0.02` (prefer 0)
4. Point/CI/type agreement on extracted comparable rows: `>= 0.98`
5. Clear unresolved/error accounting

## Governance Rules
1. Keep deterministic extraction as primary system of record.
2. Treat LLM validators as secondary gates, not authoritative extractors.
3. Keep full audit logs for all gates/overrides.
4. Never claim general-domain performance from single-field results.
5. Re-run full benchmark after any gating rule change.

## Recommended Package Layout Per Field
`data/field_portability/<field_slug>/`
- `field_profile.yaml`
- `author_meta_pmids.json`
- `README.md`
- `commands.ps1`
- `commands.sh`
- `notes.md`

`data/benchmarks/<field_slug>_meta_linked_v1/`
- `benchmark_cohort.jsonl`
- `adjudication_template.jsonl`
- `manifest.json`
- `...ensemble and spotcheck outputs...`

`output/<field_slug>_extract_*/`
- `results.jsonl`
- `results_ai_validated_balanced.jsonl`
- `*_benchmark_eval*.json`
- `report.md`

## Current Cardiology Reference State
See:
- `output/cardiology_ahmad_m_trials_extract_20260225/HANDOFF_2026-02-26.md`
- `output/cardiology_ahmad_m_trials_extract_20260225/HANDOFF_2026-02-26.json`

These files represent the reference implementation of this portability pattern.
