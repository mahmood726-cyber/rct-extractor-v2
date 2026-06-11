# Pancreatic Cancer — real-PDF accuracy (field portability bundle)

Specialty profile: `rct_extractor/_engine/specialties/pancreatic_cancer.py`
(+ `pancreatic_cancer_arm_data.py`), registered in `registry.py` and `api.py`.
Subspecialties: **systemic** (advanced / metastatic), **adjuvant** (resected),
**locally_advanced** (chemoradiation / conversion), **mortality**.

## Measured real-PDF accuracy (non-circular)

Same methodology as `docs/PDF_ACCURACY_EVAL.md` (gold harvested independently from
each abstract with the verbatim anti-fabrication guard; extractor scored on the
full PDF body).

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| pdf_raw | 130 | **127 (98%)** | 1 (1%) | 2 (2%) |

- **38 real PMC open-access pancreatic-cancer RCT articles, 130 gold effect tuples.**
- Among matched pairs: effect-type **100%**, CI bounds (tol) 100%/99%, point (exact 2 dp) 100%.
- **98% ≥ 95% target. No overfitting / no PMCID special-casing.**

### One generalizable core fix made this pass (v6.6, benefits every specialty)

The first measurement was 113/130 = 87% with **15 point_only**, of which **14 came
from just two companion prognostic-factor review PDFs** (`PMC13247336`,
`PMC13247335`). Their body text renders the `=` glyph as the vulgar fraction `¼`
*after the CI keyword* — `95% CI ¼ 1.55 to 2.05`. The existing v6.5 `¼`→`=` repair
only covered `<ratio> ¼ <number>` (so the point was recovered → point_only) but not
`CI ¼ <number>`, so both CI bounds were dropped.

The fix (`enhanced_extractor_v3.py`, v6.6) extends that **bounded** glyph repair to
the CI-keyword position only (`\b(CI|C.I.|confidence interval)\s*[¼½¾]\s*(?=\d)` →
`= `). It is a font-glyph normalization, not a value/PMCID special-case, so it
generalizes to any paper from that font family across all specialties. **The full
existing suite stays green (1387 passed, 0 regressions)** and the sentence
`HR ¼ 1.78, 95% CI ¼ 1.55 to 2.05` now extracts type+point+both CI bounds exactly.

The 3 residuals after the fix (1 point_only + 2 missed) are single-paper PDF-body
artefacts that parse correctly in isolation — not pattern gaps; not forced.

## Reproduce

`eutils.ncbi.nlm.nih.gov` does not resolve on the build machine; corpus acquired via
EuropePMC (`scripts/pdf_eval/acquire_via_europepmc.py`, reading `PANCREATIC_CANCER_TERM`
from `scripts/pancreatic_cancer/build_pancreatic_cancer_corpus.py`):

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty pancreatic_cancer --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty pancreatic_cancer \
    --per-specialty 60 --target 45 --out data/pdf_eval/gold_pancreatic_cancer.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_pancreatic_cancer.jsonl \
    --out data/pdf_eval/eval_onc_pancreatic_cancer.json --preprocess
```

PDFs, gold jsonl and eval json are git-ignored; this README records the measured numbers.
