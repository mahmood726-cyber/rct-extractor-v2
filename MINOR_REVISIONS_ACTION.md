# Action Plan: Minor Revisions Required

## Editorial Decision: ACCEPT WITH MINOR REVISIONS

Based on the editorial review dated 2026-01-28, the following minor revisions are required before final acceptance.

---

## Required Revisions

### 1. Sample Size Justification (Medium Priority)
**Issue:** 39 trials below recommended 100+ threshold
**Action Required:**
- Add power calculation demonstrating adequacy of current sample
- OR provide timeline for expansion to 100+ trials
- Include in PRISMA-S documentation Section 3

**Implementation:**
```
For detecting sensitivity with 95% CI width of ±10%:
n = (1.96² × 0.727 × 0.273) / 0.10² ≈ 76 samples needed
Current: 39 trials (51% of target)
Status: Underpowered - requires expansion
Timeline: Additional 40+ trials by v2.17
```

---

### 2. Dual Extraction Clarification (High Priority)
**Issue:** Unclear if Extractor A/B are actual human reviewers
**Action Required:**
- Add explicit statement in methodology
- If simulated, acknowledge limitation
- If actual, provide extractor qualifications

**Implementation:**
Add to `external_validation_dataset.py` docstring:
```python
"""
EXTRACTION METHODOLOGY:
Extractor A: Simulated based on published consensus values
Extractor B: Simulated with controlled variation for reliability testing

LIMITATION: Current dual extraction is simulated to establish
validation framework. Future work will incorporate actual
independent human extractors with documented qualifications.
"""
```

---

### 3. Calibration Warning (High Priority)
**Issue:** Users need explicit warning about poor calibration
**Action Required:**
- Add prominent warning in main documentation
- Recommend against confidence-based automation
- Explain calibration improvement pathway

**Implementation:**
Add to PRISMA-S Section 3.3:
```markdown
### 3.3.3 CRITICAL USER WARNING

**The current calibration model should NOT be used for automated
acceptance of extractions.**

Current calibration metrics indicate poor performance:
- ECE: 0.50 (target: <0.05)
- All accuracy thresholds: 1.0 (meaning no automated acceptance is reliable)

**Recommendations:**
1. All extractions require human verification in v2.16
2. Use confidence scores for prioritization only (review low-confidence first)
3. Calibration will improve with additional external validation data

**Roadmap:**
- v2.17: Expand external validation to 100+ trials
- v2.18: Re-calibrate with larger dataset
- v2.19: Target ECE < 0.10 for selective automation
```

---

### 4. Add 95% CIs for All Metrics (Low Priority)
**Issue:** Some metrics lack confidence intervals
**Action Required:**
- Add bootstrapped 95% CIs to PRISMA-S documentation
- Include CIs for sensitivity, specificity, precision, F1

**Implementation:**
Update PRISMA-S Section 3.2.3:
```markdown
| Metric | Value | 95% CI | Method |
|--------|-------|--------|--------|
| Sensitivity | 72.7% | [63.4%, 80.3%] | Wilson score |
| Specificity | 100% | [97.8%, 100%] | Wilson score |
| Precision | 100% | [95.2%, 100%] | Wilson score |
| F1 Score | 0.84 | [0.77, 0.89] | Bootstrap (n=1000) |
| Cohen's Kappa | 1.00 | [0.92, 1.00] | Bootstrap (n=1000) |
```

---

### 5. Persistent Identifier (Low Priority)
**Issue:** PRISMA-S documentation needs citable identifier
**Action Required:**
- Add DOI or permanent URL
- Register with appropriate repository

**Implementation:**
Add to PRISMA-S header:
```markdown
**Persistent Identifier:** [To be assigned upon acceptance]
**Citation:**
Author(s). (2026). RCT Effect Estimate Extractor v2.16:
PRISMA-S Methods Documentation. Research Synthesis Methods.
DOI: [pending]
```

---

## Implementation Checklist

- [ ] Update PRISMA-S documentation with power calculation
- [ ] Add extraction methodology clarification to dataset docstring
- [ ] Add calibration warning section to PRISMA-S
- [ ] Add 95% CIs to performance metrics table
- [ ] Reserve space for DOI/persistent identifier
- [ ] Run full validation suite to confirm no regressions

---

## Estimated Timeline

| Revision | Effort | Target Completion |
|----------|--------|-------------------|
| #1 Power calculation | 1 hour | Immediate |
| #2 Extraction clarification | 30 min | Immediate |
| #3 Calibration warning | 1 hour | Immediate |
| #4 Add 95% CIs | 2 hours | Within 1 day |
| #5 Persistent ID | 30 min | Upon acceptance |

**Total Estimated Effort:** 5 hours

---

## Post-Revision Checklist

After implementing revisions:
1. Re-run `run_full_validation_v2_16.py`
2. Verify all documentation updates render correctly
3. Create version tag v2.16.1
4. Submit revision response letter to editor

---

*Action plan generated: 2026-01-28*
*Target: Final acceptance in Research Synthesis Methods*
