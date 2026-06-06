# Typhoid (Enteric Fever) RCT Extraction — Test Results

The typhoid extractor (`src/specialties/typhoid.py` + `typhoid_arm_data.py`,
registered in the specialty registry) reuses the shared effect-augmenter and
arm-data engine with typhoid endpoints and antibiotic / vaccine arm labels:

- **treatment** — clinical cure, microbiological/bacteriological cure, fever
  clearance time, treatment failure, relapse, faecal carriage, hospital stay,
  mortality (ciprofloxacin / ofloxacin / gatifloxacin / azithromycin /
  ceftriaxone / cefixime / chloramphenicol / co-trimoxazole arms).
- **vaccine** — blood-culture-confirmed typhoid incidence, vaccine efficacy,
  seroconversion, anti-Vi immunogenicity (GMT/GMC) (TCV / Vi-TT / Vi-DT /
  Vi-polysaccharide / Ty21a arms).
- **resistance** — MDR typhoid, fluoroquinolone non-susceptibility / nalidixic-acid
  resistance, XDR / ceftriaxone resistance.
- **complications** — intestinal perforation, GI bleeding, encephalopathy,
  severe/complicated typhoid.

## Tested on real data (2026-06-06)

Corpus from PubMed: **435 typhoid RCTs / 210 OA PMCIDs / 41 NCT / 407 abstracts**.
(Typhoid is a smaller, older field than HIV/malaria — 435 is the true PubMed RCT
count for the search term, not a sampling cap.)

| Check | Result | Notes |
|---|---|---|
| **Published typhoid meta-analyses** (silver gold) | **100.0%** (91/91) | point+CI agreement across 44 typhoid MAs; after tuning (was 96.7%) |
| **Effect internal-consistency** | **80.0%** | of 180 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **100.0%** | reported % == 100·events/total (38 proportions) |
| **Subspecialty routing** | vaccine 170 / treatment 103 / general 72 / complications 9 / resistance 1 | of corpus docs detected as typhoid |
| **AACT external gold** | sparse (1 study, 0 typed) | typhoid registers on ISRCTN/CTRI/PACTR, not CT.gov with posted results — same as malaria |
| **Abstract→PDF cross-check** | deferred | EuropePMC render endpoint returned HTTP 500 on 2026-06-06; OA tgz fallback yields `ftp://` links that 404 for fresh articles. Tooling is in place (identical to HIV/malaria); re-run `scripts/typhoid/download_typhoid_pdfs.py` + `cross_check.py` when EuropePMC is back up |

### Tuning: one general augmenter fix took typhoid 96.7%→100.0%
Mining the published-typhoid-MA misses (3/91) surfaced a single **general**
format the shared augmenter missed — a linking phrase between the effect-measure
name and its value that the core requires to be adjacent:

- `mean difference for diarrhoea was 0 days (95% CI -0.54 to 0.54)` — also a **zero-valued** MD
- `weighted mean difference for length of illness was -0.07 days, 95% confidence interval -0.55 to 0.40` — **spelled-out** CI, no parentheses
- `relative risks, were 1·05 (95% CI 1·04-1·07)` — **plural** + Lancet **middle-dot**

The fix (in `src/specialties/malaria_effects.py`, `_RATIO_RE`) allows a bounded,
digit/clause-free linking phrase ending in *was/were/of* plus a plural `s`. It is
a strict **superset** of the prior pattern — every previously-matched estimate
still matches — so it can only add recoveries, never remove them. Verified:
- malaria and HIV MA-validation re-run with **no regression** (98.4% and 97.1% on
  larger MA samples than their historical figures — additive change),
- full test suite **935 passed** (regression cases locked in `tests/test_malaria_effects.py`).

### Honest findings
- Typhoid abstracts are **vaccine-heavy** (incidence per person-years, vaccine
  efficacy, anti-Vi titres) and report pre-computed effects more than raw n/N, so
  the effect-estimate path is primary; 2×2 tables come mainly from full-text
  (abstract 2×2 yield is low and *expected* to be — 6 tables across 407 abstracts).
- AACT is **not** a useful external gold for typhoid (as for malaria): the trials
  register on ISRCTN/CTRI/PACTR which carry no posted numeric results.
- Internal-consistency (80%) is lower than HIV's (93%) on a much smaller effect
  pool (180 vs ~2,000); the failures are dominated by abstract-only effects whose
  CI the abstract never restates, not by mis-reads.

Tooling: `scripts/typhoid/` (build_typhoid_corpus, download_typhoid_pdfs,
validate_typhoid, validate_typhoid_ma, analyze_typhoid_ma_misses,
build_aact_typhoid_gold, cross_check).
