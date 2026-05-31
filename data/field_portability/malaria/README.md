# Malaria RCT Extraction — Field Bundle

Adapts the deterministic RCT effect-size extractor to **malaria trials** for
meta-analysis, with automatic cross-checking against PubMed abstracts and
ClinicalTrials.gov / AACT.

## What this gives you
- A malaria-aware extractor: the universal effect-size engine (HR/OR/RR/MD/SMD/
  ARD/IRR/GMR) **plus** malaria endpoint vocabulary (ACPR, treatment failure,
  parasite/fever clearance, recrudescence, gametocyte carriage, clinical-malaria
  incidence, protective/vaccine efficacy, severe-malaria mortality) and a
  malaria-specific augmenter that catches formats the core misses
  (protective/vaccine **efficacy %**, bracketed adjusted ratios `[aOR]: …`,
  Lancet middle-dot decimals, `incidence rate ratio, 0.67; 95% CI, 0.50-0.90`).
- An **internal-consistency layer** (`src/specialties/internal_consistency.py`)
  that screens every extracted `(point, CI, p)` triple — these are
  over-determined, so a misread digit breaks their agreement. Grounded in
  Altman & Bland (BMJ 2011, CI↔p via the log-scale SE), statcheck
  (Nuijten 2016, significance-flip = "gross inconsistency"), and the
  geometric/arithmetic CI-midpoint rule. It drops internally-impossible
  extractions (point outside its CI, non-positive ratio, p↔CI significance
  flip), auto-repairs reversed CI bounds, and flags probable misread digits
  (e.g. CI upper `0.85` read as `85.0`) for review. On 1,200 corpus abstracts:
  5 impossible extractions dropped, 40 probable misread-digit errors surfaced.
- A malaria corpus: **4,094** PubMed malaria RCTs, **2,472** with open-access
  PDFs, **891** NCT-linked, **248** ISRCTN/PACTR-linked, **4,031** abstracts.
- Automatic cross-checking: every trial reconciled across PDF ↔ PubMed abstract
  ↔ AACT (where an NCT exists).

## Use it (one call, core + malaria augmenter)
```python
from src.core.enhanced_extractor_v3 import EnhancedExtractor
from src.specialties.malaria_effects import extract_malaria_effects

extractor = EnhancedExtractor()
effects = extract_malaria_effects(extractor, open("trial.txt").read())
for e in effects:
    print(e["type"], e["effect_size"], e["ci_lower"], e["ci_upper"], e.get("origin"))
```

Detect the malaria subspecialty / normalize endpoints:
```python
from src.specialties.registry import detect_specialty, normalize_endpoint_by_specialty
detect_specialty(text)                      # -> ('malaria', 'treatment', conf)
normalize_endpoint_by_specialty("PCR-corrected ACPR", "malaria", "treatment")  # -> 'ACPR'
```

## Rebuild / extend the corpus
```bash
# 1. Index malaria RCTs from PubMed (abstract + PMCID + NCT + ISRCTN/PACTR)
python scripts/malaria/build_malaria_corpus.py --retmax 4200 --email you@org

# 2. Download open-access PDFs (resumable; EuropePMC + PMC-OA fallback)
python scripts/malaria/download_malaria_pdfs.py --workers 3 --batch 3000 --resume

# 3. Build the AACT external gold (effect estimates from ClinicalTrials.gov)
python scripts/malaria/build_aact_malaria_gold.py --aact "F:/AACT-storage/AACT/<date>"

# 4. Cross-check every trial: PDF vs abstract vs AACT
python scripts/malaria/cross_check.py
```

## Measured performance (honest)
- **Published-meta-analysis agreement: 87.9%** (`validate_against_ma.py`) — across
  73 published malaria meta-analyses, of the comparative effect estimates the
  *reviewers hand-extracted* (HR/OR/RR/IRR/MD/efficacy), we reproduce **153/174**
  with the same point estimate AND the same CI (5% tol). This is a *silver*
  standard: MA data is human-extracted, so some non-recoveries are MA-side error.
- **Abstract→PDF recall: 94.9%** — effects reported in a trial's abstract are
  recovered from its full-text PDF (n=2,001 PDFs; 12,996 effects extracted).
- **PDF extraction precision: 87.3%** internally consistent; 12.7% surfaced as
  needs_review (misread digits, table-mangled values) rather than emitted silently.
- **Coverage note:** ~52% of PDFs yield zero effects — almost all because the
  paper reports **per-arm proportions/counts or within-arm descriptive stats**
  (e.g. "cure 95% vs 88%", "mean QT increase 28 ms, 95% CI 18-38"), NOT a
  pre-computed ratio+CI. The extractor is deliberately conservative here; pooling
  those trials needs ARM-LEVEL / 2x2 extraction (events/N per arm), a separate
  capability from effect-estimate extraction.
- **Malaria-augmenter lift: 62.8% → 72.6%** recall on abstracts that contain a
  genuine effect phrase (the rest are non-numeric method-sentence mentions).
- **AACT external gold** (independent numeric truth) exists for only ~43 of the
  4,094 trials, because most malaria RCTs register on PACTR/ISRCTN (no posted
  numeric results) rather than ClinicalTrials.gov. AACT-vs-PDF agreement
  strengthens as more PDFs download; AACT-vs-abstract is intentionally weak
  (abstracts carry headline numbers, AACT carries the full results table).

Validation sources, in order of independence: (1) **published meta-analyses**
(human-extracted, broad coverage — primary silver standard), (2) **AACT**
(machine truth, narrow coverage), (3) **abstract↔PDF** (internal consistency).

## Honesty / governance
- These numbers are **machine-measured** (extraction recall and source
  consistency). A **certified** accuracy figure still requires a human-
  adjudicated gold set per the Field Portability Kit governance (rule #4: never
  claim general-domain performance from machine self-consistency alone).
- PACTR/ISRCTN are registries, not results databases: useful as provenance, but
  they cannot serve as numeric cross-validation gold.
