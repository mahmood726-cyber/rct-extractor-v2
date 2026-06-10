# Melanoma — real-PDF accuracy (field portability bundle)

Specialty profile: `rct_extractor/_engine/specialties/melanoma.py`
(+ `melanoma_arm_data.py`), registered in `registry.py` and `api.py`.
Subspecialties: **systemic** (advanced / metastatic), **adjuvant** (resected
stage III/IV), **neoadjuvant**, **mortality**.

## Measured real-PDF accuracy (non-circular)

Same methodology as `docs/PDF_ACCURACY_EVAL.md` (gold harvested independently from
each abstract with the verbatim anti-fabrication guard; scored on the full PDF body).

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| pdf_raw | 140 | **138 (99%)** | 0 | 2 (1%) |

- **37 real PMC open-access melanoma RCT articles, 140 gold effect tuples.**
- Among matched pairs: effect-type 100%, CI bounds (tol) 100%/100%, point (exact 2 dp) 100%.
- **99% ≥ 95% target, no core change required for melanoma, no overfitting.**
- The 2 residuals are single-paper PDF-body artefacts that parse correctly in isolation.

## Reproduce

`eutils.ncbi.nlm.nih.gov` does not resolve on the build machine; corpus acquired via
EuropePMC (`scripts/pdf_eval/acquire_via_europepmc.py`, reading `MELANOMA_TERM`
from `scripts/melanoma/build_melanoma_corpus.py`):

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty melanoma --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty melanoma \
    --per-specialty 60 --target 45 --out data/pdf_eval/gold_melanoma.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_melanoma.jsonl \
    --out data/pdf_eval/eval_onc_melanoma.json --preprocess
```

PDFs, gold jsonl and eval json are git-ignored; this README records the measured numbers.
