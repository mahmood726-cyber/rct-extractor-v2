# RCT Extractor v2 - Statistical Methods Appendix

## A1. Pattern-Based Extraction

### A1.1 Regular Expression Patterns

The extractor uses 150+ regular expression patterns organized by effect measure type:

#### Hazard Ratio Patterns (25 patterns)
```
Key patterns include:
- "hazard ratio for X was VALUE (95% CI, A to B)"
- "HR VALUE; 95% CI, A-B"
- "hazard ratio, VALUE [95% CI A to B]"
```

#### Odds Ratio Patterns (12 patterns)
```
Key patterns include:
- "odds ratio for X was VALUE (95% CI, A to B)"
- "OR VALUE (95% CI A-B)"
```

#### Risk Ratio Patterns (14 patterns)
```
Key patterns include:
- "rate ratio for X was VALUE (95% CI, A to B)"
- "relative risk VALUE (95% CI A-B)"
- "RR VALUE; 95% CI A to B"
```

#### Risk Difference Patterns (7 patterns)
```
Key patterns include:
- "difference, VALUE percentage points; 95% CI, A to B"
- "absolute risk reduction VALUE% (95% CI A-B)"
```

#### Mean Difference Patterns (13 patterns)
```
Key patterns include:
- "difference in X was VALUE (95% CI, A to B)"
- "mean change VALUE (95% CI A-B)"
```

### A1.2 Text Normalization

Before pattern matching, text undergoes normalization:
1. Unicode minus (−) → ASCII minus (-)
2. En-dash (–) → ASCII minus (-)
3. Middle dot (·) → decimal point (.)
4. Em-dash (—) → ASCII minus (-)

---

## A2. Ensemble Architecture

### A2.1 Extractor Components

| Extractor | Method | Strengths |
|-----------|--------|-----------|
| E1 (Python) | Regex patterns | Primary extraction, provenance |
| E2 (JavaScript) | Port of RCTExtractor.js | Cross-validation |
| E3 (Wasserstein) | KM curve analysis | IPD reconstruction |
| E4 (TruthCert) | ClinicalTrials.gov API | Ground truth verification |

### A2.2 Confidence Grading Algorithm

```python
def calculate_grade(e1, e2, e3, e4):
    values = [e.value for e in [e1, e2, e3, e4] if e.value is not None]

    # Count agreements within 5% tolerance
    agreements = count_agreements(values, tolerance=0.05)

    if agreements >= 3 and e4.verified:
        return 'A'  # ≥3 agree + CTGov verified
    elif agreements >= 2 and any_has_provenance([e1, e2]):
        return 'B'  # ≥2 agree with provenance
    elif agreements >= 1 and max_confidence(values) > 0.85:
        return 'C'  # Single high-confidence
    elif any(values):
        return 'D'  # Low confidence extraction
    else:
        return 'F'  # No extraction
```

### A2.3 Merge Strategy

The ensemble uses weighted voting:
```
final_value = Σ(wi × vi) / Σ(wi)

where:
  wi = confidence weight for extractor i
  vi = extracted value from extractor i

Weights:
  E4 (verified): 1.0
  E1 (primary):  0.9
  E2 (cross):    0.8
  E3 (derived):  0.7
```

---

## A3. Validation Statistics

### A3.1 Clopper-Pearson Exact Confidence Interval

For binomial proportion p = k/n:

```
CI_low = Beta(α/2, k, n-k+1)
CI_high = Beta(1-α/2, k+1, n-k)
```

For 95% CI, α = 0.05.

**Implementation:**
```python
from scipy.stats import beta

def clopper_pearson_ci(successes, trials, confidence=0.95):
    alpha = 1 - confidence

    ci_low = beta.ppf(alpha/2, successes, trials-successes+1)
    ci_high = beta.ppf(1-alpha/2, successes+1, trials-successes)

    return (ci_low, ci_high)
```

### A3.2 Cohen's Kappa

Agreement statistic for two raters:

```
κ = (po - pe) / (1 - pe)

where:
  po = observed agreement proportion
  pe = expected agreement by chance
```

**Interpretation (Landis & Koch, 1977):**

| Kappa | Interpretation |
|-------|---------------|
| <0.00 | Poor |
| 0.00-0.20 | Slight |
| 0.21-0.40 | Fair |
| 0.41-0.60 | Moderate |
| 0.61-0.80 | Substantial |
| 0.81-1.00 | Almost Perfect |

**Standard Error:**
```
SE(κ) = √(po(1-po) / (n(1-pe)²))
```

**95% CI:**
```
κ ± 1.96 × SE(κ)
```

### A3.3 Tolerance-Based Matching

Values are considered matching if:

```
|extracted - expected| / |expected| ≤ tolerance

Default tolerances:
  Point estimates: 5%
  Confidence intervals: 10%
```

Special case for zero values:
```
if expected == 0:
    match = |extracted| < tolerance
```

---

## A4. Specialty-Specific Patterns

### A4.1 Cardiology Subspecialties

**Heart Failure:**
- Endpoints: CV death or HF hospitalization, all-cause mortality
- Drugs: Sacubitril/valsartan, empagliflozin, dapagliflozin

**Acute Coronary Syndrome:**
- Endpoints: MACE, CV death, MI, stroke
- Drugs: P2Y12 inhibitors, anticoagulants

**Atrial Fibrillation:**
- Endpoints: Stroke/SE, major bleeding
- Drugs: DOACs, warfarin

### A4.2 Oncology Subspecialties

**Survival Endpoints:**
- OS (overall survival)
- PFS (progression-free survival)
- DFS (disease-free survival)

**Response Endpoints:**
- ORR (objective response rate)
- CR (complete response)
- DCR (disease control rate)

### A4.3 Other Specialties

Documented patterns for:
- Infectious Disease (COVID, HIV)
- Diabetes/Metabolic (GLP-1, SGLT2)
- Neurology (MS, Alzheimer's)
- Autoimmune (RA, SLE, Psoriasis)
- Respiratory (COPD, Asthma)

---

## A5. Quality Assurance

### A5.1 Provenance Tracking

Each extraction includes:
```python
@dataclass
class Provenance:
    pdf_file: str           # Source PDF path
    page_number: int        # Page in PDF
    bbox: BoundingBox       # Coordinates (x1,y1,x2,y2)
    raw_text: str           # Matched text
    extraction_method: str  # 'table' or 'text'
```

### A5.2 Validation Checks

1. **Range validation**: HR/OR/RR must be > 0
2. **CI ordering**: ci_low < point_estimate < ci_high
3. **CI width**: Reject implausibly narrow CIs
4. **Cross-reference**: Compare against CTGov when available

### A5.3 Review Queue

Low-confidence extractions are flagged:
```python
@dataclass
class ReviewQueueItem:
    record_id: str
    severity: ReviewSeverity  # ERROR, WARNING, INFO
    reason_code: str
    reason_text: str
    suggested_action: str
```

---

## A6. Reproducibility

### A6.1 Software Environment

```
Python 3.9+
Dependencies:
  - scipy >= 1.9.0 (statistics)
  - rapidfuzz >= 3.0.0 (fuzzy matching)
  - pyyaml >= 6.0 (configuration)
```

### A6.2 Gold Standard Data

Located in `data/gold/`:
- `real_trials.jsonl` (20 cardiology)
- `oncology_trials.jsonl` (20 oncology)
- `infectious_disease_trials.jsonl` (15 ID)
- `diabetes_metabolic_trials.jsonl` (15 diabetes)
- `psychiatry_neurology_trials.jsonl` (15 neuro)
- `respiratory_autoimmune_trials.jsonl` (15 resp/autoimmune)

### A6.3 Running Validation

```bash
cd rct-extractor-v2
python run_benchmark.py
```

---

## References

1. Landis JR, Koch GG. The measurement of observer agreement for categorical data. Biometrics. 1977;33:159-174.

2. Clopper CJ, Pearson ES. The use of confidence or fiducial limits illustrated in the case of the binomial. Biometrika. 1934;26:404-413.

3. Cohen J. A coefficient of agreement for nominal scales. Educational and Psychological Measurement. 1960;20:37-46.

4. Fleiss JL. Measuring nominal scale agreement among many raters. Psychological Bulletin. 1971;76:378-382.

5. Wilson EB. Probable inference, the law of succession, and statistical inference. Journal of the American Statistical Association. 1927;22:209-212.
