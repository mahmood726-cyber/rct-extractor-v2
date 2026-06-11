# Ovarian Cancer — real-PDF accuracy (field portability bundle)

Specialty profile: `rct_extractor/_engine/specialties/ovarian_cancer.py`
(+ `ovarian_cancer_arm_data.py`), registered in `registry.py` and `api.py`.
Subspecialties: **systemic** (1L / relapse chemo + targeted), **maintenance**
(PARP-inhibitor / anti-angiogenic), **surgical** (cytoreduction / debulking),
**mortality**.

## Measured real-PDF accuracy (non-circular)

Same methodology as `docs/PDF_ACCURACY_EVAL.md` (gold harvested independently from
each abstract with the verbatim anti-fabrication guard; scored on the full PDF body).

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| pdf_raw | 134 | **131 (98%)** | 1 (1%) | 2 (1%) |

- **38 real PMC open-access ovarian-cancer RCT articles, 134 gold effect tuples.**
- Among matched pairs: effect-type **100%**, CI bounds (tol) 99%/99%, point (exact 2 dp) 100%.
- **98% ≥ 95% target, no overfitting / no PMCID special-casing.**

Measured on the current master core (dedup + control-character / digit-glyph PDF
repairs) plus this cluster's v6.7 CI-glyph fix. The few residuals are by-design
subgroup/biomarker-association OR declines and a per-paper body CI-split; each parses
correctly in isolation.

## Reproduce

`eutils.ncbi.nlm.nih.gov` does not resolve on the build machine; corpus acquired via
EuropePMC (`scripts/pdf_eval/acquire_via_europepmc.py`, reading `OVARIAN_CANCER_TERM`
from `scripts/ovarian_cancer/build_ovarian_cancer_corpus.py`):

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty ovarian_cancer --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty ovarian_cancer \
    --per-specialty 60 --target 45 --out data/pdf_eval/gold_ovarian_cancer.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_ovarian_cancer.jsonl \
    --out data/pdf_eval/eval_onc_ovarian_cancer.json --preprocess
```

PDFs, gold jsonl and eval json are git-ignored; this README records the measured numbers.
