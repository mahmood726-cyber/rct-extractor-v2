# Real-PDF Accuracy — chronic rhinosinusitis (CRS) specialty

> Same honest, non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold
> tuples quoted verbatim from each article's **abstract** by an independent regex
> with a verbatim-substring anti-fabrication guard; scored on the **full PDF body**.

## TL;DR (honest)

- **43/43 = 100% correct** on the **in-scope** RCT effect tuples (real PDFs).
  Above the ≥95% bar.
- **No new effect patterns and no core-engine change**: the CRS work is the
  specialty *profile* (SNOT-22 / nasal polyp score / Lund-Mackay / Lund-Kennedy
  endpoints, subspecialty routing, biologic/steroid/surgery arm labels) + corpus
  + gold; effect tuples come from the same core engine already at 95–99%.
- **69 of 112** harvested tuples flagged **out-of-scope** by the independent
  design-marker guard (observational / cohort / case-control association
  estimates — the broad corpus query pulls in many CRS-comorbidity/risk
  epidemiology studies). Reported, never scored as a miss.

## Dataset (traceable)

- **33 real PMC-OA articles**, **112 gold tuples** harvested; **43 in-scope** RCT
  effect tuples scored.
- Acquired via `scripts/pdf_eval/acquire_via_europepmc.py --specialty
  chronic_rhinosinusitis`. Corpus query:
  `scripts/chronic_rhinosinusitis/build_chronic_rhinosinusitis_corpus.py::CHRONIC_RHINOSINUSITIS_TERM`.
- All PDFs parsed cleanly with PyMuPDF (born-digital).

## Results (full PDF body)

| surface | in-scope gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 43 | 43 (100%) | 0 | 0 |
| pdf_raw | 43 | 43 (100%) | 0 | 0 |
| pdf_pp | 43 | 43 (100%) | 0 | 0 |

Among matched pairs: type 100%, CI_lo 100%, CI_hi 100%, point(2dp) 100%.

## Scope / honest limits

- Gold = "effect estimates explicitly stated with a 95% CI in the abstract".
  Many CRS RCTs report primary outcomes as continuous score differences
  (SNOT-22, nasal polyp score) without an abstract 95% CI — those are out of this
  effect-tuple gold (continuous arm-level extraction is covered by
  `chronic_rhinosinusitis_arm_data.py` but not scored here).
- The 69 out-of-scope tuples reflect a broad corpus query catching observational
  CRS-association studies; the in-scope RCT sample (43 effects / 33 papers)
  comfortably clears the ≥10 threshold.

## Reproduce

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty chronic_rhinosinusitis --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty chronic_rhinosinusitis --per-specialty 60 --target 45 --out data/pdf_eval/gold_chronic_rhinosinusitis.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_chronic_rhinosinusitis.jsonl --out data/pdf_eval/eval_chronic_rhinosinusitis.json --preprocess
```
