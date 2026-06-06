# Sickle Cell Disease (SCD) RCT Extraction — Test Results

The sickle cell extractor (`src/specialties/sickle_cell.py` +
`sickle_cell_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and arm-data engine with SCD endpoints and
disease-modifying / chelator arm labels. Sickle cell disease is an
**Africa-priority** hemoglobinopathy — the great majority of affected births
occur in sub-Saharan Africa — and the same African-student meta-analysis
workflow as the malaria, HIV and typhoid profiles applies.

- **disease_modifying** — vaso-occlusive crisis (VOC) rate, acute chest syndrome,
  hospitalisation, total-haemoglobin change, fetal haemoglobin (HbF), transfusion
  requirement, dactylitis, mortality (hydroxyurea/hydroxycarbamide, voxelotor,
  crizanlizumab, L-glutamine, gene/curative-therapy arms).
- **acute_pain** — crisis duration / time to resolution, length of hospital stay,
  opioid/analgesic consumption, pain intensity (VAS), readmission.
- **prevention** — overt stroke, silent cerebral infarct, transcranial Doppler
  (TCD) velocity, invasive bacterial/pneumococcal infection (chronic transfusion,
  hydroxyurea, penicillin prophylaxis arms).
- **transfusion / iron** — serum ferritin, liver iron concentration (LIC), red-cell
  alloimmunisation (deferasirox / deferiprone / deferoxamine arms).

Effect measures follow what these trials report: binary (VOC, ACS, stroke,
dactylitis, infection, alloimmunisation) → RR/OR/RD; recurrent events / rates
(VOC rate, hospitalisation, transfusion) → IRR/HR; continuous (haemoglobin and
HbF change, crisis duration, length of stay, pain score, TCD velocity, ferritin,
LIC) → MD/SMD.

## Tested on real data (2026-06-06)

Corpus from PubMed: **1,081 sickle cell RCTs / 537 OA PMCIDs / 175 NCT / 1,057
abstracts** (search term in `scripts/sickle_cell/build_sickle_cell_corpus.py`;
1,088 PMIDs returned, 1,081 with retrievable metadata).

| Check | Result | Notes |
|---|---|---|
| **Published sickle cell meta-analyses** (silver gold) | **97.8%** (347/355) | point+CI agreement on comparative effect estimates across 97 SCD MAs; all-CI numbers 88.7% (361/407) |
| **Effect internal-consistency** | **85.4%** | of 622 abstract effects (Altman-Bland / CI-midpoint checks) |
| **Arm-level proportion consistency** | **100.0%** | reported % == 100·events/total (32 proportions) |
| **Subspecialty routing** | disease_modifying 429 / general 348 / prevention 128 / acute_pain 78 / transfusion 35 | of corpus docs detected as sickle_cell |
| **AACT external gold** | **rich** — 1,157 SCD NCTs, **39 studies with 243 posted effects (209 typed)** | unlike malaria/typhoid (ISRCTN/PACTR-heavy), SCD registers well on ClinicalTrials.gov with posted numeric results |
| **Abstract→PDF cross-check** | tooling in place; not run this session | `scripts/sickle_cell/download_sickle_cell_pdfs.py` (537 OA PDFs) + `cross_check.py` are identical to the HIV/malaria/typhoid versions; run them to add the at-scale abstract↔PDF recall figure |

### Effect-type distribution (622 abstract effects)
MD 245, RR 216, OR 94, IRR 33, HR 17, SMD 11, ARD 2, RRR 2, GMR 2 — consistent
with SCD's mix of continuous haematologic/pain endpoints (MD/SMD) and
binary/rate event endpoints (RR/OR/IRR/HR).

### A general regex-class bug this profile surfaced (fixed)
The British double-vowel spelling **"haemoglobin"** (h-**ae**-moglobin) is not
matched by the one-character class `h[ae]moglobin` — that class matches exactly
one of `a`/`e`, so it catches American "hemoglobin" but silently misses
"haemoglobin". The same trap applies to `septic[ae]?mia`, `bacter[ae]?mia` and
`an[ae]mia`. All such tokens in `sickle_cell.py` and the registry keywords were
corrected to the `a?e` form (`ha?emoglobin`, `septica?emia`, `bactera?emia`,
`ana?emia`), which matches both spellings. Locked in by
`tests/test_sickle_cell.py::test_fetal_hemoglobin_continuous_poolable`.

### Honest findings
- **Disease-modifying** is the dominant subspecialty (429 docs), as expected:
  hydroxyurea, voxelotor and crizanlizumab trials report VOC rate, ACS, HbF and
  haemoglobin change as primaries.
- SCD abstracts report **pre-computed effects** more than raw per-arm n/N, so the
  effect-estimate path is primary; 2×2 yield from abstracts is low *and expected*
  to be (4 tables across 1,057 abstracts) — full-text PDFs are where the per-arm
  counts live.
- AACT is a **genuinely useful** external gold here (243 posted effects, 209
  typed), in contrast to malaria/typhoid where the trials register on
  PACTR/ISRCTN/CTRI without posted results.
- Internal-consistency (85.4%) sits between HIV (~93%) and typhoid (80%); the
  failures are dominated by abstract-only effects whose CI the abstract never
  restates, not by mis-reads.

Tooling: `scripts/sickle_cell/` (build_sickle_cell_corpus, download_sickle_cell_pdfs,
validate_sickle_cell, validate_sickle_cell_ma, analyze_sickle_cell_ma_misses,
build_aact_sickle_cell_gold, cross_check) — all thin wrappers reusing the malaria
corpus/AACT/validation helpers and the shared `extract_malaria_effects` augmenter.
