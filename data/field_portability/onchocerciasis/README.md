# Onchocerciasis (River Blindness) RCT Extraction — Test Results

The onchocerciasis extractor (`src/specialties/onchocerciasis.py` +
`onchocerciasis_arm_data.py`, registered in the specialty registry) reuses the
shared effect-augmenter and arm-data engine with onchocerciasis endpoints and
microfilaricidal / macrofilaricidal arm labels. Onchocerciasis (*Onchocerca
volvulus*, transmitted by *Simulium* blackflies) is a top-priority African
neglected tropical disease: >99% of the ~21 million infected people live in
sub-Saharan Africa, and it is the world's second leading infectious cause of
blindness.

- **treatment** — skin microfilarial clearance (skin-snip negative /
  amicrofilaridermic), skin microfilarial density / community microfilarial load
  (CMFL, log-normal), microfilarial-density reduction, adult-worm
  (macrofilaricidal) effect / worm sterility (ivermectin / moxidectin /
  doxycycline / diethylcarbamazine / suramin / albendazole arms).
- **mda / control** — microfilarial / skin-snip prevalence, palpable-nodule
  (onchocercoma) prevalence, transmission (annual transmission potential, infective
  blackflies, biting rate), incidence of new infection / OV-16 seroconversion
  (mass drug administration / community-directed treatment with ivermectin, CDTI).
- **morbidity** — ocular onchocerciasis (microfilariae in the cornea / anterior
  chamber, punctate / sclerosing keratitis, iridocyclitis, optic atrophy), visual
  impairment / blindness, onchocercal skin disease (onchodermatitis, severe
  itching / pruritus, depigmentation / leopard skin, hanging groin / sowda),
  onchocerciasis-associated epilepsy / nodding syndrome.
- **safety** — adverse events, Mazzotti reaction, serious adverse events (notably
  post-ivermectin encephalopathy in *Loa loa* co-endemic areas).

## Tested on real data (2026-06-09)

Corpus from PubMed: **449 onchocerciasis RCTs / 146 OA PMCIDs / 42 NCT / 426
abstracts**. (449 is the true PubMed RCT count for the search term, not a
sampling cap.)

| Check | Result | Notes |
|---|---|---|
| **Published onchocerciasis meta-analyses** (silver gold) | **75.0%** (3/4) | point+CI agreement; onchocerciasis has a *small* poolable-effect MA literature (26 MA PMIDs, 7 with reviewer data, only 4 effect-labelled estimates) — see honest findings |
| **Effect internal-consistency** | **85.7%** | of 84 abstract effects (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **100%** | reported % == 100·events/total (25 proportions) |
| **Subspecialty routing** | treatment 299 / safety 28 / morbidity 22 / mda 8 / general 4 | of corpus docs detected as onchocerciasis |
| **AACT external gold** | sparse (36 NCTs, 1 study / 12 typed effects) | onchocerciasis trials register largely on ISRCTN/PACTR or post no structured results on CT.gov — same as malaria/typhoid/schistosomiasis |
| **Abstract→PDF cross-check** | tooling in place | identical to HIV/malaria/typhoid/schistosomiasis; run `scripts/onchocerciasis/download_onchocerciasis_pdfs.py` + `cross_check.py` (EuropePMC OA render is intermittent) |

### The 1 published-MA miss is an out-of-scope adjacency form, not a mis-read
The single 4/4 → 3/4 miss (`ma_misses.jsonl`) is the same kind of intervening-clause
format the adjacency-based core deliberately does not chase, and which a looser
pattern would match at the cost of regressing the sibling
(HIV/malaria/typhoid/schistosomiasis) extractors:

- `random effect model showed the overall pooled OR to be 0.53 (95%CI: 0.29 to0.96)`
  — a long clause ("…showed the overall pooled OR to be…") between the measure name
  and the value, compounded by an OCR-joined bound (`to0.96`).

The shared augmenter was **left unchanged**: full test suite **1378 passed**
(no regression vs the HIV/malaria/typhoid/schistosomiasis baseline of 1356).

### Honest findings
- Onchocerciasis abstracts are **overwhelmingly treatment-heavy** (299/361 routed
  docs): ivermectin / moxidectin microfilaricidal efficacy — skin microfilarial
  clearance, skin microfilarial density / CMFL, microfilarial-density reduction —
  so the effect-estimate + 2×2/continuous arm-level paths are primary. Skin
  microfilarial densities, community microfilarial loads and transmission
  potentials are right-skewed and are flagged **log-normal** (pool on the log
  scale / GMR, not raw MD).
- The **poolable-effect onchocerciasis MA literature is genuinely small**: most
  onchocerciasis systematic reviews are MDA mapping / prevalence syntheses or
  narrative safety reviews rather than pooled comparative-effect meta-analyses, so
  the published-MA effect denominator (4) is thin — the headline validated metric
  for this disease is the **85.7% internal-consistency over 84 abstract effects**
  plus **100% arm-level proportion consistency**.
- AACT is **not** a useful external gold for onchocerciasis (as for
  malaria/typhoid/schistosomiasis): 36 NCTs match but only 1 carries posted, typed
  numeric results (12 effects).
- Internal-consistency (85.7%) failures are dominated by abstract-only effects
  whose CI the abstract never restates.

Tooling: `scripts/onchocerciasis/` (build_onchocerciasis_corpus,
download_onchocerciasis_pdfs, validate_onchocerciasis, validate_onchocerciasis_ma,
analyze_onchocerciasis_ma_misses, build_aact_onchocerciasis_gold, cross_check).
