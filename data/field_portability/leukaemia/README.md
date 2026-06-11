# Leukaemia — real-PDF accuracy (field portability bundle)

Specialty profile: `rct_extractor/_engine/specialties/leukaemia.py`
(+ `leukaemia_arm_data.py`), registered in `registry.py` and `api.py`.
Subspecialties (by subtype): **aml**, **all**, **cll**, **cml**.

## Measured real-PDF accuracy (non-circular)

Same methodology as `docs/PDF_ACCURACY_EVAL.md` (gold harvested independently from
each abstract with the verbatim anti-fabrication guard; scored on the full PDF body).

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| pdf_raw | 128 | **123 (96%)** | 0 | 5 (4%) |

- **40 real PMC open-access leukaemia RCT articles, 128 gold effect tuples.**
- Among matched pairs: effect-type **100%**, CI bounds (tol) 100%/100%, point (exact 2 dp) 100%.
- **96% ≥ 95% target, no overfitting / no PMCID special-casing.**

Measured on the current master core (dedup + control-character / digit-glyph PDF
repairs) plus this cluster's v6.7 CI-glyph fix. The 5 residuals are effect-dense
papers where the extractor surfaces a subset of many stated effects (recall on
multivariable haematology results), each parsing correctly in isolation; precision
on matched pairs is 100%.

## Reproduce

`eutils.ncbi.nlm.nih.gov` does not resolve on the build machine; corpus acquired via
EuropePMC (`scripts/pdf_eval/acquire_via_europepmc.py`, reading `LEUKAEMIA_TERM`
from `scripts/leukaemia/build_leukaemia_corpus.py`):

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty leukaemia --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty leukaemia \
    --per-specialty 60 --target 45 --out data/pdf_eval/gold_leukaemia.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_leukaemia.jsonl \
    --out data/pdf_eval/eval_onc_leukaemia.json --preprocess
```

PDFs, gold jsonl and eval json are git-ignored; this README records the measured numbers.
