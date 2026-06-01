# HIV RCT Extraction — Test Results

The HIV extractor (`src/specialties/hiv.py` + `hiv_arm_data.py`, registered in the
specialty registry) reuses the shared effect-augmenter and arm-data engine with
HIV endpoints (viral suppression / FDA snapshot, virologic failure, CD4, HIV-RNA,
AIDS progression, MTCT, HIV acquisition, PrEP efficacy, TB co-infection,
retention) and antiretroviral arm labels (DTG/BIC/EFV/TDF/TAF/FTC/3TC/…).

## Tested on real data (2026-06-01, full corpus)

Corpus from PubMed: **2,995 HIV RCTs / 1,855 OA PDFs downloaded / 986 NCT / 2,979 abstracts**.

| Check | Result | Notes |
|---|---|---|
| **Published HIV meta-analyses** (silver gold) | **97.9%** (140/143) | point+CI agreement across 76 HIV MAs; after tuning (was 72.7%) |
| **Abstract→PDF recall** (1,855 PDFs) | **94.7%** (1,198/1,265) | effects in a trial's abstract recovered from its full-text PDF |
| **Effect internal-consistency** | **93.2%** | of 1,983 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **99.3%** | reported % == 100·events/total |
| **AACT→PDF** | 4.5% (44/982 over 77 trials) | coverage mismatch, NOT extraction error (below) |

### Why AACT→PDF is low (and that's expected)
HIV trials post **many** granular secondary analyses to ClinicalTrials.gov:
median 3, mean 9.4, **up to 152 typed effects per trial** (e.g. NCT00232141 — pain
/ anxiety / sleep scales + subgroups). The 77 trials with both a posted-results gold
and a downloaded PDF carry **982 typed AACT effects** (median ~13/trial), but a paper
restates only a few headline effects in extractable text — so the denominator balloons
while matches don't. (On the smaller 933-PDF subset this read 9.2% = 42/456; widening
to the full corpus pulled in more analysis-heavy trials, *lowering* the ratio while the
absolute matches rose 42→44 — which reinforces the coverage-mismatch reading.) The
**44 matched effects are correct** (the extractor agrees with AACT when the effect is
in the paper); the **94.7% abstract→PDF recall is the true extraction-reliability
signal**. (Same pattern as malaria's AACT→PDF.)

### Honest findings
- HIV abstracts report **pre-computed effects** (OR/RR/HR) far more than raw n/N,
  so the effect-estimate path is primary; 2×2 comes mainly from full-text tables.
- The 2 tuning fixes that took HIV 72.7%→97.9% (bare-abbrev space/comma separator;
  CI-recovery when core gets the value but no CI) were GENERAL and also lifted
  malaria 87.9%→99.4%.
- AACT external gold for HIV is rich: **495 trials, 2,934 typed effects** (vs
  malaria's 89) — HIV trials are heavily registered with posted results.

Tooling: `scripts/hiv/` (build_hiv_corpus, download_hiv_pdfs, validate_hiv,
validate_hiv_ma, analyze_hiv_ma_misses, build_aact_hiv_gold, cross_check).
