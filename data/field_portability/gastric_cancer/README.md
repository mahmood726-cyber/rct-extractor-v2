# Gastric Cancer — real-PDF accuracy (field portability bundle)

Specialty profile: `rct_extractor/_engine/specialties/gastric_cancer.py`
(+ `gastric_cancer_arm_data.py`), registered in `registry.py` and `api.py`.
Subspecialties: **systemic** (advanced / metastatic), **perioperative**
(neoadjuvant / adjuvant), **surgical** (gastrectomy / lymphadenectomy), **mortality**.

## Measured real-PDF accuracy (non-circular)

Same methodology as `docs/PDF_ACCURACY_EVAL.md` (gold harvested independently from
each abstract with the verbatim anti-fabrication guard; scored on the full PDF body).

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| pdf_raw | 133 | **128 (96%)** | 2 (2%) | 3 (2%) |

- **39 real PMC open-access gastric-cancer RCT articles, 133 gold effect tuples.**
- Among matched pairs: effect-type **100%**, CI bounds (tol) 98%, point (exact 2 dp) 100%.
- **96% ≥ 95% target, no core change required, no overfitting / no PMCID special-casing.**
- The 5 residuals are single-paper PDF-body artefacts (CI split across a line/column
  or attached to a neighbouring estimate) that parse correctly in isolation — not
  generalizable pattern gaps.

## Reproduce

`eutils.ncbi.nlm.nih.gov` does not resolve on the build machine; corpus acquired via
EuropePMC (`scripts/pdf_eval/acquire_via_europepmc.py`, reading `GASTRIC_CANCER_TERM`
from `scripts/gastric_cancer/build_gastric_cancer_corpus.py`):

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty gastric_cancer --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty gastric_cancer \
    --per-specialty 60 --target 45 --out data/pdf_eval/gold_gastric_cancer.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_gastric_cancer.jsonl \
    --out data/pdf_eval/eval_onc_gastric_cancer.json --preprocess
```

PDFs, gold jsonl and eval json are git-ignored; this README records the measured numbers.
