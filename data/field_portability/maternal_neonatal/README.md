# Maternal & Neonatal Health RCT Extraction — Test Results

The maternal & neonatal extractor (`src/specialties/maternal_neonatal.py` +
`maternal_neonatal_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and arm-data engine with obstetric / neonatal endpoints
and intervention arm labels. Maternal and newborn health is the single largest
contributor to the sub-Saharan disease burden among reproductive-age women and
under-fives — an Africa-priority field for the student meta-analysis workflow.

- **maternal** — maternal mortality, postpartum haemorrhage (PPH), blood loss,
  blood transfusion, maternal/puerperal sepsis, caesarean section, maternal
  anaemia, duration of labour (oxytocin / carbetocin / misoprostol / ergometrine /
  syntometrine / carboprost / tranexamic acid; active vs expectant management).
- **hypertensive** — pre-eclampsia, eclampsia, severe pre-eclampsia / HELLP,
  gestational hypertension (magnesium sulphate / labetalol / nifedipine /
  hydralazine / methyldopa; low-dose aspirin & calcium for prevention).
- **neonatal** — neonatal mortality, stillbirth, perinatal mortality, neonatal
  sepsis, birth asphyxia / hypoxic-ischaemic encephalopathy, NICU admission,
  Apgar score (neonatal resuscitation / chlorhexidine cord care / kangaroo
  mother care / early breastfeeding).
- **preterm** — preterm birth, low birth weight, neonatal respiratory distress
  syndrome, small-for-gestational-age / IUGR, gestational age at delivery, birth
  weight (antenatal corticosteroids: dexamethasone / betamethasone; tocolytics:
  nifedipine / atosiban; progesterone).

Effect measures follow what these trials report: binary outcomes (PPH, mortality,
stillbirth, pre-eclampsia, sepsis, preterm birth, LBW) → RR/OR/RD; time-to-event
→ HR; continuous (blood loss in mL, birth weight in g, gestational age in weeks,
Apgar, labour duration) → MD/SMD.

## Tested on real data (2026-06-06)

Corpus from PubMed: **5,967 maternal/neonatal RCTs / 3,417 OA PMCIDs / 954 NCT /
5,900 abstracts**. (A much larger field than typhoid/TB — maternal & newborn
health is one of the most-trialled areas in global health.)

| Check | Result | Notes |
|---|---|---|
| **Published maternal/neonatal meta-analyses** (silver gold) | **98.5%** (539/547) | point+CI agreement across 139 MAs; effect estimates (HR/OR/RR/MD) |
| **Effect internal-consistency** | **87.4%** | of 11,798 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **98.8%** | reported % == 100·events/total (327 proportions) |
| **Subspecialty routing** | preterm 2,209 / hypertensive 1,093 / maternal 1,092 / neonatal 1,033 / general 9 | of corpus docs detected as maternal_neonatal — well-balanced across all four |
| **All-CI numeric agreement** | 80.9% | 692 reviewer numbers incl. raw prevalences/proportions abstracts never restate a CI for (expected ceiling, same pattern as typhoid) |
| **AACT external gold** | available via `build_aact_maternal_neonatal_gold.py` | many LMIC maternal/neonatal trials register on ISRCTN/CTRI/PACTR rather than CT.gov, so AACT gold is sparser than cardiology/HIV |
| **Abstract→PDF cross-check** | tooling in place (`download_…_pdfs.py` + `cross_check.py`) | run on the 3,417 OA PMCIDs when full-text render endpoints are available; 2×2 tables live in full text, not abstracts |

### Honest findings
- **Effect-estimate agreement (98.5%) is the headline metric** and matches the
  other field profiles (HIV 97.1%, malaria 98.4%, typhoid 100%). It needed **no
  field-specific tuning** — the shared augmenter already covered the obstetric /
  neonatal reporting forms.
- Internal-consistency (87.4%) sits between typhoid (80%) and HIV (93%) on a much
  larger effect pool (11,798); residual failures are dominated by abstract-only
  effects whose CI the abstract never restates, not by mis-reads.
- **Abstract 2×2 yield is low and expected to be** (84 tables / 2 poolable across
  5,900 abstracts): maternal/neonatal abstracts report pre-computed effects (RR/
  OR/MD) far more than raw per-arm n/N, so the effect-estimate path is primary;
  full per-arm 2×2 tables come from full text.
- **"haemorrhage" gotcha:** the British spelling has two vowels (`ha…`) — the
  regex `h[ae]morrhage` used elsewhere matches *hemorrhage*/*hamorrhage* but NOT
  *haemorrhage*. The maternal profile uses `ha?emorrhage` so both spellings match
  (locked in `tests/test_maternal_neonatal.py::test_pph_2x2`).
- **"low birth weight" vs "birth weight":** "birth weight" is a substring of "low
  birth weight"; since the arm-data engine tags the *nearest* endpoint, a binary
  LBW count could be mislabelled as the continuous BIRTH_WEIGHT endpoint. A
  fixed-width negative lookbehind (`(?<!low\s)…birth\s?weight`) prevents this
  (regression: `test_low_birth_weight_2x2_not_mislabelled_birth_weight`).

Tooling: `scripts/maternal_neonatal/` (build_maternal_neonatal_corpus,
download_maternal_neonatal_pdfs, validate_maternal_neonatal,
validate_maternal_neonatal_ma, analyze_maternal_neonatal_ma_misses,
build_aact_maternal_neonatal_gold, cross_check).
