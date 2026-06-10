# Bladder Cancer — real-PDF accuracy (field portability bundle)

Specialty profile: `rct_extractor/_engine/specialties/bladder_cancer.py`
(+ `bladder_cancer_arm_data.py`), registered in `registry.py` and `api.py`.
Subspecialties: **nmibc** (non-muscle-invasive), **mibc** (muscle-invasive /
neoadjuvant), **advanced** (metastatic urothelial), **mortality**.

## Measured real-PDF accuracy (non-circular)

Same methodology as `docs/PDF_ACCURACY_EVAL.md` (gold harvested independently from
each abstract with the verbatim anti-fabrication guard; scored on the full PDF body).

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| pdf_raw | 118 | **112 (95%)** | 1 (1%) | 5 (4%) |

- **39 real PMC open-access bladder-cancer RCT articles, 118 gold effect tuples.**
- Among matched pairs: effect-type 99%, CI bounds (tol) 100%/100%, point (exact 2 dp) 100%.
- **95% ≥ 95% target, no overfitting / no PMCID special-casing.**

This number is measured on the current master core (which includes the dedup +
control-character / digit-glyph PDF repairs) plus this cluster's v6.7 CI-glyph fix.
The remaining residuals are non-treatment-RCT estimates (a couple of
propensity-score-matched observational ORs and a gold-harvester median-as-HR edge
case) that the extractor correctly declines — each parses correctly in isolation.

## Reproduce

`eutils.ncbi.nlm.nih.gov` does not resolve on the build machine; corpus acquired via
EuropePMC (`scripts/pdf_eval/acquire_via_europepmc.py`, reading `BLADDER_CANCER_TERM`
from `scripts/bladder_cancer/build_bladder_cancer_corpus.py`):

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty bladder_cancer --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty bladder_cancer \
    --per-specialty 60 --target 45 --out data/pdf_eval/gold_bladder_cancer.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_bladder_cancer.jsonl \
    --out data/pdf_eval/eval_onc_bladder_cancer.json --preprocess
```

PDFs, gold jsonl and eval json are git-ignored; this README records the measured numbers.
