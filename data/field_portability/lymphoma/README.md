# Lymphoma — real-PDF accuracy (field portability bundle)

Specialty profile: `rct_extractor/_engine/specialties/lymphoma.py`
(+ `lymphoma_arm_data.py`), registered in `registry.py` and `api.py`.
Subspecialties: **hodgkin**, **aggressive** (DLBCL etc.), **indolent**
(follicular / marginal-zone), **mortality**.

## Measured real-PDF accuracy (non-circular)

Same methodology as `docs/PDF_ACCURACY_EVAL.md` (gold harvested independently from
each abstract with the verbatim anti-fabrication guard; scored on the full PDF body).

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| pdf_raw | 164 | **160 (98%)** | 0 | 4 (2%) |

- **40 real PMC open-access lymphoma RCT articles, 164 gold effect tuples** (effect-dense).
- Among matched pairs: effect-type **100%**, CI bounds (tol) 100%/100%, point (exact 2 dp) 99%.
- **98% ≥ 95% target, no overfitting / no PMCID special-casing.**

Measured on the current master core (dedup + control-character / digit-glyph PDF
repairs) plus this cluster's v6.7 CI-glyph fix. The 4 residuals are non-treatment-RCT
estimates (e.g. pooled environmental-risk HRs from a meta-analysis) that the extractor
correctly declines — each parses correctly in isolation.

## Reproduce

`eutils.ncbi.nlm.nih.gov` does not resolve on the build machine; corpus acquired via
EuropePMC (`scripts/pdf_eval/acquire_via_europepmc.py`, reading `LYMPHOMA_TERM`
from `scripts/lymphoma/build_lymphoma_corpus.py`):

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty lymphoma --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty lymphoma \
    --per-specialty 60 --target 45 --out data/pdf_eval/gold_lymphoma.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_lymphoma.jsonl \
    --out data/pdf_eval/eval_onc_lymphoma.json --preprocess
```

PDFs, gold jsonl and eval json are git-ignored; this README records the measured numbers.
