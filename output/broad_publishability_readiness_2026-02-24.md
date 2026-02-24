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

### 3) Expanded identity-validated PDF-only cohort (`external_all_validated_augmented_v1_pdf_only`, n=13)
- Cohort build: `data/external_all_validated_augmented_v1/protocol_lock.json`
- PDF-only metrics: `output/external_all_validated_augmented_v1_pdf_only_metrics.json`
- Human-error agreement: `output/external_all_validated_augmented_v1_pdf_only_human_error_agreement_2026-02-24.md`
- Point agreement within 10%: `90.9%` (95% CI: `72.7%` to `100.0%`) on 11 comparable trials
- CI-bound agreement within 10%: `70.0%` (95% CI: `40.0%` to `100.0%`) on 10 comparable trials
- Strict match rate: `76.9%`, lenient match rate: `84.6%`, MA-ready yield: `76.9%`

## Readiness Assessment
- Strong signal exists for point-estimate extraction under a 10% human-error envelope.
- Broad external publishability is still constrained by identity-validated sample size and CI stability.
- Current identity-validated full-text size (`n=13`) remains below the repo's own precision guidance (`n≈73` for +/-5% at 95% confidence in `docs/SAMPLE_SIZE_JUSTIFICATION.md`).

## Practical Claim Boundary
- Publishable now as a scoped methods/engineering paper with explicit boundary conditions.
- Not yet publishable as a broad external full-text generalization claim without expanding identity-validated n and reducing CI-instability cases.
