# Oesophageal Cancer — real-PDF accuracy (field portability bundle)

Specialty profile: `rct_extractor/_engine/specialties/oesophageal_cancer.py`
(+ `oesophageal_cancer_arm_data.py`), registered in `registry.py` and `api.py`.
Subspecialties: **definitive** (neoadjuvant chemoradiation / CROSS), **adjuvant**
(after oesophagectomy), **advanced** (metastatic), **mortality**.

## Measured real-PDF accuracy (non-circular)

Same methodology as `docs/PDF_ACCURACY_EVAL.md` (gold harvested independently from
each abstract with the verbatim anti-fabrication guard; scored on the full PDF body).

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| pdf_raw | 113 | **108 (96%)** | 1 (1%) | 4 (4%) |

- **30 real PMC open-access oesophageal-cancer RCT articles, 113 gold effect tuples.**
- Among matched pairs: effect-type **100%**, CI bounds (tol) 99%/99%, point (exact 2 dp) 99%.
- **96% ≥ 95% target, no overfitting / no PMCID special-casing.**
- The 5 residuals are single-paper PDF-body artefacts that parse correctly in isolation.

## Reproduce

`eutils.ncbi.nlm.nih.gov` does not resolve on the build machine; corpus acquired via
EuropePMC (`scripts/pdf_eval/acquire_via_europepmc.py`, reading
`OESOPHAGEAL_CANCER_TERM` from
`scripts/oesophageal_cancer/build_oesophageal_cancer_corpus.py`):

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty oesophageal_cancer --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty oesophageal_cancer \
    --per-specialty 60 --target 45 --out data/pdf_eval/gold_oesophageal_cancer.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_oesophageal_cancer.jsonl \
    --out data/pdf_eval/eval_onc_oesophageal_cancer.json --preprocess
```

PDFs, gold jsonl and eval json are git-ignored; this README records the measured numbers.
