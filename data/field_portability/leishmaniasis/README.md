# Leishmaniasis (Visceral + Cutaneous) RCT Extraction — Test Results

The leishmaniasis extractor (`src/specialties/leishmaniasis.py` +
`leishmaniasis_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and arm-data engine with leishmaniasis endpoints and
antileishmanial arm labels. Leishmaniasis is a top-priority neglected tropical
disease: visceral leishmaniasis (VL / kala-azar, *Leishmania donovani*) is endemic
and frequently fatal across East Africa (Sudan, South Sudan, Ethiopia, Kenya,
Somalia) and the Indian subcontinent; cutaneous leishmaniasis (CL) is the most
common form worldwide:

- **visceral (VL / kala-azar)** — the two-stage cure structure these trials always
  use: INITIAL cure (end of treatment, clinically well + parasite-free aspirate)
  and DEFINITIVE / FINAL cure (6 months / Day 210, alive with no relapse), plus
  relapse, parasitological (splenic / bone-marrow aspirate) clearance, and
  post-kala-azar dermal leishmaniasis (PKDL). Arms: liposomal amphotericin B
  (AmBisome) / miltefosine / paromomycin (aminosidine) / sodium stibogluconate
  (SSG) / meglumine antimoniate / pentamidine.
- **cutaneous (CL)** — complete cure / re-epithelialisation (cure rate), lesion
  healing, lesion size / induration (continuous, MD).
- **combination / duration** — combination therapy (the East-African SSG+PM
  standard), treatment duration, hospital stay — the shortened-regimen question.
- **safety** — mortality / case fatality, adverse and serious adverse events, and
  the drug-class toxicities that drive VL regimen choice: antimonial
  cardiotoxicity (QT prolongation), amphotericin / paromomycin nephrotoxicity,
  hepatotoxicity.

## Tested on real data (2026-06-09)

Corpus from PubMed: **587 leishmaniasis RCTs / 231 OA PMCIDs / 53 NCT / 567
abstracts**. (587 is the true PubMed RCT count for the search term, not a
sampling cap.)

| Check | Result | Notes |
|---|---|---|
| **Published leishmaniasis meta-analyses** (silver gold) | **98.0%** (98/100) | effect-estimate point+CI agreement across **62** leishmaniasis MAs |
| **Effect internal-consistency** | **84.2%** | of 222 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **100%** | reported % == 100·events/total (92 proportions) |
| **Subspecialty routing** | cutaneous 265 / visceral 206 / general 39 / safety 23 / combination 4 | 537 / 567 corpus docs detected as leishmaniasis (94.7%) |
| **AACT external gold** | sparse (208 NCTs, 0 typed) | leishmaniasis trials register on ISRCTN/PACTR/CTRI or post no structured results on CT.gov — same as malaria/typhoid/schistosomiasis |
| **Abstract→PDF cross-check** | tooling in place | identical to HIV/malaria/typhoid/schistosomiasis; run `scripts/leishmaniasis/download_leishmaniasis_pdfs.py` + `cross_check.py` (EuropePMC OA render is intermittent) |

### The 2 published-MA misses are out-of-scope forms, not mis-reads
Mining the 2/100 misses (`ma_misses.jsonl`) shows they are an intervening
multi-word clause between the measure name and its value, or a compressed
Cochrane forest-row — formats the adjacency-based core deliberately does not
chase, and which a looser pattern would match only at the cost of regressing the
sibling (HIV/malaria/typhoid/schistosomiasis) extractors:

- `pooled effect size (OR) for hepatitis B virus infection was 3.43 (95% CI
  1.66-7.10)` — a long clause between the "OR" label and the value, and an
  **association** OR (HBV co-infection prevalence), not a treatment effect.
- `... better than IM aminosidine sulphate (1RCT n= 38, RR 0.05; 95% CI 0.00,
  0.78)` — a **compressed Cochrane forest-row** with an `n=` and a comma between
  the label and the value, and a comma-separated CI.

The shared augmenter was **left unchanged**: full test suite **1381 passed** (no
regression vs the HIV/malaria/typhoid/schistosomiasis baseline; +25 new
leishmaniasis tests).

### Honest findings
- Leishmaniasis abstracts split fairly evenly between cutaneous (265) and visceral
  (206) trials; the VL two-stage cure vocabulary (initial vs definitive/final cure
  + relapse) and CL complete-cure / lesion-size vocabulary are both first-class
  endpoints, so the effect-estimate + 2×2/continuous arm-level paths are primary.
- Effect internal-consistency (84.2%) is on a 222-effect abstract pool; the
  failures are dominated by abstract-only effects whose CI the abstract never
  restates (the abstract reports a point estimate and a p-value but no CI).
- AACT is **not** a useful external gold for leishmaniasis (as for
  malaria/typhoid/schistosomiasis): 208 NCTs match but none carry posted, typed
  numeric results — these trials are run by DNDi / MSF / national programmes and
  register on ISRCTN/PACTR/CTRI.

Tooling: `scripts/leishmaniasis/` (build_leishmaniasis_corpus,
download_leishmaniasis_pdfs, validate_leishmaniasis, validate_leishmaniasis_ma,
analyze_leishmaniasis_ma_misses, build_aact_leishmaniasis_gold, cross_check).
