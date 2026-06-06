# Cholera (Vibrio cholerae) RCT Extraction — Test Results

The cholera extractor (`src/specialties/cholera.py` + `cholera_arm_data.py`,
registered in the specialty registry) reuses the shared effect-augmenter and
arm-data engine with cholera endpoints and antibiotic / vaccine / ORS arm labels.
Cholera is an **Africa-priority** topic — recurrent epidemic cholera across
sub-Saharan Africa — with a large RCT literature spanning three clinical axes:

- **treatment** — clinical cure, bacteriological / stool-culture clearance,
  duration of diarrhoea, treatment failure, hospital stay (doxycycline incl.
  single-dose / azithromycin / ciprofloxacin / erythromycin / tetracycline /
  norfloxacin / furazolidone / co-trimoxazole arms).
- **rehydration** — total stool output, ORS / fluid intake, need for unscheduled
  IV fluid, vomiting (rice-based ORS / reduced-osmolarity (hypo-osmolar) ORS /
  standard / glucose ORS / Ringer's lactate arms).
- **vaccine** — culture-confirmed cholera incidence, vaccine efficacy /
  effectiveness, vibriocidal seroconversion, vibriocidal antibody immunogenicity
  (GMT) (Dukoral / WC-rBS / Shanchol / Euvichol(-Plus) / Hillchol / CVD 103-HgR /
  Vaxchora arms).
- **severe** — severe dehydration, mortality / case fatality, hypovolaemic shock,
  acute kidney injury.

## Tested on real data (2026-06-06)

Corpus from PubMed: **418 cholera RCTs / 187 OA PMCIDs / 55 NCT / 403 abstracts**.

| Check | Result | Notes |
|---|---|---|
| **Published cholera meta-analyses** (silver gold) | **94.4%** (67/71) | point+CI agreement across 34 cholera MAs (antibiotic, OCV, ORS/zinc) |
| **Effect internal-consistency** | **89.0%** | of 191 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **100.0%** | reported % == 100·events/total (22 proportions) |
| **Subspecialty routing** | vaccine 172 / general 72 / rehydration 67 / treatment 52 / severe 10 | of corpus docs detected as cholera |
| **AACT external gold** | 6 studies / 26 effects (11 typed) | from 83 cholera NCTs — richer than typhoid (mostly OCV immunogenicity RD/seroconversion) |
| **Abstract→PDF cross-check** | tooling in place; deferred | `scripts/cholera/download_cholera_pdfs.py` + `cross_check.py` ready (identical to HIV/malaria/typhoid). EuropePMC/PMC OA render was intermittent on 2026-06-06; re-run when stable |

Effect-type distribution across the 191 abstract effects: OR 69, MD 67, RR 46,
RRR 3, HR 2, GMR 2, EFFICACY_PCT 2 — i.e. a mix of vaccine-efficacy ratios,
ORS continuous outcomes (stool output / duration), and antibiotic 2×2s.

### Honest findings
- Cholera abstracts are **vaccine-heavy** (OCV efficacy/effectiveness against
  culture-confirmed cholera, vibriocidal seroconversion/GMT) and ORS-heavy
  (continuous stool-output and diarrhoea-duration outcomes), so the
  effect-estimate path and the continuous arm-data path are primary; raw 2×2
  tables come mainly from full-text (abstract 2×2 yield is low and *expected* to
  be — 4 tables across 403 abstracts).
- **AACT is more useful for cholera than for typhoid/malaria**: 83 cholera NCTs
  on ClinicalTrials.gov, of which 6 carry posted numeric `outcome_analyses`
  (26 effects, 11 typed) — dominated by OCV immunogenicity (seroconversion rate,
  risk differences). It is still sparse relative to HIV because many African
  cholera trials register on ISRCTN / PACTR / CTRI.
- Internal-consistency (89%) is on a smaller effect pool (191) than HIV's
  (~2,000); the failures are dominated by abstract-only effects whose CI the
  abstract never restates, not by mis-reads (arm-level proportion consistency is
  100%).

### Known MA-validation misses (4/71) — shared-augmenter format gaps, not cholera bugs
Mining the published-cholera-MA misses (`analyze_cholera_ma_misses.py`) shows all
4 are generic effect-string formats the **shared** augmenter
(`src/specialties/malaria_effects.py`) does not yet parse — none are cholera
endpoint/arm problems:

- `the RR was 0.02 (95% CI 0.00 to 0.30)` (×3, one MA) — a **bare abbreviation +
  "was" linking** form. `_RATIO_RE` handles `risk ratio was …` and `aRR was …`,
  and `_BARE_RATIO_RE` handles `RR, 0.02 (95% CI …)`, but bare `RR was <val>` falls
  between the two.
- `standardised mean difference in the log scale -0.214 (95% confidence interval
  -0.305 to -0.123)` — an SMD with an **"in the log scale" clause** interposed
  between the label and the value, plus a spelled-out CI.

These belong in the shared augmenter and should be fixed as a strict **superset**
(every previously-matched estimate still matches) and re-validated across malaria
/ HIV / typhoid / cholera MA sets with the full suite green — the same discipline
used for the typhoid `was/were/of` fix. They were left out of this cholera-only
bundle to avoid touching shared code while sibling disease bundles are in flight.

Tooling: `scripts/cholera/` (build_cholera_corpus, download_cholera_pdfs,
validate_cholera, validate_cholera_ma, analyze_cholera_ma_misses,
build_aact_cholera_gold, cross_check).
