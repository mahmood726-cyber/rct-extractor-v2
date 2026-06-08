# Soil-Transmitted Helminths (STH) / Deworming RCT Extraction — Test Results

The helminths extractor (`src/specialties/helminths.py` +
`helminths_arm_data.py`, registered in the specialty registry) reuses the shared
effect-augmenter and arm-data engine with STH / deworming endpoints and
anthelmintic arm labels:

- **treatment** — parasitological cure rate, egg reduction rate (ERR), egg count
  / infection intensity (eggs per gram, EPG by Kato-Katz), treatment failure
  (albendazole / mebendazole / pyrantel pamoate / levamisole / ivermectin /
  tribendimidine / oxantel / nitazoxanide arms).
- **mass_deworming** — infection prevalence and prevalence reduction,
  moderate-to-heavy-intensity infection, programme coverage (preventive
  chemotherapy / MDA / school-based deworming).
- **nutrition** — weight gain, height / height-for-age (stunting), haemoglobin /
  anaemia, mid-upper-arm circumference (MUAC), cognition / school attendance —
  the rationale for community deworming.
- **reinfection** — reinfection rate / prevalence, incidence of (re)infection,
  time to reinfection, reinfection intensity.

Worm taxa covered: *Ascaris lumbricoides* (roundworm), *Trichuris trichiura*
(whipworm), hookworm (*Necator americanus*, *Ancylostoma duodenale*), and
*Strongyloides stercoralis*.

## Tested on real data (2026-06-08)

Corpus from PubMed: **1,267 STH / deworming RCTs / 512 OA PMCIDs / 138 NCT /
1,238 abstracts** (search term in `scripts/helminths/build_helminths_corpus.py`).

| Check | Result | Notes |
|---|---|---|
| **Published deworming / STH meta-analyses** (silver gold) | **96.8%** (398/411) | point+CI agreement for comparative effect estimates across 130 published STH MAs |
| **Effect internal-consistency** | **88.1%** | of 605 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **100.0%** | reported % == 100·events/total (64 proportions) |
| **Subspecialty routing** | treatment 800 / mass_deworming 152 / nutrition 96 / general 46 / reinfection 7 | of corpus docs detected as helminths |
| **Effect-type mix** | OR 193 / MD 172 / RR 171 / IRR 16 / SMD 16 / HR 14 / ARD 13 / RRR 7 / GMR 3 | of 605 extracted effects |
| **Abstract→PDF cross-check** | deferred | tooling is in place (identical to HIV/malaria/typhoid); 512 OA PMCIDs are available for a full-text pass via `scripts/helminths/` |

### Honest findings
- Deworming abstracts are **treatment-heavy** (cure rate, egg reduction rate,
  egg counts by Kato-Katz) — 800/1,238 route to the treatment subspecialty — so
  the cure / ERR / 2×2 path is primary. **Nutrition** (weight/height/Hb/cognition)
  and **mass_deworming** (prevalence, heavy-intensity infection) are well
  represented; **reinfection** is a smaller, full-text-reported subset (only 7
  abstracts route there, as reinfection dynamics are usually a secondary
  full-text outcome).
- Comparative effect estimates recover at **96.8%** against published STH MAs —
  in line with the sibling profiles (typhoid 100%, malaria 98.4%, HIV 97.1%).
  The residual `all-CI` figure (68.5%) is dominated by abstract-only
  prevalences/egg-counts whose CI the abstract never restates, not by mis-reads.
- Effects-per-abstract coverage (15.5%) is expected: deworming abstracts more
  often report **egg reduction rate / cure rate as bare percentages** than as
  pre-computed RR/OR with CIs, so the 2×2 and continuous arm-level paths (egg
  counts pooled **log-normal**, weight/height/Hb/MUAC pooled on the natural
  scale) carry the rest.
- Egg counts (EPG) and reinfection intensity are right-skewed and flagged
  **not poolable on the natural scale** (log-normal `pooling_note`), matching the
  schistosomiasis profile.

## Reproduce

```bash
python scripts/helminths/build_helminths_corpus.py --retmax 4000 --email you@org
python scripts/helminths/validate_helminths_ma.py  --retmax 250  --email you@org
python scripts/helminths/validate_helminths.py     --limit 4000
pytest tests/test_helminths.py -q
```

Large/transient corpus artefacts (`*.jsonl`, `*.json`, `rct_trial_pdfs/`) are
git-ignored; only this README and the code under `scripts/helminths/` are tracked.
