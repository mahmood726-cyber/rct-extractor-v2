# Real-PDF Accuracy — insomnia specialty

> Same honest, non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold
> tuples quoted verbatim from each article's **abstract**; scored on the **full
> PDF body**.

## TL;DR (honest)

- **43/44 = 98% correct** on the **in-scope** RCT effect tuples (real PDFs).
  Above the ≥95% bar.
- **No new effect patterns and no core-engine change**: the insomnia work is the
  specialty *profile* (ISI / SOL / WASO / TST / sleep-efficiency / PSQI / LPS
  endpoints, subspecialty routing, hypnotic/CBT-I arm labels) + corpus + gold;
  effect tuples come from the core engine already at 95–99%.
- **The single residual is out of scope, not a pattern gap.** `PMC10794978` is a
  **component network meta-analysis** of 241 CBT-I trials; its "incremental odds
  ratio (iOR), 1.68; 95% CI, 1.28–2.20" is an NMA-derived component estimate, not
  a randomised two-arm comparison — the extractor declines indirect/NMA effects by
  design. (The gold harvester's conservative 220-char design-marker window did not
  flag it because the "network meta-analysis" marker sits >220 chars from the
  effect, so it leaked in as in-scope.) On genuine RCT arm-comparison effect
  tuples the extractor is **43/43 = 100%**. The 98% figure is reported as-measured
  without removing that residual — i.e. it already clears the bar even counting
  the NMA estimate as a miss.
- **32 of 76** harvested tuples flagged out-of-scope by the design-marker guard
  (observational / NMA estimates). Reported, never scored as a miss.

## Dataset (traceable)

- **29 real PMC-OA articles**, **76 gold tuples** harvested; **44 in-scope** RCT
  effect tuples scored.
- Acquired via `scripts/pdf_eval/acquire_via_europepmc.py --specialty insomnia`.
  Corpus query: `scripts/insomnia/build_insomnia_corpus.py::INSOMNIA_TERM`.
- All PDFs parsed cleanly with PyMuPDF (born-digital).

## Results (full PDF body)

| surface | in-scope gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 44 | 43 (98%) | 0 | 1 |
| pdf_raw | 44 | 43 (98%) | 0 | 1 |
| pdf_pp | 44 | 43 (98%) | 0 | 1 |

Among matched pairs: type 100%, CI_lo 100%, CI_hi 100%, point(2dp) 100%.

## Scope / honest limits

- Gold = "effect estimates explicitly stated with a 95% CI in the abstract".
  Many insomnia RCTs report continuous outcomes (ISI, SOL, WASO, TST) without an
  abstract 95% CI — those are out of this effect-tuple gold (continuous arm-level
  extraction is covered by `insomnia_arm_data.py` but not scored here).
- The single residual (`PMC10794978`) is a component-NMA iOR — out of scope by
  design; not hard-coded around, not a pattern gap.

## Reproduce

```bash
python scripts/pdf_eval/acquire_via_europepmc.py --specialty insomnia --max-download 90
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty insomnia --per-specialty 90 --target 70 --out data/pdf_eval/gold_insomnia.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_insomnia.jsonl --out data/pdf_eval/eval_insomnia.json --preprocess
```
