# Real-PDF Accuracy — COVID-19 (`covid19`)

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the extractor-INDEPENDENT `build_gold_from_abstracts.harvest_effects` (verbatim
> guard) over each abstract; the shipped extractor is scored on the full PDF body.
> EuropePMC-sourced (NCBI `eutils` DNS-blocked on host); non-RCT papers excluded by
> `_looks_non_rct`.

## Routing note

COVID-19 was previously absorbed by the generic `infectious_disease` catch-all.
The dedicated `covid19` specialty now wins routing (the ID bucket is a fallback);
a regression test in `tests/test_hepatitis.py` asserts a covid abstract routes to
`covid19`, while a generic bacterial-infection abstract still falls back to
`infectious_disease`.

## Dataset

- **22 real PMC Open-Access COVID-19 RCT articles**, **65 gold effect tuples**
  (explicit ratio + 95% CI in the abstract). COVID-19 trials are ratio-rich
  (hospitalization-or-death, mortality, progression), so the sample is large.
- Gold: `data/pdf_eval/gold_covid19.jsonl`. PDFs gitignored.

## Results (match tol: point ±0.02/2%, CI ±0.03/3%)

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 65 | 64 (98%) | 1 | 0 |
| pdf_raw  | 65 | **64 (98%)** | 1 | 0 |
| pdf_pp   | 65 | 64 (98%) | 1 | 0 |

**Real-PDF accuracy = 98% (64/65) ≥ 95% target.**

## Honest remaining residual (1)

- `PMC12887464` point_only: `"adjusted odds ratio (aOR) compared with SOC: 1.12;
  95% CI 0.49 to 2.58"`. The extractor returns the point and both CI bounds; the
  single point_only is a minor type/label edge on the "(aOR) compared with SOC:"
  glue, not a missed effect.

The effect-tuple extraction is the shared core (`enhanced_extractor_v3.py`); the
`covid19` module adds endpoint vocabulary (hospitalization-or-death, 28-day
mortality, time to sustained recovery, progression to mechanical ventilation/WHO
scale, viral clearance, vaccine efficacy, symptomatic infection), subspecialty
routing (antiviral / immunomodulator / prophylaxis-vaccine / severe-supportive),
and arm-level labels (nirmatrelvir-ritonavir, molnupiravir, remdesivir,
dexamethasone, tocilizumab, baricitinib, convalescent plasma).
