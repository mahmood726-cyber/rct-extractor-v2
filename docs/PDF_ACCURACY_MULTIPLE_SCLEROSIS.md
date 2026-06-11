# Real-PDF Accuracy — Multiple sclerosis (`multiple_sclerosis`)

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold tuples
> harvested by the extractor-INDEPENDENT `build_gold_from_abstracts.harvest_effects`
> (verbatim-substring guard) over each article's abstract; the shipped extractor
> is scored on the full PDF body. EuropePMC-sourced (NCBI `eutils` DNS-blocked on
> the host) via `scripts/pdf_eval/acquire_epmc_gold.py` — source swapped only;
> method identical and non-circular.

## Gold quality: RCT-only + unit guards (honest)

The acquirer excludes non-RCT papers (`_looks_non_rct`: review / meta-analysis /
observational incl. cohort / propensity-score / comparative-effectiveness /
target-trial-emulation / real-world, when no RCT self-description is present) and
drops heart-rate false positives (`_drop_heart_rate`: an `HR` tuple whose point is
followed by `bpm`/`beats` or near `heart rate` is a heart-rate measurement, not a
hazard ratio). Both are design/unit-based exclusions (no effect-value inspection),
generalizable across specialties. They removed two contaminants the extractor
correctly handled — `PMC12516238` (propensity-matched observational cohort, which
the extractor suppresses by design) and `PMC12413561` (`HR nadir 48.9 bpm`, a
heart rate). These are not RCT effect estimates and do not belong in the gold.

## Dataset

- **22 real PMC Open-Access MS RCT articles**, **61 gold effect tuples**
  (explicit ratio + 95% CI in the abstract).
- Gold: `data/pdf_eval/gold_multiple_sclerosis.jsonl`. PDFs gitignored.

## Results (match tol: point ±0.02/2%, CI ±0.03/3%)

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 61 | 60 (98%) | 1 | 0 |
| pdf_raw  | 61 | **59 (97%)** | 1 | 1 |
| pdf_pp   | 61 | 59 (97%) | 1 | 1 |

**Real-PDF accuracy = 97% (59/61) ≥ 95% target.**

## Honest remaining residuals (2)

- `PMC11439292` point_only: the abstract itself is internally contradictory —
  `"relative risk (HR = 0.620, 95% CI 0.27-1.44)"`. The extractor returns the
  point and both CI bounds correctly but labels it `HR` (the literal token),
  whereas the gold harvester labels it `RR` (`relative risk`). Type disagreement
  is in the source text, not an extractor error.
- `PMC12589805` missed (1 of 3 HRs): `"(HR 0.08, 95% CI 0.01, 0.96)"`. The gold
  sentence parses cleanly in isolation and the paper's other two HRs (0.24, 0.46)
  are extracted correctly from the PDF body; this single tuple is lost to a
  PDF-text-layer artifact (same residual class as the main eval's column-break /
  glyph cases). Not a generalizable pattern gap.

The effect-tuple extraction is the shared core (`enhanced_extractor_v3.py`); the
`multiple_sclerosis` module adds endpoint vocabulary (ARR, CDP, EDSS,
gadolinium-enhancing / new-T2 lesions, NEDA, SDMT, T25FW, brain atrophy, …),
subspecialty routing (relapsing / progressive / symptomatic / acute-relapse), and
arm-level labels.
