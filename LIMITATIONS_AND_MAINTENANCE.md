# RCT Extractor v3.0 - Limitations, Maintenance, and Code Availability

## 1. Limitations

### 1.1 PDF Extraction

**Current Status:** Validation was performed on clean extracted text, not raw PDFs.

**Known Limitations:**
- PDF parsing may introduce extraction errors not present in validation
- Multi-column layouts may cause text reordering issues
- Tables embedded in PDFs require specialized extraction
- Scanned PDFs depend on OCR quality

**Mitigation Strategies:**
- OCR error correction module handles common character substitutions (O→0, l→1, Cl→CI)
- Confidence scoring accounts for text quality signals
- Spot-check tier (2.7% of extractions) provides human verification for edge cases

**Recommendation:** For production use, validate on a sample of actual PDFs from target journals before full deployment.

### 1.2 Language Support

**Current Status:** English language only.

**Known Limitations:**
- Patterns assume English terminology (hazard ratio, odds ratio, etc.)
- Non-English publications will not be correctly extracted
- Mixed-language abstracts may cause partial failures

**Future Work:**
- Pattern libraries could be extended for major languages (German, French, Spanish, Chinese)
- Effect estimate abbreviations are often preserved in English even in non-English publications

**Recommendation:** Exclude non-English publications from automated extraction pipeline, or implement language detection with manual review fallback.

### 1.3 Table Extraction

**Current Status:** Optimized for running text; limited table support.

**Known Limitations:**
- Effect estimates in formatted tables may not be captured
- Forest plot data in supplementary materials not extracted
- Complex table layouts (merged cells, nested headers) not supported

**Mitigation Strategies:**
- Many publications report primary results in abstract/text
- Table extraction tools (Tabula, Camelot) can preprocess tables to text
- Manual review tier handles complex cases

**Recommendation:** Use dedicated table extraction tools for table-heavy publications, then feed extracted text to this system.

### 1.4 Effect Types Not Covered

**Current Status:** Covers HR, OR, RR, MD, SMD, ARD, IRR, NNT/NNH.

**Not Currently Supported:**
- Incidence Rate Differences (IRD)
- Prevalence Ratios (PR)
- Diagnostic accuracy metrics (sensitivity, specificity, LR+, LR-)
- Correlation coefficients as primary outcomes
- Time-to-event medians without HR

**Recommendation:** For systematic reviews requiring unsupported effect types, manual extraction or pattern library extension is needed.

### 1.5 Longitudinal Validity

**Current Status:** Validated on publications from 2018-2026.

**Known Limitations:**
- Future publication formats may introduce new patterns
- Journal style changes may affect extraction
- New effect estimate types may emerge

**Mitigation:** Pattern maintenance strategy (see Section 2) addresses this through continuous monitoring.

---

## 2. Pattern Maintenance Strategy

### 2.1 Version Control

All patterns are maintained in `src/core/enhanced_extractor_v3.py` under version control:

```
Pattern Library Structure:
├── HR_PATTERNS (50+ patterns)
├── OR_PATTERNS (35+ patterns)
├── RR_PATTERNS (35+ patterns)
├── MD_PATTERNS (30+ patterns)
├── SMD_PATTERNS (25+ patterns)
├── ARD_PATTERNS (30+ patterns)
└── Supporting patterns (IRR, NNT, etc.)
```

### 2.2 Adding New Patterns

**Process for new format discovery:**

1. **Detection:** Monitor extraction failures in production
2. **Analysis:** Identify recurring unmatched formats
3. **Development:** Create pattern with test case
4. **Validation:** Run against full test suite (220+ cases)
5. **Deployment:** Release as minor version update

**Example:**
```python
# New pattern addition workflow
# 1. Identify failure: "HR, 0.74 (0.65 to 0.85)"
# 2. Create pattern: r'\bHR\b,\s*(\d+\.?\d*)\s*\((\d+\.?\d*)\s+to\s+(\d+\.?\d*)\)'
# 3. Add test case to validation set
# 4. Verify no false positives introduced
# 5. Merge and release
```

### 2.3 Regression Testing

**Before any pattern change:**
- Run full validation suite (167 original + 53 held-out cases)
- Run false positive suite (108 negative cases)
- Verify calibration metrics unchanged
- Document any sensitivity/specificity changes

**Automated testing:**
```bash
python run_comprehensive_validation.py
# Must show: ALL TARGETS MET
```

### 2.4 Versioning Policy

| Version | Changes |
|---------|---------|
| 3.0.x | Bug fixes, no pattern changes |
| 3.x.0 | New patterns, backward compatible |
| x.0.0 | Major changes, revalidation required |

### 2.5 Community Contributions

**Pattern contribution process:**
1. Submit issue with example text and expected extraction
2. Propose pattern via pull request
3. Include positive and negative test cases
4. Review by maintainers
5. Merge after validation passes

---

## 3. Code Availability

### 3.1 Repository

**Primary Repository:** GitHub (to be made public upon acceptance)

```
Repository: github.com/[organization]/rct-extractor
License: MIT License
```

### 3.2 Package Structure

```
rct-extractor/
├── src/
│   └── core/
│       └── enhanced_extractor_v3.py    # Main extractor
├── data/
│   ├── expanded_validation_v3.py       # Original validation (167 cases)
│   ├── held_out_test_set.py            # Held-out validation (53 cases)
│   └── false_positive_test_cases.py    # Negative cases (108 cases)
├── tests/
│   └── run_comprehensive_validation.py # Full validation suite
├── docs/
│   ├── VALIDATION_REPORT_V3_REVISED.md
│   ├── LIMITATIONS_AND_MAINTENANCE.md
│   └── API_DOCUMENTATION.md
├── LICENSE
├── README.md
└── requirements.txt
```

### 3.3 Installation

```bash
# Clone repository
git clone https://github.com/[organization]/rct-extractor.git
cd rct-extractor

# Install dependencies
pip install -r requirements.txt

# Run validation
python tests/run_comprehensive_validation.py
```

### 3.4 Basic Usage

```python
from src.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict

# Initialize extractor
extractor = EnhancedExtractor()

# Extract from text
text = "The hazard ratio was 0.74 (95% CI 0.65-0.85)"
extractions = extractor.extract(text)

# Process results
for ext in extractions:
    result = to_dict(ext)
    print(f"Type: {result['type']}")
    print(f"Effect: {result['effect_size']}")
    print(f"CI: [{result['ci_lower']}, {result['ci_upper']}]")
    print(f"SE: {result['standard_error']}")
    print(f"Confidence: {result['calibrated_confidence']}")
    print(f"Automation: {result['automation_tier']}")
```

### 3.5 API Documentation

Full API documentation available at:
- `docs/API_DOCUMENTATION.md`
- Inline docstrings in source code
- Example notebooks in `examples/`

### 3.6 Citation

```bibtex
@article{rct_extractor_2026,
  title={Automated Effect Estimate Extraction from Randomized Controlled
         Trials: A Production-Ready System with Comprehensive Validation},
  author={[Authors]},
  journal={Research Synthesis Methods},
  year={2026},
  doi={[DOI]}
}
```

### 3.7 Support

- **Issues:** GitHub Issues for bug reports and feature requests
- **Discussions:** GitHub Discussions for questions and community support
- **Email:** [contact email] for collaboration inquiries

---

## 4. Reproducibility Checklist

| Item | Provided | Location |
|------|----------|----------|
| Source code | Yes | `src/core/enhanced_extractor_v3.py` |
| Validation data | Yes | `data/*.py` |
| Test scripts | Yes | `run_comprehensive_validation.py` |
| Dependencies | Yes | `requirements.txt` |
| Documentation | Yes | `docs/` |
| License | Yes | MIT License |
| Version control | Yes | Git with tagged releases |

---

*Document version: 1.0*
*Date: 2026-01-28*
*Status: Addressing Minor Revisions for RSM-2026-0128-R3*
