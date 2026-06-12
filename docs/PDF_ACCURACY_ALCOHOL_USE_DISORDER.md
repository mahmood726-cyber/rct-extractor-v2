# Real-PDF Accuracy — alcohol use disorder (AUD) specialty

> Same honest, non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold
> tuples quoted verbatim from each article's **abstract**; scored on the **full
> PDF body**.

## TL;DR (honest)

- **25/25 = 100% correct** on the **in-scope** RCT effect tuples (real PDFs).
  Above the ≥95% bar.
- **No new effect patterns and no core-engine change**: the AUD work is the
  specialty *profile* (abstinence / heavy-drinking-days / percent-days-abstinent /
  drinks-per-day / relapse / craving / CIWA-Ar endpoints, subspecialty routing,
  pharmacotherapy/behavioural arm labels) + corpus + gold; effect tuples come from
  the core engine already at 95–99%.
- **12 of 37** harvested tuples flagged out-of-scope by the design-marker guard
  (observational estimates). Reported, never scored as a miss.

## Dataset (traceable) — honest sample-size note

- **6 real PMC-OA articles**, **37 gold tuples** harvested; **25 in-scope** RCT
  effect tuples scored.
- The corpus is deliberately small **because of how the AUD literature reports
  results**, not because of a tooling limit: most AUD RCTs report their primary
  outcomes as *continuous* measures (percentage of heavy-drinking days, percent
  days abstinent, drinks per drinking day) without an explicit OR/RR + 95% CI in
  the abstract, so they never enter this effect-tuple gold. A larger EuropePMC
  pull (`--max-download 120 --max-pages 60`) returned the same 6 OA papers whose
  abstracts state an explicit ratio + 95% CI. The **25 in-scope effect tuples**
  comfortably exceed the methodology's ≥10-tuple threshold even though the paper
  count is modest.
- Acquired via `scripts/pdf_eval/acquire_via_europepmc.py --specialty
  alcohol_use_disorder`. Corpus query:
  `scripts/alcohol_use_disorder/build_alcohol_use_disorder_corpus.py::ALCOHOL_USE_DISORDER_TERM`.
- All PDFs parsed cleanly with PyMuPDF (born-digital).

## Results (full PDF body)

| surface | in-scope gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 25 | 25 (100%) | 0 | 0 |
| pdf_raw | 25 | 25 (100%) | 0 | 0 |
| pdf_pp | 25 | 25 (100%) | 0 | 0 |

Among matched pairs: type 100%, CI_lo 100%, CI_hi 100%, point(2dp) 100%.

## Scope / honest limits

- Gold = "effect estimates explicitly stated with a 95% CI in the abstract".
  The continuous AUD primary outcomes (heavy-drinking days, PDA, drinks/day) are
  covered by `alcohol_use_disorder_arm_data.py` (arm-level extraction) but are not
  scored in this effect-tuple gold.
- Modest paper count (6) reflects the field's reporting style; effect-tuple count
  (25) clears the ≥10 threshold.

## Reproduce

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty alcohol_use_disorder --max-download 120 --max-pages 60
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty alcohol_use_disorder --per-specialty 120 --target 90 --out data/pdf_eval/gold_alcohol_use_disorder.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_alcohol_use_disorder.jsonl --out data/pdf_eval/eval_alcohol_use_disorder.json --preprocess
```
