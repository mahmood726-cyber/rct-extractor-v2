# RCT Extractor v3.0

Production-grade automated extraction of effect estimates from randomized controlled trial publications with calibrated confidence scores and meta-analysis ready output.

## Key Results (v3.0)

| Metric | Value | Target |
|--------|-------|--------|
| Sensitivity (Original) | 100% (167/167) | 100% |
| Sensitivity (Held-Out) | 100% (53/53) | >90% |
| False Positive Rate | 0% (0/108) | <5% |
| Calibration (ECE) | 0.012 | <0.10 |
| SE Coverage | 100% | >95% |
| Automation Rate | 97.3% | 80% |

## Features

- **180+ Extraction Patterns**: Comprehensive coverage of effect estimate formats
- **Calibrated Confidence**: ECE = 0.012 for reliable automation decisions
- **Tiered Automation**: 97.3% full automation, 2.7% spot-check
- **Meta-Analysis Ready**: Automatic SE calculation and ARD normalization
- **OCR Error Correction**: Handles common OCR errors (O→0, l→1, Cl→CI)
- **Comprehensive Validation**: Tested on 220+ positive and 108 negative cases

## Supported Effect Types

| Type | Description | Patterns |
|------|-------------|----------|
| HR | Hazard Ratio | 50+ |
| OR | Odds Ratio | 35+ |
| RR | Risk Ratio / Relative Risk | 35+ |
| MD | Mean Difference | 30+ |
| SMD | Standardized Mean Difference | 25+ |
| ARD | Absolute Risk Difference | 30+ |
| IRR | Incidence Rate Ratio | 5+ |
| NNT/NNH | Number Needed to Treat/Harm | 5+ |

## Installation

```bash
git clone https://github.com/[organization]/rct-extractor.git
cd rct-extractor
pip install -r requirements.txt
```

## Quick Start

```python
from src.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict

# Initialize extractor
extractor = EnhancedExtractor()

# Extract from text
text = """
The primary endpoint showed a hazard ratio of 0.74
(95% CI 0.65-0.85, P<0.001) favoring treatment.
"""
extractions = extractor.extract(text)

# Process results
for ext in extractions:
    result = to_dict(ext)
    print(f"Type: {result['type']}")           # HR
    print(f"Effect: {result['effect_size']}")  # 0.74
    print(f"CI: [{result['ci_lower']}, {result['ci_upper']}]")  # [0.65, 0.85]
    print(f"SE: {result['standard_error']:.4f}")  # 0.0684
    print(f"Confidence: {result['calibrated_confidence']:.1%}")  # 99.0%
    print(f"Automation: {result['automation_tier']}")  # full_auto
```

## Automation Tiers

| Tier | Confidence | Action | % of Extractions |
|------|------------|--------|------------------|
| FULL_AUTO | ≥92% | No review needed | 97.3% |
| SPOT_CHECK | 85-92% | Random 10% sampling | 2.7% |
| VERIFY | 70-85% | Quick verification | 0% |
| MANUAL | <70% | Full manual review | 0% |

## Validation

Run the comprehensive validation suite:

```bash
python run_comprehensive_validation.py
```

Expected output:
```
CRITICAL METRICS (Editorial Requirements)
  Original Sensitivity      100.0%     (target: 100%    ) [PASS]
  Held-Out Sensitivity      100.0%     (target: >90%    ) [PASS]
  False Positive Rate       0.0%       (target: <5%     ) [PASS]
  ECE (Calibration)         0.012      (target: <0.10   ) [PASS]
  SE Coverage               100.0%     (target: >95%    ) [PASS]

OVERALL STATUS: ALL TARGETS MET
```

## Project Structure

```
rct-extractor-v2/
├── src/core/
│   └── enhanced_extractor_v3.py      # Main extractor (180+ patterns)
├── data/
│   ├── expanded_validation_v3.py     # Original validation (167 cases)
│   ├── held_out_test_set.py          # External validation (53 cases)
│   └── false_positive_test_cases.py  # Negative cases (108 cases)
├── docs/
│   └── API_DOCUMENTATION.md          # Full API documentation
├── run_comprehensive_validation.py    # Validation runner
├── VALIDATION_REPORT_V3_REVISED.md   # Validation report
├── LIMITATIONS_AND_MAINTENANCE.md    # Limitations and maintenance
└── README.md
```

## Standard Error Calculation

SE is automatically calculated from confidence intervals:

```python
# For ratios (HR, OR, RR) - log scale:
SE = (log(CI_upper) - log(CI_lower)) / (2 * 1.96)

# For differences (MD, SMD, ARD) - linear scale:
SE = (CI_upper - CI_lower) / (2 * 1.96)
```

## ARD Normalization

Absolute Risk Differences are automatically normalized to decimal scale:

| Original | Detected Scale | Normalized |
|----------|----------------|------------|
| -3.2% | percentage | -0.032 |
| -0.032 | decimal | -0.032 |

## Limitations

- **PDF Extraction:** Validated on clean text; real PDFs may require preprocessing
- **Language:** English only
- **Tables:** Optimized for running text; tables may need separate extraction

See [LIMITATIONS_AND_MAINTENANCE.md](LIMITATIONS_AND_MAINTENANCE.md) for details.

## Citation

```bibtex
@article{rct_extractor_2026,
  title={Automated Effect Estimate Extraction from Randomized Controlled
         Trials: A Production-Ready System with Comprehensive Validation},
  author={[Authors]},
  journal={Research Synthesis Methods},
  year={2026}
}
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new patterns
4. Run validation suite (`python run_comprehensive_validation.py`)
5. Submit pull request

See [LIMITATIONS_AND_MAINTENANCE.md](LIMITATIONS_AND_MAINTENANCE.md) for pattern contribution guidelines.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v3.0 | 2026-01-28 | 180+ patterns, calibration, SE calculation, held-out validation |
| v2.16 | 2026-01-27 | External validation framework, provenance tracking |
| v2.0 | 2026-01-26 | Initial production release |
