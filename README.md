# RCT Extractor v5.0

Automated extraction of effect estimates from randomized controlled trial PDFs for meta-analysis.

## What It Does

Takes a real RCT PDF and outputs structured data: effect type, point estimate, confidence interval, p-value, source text, and page number.

## Supported Effect Types

| Type | Description |
|------|-------------|
| HR | Hazard Ratio |
| OR | Odds Ratio |
| RR | Risk Ratio / Relative Risk |
| MD | Mean Difference |
| SMD | Standardized Mean Difference |
| ARD | Absolute Risk Difference |
| IRR | Incidence Rate Ratio |
| GMR | Geometric Mean Ratio |
| NNT/NNH | Number Needed to Treat/Harm |

## Install & Use

Install from a clone or directly from GitHub — the console scripts and all 17
disease specialties are available immediately:

```bash
# from a clone
git clone https://github.com/mahmood726-cyber/rct-extractor-v2.git
cd rct-extractor-v2
pip install .                      # core: text/abstract extraction + all 17 specialties

# ...or directly from GitHub
pip install "git+https://github.com/mahmood726-cyber/rct-extractor-v2.git"

# optional extras
pip install ".[pdf,ocr]"           # add PDF parsing + OCR
pip install ".[all]"               # everything (API server, PDF, OCR, validation)
```

This installs two console scripts:

| Command | What it does |
|---------|--------------|
| `rct-extract` | **Primary CLI** — run any of the 17 disease specialties on abstracts/text (auto-detect or forced). |
| `rct-extract-pdf` | Original PDF-table extraction pipeline (cardiology vocabulary). |

### Quickstart — CLI

```bash
# what can I extract?
rct-extract --list-specialties

# force a specialty on one abstract
rct-extract --specialty diabetes --input abstract.txt

# auto-detect the specialty, emit JSON
rct-extract --auto --text "Empagliflozin vs placebo: CV death 30/200 (15.0%) in the empagliflozin group and 50/200 (25.0%) in the placebo group (hazard ratio 0.62, 95% CI 0.45-0.85)." --json

# batch every *.txt in a folder -> one JSON object per line
rct-extract --auto --input ./corpus --json -o results.jsonl

# just detect the specialty
rct-extract --detect --input abstract.txt
```

### Quickstart — Python API

```python
import rct_extractor as rx

rx.list_specialties()          # the 17 supported disease specialties

result = rx.extract(abstract_text, specialty="diabetes")   # or specialty="auto"
result["specialty"], result["subspecialty"], result["confidence"]
result["effects"]      # [{type, effect_size, ci_lower, ci_upper, endpoint, ...}]
result["arm_level"]    # {poolable_2x2, tables_2x2, continuous}

# build a meta-analysis config (the universal meta-starter-kit interchange JSON,
# consumed by RapidMeta / allmeta / E156 capsules / Pairwise70):
cfg = rx.to_metakit_config(
    [{"name": "SPRINT", "text": "...hazard ratio 0.75 (95% CI 0.64-0.89)..."},
     {"name": "ACCORD", "text": "...hazard ratio 0.88 (95% CI 0.73-1.06)..."}],
    title="Intensive BP control", effect_measure="HR",
)
```

### Supported specialties (17)

`hiv`, `malaria`, `typhoid`, `schistosomiasis`, `sickle_cell`, `cholera`,
`maternal_neonatal`, `tuberculosis`, `hepatitis`, `meningitis`, `pneumonia`,
`diarrhoeal`, `malnutrition`, `helminths`, `hypertension`, `cervical_cancer`,
`diabetes`. Each ships a subspecialty detector, endpoint normalizer, and an
arm-level extractor (poolable 2×2 + continuous). The corpus data used to build
each profile is gitignored — the wheel is ~0.4 MB.

See [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md) for wiring the engine into
Beast, RapidMeta, the allmeta browser apps, and the Pairwise70 / journal pipeline.

### Low-level core (advanced)

The unified API above is the recommended entry point. The raw effect extractor
is still available directly:

```python
from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict
extractor = EnhancedExtractor()
extractions = [to_dict(x) for x in extractor.extract(
    "The primary endpoint showed a hazard ratio of 0.74 (95% CI 0.65-0.85, P<0.001).")]
```

## Architecture

- **180+ regex patterns** for effect estimate extraction
- **PDF pipeline**: pdfplumber -> PyMuPDF -> OCR fallback
- **Table extraction**: structured table parsing for results tables
- **Team-of-rivals**: multiple extractors with consensus voting
- **Provenance**: every extraction traces back to source text + page

## Field Portability

This repo now includes a reusable field-portability kit so other specialties can run the same workflow with their own meta-analysis corpus.

- Spec: `docs/FIELD_PORTABILITY_KIT.md`
- Field profile template: `configs/field_profile.template.yaml`
- Scaffold tool: `scripts/scaffold_field_portability_bundle.py`

### Specialty profiles

Disease-specific endpoint vocabularies and arm-level extractors live in
`rct_extractor/_engine/specialties/`, registered in `rct_extractor/_engine/specialties/registry.py`:

| Specialty | Module | Subspecialties |
|-----------|--------|----------------|
| HIV | `hiv.py` + `hiv_arm_data.py` | treatment, prevention, pmtct, coinfection |
| Malaria | `malaria.py` + `malaria_arm_data.py` | treatment, prevention, severe, transmission |
| Typhoid | `typhoid.py` + `typhoid_arm_data.py` | treatment, vaccine, resistance, complications |
| Schistosomiasis | `schistosomiasis.py` + `schistosomiasis_arm_data.py` | treatment, prevention, morbidity, vaccine |
| Sickle cell | `sickle_cell.py` + `sickle_cell_arm_data.py` | disease_modifying, acute_pain, prevention, transfusion |
| Cholera | `cholera.py` + `cholera_arm_data.py` | treatment, rehydration, vaccine, severe |
| Maternal & neonatal | `maternal_neonatal.py` + `maternal_neonatal_arm_data.py` | maternal, hypertensive, neonatal, preterm |
| Tuberculosis | `tuberculosis.py` + `tuberculosis_arm_data.py` | treatment, drug_resistant, prevention, latent |
| Hepatitis (HBV/HCV) | `hepatitis.py` + `hepatitis_arm_data.py` | treatment, prevention, pmtct, outcomes |
| Meningitis | `meningitis.py` + `meningitis_arm_data.py` | treatment, vaccine, mortality, sequelae |
| Pneumonia | `pneumonia.py` + `pneumonia_arm_data.py` | treatment, vaccine, mortality, severe |
| Diarrhoeal | `diarrhoeal.py` + `diarrhoeal_arm_data.py` | rehydration, rotavirus, treatment, mortality_duration |
| Malnutrition | `malnutrition.py` + `malnutrition_arm_data.py` | therapeutic_feeding, micronutrient, mortality, recovery_growth |
| Helminths (STH) | `helminths.py` + `helminths_arm_data.py` | treatment, mass_deworming, nutrition, reinfection |
| Hypertension | `hypertension.py` + `hypertension_arm_data.py` | bp_lowering, cv_events, bp_reduction, adherence |
| Cervical cancer | `cervical_cancer.py` + `cervical_cancer_arm_data.py` | vaccine, screening, treatment, mortality |
| Diabetes (T2DM) | `diabetes.py` + `diabetes_arm_data.py` | glycemic, cardiorenal, hypoglycemia, complications |

Two additional endpoint-only profiles (`cardiology.py`, `oncology.py`) are
registered for detection and endpoint normalization but do not ship a dedicated
arm-level extractor.

Per-specialty corpus / validation scripts live under `scripts/<specialty>/`
(e.g. `scripts/hepatitis/` mirrors `scripts/hiv/`: corpus build, OA-PDF download,
extractor validation, AACT gold, published-MA validation, miss analysis,
cross-check).

## Validation Status

| Metric | Value | Notes |
|--------|-------|-------|
| ClinicalTrials.gov (33 studies) | 97.7% sensitivity | Only credible external validation |
| Pattern tests | 757 passing | Unit + integration |
| Real PDF corpus | 407 PDFs | Collected, validation in progress |
| Gold standard | IN PROGRESS | 50 manually-annotated PDFs planned |

Real-world accuracy on arbitrary PDFs is still being validated. Do not assume 100% accuracy.

## Known Limitations

- English-only (multi-language patterns exist but not validated)
- Table extraction works but needs improvement for complex layouts
- MD/SMD CI extraction has known gaps
- OCR requires Tesseract installed separately
- Not validated for regulatory use

## Running Tests

```bash
python -m pytest tests/ --tb=short -q
```

## License

MIT
