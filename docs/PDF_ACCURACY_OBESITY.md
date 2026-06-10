# Real-PDF Accuracy — obesity / weight-management specialty

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the repo's independent regex (`build_gold_from_abstracts.harvest_effects`,
> verbatim guard) from each article's abstract; scored on the **full PDF body**.
> Corpus + abstracts from EuropePMC (eutils DNS-unreachable here), RCT-only filter.

## Dataset

- **45 real PMC-OA obesity RCT articles**, **128 gold effect tuples**
  (HR 64 / OR 46 / RR 16 / IRR 2). Gold in `data/pdf_eval/gold_obesity.jsonl`.

## Results

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 128 | 119 (93%) | 2 (2%) | 7 (5%) |
| **pdf_raw** | **128** | **124 (97%)** | **1 (1%)** | **3 (2%)** |
| pdf_pp | 128 | 124 (97%) | 1 (1%) | 3 (2%) |

**pdf_raw = 97% correct — above the 95% bar** (type 100%, CI 100%/99% among matched).

## One generalizable core fix this pass (v6.6)

A first pass scored 94%, with four of the eight misses all from **`PMC10697786`**
sharing one cause: that journal's font extracts `=` as the vulgar-fraction glyph
**`¼` (U+00BC)**, so the text read `HR ¼ 1.26; 95% CI ¼ 1.03 to 1.54`. The existing
v6.5 repair already converts `HR ¼`→`HR =` (so the point estimate extracted), but
it did **not** cover the same glyph in the **CI-keyword** position (`95% CI ¼ …`),
which silently dropped the whole interval. Extending that identical, documented
glyph repair to the CI position (`CI`/`confidence interval` `¼`→`=`, only when
immediately followed by a digit) recovers the CI. This is a value-independent font
repair — not benchmark gaming — and it benefits every specialty. It lifted pdf_raw
from 94%→97%; the full suite stayed green (no regressions).

## Honest residuals (pdf_raw) — not generalizable pattern gaps

- `PMC8860212` missed — `HR 0.71 for 30% reduction (95% CI, 0.59-0.85)`: a
  descriptive clause ("for 30% reduction") between point and CI; one paper's prose.
- `PMC13197901` missed — `OR T3 compared with T1 : 2.36; 95% CI: 1.09, 5.12`: a
  tertile-contrast label between the type and value plus comma-separated bounds
  (this exact paper is already a listed residual in the main `PDF_ACCURACY_EVAL.md`).
- `PMC13052788` point_only — `HR for IMT versus UC of 0.74 95% CI (0.352 to 1.558)`:
  arm-contrast glue + 3-decimal bounds; near-duplicate adjacent HR matched instead.

All parse-able variants were addressed by the v6.6 glyph repair; these three are
paper-specific prose/layout, not pattern gaps. Nothing overfit.

## Subspecialties & disambiguation

weight_loss (percent / kg body-weight change, BMI, >=5/10/15% responders),
body_composition (waist circumference, fat mass), cardiometabolic (SBP, HbA1c),
safety (GI adverse events, discontinuation, gallbladder). Obesity and diabetes
share an incretin drug vocabulary (semaglutide/tirzepatide); routing is
weight-centric vs glycaemic-centric — a dedicated test
(`test_obesity_vs_diabetes_disambiguation`) pins both directions.

## Reproduce

```bash
python scripts/pdf_eval/acquire_and_gold_epmc.py --specialty obesity \
  --query '(obesity OR overweight OR "weight loss" OR "weight management" OR \
    "body weight" OR semaglutide OR tirzepatide OR liraglutide OR orlistat OR "anti-obesity")' \
  --max-search 2500 --max-download 60 --target 45 --workers 8 --out data/pdf_eval/gold_obesity.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_obesity.jsonl \
  --out data/pdf_eval/eval_obesity.json --preprocess
```
