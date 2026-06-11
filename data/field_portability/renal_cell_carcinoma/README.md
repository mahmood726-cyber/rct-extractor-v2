# Renal Cell Carcinoma (RCC) — real-PDF accuracy (field portability bundle)

Specialty profile: `rct_extractor/_engine/specialties/renal_cell_carcinoma.py`
(+ `renal_cell_carcinoma_arm_data.py`), registered in `registry.py` and `api.py`.
Subspecialties: **advanced** (1L metastatic), **adjuvant**, **subsequent_line**
(VEGF/mTOR), **mortality**.

**Routing note:** RCC deliberately overlaps the `nephrology` keyword bucket
("renal"/"kidney"). Dedicated routing tests confirm an RCC trial routes to
`renal_cell_carcinoma` while a pure CKD/dialysis trial does not.

## Measured real-PDF accuracy (non-circular)

Same methodology as `docs/PDF_ACCURACY_EVAL.md` (gold harvested independently from
each abstract with the verbatim anti-fabrication guard; scored on the full PDF body).

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| pdf_raw | 141 | **135 (96%)** | 2 (1%) | 4 (3%) |

- **37 real PMC open-access RCC RCT articles, 141 gold effect tuples.**
- Among matched pairs: effect-type **100%**, CI bounds (tol) 99%/99%, point (exact 2 dp) 99%.
- **96% ≥ 95% target, no overfitting / no PMCID special-casing.**
- The 6 residuals are single-paper PDF-body / non-RCT-association cases that parse
  correctly in isolation — not generalizable pattern gaps.

This branch carries the v6.7 CI-glyph core fix (extends the existing `¼`-for-`=`
font-glyph repair to the CI-keyword position) on top of the current master core.

## Reproduce

`eutils.ncbi.nlm.nih.gov` does not resolve on the build machine; corpus acquired via
EuropePMC (`scripts/pdf_eval/acquire_via_europepmc.py`, reading
`RENAL_CELL_CARCINOMA_TERM` from
`scripts/renal_cell_carcinoma/build_renal_cell_carcinoma_corpus.py`):

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty renal_cell_carcinoma --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty renal_cell_carcinoma \
    --per-specialty 60 --target 45 --out data/pdf_eval/gold_renal_cell_carcinoma.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_renal_cell_carcinoma.jsonl \
    --out data/pdf_eval/eval_onc_renal_cell_carcinoma.json --preprocess
```

PDFs, gold jsonl and eval json are git-ignored; this README records the measured numbers.
