# Real-PDF Accuracy — otitis media (middle-ear) specialty

> Same honest, non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold
> tuples quoted verbatim from each article's **abstract**; scored on the **full
> PDF body**.

## TL;DR (honest)

- **40/40 = 100% correct** on the **in-scope** RCT effect tuples (real PDFs).
  Above the ≥95% bar.
- **No new effect patterns and no core-engine change**: the otitis-media work is
  the specialty *profile* (treatment-failure/cure/recurrence/effusion/hearing/
  otorrho?ea/tube endpoints, subspecialty routing, antibiotic/vaccine/surgery arm
  labels) + corpus + gold; effect tuples come from the core engine already at
  95–99%.
- **10 of 50** harvested tuples flagged **out-of-scope** by the independent
  design-marker guard (observational association estimates). Reported, never
  scored as a miss.

## Dataset (traceable)

- **13 real PMC-OA articles**, **50 gold tuples** harvested; **40 in-scope** RCT
  effect tuples scored.
- Acquired via `scripts/pdf_eval/acquire_via_europepmc.py --specialty
  otitis_media`. Corpus query:
  `scripts/otitis_media/build_otitis_media_corpus.py::OTITIS_MEDIA_TERM`.
- All PDFs parsed cleanly with PyMuPDF (born-digital).

## Results (full PDF body)

| surface | in-scope gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 40 | 40 (100%) | 0 | 0 |
| pdf_raw | 40 | 40 (100%) | 0 | 0 |
| pdf_pp | 40 | 40 (100%) | 0 | 0 |

Among matched pairs: type 100%, CI_lo 100%, CI_hi 100%, point(2dp) 100%.

## Scope / honest limits

- Gold = "effect estimates explicitly stated with a 95% CI in the abstract".
  Many otitis-media RCTs report continuous outcomes (hearing level, pain score)
  without an abstract 95% CI — those are out of this effect-tuple gold (continuous
  arm-level extraction is covered by `otitis_media_arm_data.py` but not scored).
- The in-scope RCT sample (40 effects / 13 papers) clears the ≥10 threshold.

## Reproduce

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty otitis_media --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty otitis_media --per-specialty 60 --target 45 --out data/pdf_eval/gold_otitis_media.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_otitis_media.jsonl --out data/pdf_eval/eval_otitis_media.json --preprocess
```
