# Hepatitis (HBV/HCV) RCT Extraction — Test Results

The hepatitis extractor (`src/specialties/hepatitis.py` + `hepatitis_arm_data.py`,
registered in the specialty registry) reuses the shared effect-augmenter and
arm-data engine with hepatitis endpoints (27 across four subspecialties) and
antiviral / vaccine arm labels:

- **treatment** — SVR (sustained virologic response) / RVR / EVR / ETR,
  virologic relapse, on-treatment failure, virologic breakthrough, drug
  resistance, HBV DNA suppression, HBeAg seroconversion, HBsAg loss, ALT
  normalization, HBV DNA / HCV RNA / ALT levels, liver stiffness, treatment
  discontinuation (HCV direct-acting antivirals — sofosbuvir / ledipasvir /
  velpatasvir / glecaprevir-pibrentasvir / elbasvir-grazoprevir / … as
  fixed-dose combos; HBV nucleos(t)ides — entecavir / tenofovir (TDF/TAF) /
  besifovir / telbivudine / lamivudine; peg-interferon ± ribavirin).
- **prevention** — seroprotection (anti-HBs ≥10 mIU/mL), HBV infection /
  incidence, anti-HBs titre (GMT) (hepatitis-B vaccine — Engerix / Recombivax —
  vs placebo).
- **pmtct** — perinatal (mother-to-child) transmission, infant HBsAg (maternal
  tenofovir / HBIG / infant vaccine arms).
- **outcomes** — hepatocellular carcinoma (HCC), cirrhosis / hepatic
  decompensation, liver-related and all-cause mortality, liver transplant.

## Tested on real data (2026-06-08)

Corpus from PubMed: **699 hepatitis RCTs / 436 OA PMCIDs / 213 NCT-linked /
689 abstracts**.

| Check | Result | Notes |
|---|---|---|
| **Published hepatitis meta-analyses** (silver gold) | **96.1%** (220/229) | point+CI agreement across 109 hepatitis MAs; after tuning (was 92.1%) |
| **Effect internal-consistency** | **91.0%** | of 523 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **100.0%** | reported % == 100·events/total (65 proportions) |
| **Subspecialty routing** | treatment 261 / general 116 / outcomes 107 / prevention 46 / pmtct 1 | of corpus docs detected as hepatitis |
| **Effect-type mix** (523) | OR 135 / RR 126 / MD 121 / HR 101 / ARD 25 / IRR 9 / SMD 5 / GMR 1 | hepatitis MAs report pre-computed ratios far more than raw n/N |
| **AACT external gold** | not built (offline) | tooling in place (`build_aact_hepatitis_gold.py`); requires a local AACT snapshot, which was not available this session |
| **Abstract→PDF cross-check** | deferred | no OA full-text PDFs downloaded this session; tooling is in place (identical to HIV/malaria) — re-run `scripts/hepatitis/download_hepatitis_pdfs.py` + `cross_check.py` when full text is fetched |

### Tuning: one general augmenter fix took hepatitis 92.1%→96.1%
Mining the published-hepatitis-MA misses (18/229) surfaced a single **general**
format the shared augmenter missed — a linking phrase between a *bare* effect
abbreviation and its value that the core requires to be adjacent:

- `pooled OR of 1.015 (95% CI 0.860-1.199)` — an **"of"** linker after a bare `OR`
- `the pooled HR for OS of 1.04 (95%CI: 0.93-1.16)` — a **"for &lt;subgroup&gt; of"**
  linker after a bare `HR`

The fix (in `src/specialties/malaria_effects.py`, `_BARE_RATIO_RE`) lets the
separator between the abbreviation and the value be either the existing
`[\s:=,]+` **or** a lower-case `of` / `for <subgroup> of` linker. It is a strict
**superset** of the prior pattern — the original `[\s:=,]+` alternative is kept
first, so every previously-matched estimate still matches — so it can only add
recoveries, never remove them. (Same linking-phrase class as the earlier typhoid
`was/were/of` fix in `_RATIO_RE`.) The linker stays lower-case so the conjunction
"or" / a sentence-initial "For" can never supply it. Verified:
- **malaria MA-validation re-run with no regression** (99.1%, 116/117 — additive),
- full test suite **954 passed** (new formats locked in `tests/test_malaria_effects.py`,
  with a negated case asserting the "of" linker never fires without a ratio
  abbreviation in front).

### Honest findings
- Hepatitis abstracts report **pre-computed effects** (OR/RR/HR/MD) far more than
  raw n/N (523 typed effects vs only 20 candidate 2×2 cells across 689
  abstracts), so the effect-estimate path is primary; poolable 2×2 tables come
  almost entirely from full-text — abstract 2×2 yield is low and *expected* to be
  (0 poolable pairs recovered from abstracts alone, all arm pairs need the
  full-text results table).
- The 9 effects still missed after tuning are dominated by (a) **observational /
  prognostic associations** that are not RCT treatment effects — HBV+alcohol
  `OR 14.56`, HBV-and-multiple-myeloma `RR 1.25`, pre-albumin prognostic
  `HR 0.64` — legitimately outside the RCT-effect domain, and (b) one implausibly
  large ratio (`RR 65.62`, undetectable-HBV-DNA) the value-plausibility guard
  (`0.01 ≤ |val| ≤ 50`) deliberately rejects to keep bare-abbrev matching safe.
- The combination-regimen arm labeller keeps **fixed-dose DAA combos whole**
  (`glecaprevir-pibrentasvir`, `sofosbuvir-velpatasvir`, `ledipasvir-sofosbuvir`,
  brand names Mavyret/Epclusa/Harvoni/…) rather than fragmenting them into single
  components that then fail to pair — verified by `tests/test_hepatitis.py`.
- HBV DNA, HCV RNA viral loads and anti-HBs GMT are flagged **log-normal**
  (pool on the log scale), not pooled on the natural scale.

Tooling: `scripts/hepatitis/` (build_hepatitis_corpus, download_hepatitis_pdfs,
validate_hepatitis, validate_hepatitis_ma, analyze_hepatitis_ma_misses,
build_aact_hepatitis_gold, cross_check).
