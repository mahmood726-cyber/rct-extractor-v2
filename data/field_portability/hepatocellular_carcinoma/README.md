# Hepatocellular Carcinoma (HCC) — real-PDF accuracy (field portability bundle)

Specialty profile: `rct_extractor/_engine/specialties/hepatocellular_carcinoma.py`
(+ `hepatocellular_carcinoma_arm_data.py`), registered in `registry.py` and `api.py`.
Subspecialties: **systemic** (advanced / BCLC-C), **locoregional** (TACE / TARE),
**curative** (resection / transplant / ablation), **mortality**.

**Routing note:** HCC deliberately overlaps the `hepatitis` keyword bucket (both
mention "hepatocellular carcinoma" / "cirrhosis"). A dedicated routing test confirms
an HCC trial that also mentions HBV-related cirrhosis routes to
`hepatocellular_carcinoma`, while a pure antiviral hepatitis-C trial still routes to
`hepatitis`.

## Measured real-PDF accuracy (non-circular)

Same methodology as `docs/PDF_ACCURACY_EVAL.md` (gold harvested independently from
each abstract with the verbatim anti-fabrication guard; scored on the full PDF body).

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| pdf_raw | 154 | **149 (97%)** | 1 (1%) | 4 (3%) |

- **40 real PMC open-access HCC RCT articles, 154 gold effect tuples** (effect-dense).
- Among matched pairs: effect-type **100%**, CI bounds (tol) 100%/99%, point (exact 2 dp) 99%.
- **97% ≥ 95% target, no overfitting / no PMCID special-casing.**

Measured on the current master core (dedup + control-character / digit-glyph PDF
repairs) plus this cluster's v6.7 CI-glyph fix. The few residuals are single-paper
PDF-body artefacts (one paper with a fully space-stripped abstract text layer) and a
known residual already documented in the repo's own eval; each parses in isolation.

## Reproduce

`eutils.ncbi.nlm.nih.gov` does not resolve on the build machine; corpus acquired via
EuropePMC (`scripts/pdf_eval/acquire_via_europepmc.py`, reading
`HEPATOCELLULAR_CARCINOMA_TERM` from
`scripts/hepatocellular_carcinoma/build_hepatocellular_carcinoma_corpus.py`):

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty hepatocellular_carcinoma --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty hepatocellular_carcinoma \
    --per-specialty 60 --target 45 --out data/pdf_eval/gold_hepatocellular_carcinoma.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_hepatocellular_carcinoma.jsonl \
    --out data/pdf_eval/eval_onc_hepatocellular_carcinoma.json --preprocess
```

PDFs, gold jsonl and eval json are git-ignored; this README records the measured numbers.
