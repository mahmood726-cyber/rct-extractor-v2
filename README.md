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

## Installation

```bash
git clone <repo-url>
cd rct-extractor-v2
pip install -e ".[pdf,ocr]"
```

## Quick Start

```python
from src.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict

extractor = EnhancedExtractor()

text = """
The primary endpoint showed a hazard ratio of 0.74
(95% CI 0.65-0.85, P<0.001) favoring treatment.
"""
extractions = extractor.extract(text)

for ext in extractions:
    result = to_dict(ext)
    print(f"Type: {result['type']}")
    print(f"Effect: {result['effect_size']}")
    print(f"CI: [{result['ci_lower']}, {result['ci_upper']}]")
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
