# Schistosomiasis (Bilharzia) RCT Extraction — Test Results

The schistosomiasis extractor (`src/specialties/schistosomiasis.py` +
`schistosomiasis_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and arm-data engine with schistosomiasis endpoints and
anthelmintic / vaccine arm labels. Schistosomiasis is a top-priority African
neglected tropical disease (~90% of the global burden is in sub-Saharan Africa):

- **treatment** — parasitological cure, egg reduction rate (ERR), egg count /
  infection intensity (log-normal), treatment failure (praziquantel / artesunate /
  artemether / oxamniquine / mefloquine / albendazole / mebendazole arms).
- **prevention / control** — infection prevalence and prevalence reduction,
  reinfection / incidence of infection, heavy-intensity infection (mass drug
  administration / preventive chemotherapy / school-based treatment).
- **morbidity** — periportal (liver) fibrosis / hepatosplenic disease, haematuria,
  bladder / urinary-tract pathology, anaemia.
- **vaccine** — protective efficacy, immunogenicity / antibody response
  (anti-Sh28GST, anti-Sm14), seroconversion (Sh28GST/Bilhvax, Sm14, Sm-TSP-2 arms).

## Tested on real data (2026-06-06)

Corpus from PubMed: **595 schistosomiasis RCTs / 277 OA PMCIDs / 41 NCT / 581
abstracts**. (595 is the true PubMed RCT count for the search term, not a
sampling cap.)

| Check | Result | Notes |
|---|---|---|
| **Published schistosomiasis meta-analyses** (silver gold) | **95.2%** (80/84) | point+CI agreement across 58 schistosomiasis MAs |
| **Effect internal-consistency** | **92.5%** | of 241 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **97.1%** | reported % == 100·events/total (34 proportions) |
| **Subspecialty routing** | treatment 360 / morbidity 39 / prevention 38 / general 34 / vaccine 6 | of corpus docs detected as schistosomiasis |
| **AACT external gold** | sparse (100 NCTs, 0 typed) | schistosomiasis trials register on ISRCTN/PACTR or post no structured results on CT.gov — same as malaria/typhoid |
| **Abstract→PDF cross-check** | tooling in place | identical to HIV/malaria/typhoid; run `scripts/schistosomiasis/download_schistosomiasis_pdfs.py` + `cross_check.py` (EuropePMC OA render is intermittent) |

### The 4 published-MA misses are out-of-scope forms, not mis-reads
Mining the 4/84 misses (`ma_misses.jsonl`) shows they are all multi-word phrases
*between* the measure name and its value, or a non-treatment measure — formats the
adjacency-based core deliberately does not chase, and which a looser pattern would
match at the cost of regressing the sibling (HIV/malaria/typhoid) extractors:

- `OR among females was 1.31 (95% CI: 0.87-1.99)` — a **subgroup** OR with
  intervening words between "OR" and the value
- `adjusted OR showed that the pooled estimate was 1.85` — long clause between
  the measure name and the value
- `DOR of IHA was 9.41 (95% CI: 4.88-18.18)` — **diagnostic** odds ratio from a
  test-accuracy meta-analysis, not a treatment effect
- `total OR of 0.11 (95% CI 0.06 to 0.21)` — "total OR of" prefix

The shared augmenter was **left unchanged**: full test suite **975 passed**
(no regression vs the HIV/malaria/typhoid baseline).

### Honest findings
- Schistosomiasis abstracts are **treatment-heavy** (praziquantel efficacy:
  parasitological cure, egg reduction rate, egg counts), so the effect-estimate +
  2×2/continuous arm-level paths are primary; egg counts and antibody titres are
  right-skewed and are flagged **log-normal** (pool on the log scale / GMR, not
  raw MD).
- AACT is **not** a useful external gold for schistosomiasis (as for
  malaria/typhoid): 100 NCTs match but none carry posted, typed numeric results.
- Internal-consistency (92.5%) is on a 241-effect abstract pool; the failures are
  dominated by abstract-only effects whose CI the abstract never restates.

Tooling: `scripts/schistosomiasis/` (build_schistosomiasis_corpus,
download_schistosomiasis_pdfs, validate_schistosomiasis, validate_schistosomiasis_ma,
analyze_schistosomiasis_ma_misses, build_aact_schistosomiasis_gold, cross_check).
