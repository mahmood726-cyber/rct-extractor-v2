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

## Status

- Specialty profile, registry wiring, and arm-level extraction **built and
  unit-tested** — `tests/test_tuberculosis.py` (23 tests; subspecialty routing,
  endpoint normalization, registry wiring, culture-conversion / treatment-success
  / relapse / TPT-completion 2×2). Full suite green, no regressions to the malaria
  / HIV / cardiology profiles.
- **Corpus validation pending** — run the scripts below. No corpus result numbers
  are quoted here until they are produced from a real run (cf. the measured HIV /
  malaria READMEs).

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
