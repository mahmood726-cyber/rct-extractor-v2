# Childhood Pneumonia / ARI RCT Extraction — Test Results

The pneumonia extractor (`src/specialties/pneumonia.py` + `pneumonia_arm_data.py`,
registered in the specialty registry) reuses the shared effect-augmenter and
arm-data engine with pneumonia endpoints and antibiotic / pneumococcal-vaccine
arm labels:

- **treatment** — clinical cure / treatment success, treatment failure, time to
  resolution of symptoms (fever, fast breathing, chest indrawing), oxygen
  saturation recovery, relapse (amoxicillin / amoxicillin-clavulanate /
  co-trimoxazole / penicillin / ampicillin / ceftriaxone / cefuroxime /
  azithromycin / chloramphenicol / gentamicin arms).
- **vaccine** — radiologically/clinically-confirmed pneumonia incidence, vaccine
  efficacy, invasive pneumococcal disease (IPD), vaccine-type nasopharyngeal
  carriage, serotype-specific immunogenicity (anti-pneumococcal IgG GMC / OPA)
  (PCV7/10/13/15/20 / PPSV23 / Hib arms).
- **mortality** — all-cause mortality, pneumonia-specific mortality, case fatality.
- **severe** — severe / very severe pneumonia, hospitalisation / hospital
  admission, length of hospital stay, ICU / PICU admission, mechanical
  ventilation / respiratory support, empyema / pleural effusion / lung abscess.

Childhood pneumonia is the single largest infectious cause of under-5 death
worldwide and is disproportionately concentrated in the WHO African Region — a
core Africa-priority topic for the student meta-analysis workflow.

## Tested on real data (2026-06-08)

Corpus from PubMed: **2,444 childhood-pneumonia / ARI RCTs / 1,050 OA PMCIDs /
461 NCT / 2,424 abstracts** (search restricted to paediatric/under-five
populations).

| Check | Result | Notes |
|---|---|---|
| **Published pneumonia meta-analyses** (silver gold) | **97.9%** (237/242) | point+CI agreement across 109 childhood-pneumonia MAs; effect estimates (HR/OR/RR/IRR/MD) |
| **All-CI numbers** (effects + prevalences) | 64.2% (262/408) | the residual is dominated by bare prevalences/percentages the comparative-effect path does not target |
| **Effect internal-consistency** | **93.3%** | of 638 abstract effects on a 500-abstract diagnostic sample (Altman-Bland / midpoint checks) |
| **Arm-level proportion consistency** | **100.0%** | reported % == 100·events/total (33 proportions) |
| **Subspecialty routing** | vaccine 111 / treatment 77 / mortality 71 / general 61 / severe 51 | of the 500-doc diagnostic sample detected as pneumonia |
| **AACT external gold** | **rich** (434 studies, 10,173 effects, 3,260 typed) | 11,813 pneumonia NCTs in AACT; vaccine + adult-CAP trials post numeric results on CT.gov, so AACT is a usable independent numeric gold here (unlike typhoid/malaria) |
| **Abstract→PDF cross-check** | tooling in place | `scripts/pneumonia/download_pneumonia_pdfs.py` + `cross_check.py` (identical to HIV/malaria/typhoid); 1,050 OA PMCIDs available to download |

## Honest findings

- Pneumonia RCT abstracts are **effect-estimate-heavy** (incidence rate ratios,
  vaccine efficacy, risk ratios for treatment failure / mortality) and report
  pre-computed effects more than raw n/N, so the effect-estimate path is primary;
  paired 2×2 tables come mainly from full text (abstract 2×2 yield is low and
  *expected* to be — 10 tables across the 500-abstract sample, 0 poolable because
  abstracts rarely restate both arms' n/N adjacently).
- Effect coverage on abstracts is **31.2%** — most abstracts that report no
  parenthetical effect estimate are conference-style or descriptive; this is the
  same coverage regime as the sibling profiles.
- **AACT is a genuinely useful external gold for pneumonia** (contrast with
  typhoid/malaria, which register on ISRCTN/CTRI/PACTR): the large pneumococcal
  vaccine programmes and adult community-acquired-pneumonia trials register on
  ClinicalTrials.gov with posted numeric results — `aact_pneumonia_gold.json`
  carries 10,173 effect rows (3,260 typed) across 434 studies.
- Internal-consistency (93.3%) is on par with HIV's (~93%); failures are
  dominated by abstract-only effects whose CI the abstract never restates, not by
  mis-reads.

## Validation reproduction

```
python scripts/pneumonia/build_pneumonia_corpus.py --retmax 5000 --email you@org
python scripts/pneumonia/validate_pneumonia_ma.py --retmax 250 --email you@org   # silver gold (MA agreement)
python scripts/pneumonia/validate_pneumonia.py --limit 2444                        # corpus yield + consistency
python scripts/pneumonia/build_aact_pneumonia_gold.py                              # AACT external numeric gold
python scripts/pneumonia/download_pneumonia_pdfs.py --workers 3 --resume           # OA full text
python scripts/pneumonia/cross_check.py                                            # abstract↔PDF↔AACT reconcile
```

Tooling: `scripts/pneumonia/` (build_pneumonia_corpus, download_pneumonia_pdfs,
validate_pneumonia, validate_pneumonia_ma, analyze_pneumonia_ma_misses,
build_aact_pneumonia_gold, cross_check).
