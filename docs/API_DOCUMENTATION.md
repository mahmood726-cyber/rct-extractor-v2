# RCT Extractor v3.0 - API Documentation

## Overview

The RCT Extractor provides automated extraction of effect estimates from clinical trial text with calibrated confidence scores and automation tier recommendations.

---

## Core Classes

### EnhancedExtractor

Main extraction class with comprehensive pattern library.

```python
from enhanced_extractor_v3 import EnhancedExtractor

extractor = EnhancedExtractor()
extractions = extractor.extract(text)
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `extract(text)` | `text: str` | `List[Extraction]` | Extract all effect estimates from text |

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `FULL_AUTO_THRESHOLD` | `float` | Confidence threshold for full automation (0.92) |
| `SPOT_CHECK_THRESHOLD` | `float` | Threshold for spot check tier (0.85) |
| `VERIFY_THRESHOLD` | `float` | Threshold for verification tier (0.70) |

---

### Extraction

Dataclass representing a single extracted effect estimate.

```python
@dataclass
class Extraction:
    effect_type: EffectType
    point_estimate: float
    ci: Optional[ConfidenceInterval]
    p_value: Optional[float]
    standard_error: Optional[float]
    se_method: str
    source_text: str
    char_start: int
    char_end: int
    raw_confidence: float
    calibrated_confidence: float
    automation_tier: AutomationTier
    has_complete_ci: bool
    is_plausible: bool
    warnings: List[str]
    original_scale: str  # For ARD only
    normalized_value: Optional[float]  # For ARD only
    normalized_ci_lower: Optional[float]
    normalized_ci_upper: Optional[float]
```

---

### EffectType

Enum of supported effect estimate types.

```python
class EffectType(Enum):
    HR = "HR"    # Hazard Ratio
    OR = "OR"    # Odds Ratio
    RR = "RR"    # Risk Ratio
    IRR = "IRR"  # Incidence Rate Ratio
    ARD = "ARD"  # Absolute Risk Difference
    ARR = "ARR"  # Absolute Risk Reduction
    RRR = "RRR"  # Relative Risk Reduction
    NNT = "NNT"  # Number Needed to Treat
    NNH = "NNH"  # Number Needed to Harm
    MD = "MD"    # Mean Difference
    SMD = "SMD"  # Standardized Mean Difference
    WMD = "WMD"  # Weighted Mean Difference
```

---

### AutomationTier

Enum for automation confidence tiers.

```python
class AutomationTier(Enum):
    FULL_AUTO = "full_auto"    # No review needed (≥92% confidence)
    SPOT_CHECK = "spot_check"  # Random 10% sampling (85-92%)
    VERIFY = "verify"          # Quick verification (70-85%)
    MANUAL = "manual"          # Full manual review (<70%)
```

---

### ConfidenceInterval

Dataclass for confidence interval data.

```python
@dataclass
class ConfidenceInterval:
    lower: float
    upper: float
    level: float = 0.95
    method: str = ""
```

---

## Utility Functions

### to_dict

Convert Extraction to dictionary format.

```python
from enhanced_extractor_v3 import to_dict

result = to_dict(extraction)
```

**Returns:**
```python
{
    'type': str,                    # Effect type (HR, OR, etc.)
    'effect_size': float,           # Point estimate
    'ci_lower': float,              # CI lower bound
    'ci_upper': float,              # CI upper bound
    'p_value': Optional[float],     # P-value if extracted
    'standard_error': float,        # Calculated SE
    'se_method': str,               # SE calculation method
    'raw_confidence': float,        # Raw confidence score
    'calibrated_confidence': float, # Calibrated confidence
    'automation_tier': str,         # Automation recommendation
    'source_text': str,             # Original matched text
    'char_start': int,              # Start position in text
    'char_end': int,                # End position in text
    'is_plausible': bool,           # Plausibility check result
    'warnings': List[str],          # Any warnings
    'needs_review': bool,           # True if not FULL_AUTO
    # ARD-specific fields:
    'original_scale': str,          # "percentage" or "decimal"
    'normalized_value': float,      # Normalized to decimal
    'normalized_ci_lower': float,
    'normalized_ci_upper': float,
}
```

---

### calculate_se_from_ci

Calculate standard error from confidence interval.

```python
from enhanced_extractor_v3 import calculate_se_from_ci

se, method = calculate_se_from_ci(ci_lower, ci_upper, effect_type)
```

**Parameters:**
- `ci_lower: float` - Lower bound of CI
- `ci_upper: float` - Upper bound of CI
- `effect_type: EffectType` - Type of effect estimate
- `ci_level: float = 0.95` - Confidence level (default 95%)

**Returns:**
- `Tuple[float, str]` - (standard_error, method)

**Methods:**
- `"calculated_log_scale"` - For ratios (HR, OR, RR)
- `"calculated_linear_scale"` - For differences (MD, SMD, ARD)

---

### normalize_ard

Normalize ARD values to decimal scale.

```python
from enhanced_extractor_v3 import normalize_ard

value, ci_low, ci_high, scale = normalize_ard(value, ci_low, ci_high, source_text)
```

**Parameters:**
- `value: float` - ARD point estimate
- `ci_low: float` - CI lower bound
- `ci_high: float` - CI upper bound
- `source_text: str` - Original text for format detection

**Returns:**
- `Tuple[float, float, float, str]` - (normalized_value, normalized_ci_low, normalized_ci_high, original_scale)

---

### correct_ocr_errors

Correct common OCR errors in text.

```python
from enhanced_extractor_v3 import correct_ocr_errors

corrected = correct_ocr_errors(text)
```

**Corrections Applied:**
- `Cl` → `CI`
- `O` → `0` (in numeric contexts)
- `l` → `1` (in numeric contexts)

---

### calculate_calibration_metrics

Calculate calibration metrics for confidence evaluation.

```python
from enhanced_extractor_v3 import calculate_calibration_metrics

metrics = calculate_calibration_metrics(predictions, actuals, n_bins=10)
```

**Parameters:**
- `predictions: List[float]` - Predicted probabilities
- `actuals: List[bool]` - Actual outcomes (True if correct)
- `n_bins: int = 10` - Number of bins for ECE/MCE

**Returns:** `CalibrationMetrics` dataclass with:
- `ece: float` - Expected Calibration Error
- `mce: float` - Maximum Calibration Error
- `brier_score: float` - Brier Score
- `calibration_slope: float`
- `calibration_intercept: float`
- `bin_accuracies: List[float]`
- `bin_confidences: List[float]`
- `bin_counts: List[int]`

---

### calculate_automation_metrics

Calculate automation tier statistics.

```python
from enhanced_extractor_v3 import calculate_automation_metrics

metrics = calculate_automation_metrics(extractions)
```

**Returns:** `AutomationMetrics` dataclass with:
- `total: int` - Total extractions
- `full_auto: int` - Count in FULL_AUTO tier
- `spot_check: int` - Count in SPOT_CHECK tier
- `verify: int` - Count in VERIFY tier
- `manual: int` - Count in MANUAL tier
- `automation_rate: float` - Percentage fully automated
- `human_effort_reduction: float` - Weighted effort reduction

---

## Usage Examples

### Basic Extraction

```python
from enhanced_extractor_v3 import EnhancedExtractor, to_dict

extractor = EnhancedExtractor()

text = """
The primary endpoint showed a hazard ratio of 0.74
(95% CI 0.65-0.85, P<0.001) favoring treatment.
"""

extractions = extractor.extract(text)

for ext in extractions:
    result = to_dict(ext)
    print(f"Found {result['type']}: {result['effect_size']}")
    print(f"  CI: [{result['ci_lower']}, {result['ci_upper']}]")
    print(f"  SE: {result['standard_error']:.4f}")
    print(f"  Confidence: {result['calibrated_confidence']:.2%}")
    print(f"  Tier: {result['automation_tier']}")
```

### Batch Processing

```python
def process_abstracts(abstracts: List[str]) -> List[dict]:
    extractor = EnhancedExtractor()
    results = []

    for abstract in abstracts:
        extractions = extractor.extract(abstract)
        for ext in extractions:
            result = to_dict(ext)
            if result['automation_tier'] == 'full_auto':
                results.append(result)
            else:
                # Queue for manual review
                queue_for_review(result)

    return results
```

### With OCR Correction

```python
from enhanced_extractor_v3 import EnhancedExtractor, correct_ocr_errors

extractor = EnhancedExtractor()

# OCR text with errors
ocr_text = "HR O.74 (95% Cl O.65-O.85)"

# Correct errors first
corrected = correct_ocr_errors(ocr_text)
# Result: "HR 0.74 (95% CI 0.65-0.85)"

extractions = extractor.extract(corrected)
```

### Calibration Assessment

```python
from enhanced_extractor_v3 import (
    EnhancedExtractor,
    calculate_calibration_metrics,
    generate_reliability_diagram_data
)

# After running validation
predictions = [ext.calibrated_confidence for ext in all_extractions]
actuals = [is_correct(ext) for ext in all_extractions]

metrics = calculate_calibration_metrics(predictions, actuals)

print(f"ECE: {metrics.ece:.4f}")
print(f"MCE: {metrics.mce:.4f}")
print(f"Brier: {metrics.brier_score:.4f}")

# Generate reliability diagram data
diagram_data = generate_reliability_diagram_data(metrics)
```

---

## Error Handling

The extractor handles errors gracefully:

```python
# Invalid text returns empty list
extractions = extractor.extract("")  # Returns []
extractions = extractor.extract(None)  # Returns []

# Malformed patterns are skipped
text = "HR 0.74 (95% CI incomplete"  # No extraction

# Implausible values are flagged
text = "HR 999.99 (95% CI 0.01-0.02)"
# Extraction has is_plausible=False, warnings=["IMPLAUSIBLE_VALUE"]
```

---

## Performance

Typical performance characteristics:

| Operation | Time | Memory |
|-----------|------|--------|
| Single extraction | <10ms | <1MB |
| 1000 abstracts | ~5s | ~50MB |
| Pattern compilation | ~100ms (once) | ~10MB |

---

*API Documentation v3.0*
*Date: 2026-01-28*
