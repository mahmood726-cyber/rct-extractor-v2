# Real-PDF Accuracy — Migraine (`migraine`)

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold tuples
> harvested by the extractor-INDEPENDENT `build_gold_from_abstracts.harvest_effects`
> (verbatim guard) over each article's abstract; the shipped extractor is scored
> on the full PDF body. EuropePMC-sourced (NCBI `eutils` DNS-blocked on the host)
> via `scripts/pdf_eval/acquire_epmc_gold.py`; source swapped only, method identical.

## Gold quality: RCT-only filter (honest)

The "migraine" literature is unusually rich in **Mendelian randomization** (MR)
studies — a genetic-instrument *observational* design whose name misleadingly
contains "randomization". The acquirer's `_looks_non_rct` hard-excludes MR,
reviews/meta-analyses, cohort/case-control/observational studies, retrospective
and real-world studies, and propensity-score / target-trial-emulation designs
(decisive design markers; no effect-value inspection). On the first pass 7 of 22
candidate papers were MR or retrospective/real-world contaminants (e.g.
`PMC11338938` allergic-disease↔Ménière MR, `PMC12849531` retrospective real-world
pediatric gepant study) that the extractor correctly declines; after filtering,
the gold is genuinely RCT-only.

## Dataset

- **22 real PMC Open-Access migraine RCT articles**, **48 gold effect tuples**
  (explicit ratio + 95% CI in the abstract).
- Gold: `data/pdf_eval/gold_migraine.jsonl`. PDFs gitignored.

## Results (match tol: point ±0.02/2%, CI ±0.03/3%)

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 48 | 48 (100%) | 0 | 0 |
| pdf_raw  | 48 | **48 (100%)** | 0 | 0 |
| pdf_pp   | 48 | 48 (100%) | 0 | 0 |

**Real-PDF accuracy = 100% (48/48) ≥ 95% target.** No remaining gaps.

The effect-tuple extraction is the shared core (`enhanced_extractor_v3.py`); the
`migraine` module adds endpoint vocabulary (2-h pain freedom / relief, MBS
freedom, monthly migraine / headache days, ≥50% responder, acute medication days,
MIDAS/HIT-6), subspecialty routing (acute / preventive / chronic / device-neuromod),
and arm-level labels (triptans, gepants, lasmiditan, anti-CGRP mAbs,
onabotulinumtoxinA).
