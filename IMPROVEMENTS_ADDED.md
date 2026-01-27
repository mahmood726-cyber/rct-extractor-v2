# Improvements Added to RCT Extractor v2

**Date:** 2026-01-26

These improvements were ported from:
1. **TruthCert-Validation-Papers** - Ensemble merging and value validation
2. **Wasserstein Project** - Survival curve analysis and IPD reconstruction

## 1. OutcomeTextMatcher (New Class)

**File:** `src/core/ensemble.py`

Matches outcome text between different extraction sources to improve endpoint matching accuracy.

### Features:
- Keyword-based outcome type detection (OS, PFS, DFS, MACE, etc.)
- Jaccard similarity fallback for unknown outcomes
- Handles both oncology and cardiology endpoints

### Usage:
```python
from src.core.ensemble import OutcomeTextMatcher

# Detect outcome type
outcome_type = OutcomeTextMatcher.extract_outcome_type("overall survival")
# Returns: 'os'

# Match two outcomes
score = OutcomeTextMatcher.outcomes_match(
    "overall survival in ITT population",
    "OS primary endpoint"
)
# Returns: 1.0 (exact match)
```

## 2. ValueValidator (New Class)

**File:** `src/core/ensemble.py`

Validates extracted effect measure values for plausibility.

### Features:
- Filters implausible values (HR > 15 or < 0.05)
- Adjusts confidence for unusual but valid values
- Detects potential measure type misclassification (HR vs OR)

### Plausibility Ranges:
| Measure | Plausible Range | Typical Range |
|---------|-----------------|---------------|
| HR | 0.05 - 15.0 | 0.3 - 3.0 |
| RR | 0.05 - 15.0 | 0.3 - 3.0 |
| OR | 0.02 - 50.0 | 0.3 - 5.0 |

### Usage:
```python
from src.core.ensemble import ValueValidator

plausible, confidence = ValueValidator.is_plausible(
    value=0.75,
    ci_low=0.65,
    ci_high=0.87,
    measure_type="HR"
)
# Returns: (True, 1.0)

# Unusual value gets reduced confidence
plausible, confidence = ValueValidator.is_plausible(5.0, 3.0, 8.0, "HR")
# Returns: (True, 0.7)

# Implausible value is rejected
plausible, confidence = ValueValidator.is_plausible(100.0, 50.0, 200.0, "HR")
# Returns: (False, 0.0)
```

## 3. Enhanced EnsembleMerger

**File:** `src/core/ensemble.py`

### New Parameters:
```python
merger = EnsembleMerger(
    agreement_tolerance=0.02,
    prefer_verified=True,
    use_outcome_matching=True,   # NEW: Use OutcomeTextMatcher
    filter_implausible=True      # NEW: Filter implausible values
)
```

### New Methods:
- `_filter_implausible()`: Removes implausible values before merging
- `_find_best_endpoint_match()`: Uses outcome text to find matching groups

### Improved Matching:
- `values_agree_with_outcome()`: Adaptive CI tolerance based on outcome match
  - If outcomes clearly match: more lenient CI tolerance (1.5x)
  - If outcomes clearly mismatch: reject even if values close

## 4. New Validators

**File:** `src/validators/validators.py`

### HR Plausibility Check:
Added to `validate_hazard_ratio()`:
- WARNING if HR < 0.1 or HR > 10.0 (implausible)
- INFO if HR < 0.3 or HR > 3.0 (unusual)

### Measure Type Detection:
New function `validate_measure_type()`:
- Detects when large HR values (>3) might be misclassified ORs
- Uses context keywords (hazard, survival vs odds, logistic)

## 5. ExtractorResult Changes

**File:** `src/core/ensemble.py`

Added new fields to `ExtractorResult`:
```python
@dataclass
class ExtractorResult:
    # ... existing fields ...

    # NEW fields
    outcome_text: Optional[str] = None  # Full outcome description
    is_primary: bool = False            # Is this a primary endpoint?
```

## Impact

These improvements address key failure patterns identified in validation:

| Issue | Solution | Impact |
|-------|----------|--------|
| CI mismatches (14 cases) | Adaptive CI tolerance | Better matching |
| Unusual HR values (7 cases) | ValueValidator filtering | Fewer false positives |
| Endpoint mismatch | OutcomeTextMatcher | Correct subgroup identification |
| Large HR may be OR | Measure type detection | Early warning |

## Testing

Run the test suite:
```bash
cd C:/Users/user/rct-extractor-v2
python -m pytest tests/ -v
```

Quick validation:
```python
from src.core.ensemble import EnsembleMerger, ExtractorResult, OutcomeTextMatcher, ValueValidator

# Test outcome matching
assert OutcomeTextMatcher.extract_outcome_type('overall survival') == 'os'

# Test value validation
plausible, conf = ValueValidator.is_plausible(0.75, 0.65, 0.87, 'HR')
assert plausible and conf == 1.0

# Test merger with filtering
merger = EnsembleMerger(filter_implausible=True)
```
