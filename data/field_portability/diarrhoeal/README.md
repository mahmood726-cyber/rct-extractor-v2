# Diarrhoeal Disease RCT Extraction — Test Results

The diarrhoeal-disease extractor (`src/specialties/diarrhoeal.py` +
`diarrhoeal_arm_data.py`, registered in the specialty registry) reuses the shared
effect-augmenter and arm-data engine with diarrhoeal endpoints and ORS / zinc /
rotavirus-vaccine / antibiotic arm labels. Diarrhoeal disease is the
second-leading infectious cause of under-5 mortality and an Africa-priority topic
for the student meta-analysis workflow.

- **rehydration** — rehydration / treatment failure (need for IV), stool output /
  volume, ORS intake, vomiting (reduced-osmolarity / hypo-osmolar / rice-based /
  standard ORS, zinc, racecadotril, probiotics, smectite arms).
- **rotavirus** — rotavirus gastroenteritis incidence, severe rotavirus
  gastroenteritis, vaccine efficacy, anti-rotavirus IgA seroconversion /
  immunogenicity (GMC/GMT) (Rotarix/RV1, RotaTeq/RV5, Rotavac, Rotasiil arms).
- **treatment** — clinical cure, bacteriological / microbiological cure, treatment
  failure, time to resolution (azithromycin / ciprofloxacin / ceftriaxone /
  cefixime / nalidixic acid / co-trimoxazole / metronidazole / erythromycin arms
  for dysentery and invasive diarrhoea).
- **mortality_duration** — duration of diarrhoea, stool frequency, mortality /
  case fatality, hospitalisation, dehydration, persistent diarrhoea (the
  childhood-mortality core).

British / American spelling is handled throughout with `diarrho?ea` (and
`diarrho?eal?`), so both "diarrhoea" (UK) and "diarrhea" (US) match — per the
double-vowel rule in the lessons file (the British form inserts an extra 'o'
before "ea").

## Tested on real data (2026-06-08)

Corpus from PubMed: **5,985 diarrhoeal RCTs / 3,522 OA PMCIDs / 1,485 NCT /
5,959 abstracts**. Diarrhoeal disease is a large, active field (ORS/zinc,
rotavirus vaccines, dysentery antibiotics), so the corpus is an order of
magnitude larger than typhoid's (435).

| Check | Result | Notes |
|---|---|---|
| **Published diarrhoeal meta-analyses** (silver gold) | **96.5%** (446/462) | point+CI agreement across 142 diarrhoeal MAs (retmax 300); above cholera's 94.4%, near malaria (98.4%) / HIV (97.1%). No tuning applied. |
| **All CI-bearing numbers** (context only) | 77.2% (596) | expected lower — includes prevalences / proportions / I² the extractor deliberately ignores. |
| **AACT external gold** | **rich** (255 studies, 4,458 effects, 3,101 typed) | unlike typhoid/malaria: rotavirus-vaccine and zinc trials DO register on ClinicalTrials.gov with posted numeric results. `aact_diarrhoeal_gold.json`. |
| **Effect internal-consistency** | **96.7%** | of 910 abstract effects (Altman-Bland / midpoint checks) on a 700-abstract representative corpus sample. Higher than typhoid's 80% and HIV's 93%. |
| **Arm-level proportion consistency** | **100.0%** | reported % == 100·events/total (13 proportions in the sample). |
| **Subspecialty routing** (of docs detected as diarrhoeal) | rehydration 82 / mortality_duration 48 / rotavirus 18 / treatment 15 / general 158 | 700-abstract sample; `general` = detected as diarrhoeal but no subspecialty keyword fired. Run `validate_diarrhoeal.py` (no `--limit`) for the full 5,959-abstract pass and `--pdfs` for the 3,522 OA full-texts. |
| **Abstract→PDF cross-check** | tooling in place | `scripts/diarrhoeal/download_diarrhoeal_pdfs.py` + `cross_check.py`, identical to HIV/malaria/typhoid; run when full-text recall at scale is needed. |

### Why no augmenter tuning (96.5% is the honest figure)
Mining the 16 published-MA misses (`ma_misses.jsonl`) showed they are **not** a
single fixable diarrhoeal format gap (the way typhoid's 3 misses were). They split
into:

- **Off-topic outcomes** in broad diarrhoeal-term MAs — respiratory disease,
  depressive symptoms (SMD), overall survival (HR), stroke (RR) — that happen to
  sit in reviews retrieved by the diarrhoeal MA query.
- **Genuine MA-side reporting errors** — e.g. PMID 41349216 prints a *negative*
  "risk ratio, -1.28 (95% CI -2.05 to -0.51)" for a 72% risk reduction; a negative
  risk ratio is impossible, and the extractor **correctly rejects** it as
  implausible (ratio bounds + point-in-CI checks). Counting these as extractor
  misses would be wrong.

Because there is no clean *superset* format win, the shared augmenter
(`src/specialties/malaria_effects.py`) was left untouched — preserving the
no-regression guarantee for malaria / HIV / typhoid (full suite **979 passed**,
0 failures; +25 new diarrhoeal regression tests in `tests/test_diarrhoeal.py`).

### Honest findings
- Diarrhoeal abstracts are a **healthy mix** of comparative effects (rotavirus VE,
  zinc/ORS RR/MD) and raw n/N, so both the effect-estimate path and the 2×2 /
  continuous arm-level path apply.
- **AACT is a genuinely useful external gold here** (255 studies / 3,101 typed
  effects) — the first sibling for which CT.gov posts substantial numeric results,
  driven by industry rotavirus-vaccine trials and large zinc/ORS trials.
- The "severe rotavirus gastroenteritis" endpoint (the primary efficacy endpoint
  of rotavirus-vaccine RCTs) is tagged distinctly from generic rotavirus
  gastroenteritis via a negative-lookbehind guard, so vaccine-efficacy 2×2 tables
  resolve to `SEVERE_RV_GE`, not the generic incidence endpoint.

Tooling: `scripts/diarrhoeal/` (build_diarrhoeal_corpus, download_diarrhoeal_pdfs,
validate_diarrhoeal, validate_diarrhoeal_ma, analyze_diarrhoeal_ma_misses,
build_aact_diarrhoeal_gold, cross_check).
