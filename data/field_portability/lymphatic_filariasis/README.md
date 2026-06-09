# Lymphatic Filariasis (LF / elephantiasis) RCT Extraction — Test Results

The lymphatic-filariasis extractor (`src/specialties/lymphatic_filariasis.py` +
`lymphatic_filariasis_arm_data.py`, registered in the specialty registry) reuses
the shared effect-augmenter and arm-data engine with LF endpoints and
antifilarial / MDA arm labels:

- **mda** — clearance of microfilaraemia (mf clearance / amicrofilaraemia /
  mf-negative conversion), microfilaria (mf) density reduction, circulating-
  filarial-antigen (CFA / antigenaemia) clearance, and adult-(macrofilaricidal)
  worm death. Arms: diethylcarbamazine (DEC), albendazole (ALB) and ivermectin
  (IVM) as the two-drug DA (DEC+ALB) / IA (IVM+ALB) regimens or the WHO triple-
  drug IDA (IVM+DEC+ALB), plus DEC-medicated salt and the anti-Wolbachia
  macrofilaricide doxycycline.
- **transmission** — community microfilaria prevalence, circulating-filarial-
  antigen prevalence, incidence of (new) infection, and entomological
  transmission (transmission assessment survey / TAS, mosquito infection rate /
  xenomonitoring) — the WHO elimination endpoints.
- **morbidity** — lymphoedema / elephantiasis stage and progression, hydrocele,
  acute adenolymphangitis (ADL / acute filarial attacks), and limb volume
  (morbidity management and disability prevention, MMDP).
- **safety** — adverse events, serious adverse events, and systemic post-
  treatment (Mazzotti-type) reactions to dying microfilariae (fever, headache,
  myalgia).

Parasites covered: *Wuchereria bancrofti* (~90% of the global burden),
*Brugia malayi* and *Brugia timori*.

## Tested on real data (2026-06-09)

Corpus from PubMed: **291 LF RCTs / 102 OA PMCIDs / 31 NCT / 287 abstracts**
(search term in `scripts/lymphatic_filariasis/build_lymphatic_filariasis_corpus.py`).

| Check | Result | Notes |
|---|---|---|
| **Published LF / filariasis meta-analyses** (silver gold) | **98.0%** (201/205) | point+CI agreement for comparative effect estimates across 78 published LF MAs |
| **Effect internal-consistency** | **83.3%** | of 78 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **100.0%** | reported % == 100·events/total (23 proportions) |
| **Subspecialty routing** | mda 196 / morbidity 26 / safety 17 / general 14 / transmission 6 | of corpus docs detected as lymphatic_filariasis |
| **Effect-type mix** | MD 30 / RR 28 / OR 16 / RRR 2 / ARD 1 / HR 1 | of 78 extracted effects |
| **Abstract→PDF cross-check** | deferred | tooling is in place (identical to HIV/malaria/helminths); 102 OA PMCIDs are available for a full-text pass via `scripts/lymphatic_filariasis/` |

### Honest findings
- LF abstracts are **MDA / efficacy-heavy** (microfilaraemia clearance, mf density
  reduction, antigenaemia clearance) — 196/287 route to the `mda` subspecialty —
  so the clearance / 2×2 path is primary. **Morbidity** (lymphoedema, hydrocele,
  acute adenolymphangitis, limb volume) and **safety** (post-treatment systemic
  reactions) are well represented; **transmission** (community mf / antigen
  prevalence, TAS, xenomonitoring) is a smaller, often programmatic / full-text-
  reported subset (only 6 abstracts route there, as transmission endpoints are
  usually reported in elimination-programme reports rather than the trial
  abstract).
- Comparative effect estimates recover at **98.0%** against published LF MAs — in
  line with the sibling profiles (typhoid 100%, malaria 98.4%, helminths 96.8%,
  HIV 97.1%). The residual `all-CI` figure (73.0%) is dominated by abstract-only
  prevalences / mf-density values whose CI the abstract never restates, not by
  mis-reads.
- Effects-per-abstract coverage (10.5%) is expected: LF abstracts more often
  report **mf clearance / antigen clearance as bare percentages** and **mf
  density as a geometric mean** than as pre-computed RR/OR with CIs, so the 2×2
  and continuous arm-level paths (microfilaria density pooled **log-normal**,
  limb volume pooled on the natural scale) carry the rest.
- Microfilaria density is strongly right-skewed and flagged **not poolable on the
  natural scale** (log-normal `pooling_note` → geometric mean ratio), matching the
  schistosomiasis / helminths egg-count handling.

## Reproduce

```bash
python scripts/lymphatic_filariasis/build_lymphatic_filariasis_corpus.py --retmax 4000 --email you@org
python scripts/lymphatic_filariasis/validate_lymphatic_filariasis_ma.py  --retmax 300  --email you@org
python scripts/lymphatic_filariasis/validate_lymphatic_filariasis.py     --limit 4000
pytest tests/test_lymphatic_filariasis.py -q
```

Large/transient corpus artefacts (`*.jsonl`, `*.json`, `rct_trial_pdfs/`) are
git-ignored; only this README and the code under `scripts/lymphatic_filariasis/`
are tracked.
