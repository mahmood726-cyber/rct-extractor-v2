# Real-PDF Accuracy — Alzheimer's disease / dementia (`alzheimers`)

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold tuples are
> harvested by the extractor-INDEPENDENT `scripts/pdf_eval/build_gold_from_abstracts.py`
> (`harvest_effects`, verbatim-substring guard) over each article's own abstract;
> the shipped extractor is scored on the full PDF body. No gold value is produced
> by the extractor under test; nothing is hard-coded per paper.

## Provenance note

EuropePMC-sourced (NCBI `eutils` DNS-blocked on the build host) via
`scripts/pdf_eval/acquire_epmc_gold.py` — swaps only the data source; identical
gold method, scored on the full PDF body. Each record stores `source="europepmc"`
and the verbatim quote.

## Gold quality: RCT-only filter (honest)

The acquirer now excludes papers whose abstract is itself a **meta-analysis /
systematic review** or a purely **observational study** (cohort / case-control /
registry / real-world) with no RCT self-description (`_looks_non_rct`). This is a
study-DESIGN exclusion (no effect-value inspection), generalizable across all
specialties: those are exactly the non-RCT estimates the extractor declines by
design, so they do not belong in an RCT gold set. (Before this filter, one
contaminant — `PMC12957778`, a meta-analysis of SGLT2i-vs-DPP4i observational
cohorts — produced 3 spurious "misses" where the extractor correctly returned
nothing; the filter removes it and the genuine RCT golds score 100%.)

## Dataset

- **22 real PMC Open-Access Alzheimer's/dementia RCT articles**, **45 gold effect
  tuples** (explicit ratio + 95% CI in the abstract).
- Gold: `data/pdf_eval/gold_alzheimers.jsonl`. PDFs gitignored.

## Results (match tol: point ±0.02/2%, CI ±0.03/3%)

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 45 | 45 (100%) | 0 | 0 |
| pdf_raw  | 45 | **45 (100%)** | 0 | 0 |
| pdf_pp   | 45 | 45 (100%) | 0 | 0 |

Among matched pairs on pdf_raw (n=45): type 100%, CI-low 100%, CI-high 100%,
point(exact 2dp) 100%.

**Real-PDF accuracy = 100% (45/45) ≥ 95% target.** No remaining gaps.

The effect-tuple extraction is the shared core (`enhanced_extractor_v3.py`); the
`alzheimers` module adds endpoint vocabulary (ADAS-Cog, CDR-SB, MMSE, ADCS-ADL,
iADRS, amyloid PET centiloids, ARIA, NPI/CMAI, progression-to-dementia, …),
subspecialty routing (symptomatic / disease-modifying / neuropsychiatric /
prevention-MCI), and arm-level labels.
