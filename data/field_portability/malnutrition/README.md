# Malnutrition (Severe/Moderate Acute Malnutrition, Undernutrition) RCT Extraction — Test Results

The malnutrition extractor (`src/specialties/malnutrition.py` +
`malnutrition_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and arm-data engine with malnutrition endpoints and
therapeutic-feeding / micronutrient arm labels. Malnutrition is an
**Africa-priority** child-health topic.

- **therapeutic_feeding** — nutritional recovery / cure, weight-gain rate
  (g/kg/day), defaulting, relapse / readmission, length of stay (RUTF / RUSF /
  F-75 / F-100 therapeutic milk / corn-soy blend / CMAM programme arms).
- **micronutrient** — stunting, wasting, anaemia, serum micronutrient status
  (zinc / retinol / ferritin), morbidity (diarrhoea / respiratory infection)
  (zinc / vitamin A / iron / multiple micronutrient powder / LNS / SQ-LNS arms).
- **mortality** — all-cause mortality, case fatality, in-hospital / inpatient
  mortality (severe acute malnutrition, e.g. routine-antibiotic trials).
- **recovery_growth** — weight-for-height z-score (WHZ/WLZ), MUAC change, weight
  gain, height / length gain, oedema resolution, time to recovery.

## Tested on real data (2026-06-08)

Corpus from PubMed: **2,988 malnutrition RCTs / 1,998 OA PMCIDs / 638 NCT / 2,977
abstracts** (search term in `scripts/malnutrition/build_malnutrition_corpus.py`).

| Check | Result | Notes |
|---|---|---|
| **Published malnutrition meta-analyses** (silver gold) | **98.2%** (371/378) | point+CI agreement across 108 nutrition MAs (effect estimates HR/OR/RR/IRR/MD); `ma_validation.json` |
| **All-CI numeric recovery** | **81.2%** (377/464) | includes bare prevalences/proportions the reviewers restate without a labelled effect measure |
| **Effect internal-consistency** | **92.9%** | of 2,301 abstract effects (Altman-Bland / midpoint checks) over the 2,977 abstracts |
| **Arm-level proportion consistency** | **97.1%** | reported % == 100·events/total (70 proportions; 17 2×2 tables across 14 trials; 205 continuous rows) |
| **Subspecialty routing** | micronutrient 708 / mortality 279 / recovery_growth 249 / therapeutic_feeding 171 / general 525 | of corpus docs detected as malnutrition; effect-type mix MD 980 / RR 486 / OR 484 / HR 213 / SMD 78 / IRR 28 |
| **AACT external gold** | sparse (nutrition trials register on ISRCTN/PACTR/CTRI) | `build_aact_malnutrition_gold.py` provided; many SAM trials carry no posted numeric results on CT.gov |
| **Abstract→PDF cross-check** | tooling in place | run `download_malnutrition_pdfs.py` + `cross_check.py` (1,998 OA PMCIDs available) |

### British / American spelling guard (lessons.md)
Anaemia / haemoglobin and oedema / diarrhoea use `ha?emoglobin`, `ana?emia`,
`o?edema`, `diarrh(?:oea|ea)` so both the British double-vowel and American
single-vowel forms match — the `[ae]`-class trap (haEmoglobin ⊃ hEmoglobin) is
avoided. Locked by `tests/test_malnutrition.py::test_anaemia_british_and_american_spelling`.

### Honest findings
- Malnutrition is a **large, modern field** (2,988 RCTs vs typhoid's 435), with a
  high OA-PDF rate (67%) and many CT.gov registrations (638 NCT) — richer than the
  typhoid/malaria bundles.
- Abstracts mix **pre-computed effects** (RR/MD with CI, the primary recovery
  path) with **raw n/N recovery proportions** (2×2 mainly from full text).
- AACT remains a **weak external gold** for nutrition (as for malaria/typhoid):
  trials register on ISRCTN/PACTR/CTRI which carry no posted numeric results.

Tooling: `scripts/malnutrition/` (build_malnutrition_corpus, download_malnutrition_pdfs,
validate_malnutrition, validate_malnutrition_ma, analyze_malnutrition_ma_misses,
build_aact_malnutrition_gold, cross_check).
