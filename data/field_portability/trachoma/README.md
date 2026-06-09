# Trachoma RCT Extraction — Test Results

The trachoma extractor (`src/specialties/trachoma.py` + `trachoma_arm_data.py`,
registered in the specialty registry) reuses the shared effect-augmenter and
arm-data engine with trachoma endpoints (the WHO simplified grading codes TF, TI,
TT, CO) and antibiotic / surgery / F&E arm labels. Trachoma (ocular *Chlamydia
trachomatis*) is the leading infectious cause of blindness and a top-priority
African neglected tropical disease; control follows the WHO **SAFE** strategy
(Surgery, Antibiotics, Facial cleanliness, Environmental improvement):

- **mda** (antibiotic mass drug administration) — active trachoma / TF
  (trachomatous inflammation-follicular), intense trachoma / TI, ocular-chlamydia
  infection prevalence and chlamydial load (qPCR, log-normal). Arms: azithromycin
  (single oral dose, the mainstay), tetracycline 1% eye ointment, doxycycline,
  erythromycin; annual vs biannual MDA rounds.
- **surgery** (for trichiasis) — trachomatous trichiasis / TT, post-operative
  trichiasis recurrence, corneal opacity / blindness, visual acuity (logMAR).
  Arms: bilamellar tarsal rotation (BLTR), posterior lamellar tarsal rotation
  (PLTR), epilation.
- **transmission** (F&E) — reinfection / re-emergence, facial cleanliness
  ("clean face", ocular / nasal discharge), fly density / fly-eye contact
  (*Musca sorbens*), latrine coverage.
- **mortality_safety** (of MDA) — all-cause childhood mortality (the MORDOR
  signal that azithromycin MDA reduces under-5 mortality), adverse events, and
  macrolide (azithromycin) antimicrobial resistance.

## Tested on real data (2026-06-09)

Corpus from PubMed: **232 trachoma RCTs / 141 OA PMCIDs / 63 NCT / 223
abstracts**. (232 is the true PubMed RCT count for the search term, not a
sampling cap.)

| Check | Result | Notes |
|---|---|---|
| **Published trachoma meta-analyses** (silver gold) | **93.3%** (56/60) | point+CI agreement across 17 trachoma MAs; all-CI numbers 80.8% (59/73) |
| **Effect internal-consistency** | **94.3%** | of 159 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **88.9%** | reported % == 100·events/total (9 proportions) |
| **Subspecialty routing** | mda 122 / surgery 53 / transmission 20 / general 5 / mortality_safety 5 | of 205/223 corpus docs detected as trachoma |
| **AACT external gold** | 101 NCTs, **11 studies / 78 effects (51 typed)** | richer than malaria/typhoid/schistosomiasis — some trachoma trials post structured CT.gov results |
| **Abstract→PDF cross-check** | tooling in place | identical to HIV/malaria/typhoid/schistosomiasis; run `scripts/trachoma/download_trachoma_pdfs.py` + `cross_check.py` (EuropePMC OA render is intermittent) |

### The 4 published-MA misses are out-of-scope forms, not mis-reads
The gap between effect recovery (93.3%, 56/60) and the all-CI-numbers rate
(80.8%, 59/73) is the usual sibling pattern: the adjacency-based core
deliberately does not chase effect numbers separated from their measure name by
intervening words, nor non-treatment estimates. Chasing them would match at the
cost of regressing the sibling (HIV / malaria / typhoid / schistosomiasis)
extractors, so the shared augmenter was **left unchanged**. The recurring
out-of-scope forms are:

- **subgroup** estimates with intervening words between the measure abbreviation
  and its value (`OR among children aged 1-9 was …`)
- **adjusted** estimates inside a long clause (`the adjusted OR showed that …`)
- **non-treatment** estimates (a prevalence-ratio reported as a descriptive
  cross-sectional association, not a randomised arm contrast)

Full test suite after wiring trachoma: **1382 passed, 128 skipped** — no
regression vs the pre-trachoma baseline (1356 passed).

### Honest findings
- Trachoma abstracts are **MDA-heavy** (azithromycin efficacy: active trachoma /
  TF prevalence, ocular-chlamydia infection), so the effect-estimate +
  2×2/continuous arm-level paths are primary; chlamydial load and fly counts are
  right-skewed and are flagged **log-normal** (pool on the log scale / GMR, not
  raw MD), while visual acuity (logMAR) pools as a raw mean difference.
- **AACT is a genuinely useful external gold for trachoma** (unlike
  malaria/typhoid/schistosomiasis): 101 NCTs match and 11 carry posted, typed
  numeric results (78 effects, 51 typed) — a real CT.gov footprint from the large
  azithromycin-MDA and trichiasis-surgery trials.
- The two arm-level 2×2 tables found in abstracts are not auto-poolable because
  one arm is a generic role label ("control"); this is the by-design
  `poolable_2x2` gate (both arms must be drug/procedure-named), not a miss.
- Effect-estimate coverage is 25% of abstracts because many trachoma abstracts
  report prevalences/percentages rather than a single headline ratio; those are
  captured by the arm-level proportion path, not the effect path.

Tooling: `scripts/trachoma/` (build_trachoma_corpus, download_trachoma_pdfs,
validate_trachoma, validate_trachoma_ma, analyze_trachoma_ma_misses,
build_aact_trachoma_gold, cross_check).
