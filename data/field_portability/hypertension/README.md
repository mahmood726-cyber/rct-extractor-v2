# Hypertension / Cardiovascular RCT Extraction — Field Bundle

The hypertension extractor (`src/specialties/hypertension.py` +
`hypertension_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and arm-data engine with hypertension endpoints and
antihypertensive drug-class arm labels. Hypertension/CVD is a rising
Africa-priority non-communicable-disease (NCD) topic, so this profile follows the
same African-student meta-analysis workflow as the malaria / HIV / typhoid bundles.

- **bp_lowering** — blood-pressure control / target attainment, treatment
  (responder) response (ACE inhibitor / ARB / calcium-channel-blocker / thiazide /
  beta-blocker / MRA / ARNI / single-pill-combination arms: lisinopril, enalapril,
  ramipril, losartan, valsartan, telmisartan, amlodipine, nifedipine,
  hydrochlorothiazide, chlorthalidone, indapamide, atenolol, bisoprolol,
  spironolactone, sacubitril-valsartan …).
- **cv_events** — major adverse cardiovascular events (MACE), stroke, myocardial
  infarction, cardiovascular death, all-cause mortality, heart-failure
  hospitalisation.
- **bp_reduction** — change in systolic / diastolic blood pressure, mean arterial
  pressure, 24-hour ambulatory blood pressure (continuous; MD/SMD, natural scale).
- **adherence** — medication adherence / compliance (proportion of days covered,
  medication possession ratio), persistence / discontinuation.

## How it works

Same architecture as the sibling bundles:

- **specialty routing** — `detect_specialty()` routes blood-pressure / antihypertensive
  abstracts to `hypertension`. Keywords are deliberately BP-specific (blood
  pressure, systolic/diastolic, mmHg, antihypertensive, ACE inhibitor / ARB / CCB /
  thiazide, amlodipine / hydrochlorothiazide …) so a CVD-framed antihypertensive
  trial wins over generic `cardiology`, while pure heart-failure / ACS trials
  (sacubitril-valsartan in HFrEF, ticagrelor after ACS) correctly stay `cardiology`.
- **effect estimates** — the shared `malaria_effects` augmenter recovers
  `value (95% CI lo–hi)` for HR/OR/RR/MD (BP differences, MACE/stroke/MI HRs).
- **arm-level 2×2 / continuous** — `hypertension_arm_data` wraps the shared
  `malaria_arm_data` engine (same proportion patterns, 2×2 pairing, Wan IQR→SD,
  poolable gate) configured with HTN endpoints and drug-class arm labels. Binary
  outcomes (BP control, stroke, MI, CV death, adherence) → 2×2 events/N per arm;
  continuous (SBP/DBP/MAP/ambulatory reduction) → mean+SD / median+IQR, pooled as
  MD/SMD on the natural scale (no log-normal endpoints — BP is normal-scale).

One hypertension-specific arm-label fix was needed: the generic `control` arm
label must NOT fire on the *endpoint* phrase "blood pressure **control**" — a
negative-lookbehind `(?<!pressure[- ])control` guards this (regression test
`test_bp_control_arm_not_stolen_by_endpoint_phrase`).

## Tested on real data (2026-06-08)

Corpus from PubMed: **597 hypertension RCTs / 322 OA PMCIDs / 99 NCT / 588
abstracts** (`--retmax 600` sample; hypertension is a very large field, so this is
a sample, not the population count).

| Check | Result | Notes |
|---|---|---|
| **Published antihypertensive meta-analyses** (silver gold) | **95.3%** (327/343) | point+CI agreement across **132** hypertension MAs (`validate_hypertension_ma.py --retmax 250`) |
| All-CI numbers (effects + prevalences) | 72.1% (356/494) | the ~28% gap is abstract-only CIs the abstract never restates, not mis-reads |
| **Effect internal-consistency** | **95.9%** | of 589 corpus effects (Altman-Bland / midpoint checks); effect coverage 26.2% of 588 abstracts |
| Arm-level proportion consistency | 100% | reported % == 100·events/total (abstract 2×2 yield is low and expected; full-text via `--pdfs`) — 14 continuous BP rows |
| **Specialty routing** | hypertension **289 / 588** (49%) | next: cardiology 224 (the genuine HTN↔CVD overlap — HF/ACS/AF trials), diabetes 34, oncology 22 |
| **Subspecialty routing** | bp_reduction 125 / bp_lowering 95 / general 30 / cv_events 25 / adherence 14 | of the 289 docs routed to hypertension |
| No-regression (cardiology/HIV/malaria/typhoid) | green | pure HFrEF / ACS trials correctly stay cardiology |

The MA-validation harness (`validate_hypertension_ma.py`) treats every
`value (95% CI lo–hi)` in published antihypertensive meta-analyses as a reviewer
datum and measures point+CI recovery — identical machinery to HIV / malaria /
typhoid (which scored 97.1% / 98.4% / 100% on their own MA samples). Hypertension
also registers heavily on ClinicalTrials.gov with posted results, so
`build_aact_hypertension_gold.py` yields a genuinely rich external numeric gold
(unlike typhoid/malaria, which register on ISRCTN/CTRI/PACTR with no posted
results). Corpus-wide arm-level 2×2 / continuous yield + internal-consistency is
produced by `validate_hypertension.py` (full-extractor pass).

### Honest findings
- The HTN↔CVD overlap is real and expected: 224/588 abstracts route to
  `cardiology` because cardiology legitimately also matches "hypertension" +
  "cardiovascular". Routing keeps BP-/antihypertensive-framed trials in
  `hypertension` (including BP-lowering CVD-outcome trials like SPRINT) while pure
  heart-failure / ACS trials stay cardiology — verified by regression tests.
- Hypertension abstracts are **bp_reduction-heavy** (SBP/DBP/ambulatory change in
  mmHg) and report pre-computed effects more than raw n/N, so the effect-estimate
  path is primary; 2×2 tables come mainly from full-text.

Run order:

```
python scripts/hypertension/build_hypertension_corpus.py   --retmax 4000 --email you@org
python scripts/hypertension/validate_hypertension_ma.py    --retmax 200  --email you@org
python scripts/hypertension/validate_hypertension.py       --limit 4000
python scripts/hypertension/analyze_hypertension_ma_misses.py --retmax 200 --email you@org
python scripts/hypertension/build_aact_hypertension_gold.py --aact <AACT snapshot>
python scripts/hypertension/download_hypertension_pdfs.py  --workers 3 --resume
python scripts/hypertension/cross_check.py
```

Corpus / PDF / report artifacts are gitignored (large/transient); the code under
`scripts/hypertension/` and this README are tracked.

## Test status

`tests/test_hypertension.py` — 23 tests (subspecialty detection, endpoint
normalization, registry wiring, no-regression vs cardiology/HIV/malaria/typhoid,
arm-level 2×2 BP-control + stroke, continuous SBP/DBP). Green within the full
suite (977 passed / 128 skipped at time of writing — no regressions).
