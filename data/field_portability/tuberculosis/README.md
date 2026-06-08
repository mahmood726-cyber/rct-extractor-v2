# Tuberculosis RCT Extraction

The tuberculosis extractor (`src/specialties/tuberculosis.py` +
`tuberculosis_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter (`malaria_effects.extract_malaria_effects`) and the
arm-data engine (`malaria_arm_data`) with TB endpoints and anti-TB arm labels —
the same one-core-engine / per-topic-profile design as the malaria and HIV
profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **treatment** (drug-susceptible active TB) | culture conversion (2-month / 8-week), time to culture conversion, smear conversion, treatment success / cure, unfavourable outcome, treatment failure, relapse / recurrence, mortality, hepatotoxicity |
| **drug_resistant** (MDR / RR / pre-XDR / XDR-TB) | favourable / unfavourable outcome, culture conversion, acquired drug resistance, serious adverse events (QT prolongation), mortality, relapse |
| **prevention** (vaccine / prevention of infection or disease) | incident / active tuberculosis, TB infection (IGRA / QFT conversion), vaccine efficacy (BCG, M72/AS01E) |
| **latent** (LTBI / TB preventive therapy) | TPT / treatment completion, incident TB, hepatotoxicity, TB infection |

**Arm labels** cover individual drugs (isoniazid, rifampicin, rifapentine,
pyrazinamide, ethambutol, moxifloxacin/levofloxacin, bedaquiline, delamanid,
pretomanid, linezolid, clofazimine, …) and the multi-drug regimen abbreviations
TB trials report (HRZE, BPaL, BPaLM, 3HP, 1HP, 6H, 9H, 4R), plus BCG / M72-AS01E
for vaccine trials.

**Effect measures** follow what these trials report: binary (culture conversion,
treatment success, relapse, completion) → RR/OR/RD; incidence / time-to-event
(incident TB, time to culture conversion, mortality) → IRR/HR; vaccine and
preventive efficacy reported as efficacy % (1 − HR/RR), handled by the shared
effects augmenter.

> **Arm-level note:** TB poolable arm-level data is overwhelmingly **binary 2×2**
> (culture conversion, treatment success, relapse, TPT completion). Time to
> culture conversion — the main continuous-looking outcome — is reported and
> pooled as a **hazard ratio** via the core effect-size engine, not as a per-arm
> mean+SD, so `tuberculosis_arm_data` exposes no continuous endpoints.

## Tested on real data (2026-06-07)

Corpus from PubMed: **2,990 tuberculosis RCTs / 1,897 OA PMCIDs / 655 NCT /
2,965 abstracts** (search term in `scripts/tuberculosis/build_tb_corpus.py`).

| Check | Result | Notes |
|---|---|---|
| **Published TB meta-analyses** (silver gold) | **97.1%** (134/138) | point+CI agreement on comparative effect estimates across 86 TB MAs; all-CI numbers 50.3% (148/294) |
| **Effect internal-consistency** | **91.4%** | of 2,179 abstract effects (Altman-Bland / CI-midpoint checks) |
| **Arm-level proportion consistency** | **100.0%** | reported % == 100·events/total (206 proportions) |
| **Subspecialty routing** | treatment 952 / general_tb 638 / prevention 227 / latent 200 / drug_resistant 162 | of corpus docs detected as tuberculosis |
| **AACT external gold** | **45 TB studies, 316 posted effects (237 typed)** | TB coverage is partial — many TB RCTs register on ISRCTN / PACTR / CTRI or post no numeric results, so abstract→PDF recall is the at-scale signal |
| **Abstract→PDF cross-check** | tooling in place; not run this session | `scripts/tuberculosis/download_tb_pdfs.py` (1,897 OA PDFs) + `cross_check.py` are identical to the HIV/malaria/typhoid versions; run them to add the at-scale abstract↔PDF recall figure |

Specialty profile, registry wiring, and arm-level extraction are unit-tested in
`tests/test_tuberculosis.py` (23 tests; subspecialty routing, endpoint
normalization, registry wiring, culture-conversion / treatment-success / relapse
/ TPT-completion 2×2). Full suite green (954 passed, 128 skipped), no regressions
to the malaria / HIV / cardiology profiles.

### Effect-type distribution (2,179 abstract effects)
RR 680, OR 529, MD 523, HR 263, ARD 83, IRR 76, GMR 9, SMD 7, RRR 5,
EFFICACY_PCT 3, NNT 1 — the RR/OR/HR/IRR-heavy mix expected for TB's binary
(culture conversion, treatment success, relapse) and rate / time-to-event
(incident TB, mortality) endpoints; the MD count is largely co-reported
continuous secondaries (e.g. time-to-culture-conversion in days, lab changes),
not poolable arm-level TB primaries.

### Shared-augmenter improvements this profile surfaced (fixed)
- **Prose-connector effects.** TB MA abstracts frequently report the pooled
  estimate as `OR of 1.65 (95% CI 0.96 to 2.84)` or `the OR was 3.35 (95% CI
  2.23–5.03)`. The bare-ratio regex in `malaria_effects.py` only accepted
  `=`/`:`/`,`/whitespace separators, so these were missed. Adding the spelled-out
  connectors `of`/`was` recovered them, lifting MA misses from 13 → 4 (97.1%).
- **EFFICACY_PCT precedence.** A `(protective|vaccine) efficacy of NN% (95% CI …)`
  clause was sometimes mis-typed by the core as a mean difference, putting it on
  the wrong pooling scale. `extract_malaria_effects` now drops any non-efficacy
  core copy overlapping an `EFFICACY_PCT` span, so the authoritative efficacy %
  (with its `log(1−VE)` pooling field) wins — relevant for BCG / M72-AS01E and
  TPT-prevention trials.
- **`unfavourable` ≠ `favourable`.** The MDR/drug-resistant endpoint map matched
  `favou?rable (outcome|status)` as `TREATMENT_SUCCESS`, which also fired inside
  `unfavourable` and mis-paired the 2×2. A negative look-behind `(?<!un)` now keeps
  the favourable / unfavourable WHO outcomes as distinct, correctly-paired arms.

### Honest findings
- **Treatment** (drug-susceptible active TB) is the dominant subspecialty (952
  docs): HRZE / 4-month rifapentine-moxifloxacin and similar regimen trials
  reporting culture conversion, treatment success and relapse.
- TB poolable arm-level data is **binary 2×2 only** — 206 proportions (100%
  consistent) and 53 2×2 tables across the corpus, **0 continuous rows**, exactly
  as the arm-level note predicts (time-to-culture-conversion is pooled as an HR by
  the core engine, not as per-arm mean+SD).
- AACT is a **partial** external gold for TB (45 studies / 316 posted effects),
  unlike sickle cell where ClinicalTrials.gov posting is rich — many TB trials
  register on ISRCTN / PACTR / CTRI without posted numeric results.
- The 4 residual MA misses are genuinely hard formats (a label detached from its
  value — "studies reporting hazard ratios, the pooled estimate was 2.39"; an
  "increased to 4.59" connector; bracketed `95% CI [lo, hi]` / `95% confidence
  interval [CI]` forms) and were left rather than over-fit the shared augmenter.

## Validation workflow (`scripts/tuberculosis/`)

```bash
# 1. Build the PubMed RCT corpus index
python scripts/tuberculosis/build_tb_corpus.py --retmax 3000 --email you@org

# 2. Download OA full-text PDFs (resumable)
python scripts/tuberculosis/download_tb_pdfs.py --workers 3 --resume

# 3. Build the AACT posted-results gold (needs a local AACT snapshot)
python scripts/tuberculosis/build_aact_tb_gold.py --aact /path/to/AACT/snapshot

# 4. Validate
python scripts/tuberculosis/validate_tb.py --limit 3000        # yield + consistency (abstracts)
python scripts/tuberculosis/validate_tb.py --pdfs              # over full-text PDFs
python scripts/tuberculosis/validate_tb_ma.py --email you@org  # vs published TB meta-analyses
python scripts/tuberculosis/cross_check.py                     # abstract↔PDF↔AACT reconciliation

# 5. Mine misses to find fixable format gaps
python scripts/tuberculosis/analyze_tb_ma_misses.py --email you@org
```

Validation order (same as malaria / HIV): published TB meta-analyses (primary
silver standard) > AACT posted results > abstract↔PDF recall. AACT TB coverage is
expected to be partial — many TB RCTs register on ISRCTN / PACTR or post no numeric
results — so abstract→PDF recall is the at-scale extraction-reliability signal.
