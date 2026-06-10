# Prostate Cancer — real-PDF accuracy (field portability bundle)

Specialty profile: `rct_extractor/_engine/specialties/prostate_cancer.py`
(+ `prostate_cancer_arm_data.py`), registered in `registry.py` and `api.py`.
Subspecialties: **systemic** (mCRPC / mHSPC), **localized** (radiotherapy /
prostatectomy / active surveillance), **hormonal** (androgen-deprivation therapy),
**mortality / metastasis**.

## Measured real-PDF accuracy (non-circular)

Same methodology as the repo's 17-specialty eval (`docs/PDF_ACCURACY_EVAL.md`):
gold tuples `(effect_type, point, ci_lo, ci_hi)` are harvested by an **independent**
regex from each article's **abstract** with the verbatim-substring anti-fabrication
guard (`scripts/pdf_eval/build_gold_from_abstracts.py`), then the shipped extractor
is scored on the **full PDF body** — a different, messier input surface.

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 135 | 132 (98%) | 0 | 3 (2%) |
| pdf_raw  | 135 | **131 (97%)** | 3 (2%) | 1 (1%) |
| pdf_pp   | 135 | 131 (97%) | 3 (2%) | 1 (1%) |

- **30 real PMC open-access prostate-cancer RCT articles, 135 gold effect tuples.**
- Among matched pairs: effect-type 100%, CI bounds (tol) 98%, point (exact 2 dp) 100%.
- **97% ≥ 95% target, achieved with NO core-extractor change and NO overfitting**
  (no gold value or PMCID was special-cased).

### The 4 residuals (all idiosyncratic PDF-layer, not pattern gaps)

- `PMC12681322` (×3, point_only): `OR = 6.22, 95% CI = 1.35 to 47.57` etc. The
  identical sentence parses **correctly in isolation** (type+point+both CI bounds);
  on this paper's PDF body the CI bounds are dropped by a text-layer artefact. Not
  a generalizable separator gap.
- `PMC11409154` (×1, missed): `IPCW HR, 0.82 (95% CI, 0.53-1.27)` — an
  inverse-probability-of-censoring-weighting-prefixed HR present only in this paper.

Forcing these would mean special-casing PMCIDs (benchmark gaming) — declined.
An honest 97% beats a manufactured 100%.

## Reproduce

`eutils.ncbi.nlm.nih.gov` does not resolve on the build machine, so the corpus was
acquired through EuropePMC (same artefacts: same human-authored abstracts, same
real PMC PDFs) via `scripts/pdf_eval/acquire_via_europepmc.py`, which reads the
PubMed `PROSTATE_CANCER_TERM` from `scripts/prostate_cancer/build_prostate_cancer_corpus.py`:

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty prostate_cancer --max-download 40
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty prostate_cancer \
    --per-specialty 60 --target 40 --out data/pdf_eval/gold_prostate_cancer.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_prostate_cancer.jsonl \
    --out data/pdf_eval/eval_onc_prostate_cancer.json --preprocess
```

PDFs, gold jsonl and eval json are git-ignored (re-fetchable); this README records
the measured numbers.
