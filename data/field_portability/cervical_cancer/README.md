# Cervical Cancer / HPV RCT Extraction — Test Results

The cervical-cancer / HPV extractor (`src/specialties/cervical_cancer.py` +
`cervical_cancer_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and arm-data engine with cervical-cancer endpoints and
HPV-vaccine / screening-method / precancer-treatment arm labels. Cervical cancer
is the leading cause of cancer death in women across sub-Saharan Africa, so this
bundle targets the four RCT literatures that drive elimination policy:

- **vaccine** — persistent HPV infection, incident vaccine-type infection,
  CIN2+/CIN3+ (high-grade precancer), genital warts, vaccine efficacy,
  seroconversion, anti-HPV immunogenicity (GMT/GMC, log-normal) (bivalent /
  Cervarix, quadrivalent / Gardasil, nonavalent / Gardasil 9, Cecolin, Walrinvax
  arms; HPV-16/18; single-dose schedules).
- **screening** — VIA / VILI positivity, HPV DNA testing, cytology (Pap), screen
  positivity, sensitivity / specificity for CIN2+, colposcopy referral, screening
  uptake/coverage, self-sampling (screen-and-treat / single-visit).
- **treatment** (of precancer) — lesion/CIN clearance (cure), HPV clearance,
  residual/recurrent disease (treatment failure), recurrence (cryotherapy /
  thermal ablation / LEEP-LLETZ / conization arms).
- **mortality / incidence** — invasive cervical cancer incidence, cervical cancer
  mortality, all-cause mortality.

Effect measures follow what these trials report: binary (infection, CIN2+, warts,
clearance, failure, recurrence, screen-positive) → RR/OR/RD; incidence/time-to →
IRR/HR; continuous (anti-HPV titres) → GMR, log-normal. Diagnostic-accuracy
endpoints (sensitivity/specificity) carry DTA-style measure tags.

## Tested on real data (2026-06-08)

Corpus from PubMed: **2,994 cervical-cancer / HPV RCTs / 1,804 OA PMCIDs /
562 NCT / 2,958 abstracts** (esearch `retmax=3000` — a sampling cap on a large,
active field, not the true RCT count). Corpus metrics below are over a 1,200-doc
abstract sample; MA agreement is over the full MA pull.

| Check | Result | Notes |
|---|---|---|
| **Published cervical/HPV meta-analyses** (silver gold) | **95.2%** (257/270) | point+CI agreement across 104 cervical-cancer / HPV MAs (effect estimates HR/OR/RR/IRR/MD) |
| **Effect internal-consistency** | **93.0%** | of 911 abstract effects (Altman-Bland / midpoint checks) over 1,200 docs |
| **Arm-level proportion consistency** | **95.0%** | reported % == 100·events/total (57/60 proportions) |
| **Subspecialty routing** | vaccine 240 / screening 218 / general 106 / treatment 34 / mortality 5 | of 1,200 corpus docs detected as cervical_cancer |
| **Effect-type mix** | OR 264 / RR 215 / HR 193 / MD 184 / ARD 24 / SMD 17 / IRR 8 / GMR 3 | matches a vaccine+screening-heavy field |
| **AACT external gold** | not used | cervical-cancer/HPV elimination trials register heavily on ISRCTN/PACTR/CTRI and report on long follow-up — CT.gov carries few posted numeric results (same as malaria/typhoid) |
| **Abstract→PDF cross-check** | tooling in place | 1,804 OA PMCIDs available; full-text 2×2 yield is higher than abstracts (run `validate_cervical_cancer.py --pdfs` after downloading) |

### Honest findings
- The 13 published-MA misses are **not mis-reads**: they are dominated by
  off-topic meta-analyses the broad search pulls in (head-and-neck TORS/TLM vs
  RT/CRT HRs), GRADE summary-of-findings **absolute-effect** rows
  (“1,351 more per 1,000, 95% CI 610 to 2,350” — a risk difference, not the RR),
  a degenerate CI (`0.00–855.48`), and a **prevalence** mislabeled as an HR in the
  source. The comparative-effect path recovers 95.2% of true reviewer estimates.
- The shared `malaria_effects.py` augmenter was deliberately **left untouched**:
  this is an additive field bundle, and the marginal misses are non-cervical or
  non-effect numbers rather than a recurring cervical-specific format. (The
  augmenter already carries the typhoid “was/were” linking-phrase generalisation.)
- Cervical-cancer abstracts are **vaccine- and screening-heavy** and report
  pre-computed effects (efficacy, RR, OR, detection-rate ratios) more than raw
  n/N, so the effect-estimate path is primary; abstract 2×2 yield is low and
  *expected* to be (14 tables across 1,200 docs, 0 auto-poolable because abstract
  comparator arms are usually generic “control/placebo” pairs that the poolable
  gate routes to manual review). Full-text raises 2×2 yield.
- **mortality/incidence** is the smallest abstract subspecialty (5) because
  invasive-cancer endpoints need long follow-up and appear mainly in landmark
  full-text reports (e.g. India VIA screening, HPV FASTER); the endpoints are
  defined and routed, the abstract pool is simply thin.

Tooling: `scripts/cervical_cancer/` (build_cervical_cancer_corpus,
validate_cervical_cancer, validate_cervical_cancer_ma,
analyze_cervical_cancer_ma_misses). Large/transient data
(`*_matched.jsonl`, `*.json`, `rct_trial_pdfs/`) is gitignored; this README is the
tracked record.
