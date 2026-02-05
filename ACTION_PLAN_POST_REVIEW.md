# Action Plan: Post-Editorial Review

Based on the Research Synthesis Methods editorial review, this document outlines concrete steps to address the identified concerns.

---

## Priority 1: External Validation (Critical)

### 1.1 Prospective PDF Collection
**Status:** Not Started
**Effort:** High

Tasks:
- [ ] Collect 100+ open-access RCT PDFs from PubMed Central
- [ ] Stratify by: therapeutic area, journal, year, effect type
- [ ] Include challenging cases: scanned PDFs, multi-column, tables

### 1.2 Dual Manual Extraction
**Status:** Not Started
**Effort:** High

Tasks:
- [ ] Recruit 2 trained extractors (clinical background preferred)
- [ ] Create extraction protocol aligned with Cochrane guidance
- [ ] Extract all effect estimates independently
- [ ] Calculate inter-rater reliability (Cohen's kappa)
- [ ] Adjudicate discrepancies with third reviewer

### 1.3 Validation Metrics
**Status:** Not Started
**Effort:** Medium

Tasks:
- [ ] Calculate sensitivity/specificity by effect type
- [ ] Generate Bland-Altman plots (automated vs. manual)
- [ ] Stratify by journal, therapeutic area, PDF quality
- [ ] Report false positive/negative examples

---

## Priority 2: Confidence Calibration (Critical)

### 2.1 Calibration Dataset
**Status:** Not Started
**Effort:** Medium

Tasks:
- [ ] Use external validation data for calibration
- [ ] Bin extractions by confidence (0.5-0.6, 0.6-0.7, etc.)
- [ ] Calculate observed accuracy in each bin
- [ ] Generate calibration plot

### 2.2 Threshold Determination
**Status:** Not Started
**Effort:** Low

Tasks:
- [ ] Determine threshold for "high confidence" (target: 95% accuracy)
- [ ] Determine threshold for "low confidence" (flag for review)
- [ ] Report Expected Calibration Error (ECE)

### 2.3 Implementation
**Status:** Not Started
**Effort:** Low

```python
# Add to ml_extractor.py
def get_calibrated_confidence(raw_confidence: float) -> Tuple[float, str]:
    """
    Convert raw confidence to calibrated probability.
    Returns (calibrated_prob, recommendation)
    """
    # Calibration curve (to be fitted from data)
    calibrated = calibration_curve(raw_confidence)

    if calibrated >= 0.95:
        return calibrated, "HIGH_CONFIDENCE"
    elif calibrated >= 0.80:
        return calibrated, "VERIFY_RECOMMENDED"
    else:
        return calibrated, "MANUAL_EXTRACTION_NEEDED"
```

---

## Priority 3: Extraction Metadata (Important)

### 3.1 Source Location
**Status:** Not Started
**Effort:** Medium

Tasks:
- [ ] Capture character offset in source text
- [ ] For PDFs: capture page number and approximate coordinates
- [ ] Store 100 characters of surrounding context

### 3.2 Comparison Arm Labels
**Status:** Not Started
**Effort:** Medium

```python
@dataclass
class ExtractedEffect:
    # Existing fields...

    # New metadata
    source_location: Optional[SourceLocation]
    treatment_arm: Optional[str]  # "dapagliflozin", "empagliflozin"
    control_arm: Optional[str]    # "placebo", "standard care"
    analysis_population: Optional[str]  # "ITT", "mITT", "per-protocol"
    timepoint: Optional[str]      # "52 weeks", "median 3.2 years"
```

### 3.3 Analysis Population Detection
**Status:** Not Started
**Effort:** Low

Tasks:
- [ ] Add regex patterns for ITT/mITT/per-protocol mentions
- [ ] Flag when multiple populations reported
- [ ] Default to ITT when unclear

---

## Priority 4: Subgroup Analysis Flagging (Important)

### 4.1 Subgroup Detection Patterns
**Status:** Not Started
**Effort:** Low

```python
SUBGROUP_PATTERNS = [
    r"subgroup\s+analysis",
    r"in\s+(?:patients|subjects)\s+with",
    r"stratified\s+by",
    r"among\s+(?:those|patients)\s+who",
    r"(?:pre-?specified|exploratory)\s+subgroup",
    r"interaction\s+p[- ]?value",
]
```

### 4.2 Interaction P-Value Extraction
**Status:** Not Started
**Effort:** Low

Tasks:
- [ ] Extract p-interaction when present
- [ ] Flag subgroup effects without interaction test
- [ ] Warn about selective reporting risk

---

## Priority 5: Training Data Improvement (Important)

### 5.1 Separate Train/Test Split
**Status:** Not Started
**Effort:** Medium

Tasks:
- [ ] Hold out 20% of gold standard for testing only
- [ ] Stratify by effect type and trial type
- [ ] No data leakage between splits

### 5.2 Negative Examples
**Status:** Not Started
**Effort:** Medium

Tasks:
- [ ] Add 50+ "looks like effect but isn't" examples
- [ ] Include: gene expressions, biomarkers, imaging metrics
- [ ] Balance positive/negative examples in training

### 5.3 OCR Artifact Handling
**Status:** Not Started
**Effort:** Medium

Tasks:
- [ ] Add test cases with common OCR errors (1/l, 0/O, rn/m)
- [ ] Implement fuzzy matching for corrupted patterns
- [ ] Test on actually OCR'd PDFs (not just clean text)

---

## Priority 6: Reproducibility (Medium)

### 6.1 Version Pinning
**Status:** Not Started
**Effort:** Low

Create `requirements.txt`:
```
scikit-learn==1.4.0
numpy==1.26.3
```

### 6.2 Random Seed Documentation
**Status:** Partial (random_state=42 used)
**Effort:** Low

Tasks:
- [ ] Document all random seeds in code
- [ ] Add global seed configuration option
- [ ] Verify deterministic results

### 6.3 Docker Container
**Status:** Not Started
**Effort:** Medium

```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ /app/src/
COPY data/ /app/data/
WORKDIR /app
CMD ["python", "-m", "pytest"]
```

---

## Priority 7: Multi-Language Support (Medium)

### 7.1 European Number Formats
**Status:** Not Started
**Effort:** Low

Tasks:
- [ ] Handle comma as decimal separator (1,25 vs 1.25)
- [ ] Handle period as thousands separator (1.234 vs 1234)
- [ ] Add locale parameter to extraction functions

### 7.2 Non-English Patterns
**Status:** Not Started
**Effort:** Medium

Tasks:
- [ ] Add German patterns (Hazard-Ratio, Konfidenzintervall)
- [ ] Add French patterns (rapport de cotes, intervalle de confiance)
- [ ] Add Spanish patterns (razón de riesgos, intervalo de confianza)

---

## Priority 8: Network Meta-Analysis Support (Medium)

### 8.1 Multi-Arm Correlation Structure
**Status:** Partial (detection only)
**Effort:** High

Tasks:
- [ ] Calculate shared control arm correlations
- [ ] Generate contrast matrix for indirect comparisons
- [ ] Export format compatible with netmeta R package

### 8.2 Treatment Standardization
**Status:** Not Started
**Effort:** Medium

Tasks:
- [ ] Build drug name synonym dictionary
- [ ] Handle dose variations (10mg, 20mg as separate nodes)
- [ ] Detect active comparator vs placebo

---

## Timeline

| Priority | Task | Target Date | Status |
|----------|------|-------------|--------|
| P1 | External validation protocol | Week 1-2 | Not Started |
| P1 | PDF collection (100+) | Week 2-4 | Not Started |
| P1 | Dual manual extraction | Week 4-8 | Not Started |
| P2 | Confidence calibration | Week 8-10 | Not Started |
| P3 | Extraction metadata | Week 4-6 | Not Started |
| P4 | Subgroup flagging | Week 2-3 | Not Started |
| P5 | Training data split | Week 2-3 | Not Started |
| P6 | Docker + requirements | Week 1 | Not Started |
| P7 | Multi-language | Week 6-8 | Not Started |
| P8 | NMA support | Week 10-12 | Not Started |

---

## Success Criteria

### For "Minor Revision" Status
- [ ] External validation on 50+ PDFs with kappa > 0.8
- [ ] Confidence calibration with ECE < 0.05
- [ ] Source location metadata for all extractions
- [ ] Subgroup analysis flagging implemented

### For "Accept" Status
- [ ] External validation on 100+ PDFs with sensitivity > 0.95
- [ ] Calibrated confidence with threshold for 95% accuracy
- [ ] PRISMA-S compliant methods documentation
- [ ] Docker container with reproducible results
- [ ] Comparison with manual extraction (Bland-Altman)

---

*Document created: 2026-01-28*
*Based on: Research Synthesis Methods Editorial Review*
