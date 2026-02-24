# Broad Publishability Readiness (2026-02-24)

## Goal Framing
- Target claim: extraction from real OA RCT result PDFs is suitable for meta-analysis workflows at broad scope.
- Human-error envelope assumption: up to 10% relative point-estimate variance is plausible in manual extraction.

## Cohort Results
### 1) Cochrane-linked frozen cohort (`multipersona`, n=37)
- Source metrics: `output/real_rct_metrics_campaign_multipersona.json`
- Human-error agreement: `output/multipersona_human_error_agreement_2026-02-24.md`
- Point agreement within 10%: `100.0%` (95% CI: `100.0%` to `100.0%`)
- Effect-type match: `100.0%`
- CI-bound agreement within 10%: `85.3%` (95% CI: `73.5%` to `97.1%`)

### 2) External full-40 cohort (`external_no_tune_40_v7`, n=40, PubMed fallback enabled)
- Source metrics: `output/external_no_tune_40_v7_metrics.json`
- Human-error agreement: `output/external_no_tune_40_v7_human_error_agreement_2026-02-24.md`
- Point agreement within 10%: `100.0%` (95% CI: `100.0%` to `100.0%`)
- Effect-type match: `100.0%`
- CI-bound agreement within 10%: `25.6%` (95% CI: `12.8%` to `38.5%`)
- Caveat: 31/40 are `manual` + `needs_review`, and fallback is enabled for selected studies.

### 3) Expanded identity-validated PDF-only cohort (`external_all_validated_augmented_v3_deep_pdf_only_advfix`, n=19)
- Cohort build: `data/external_all_validated_augmented_v3_deep/protocol_lock.json`
- PDF-only metrics: `output/external_all_validated_augmented_v3_deep_pdf_only_advfix_metrics.json`
- Human-error agreement: `output/external_all_validated_augmented_v3_deep_pdf_only_advfix_human_error_agreement_2026-02-24.md`
- Point agreement within 10%: `94.4%` (95% CI: `83.3%` to `100.0%`) on 18 comparable trials
- CI-bound agreement within 10%: `82.4%` (95% CI: `64.7%` to `100.0%`) on 17 comparable trials
- Strict match rate: `89.5%`, lenient match rate: `94.7%`, MA-ready yield: `89.5%`
- Frozen bootstrap CI artifact: `output/external_all_validated_augmented_v3_deep_pdf_only_advfix_bootstrap_95ci.json`
- MA-contract validity: `16/16` accepted from emitted records (`output/external_all_validated_augmented_v3_deep_pdf_only_advfix_ma_records_validated.jsonl`)
- Published-meta comparison: `output/external_all_validated_augmented_v3_deep_pdf_only_advfix_published_meta_comparison_2026-02-24.md`
- Net validated full-text lift vs prior v1 cohort: `+6` trials (13 -> 19)

### 4) Large real-data mega cohort (`mega_eval`, n=560; Cochrane-linked n=546)
- Source artifact: `gold_data/mega/mega_eval.jsonl`
- Human-error agreement report: `output/mega_human_error_agreement_2026-02-24.md`
- Rows with PMCID: `560`
- Rows with Cochrane reference: `546`
- Strict match rate (5% criterion): `98.7%`
- Point agreement within 10% (conservative, status-based): `98.7%` (95% CI: `97.6%` to `99.6%`)
- Residual non-match rows: `7`
- Caveat: this report is point-estimate focused and does not by itself establish CI-field completeness for all rows.

## Readiness Assessment
- Strong signal exists for point-estimate extraction under a 10% human-error envelope.
- Broad external publishability is still constrained by identity-validated sample size and CI stability despite strong large-cohort point-estimate performance.
- Current identity-validated full-text size (`n=19`) remains below the repo's own precision guidance (`n≈73` for +/-5% at 95% confidence in `docs/SAMPLE_SIZE_JUSTIFICATION.md`).

## Practical Claim Boundary
- Publishable now as a scoped methods/engineering paper with explicit boundary conditions.
- Not yet publishable as a broad external full-text generalization claim without expanding identity-validated n and reducing CI-instability cases.
