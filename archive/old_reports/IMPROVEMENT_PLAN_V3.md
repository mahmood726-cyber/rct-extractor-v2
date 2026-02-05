# RCT Extractor v3.0 Improvement Plan
## Target: Production-Ready Fully Automated Extraction

**Current State (v2.16):**
- Sensitivity: 72.7% (missing 27% of effects)
- Calibration: ECE 0.50 (poor - cannot trust confidence scores)
- External validation: 39 trials (insufficient)
- Automation: NOT READY (all extractions need human review)

**Target State (v3.0):**
- Sensitivity: 95%+
- Calibration: ECE < 0.05 (well-calibrated)
- External validation: 200+ trials
- Automation: HIGH_CONFIDENCE extractions auto-accepted (80%+ of extractions)

---

## PHASE 1: PATTERN COVERAGE EXPANSION
**Goal:** Increase sensitivity from 72.7% to 95%+
**Timeline:** Sprint 1-2

### 1.1 Failure Analysis
Analyze why 27.3% of extractions are missed:

```
Categories of missed extractions:
├── Format variations (estimated 40% of misses)
│   ├── European decimal format (0,74 vs 0.74)
│   ├── Semicolon separators (HR 0.74; 95% CI 0.65; 0.85)
│   ├── Space variations (HR = 0.74 vs HR=0.74)
│   └── Unicode characters (en-dash, minus sign)
│
├── Alternate terminology (estimated 30% of misses)
│   ├── "relative hazard" instead of "hazard ratio"
│   ├── "incidence rate ratio" (IRR)
│   ├── "prevalence ratio"
│   └── "risk reduction" without explicit RR
│
├── Complex structures (estimated 20% of misses)
│   ├── Multi-line spans
│   ├── Table formats
│   ├── Parenthetical nesting
│   └── Reference to earlier values
│
└── Edge cases (estimated 10% of misses)
    ├── Adjusted vs unadjusted in same sentence
    ├── Multiple timepoints
    └── Subgroup-only reporting
```

### 1.2 New Patterns to Add

```python
NEW_PATTERNS = {
    # Incidence Rate Ratio
    'IRR': [
        r'incidence\s+rate\s+ratio[,:\s]+(\d+\.?\d*)',
        r'IRR\s*[=:]\s*(\d+\.?\d*)',
    ],

    # Prevalence Ratio
    'PR': [
        r'prevalence\s+ratio[,:\s]+(\d+\.?\d*)',
        r'PR\s*[=:]\s*(\d+\.?\d*)',
    ],

    # Rate Ratio (generic)
    'RaR': [
        r'rate\s+ratio[,:\s]+(\d+\.?\d*)',
    ],

    # Relative Hazard (synonym for HR)
    'HR_ALT': [
        r'relative\s+hazard[,:\s]+(\d+\.?\d*)',
    ],

    # Risk Reduction patterns
    'RRR': [
        r'relative\s+risk\s+reduction[,:\s]+(\d+\.?\d*)%?',
        r'RRR\s*[=:]\s*(\d+\.?\d*)%?',
    ],

    'ARR': [
        r'absolute\s+risk\s+reduction[,:\s]+(\d+\.?\d*)%?',
        r'ARR\s*[=:]\s*(\d+\.?\d*)%?',
    ],

    # European formats
    'EU_FORMAT': [
        r'HR\s*[=:]\s*(\d+),(\d+)',  # 0,74 format
    ],

    # Semicolon-separated CIs
    'SEMICOLON_CI': [
        r'(\d+\.?\d*)\s*;\s*95%?\s*CI\s*[;:]\s*(\d+\.?\d*)\s*;\s*(\d+\.?\d*)',
    ],
}
```

### 1.3 Pattern Testing Framework

Create systematic pattern coverage tests:

```python
# test_pattern_coverage.py
COVERAGE_TEST_CASES = [
    # Standard formats (should all pass)
    ("HR 0.74 (95% CI 0.65-0.85)", "HR", 0.74),
    ("hazard ratio 0.74 (0.65 to 0.85)", "HR", 0.74),

    # European formats
    ("HR 0,74 (95% CI 0,65-0,85)", "HR", 0.74),

    # Alternate terminology
    ("relative hazard 0.74", "HR", 0.74),
    ("incidence rate ratio 2.3 (1.5-3.4)", "IRR", 2.3),

    # Complex structures
    ("The HR was 0.74\n(95% CI, 0.65 to 0.85)", "HR", 0.74),

    # ... 500+ test cases covering all variations
]
```

---

## PHASE 2: EXTERNAL VALIDATION EXPANSION
**Goal:** Expand from 39 to 200+ trials
**Timeline:** Sprint 2-3

### 2.1 Data Sources

| Source | Target Trials | Access Method |
|--------|---------------|---------------|
| PubMed Central OA | 80 | API bulk download |
| Cochrane CENTRAL | 40 | Manual curation |
| ClinicalTrials.gov | 30 | Results API |
| EMA EPAR | 25 | PDF extraction |
| FDA Drug Approvals | 25 | PDF extraction |

### 2.2 Therapeutic Area Balance

```
Target distribution (200 trials):
├── Cardiovascular: 50 trials (25%)
├── Oncology: 50 trials (25%)
├── Diabetes/Metabolic: 30 trials (15%)
├── Infectious Disease: 25 trials (12.5%)
├── Neurology: 20 trials (10%)
├── Respiratory: 15 trials (7.5%)
└── Other: 10 trials (5%)
```

### 2.3 Difficulty Distribution

```
Target by difficulty:
├── Easy: 80 trials (40%) - clear format, single comparison
├── Moderate: 80 trials (40%) - multiple effects, some ambiguity
├── Hard: 30 trials (15%) - complex tables, multi-arm
└── Very Hard: 10 trials (5%) - edge cases, OCR issues
```

### 2.4 Actual Dual Human Extraction

```python
@dataclass
class HumanExtractor:
    """Qualified human extractor"""
    name: str
    qualification: str  # "PhD epidemiology", "MD", "MSc biostatistics"
    experience_years: int
    training_completed: bool

EXTRACTOR_POOL = [
    HumanExtractor("Extractor_1", "PhD Epidemiology", 5, True),
    HumanExtractor("Extractor_2", "MSc Biostatistics", 3, True),
    HumanExtractor("Extractor_3", "MD Clinical Research", 7, True),
]

# Extraction protocol:
# 1. Random assignment of 2 extractors per trial
# 2. Independent extraction without communication
# 3. Adjudication by third extractor for disagreements
# 4. Consensus recorded with disagreement notes
```

---

## PHASE 3: CALIBRATION IMPROVEMENT
**Goal:** Reduce ECE from 0.50 to <0.05
**Timeline:** Sprint 3-4

### 3.1 Root Cause Analysis

Current calibration failure reasons:
1. **Training data circularity**: Confidence scorer trained on same data as patterns
2. **Insufficient negative examples**: Few false positive cases in training
3. **Feature imbalance**: Some features dominate scoring

### 3.2 Calibration Improvement Strategy

```python
class ImprovedCalibrator:
    """
    Multi-stage calibration with isotonic regression
    """

    def __init__(self):
        self.stage1_platt = PlattScaling()
        self.stage2_isotonic = IsotonicRegression()
        self.stage3_temperature = TemperatureScaling()

    def fit(self, predictions, actuals):
        """
        Three-stage calibration:
        1. Platt scaling for initial calibration
        2. Isotonic regression for non-parametric adjustment
        3. Temperature scaling for final tuning
        """
        # Stage 1: Platt scaling
        platt_calibrated = self.stage1_platt.fit_transform(predictions, actuals)

        # Stage 2: Isotonic regression
        isotonic_calibrated = self.stage2_isotonic.fit_transform(
            platt_calibrated, actuals
        )

        # Stage 3: Temperature scaling
        final_calibrated = self.stage3_temperature.fit_transform(
            isotonic_calibrated, actuals
        )

        return final_calibrated

    def get_reliable_threshold(self, target_accuracy=0.95):
        """
        Find threshold where observed accuracy >= target
        """
        # Binary search on calibration curve
        ...
```

### 3.3 Calibration Validation

```python
def validate_calibration(calibrator, holdout_data):
    """
    Validate calibration on held-out data
    """
    metrics = {
        'ece': expected_calibration_error(calibrator, holdout_data),
        'mce': max_calibration_error(calibrator, holdout_data),
        'brier': brier_score(calibrator, holdout_data),
        'reliability_diagram': plot_reliability(calibrator, holdout_data),
    }

    # Target thresholds
    assert metrics['ece'] < 0.05, f"ECE {metrics['ece']} too high"
    assert metrics['mce'] < 0.15, f"MCE {metrics['mce']} too high"

    return metrics
```

---

## PHASE 4: AUTOMATION FRAMEWORK
**Goal:** Enable safe automated extraction
**Timeline:** Sprint 4-5

### 4.1 Tiered Automation System

```python
class AutomationTier(Enum):
    FULL_AUTO = "full_auto"      # No human review needed
    SPOT_CHECK = "spot_check"    # Random 10% review
    VERIFY = "verify"            # Human verification required
    MANUAL = "manual"            # Automated extraction failed

class AutomatedExtractor:
    """
    Production extractor with tiered automation
    """

    def __init__(self, calibrator, config):
        self.calibrator = calibrator
        self.config = config

        # Thresholds (determined empirically from calibration)
        self.FULL_AUTO_THRESHOLD = 0.98  # 98%+ expected accuracy
        self.SPOT_CHECK_THRESHOLD = 0.95  # 95-98% expected accuracy
        self.VERIFY_THRESHOLD = 0.85      # 85-95% expected accuracy
        # Below 0.85 = MANUAL

    def extract_with_automation(self, text):
        """
        Extract with automation tier assignment
        """
        extractions = self.extract_all(text)

        results = []
        for ext in extractions:
            raw_conf = self.score_confidence(ext)
            calibrated_conf = self.calibrator.calibrate(raw_conf)

            # Assign automation tier
            if calibrated_conf >= self.FULL_AUTO_THRESHOLD:
                tier = AutomationTier.FULL_AUTO
            elif calibrated_conf >= self.SPOT_CHECK_THRESHOLD:
                tier = AutomationTier.SPOT_CHECK
            elif calibrated_conf >= self.VERIFY_THRESHOLD:
                tier = AutomationTier.VERIFY
            else:
                tier = AutomationTier.MANUAL

            results.append({
                **ext,
                'raw_confidence': raw_conf,
                'calibrated_confidence': calibrated_conf,
                'automation_tier': tier,
                'human_review_required': tier != AutomationTier.FULL_AUTO,
            })

        return results
```

### 4.2 Automation Metrics Dashboard

```python
@dataclass
class AutomationMetrics:
    """Track automation performance"""
    total_extractions: int
    full_auto_count: int
    full_auto_accuracy: float  # Must stay >= 98%
    spot_check_count: int
    spot_check_accuracy: float
    verify_count: int
    verify_accuracy: float
    manual_count: int

    @property
    def automation_rate(self):
        """Percentage handled without human review"""
        return self.full_auto_count / self.total_extractions

    @property
    def human_effort_reduction(self):
        """Reduction in human extraction effort"""
        # FULL_AUTO = 0% effort
        # SPOT_CHECK = 10% effort (random sample)
        # VERIFY = 50% effort (quick check)
        # MANUAL = 100% effort
        effort = (
            self.full_auto_count * 0.0 +
            self.spot_check_count * 0.1 +
            self.verify_count * 0.5 +
            self.manual_count * 1.0
        ) / self.total_extractions
        return 1.0 - effort

# Target metrics for v3.0:
# - automation_rate >= 0.80 (80% fully automated)
# - full_auto_accuracy >= 0.98 (98% accuracy on auto-accepted)
# - human_effort_reduction >= 0.70 (70% less human work)
```

---

## PHASE 5: PRODUCTION DEPLOYMENT
**Goal:** Deployment-ready system
**Timeline:** Sprint 5-6

### 5.1 API Design

```python
# api/extractor.py
from fastapi import FastAPI, UploadFile
from pydantic import BaseModel

app = FastAPI(title="RCT Extractor API", version="3.0")

class ExtractionResult(BaseModel):
    effect_type: str
    effect_size: float
    ci_lower: float
    ci_upper: float
    p_value: Optional[float]
    confidence: float
    automation_tier: str
    provenance: dict

@app.post("/extract")
async def extract_from_pdf(file: UploadFile) -> List[ExtractionResult]:
    """
    Extract effect estimates from uploaded PDF
    """
    ...

@app.post("/extract/text")
async def extract_from_text(text: str) -> List[ExtractionResult]:
    """
    Extract effect estimates from text
    """
    ...

@app.get("/health")
async def health_check():
    """API health check"""
    return {"status": "healthy", "version": "3.0"}
```

### 5.2 Batch Processing

```python
class BatchExtractor:
    """
    Process multiple documents efficiently
    """

    def __init__(self, n_workers=4):
        self.n_workers = n_workers
        self.extractor = AutomatedExtractor()

    async def process_batch(self, documents: List[str]) -> List[ExtractionResult]:
        """
        Process documents in parallel
        """
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            results = list(executor.map(self.extractor.extract, documents))
        return results

    def process_systematic_review(self, included_studies: List[str]) -> DataFrame:
        """
        Process all included studies for a systematic review
        Returns DataFrame ready for meta-analysis
        """
        all_results = []

        for study in included_studies:
            extractions = self.extractor.extract_with_automation(study)

            for ext in extractions:
                all_results.append({
                    'study': study[:50],
                    'effect_type': ext['type'],
                    'effect_size': ext['effect_size'],
                    'ci_lower': ext['ci_lower'],
                    'ci_upper': ext['ci_upper'],
                    'se': self._calculate_se(ext),
                    'automation_tier': ext['automation_tier'],
                    'needs_review': ext['human_review_required'],
                })

        return pd.DataFrame(all_results)
```

### 5.3 Integration with Meta-Analysis Tools

```python
class MetaAnalysisExport:
    """
    Export extractions in formats for common MA tools
    """

    def to_revman(self, extractions: List[dict]) -> str:
        """Export for Cochrane RevMan"""
        ...

    def to_stata(self, extractions: List[dict]) -> str:
        """Export for Stata metan"""
        ...

    def to_r_meta(self, extractions: List[dict]) -> str:
        """Export for R meta/metafor packages"""
        ...

    def to_csv(self, extractions: List[dict]) -> str:
        """Generic CSV export"""
        ...
```

---

## IMPLEMENTATION ROADMAP

### Sprint 1: Pattern Expansion (Week 1-2)
- [ ] Analyze current miss patterns from external validation
- [ ] Add 50+ new pattern variants
- [ ] Create comprehensive pattern test suite (500+ cases)
- [ ] Target: Sensitivity 85%+

### Sprint 2: Validation Expansion (Week 3-4)
- [ ] Expand external validation to 100 trials
- [ ] Implement actual dual human extraction protocol
- [ ] Balance therapeutic areas and difficulty
- [ ] Target: 100 trials validated

### Sprint 3: Calibration V2 (Week 5-6)
- [ ] Implement multi-stage calibration
- [ ] Add isotonic regression
- [ ] Validate on held-out data
- [ ] Target: ECE < 0.10

### Sprint 4: Automation Framework (Week 7-8)
- [ ] Implement tiered automation system
- [ ] Add automation metrics dashboard
- [ ] Test on 50 new documents
- [ ] Target: 60% automation rate

### Sprint 5: Production Prep (Week 9-10)
- [ ] Expand to 200 trials external validation
- [ ] Final calibration tuning
- [ ] API implementation
- [ ] Target: ECE < 0.05, 80% automation

### Sprint 6: Deployment (Week 11-12)
- [ ] Batch processing implementation
- [ ] Meta-analysis tool integrations
- [ ] Documentation and user guides
- [ ] Target: Production release v3.0

---

## SUCCESS CRITERIA FOR v3.0

| Metric | Current (v2.16) | Target (v3.0) | Status |
|--------|-----------------|---------------|--------|
| Sensitivity | 72.7% | 95%+ | Pending |
| Specificity | 100% | 99%+ | On track |
| Precision | 100% | 98%+ | On track |
| ECE (Calibration) | 0.50 | <0.05 | Critical |
| External Validation N | 39 | 200+ | Pending |
| Automation Rate | 0% | 80%+ | Pending |
| Full-Auto Accuracy | N/A | 98%+ | Pending |
| Human Effort Reduction | 0% | 70%+ | Pending |

---

## RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Cannot achieve 95% sensitivity | Medium | High | Focus on highest-value patterns first |
| Calibration remains poor | Medium | High | Use conservative thresholds, more manual review |
| Insufficient validation data | Low | Medium | Partner with systematic review groups |
| False positives in production | Low | High | Mandatory verification tier for edge cases |

---

*Plan created: 2026-01-28*
*Target completion: v3.0 in 12 weeks*
