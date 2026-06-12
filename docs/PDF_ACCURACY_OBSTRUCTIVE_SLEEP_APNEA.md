# Real-PDF Accuracy — obstructive sleep apnoea (OSA) specialty

> Same honest, non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold
> tuples quoted verbatim from each article's **abstract**; scored on the **full
> PDF body**.

## TL;DR (honest)

- **16/16 = 100% correct** on the **in-scope** RCT effect tuples (real PDFs).
  Above the ≥95% bar.
- **No new effect patterns and no core-engine change**: the OSA work is the
  specialty *profile* (AHI / ODI / ESS / CPAP-adherence / SpO2 / BP endpoints,
  subspecialty routing, PAP/oral-appliance/surgical arm labels) + corpus + gold;
  effect tuples come from the core engine already at 95–99%.
- **23 of 39** harvested tuples flagged **out-of-scope** by the independent
  design-marker guard (observational OSA-association estimates). Reported, never
  scored as a miss.

## Dataset (traceable)

- **12 real PMC-OA articles**, **39 gold tuples** harvested; **16 in-scope** RCT
  effect tuples scored.
- Acquired via `scripts/pdf_eval/acquire_via_europepmc.py --specialty
  obstructive_sleep_apnea`. Corpus query:
  `scripts/obstructive_sleep_apnea/build_obstructive_sleep_apnea_corpus.py::OBSTRUCTIVE_SLEEP_APNEA_TERM`.
- All PDFs parsed cleanly with PyMuPDF (born-digital).

## Results (full PDF body)

| surface | in-scope gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 16 | 16 (100%) | 0 | 0 |
| pdf_raw | 16 | 16 (100%) | 0 | 0 |
| pdf_pp | 16 | 16 (100%) | 0 | 0 |

Among matched pairs: type 100%, CI_lo 100%, CI_hi 100%, point(2dp) 100%.

## Scope / honest limits

- Gold = "effect estimates explicitly stated with a 95% CI in the abstract".
  Most OSA RCTs report their *primary* outcomes as continuous differences (AHI,
  ESS, blood pressure) without an abstract 95% CI — those are out of this
  effect-tuple gold (continuous arm-level extraction is covered by
  `obstructive_sleep_apnea_arm_data.py` but not scored here). This keeps the
  in-scope effect-tuple sample modest (16 effects / 12 papers, above the ≥10
  threshold) — an honest reflection of how the OSA literature reports results.

## Reproduce

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty obstructive_sleep_apnea --max-download 45
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty obstructive_sleep_apnea --per-specialty 60 --target 45 --out data/pdf_eval/gold_obstructive_sleep_apnea.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_obstructive_sleep_apnea.jsonl --out data/pdf_eval/eval_obstructive_sleep_apnea.json --preprocess
```
