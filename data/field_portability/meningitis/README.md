# Meningitis RCT Extraction — Test Results

The meningitis extractor (`src/specialties/meningitis.py` + `meningitis_arm_data.py`,
registered in the specialty registry) reuses the shared effect-augmenter and
arm-data engine with meningitis endpoints and antibiotic / adjunctive / vaccine
arm labels. Meningitis is an Africa-priority topic — the sub-Saharan "meningitis
belt" (Neisseria meningitidis, Streptococcus pneumoniae, Haemophilus influenzae
type b) drives large epidemic and endemic burden:

- **treatment** — clinical cure, treatment failure, CSF sterilisation, time to
  recovery / fever clearance (ceftriaxone / cefotaxime / chloramphenicol incl.
  single-dose oily chloramphenicol / benzylpenicillin / ampicillin / meropenem /
  vancomycin arms; adjunctive dexamethasone / glycerol).
- **vaccine** — laboratory-confirmed meningitis / invasive disease incidence,
  vaccine efficacy, seroconversion (SBA seroresponse), immunogenicity
  (SBA / rSBA / hSBA GMT, GMC), nasopharyngeal carriage (MenAfriVac / MenA-TT /
  MenACWY / MenB / 4CMenB / PCV10 / PCV13 / Hib conjugate arms).
- **mortality** — all-cause mortality, case fatality, in-hospital death.
- **sequelae** — neurological sequelae: hearing loss / deafness, seizures,
  hydrocephalus, focal neurological deficit, neurodevelopmental / cognitive
  impairment.

## Tested on real data (2026-06-08)

Corpus from PubMed: **1,764 meningitis RCTs / 677 OA PMCIDs / 299 NCT / 1,718
abstracts**.

| Check | Result | Notes |
|---|---|---|
| **Published meningitis meta-analyses** (silver gold) | **97.4%** (225/231) | point+CI agreement across 108 meningitis MAs (effect estimates: HR/OR/RR/IRR/MD) |
| **Effect internal-consistency** | **86.8%** | of 1,290 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **97.2%** | reported % == 100·events/total (144 proportions) |
| **Subspecialty routing** | vaccine 542 / treatment 325 / general 163 / mortality 152 / sequelae 50 | of corpus docs detected as meningitis |
| **AACT external gold** | available (vaccine-trial-heavy) | meningococcal/pneumococcal vaccine trials register on CT.gov with posted results; epidemic-belt treatment trials skew to ISRCTN/PACTR — run `scripts/meningitis/build_aact_meningitis_gold.py` |
| **Abstract→PDF cross-check** | tooling in place | identical to HIV/malaria/typhoid; run `scripts/meningitis/download_meningitis_pdfs.py` + `cross_check.py` (677 OA PDFs available) |

### Honest findings
- Meningitis abstracts are **vaccine-heavy** (542/1,232 routed docs): incidence per
  person-years, vaccine efficacy, and SBA/rSBA/hSBA titres dominate, so the
  pre-computed effect-estimate path is primary; 2×2 tables come mainly from
  full-text (abstract 2×2 yield is low and *expected* to be — 38 tables across
  1,718 abstracts).
- **Treatment** trials (325) are the second-largest stratum — antibiotic
  head-to-heads and adjunctive **dexamethasone / glycerol** trials reporting
  mortality and **neurological sequelae** (hearing loss in particular), which is
  why mortality (152) and sequelae (50) are first-class subspecialties here rather
  than buried as generic outcomes.
- The 6 MA-validation misses (97.4%) are **not** a systematic, fixable format gap:
  they are abbreviation collisions where "OR" means *objective response* not odds
  ratio (where **not** extracting is the correct behaviour), diagnostic odds
  ratios (a diagnostic-accuracy measure, out of scope for the comparative-effect
  engine), and off-topic papers (e.g. a cardioembolic-stroke MA caught by the
  meningitis search term). The shared augmenter was **deliberately left
  untouched** — editing it for ≤2 genuinely-recoverable cases would risk
  regressions across the 7 sibling extractors that share it.
- Internal-consistency (86.8%) on a 1,290-effect pool is dominated by abstract-only
  effects whose CI the abstract never restates, not by mis-reads (arm-level
  proportion consistency is 97.2%).

Tooling: `scripts/meningitis/` (build_meningitis_corpus, download_meningitis_pdfs,
validate_meningitis, validate_meningitis_ma, analyze_meningitis_ma_misses,
build_aact_meningitis_gold, cross_check). Same pattern as `scripts/typhoid/` and
`scripts/hiv/`.
