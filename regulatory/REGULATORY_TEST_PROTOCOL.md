# Regulatory Test Protocol
## IQ/OQ/PQ Test Specifications

**Protocol ID:** TP-RCT-2026-001
**Version:** 1.0
**System:** RCT Effect Estimate Extractor v4.0.3

---

## PART 1: INSTALLATION QUALIFICATION (IQ)

### IQ-001: Software Component Verification

**Objective:** Verify all required software components are installed correctly.

| Test ID | Component | Expected | Pass Criteria |
|---------|-----------|----------|---------------|
| IQ-001-01 | enhanced_extractor_v3.py | Present | File exists, size > 0 |
| IQ-001-02 | ocr_preprocessor.py | Present | File exists, size > 0 |
| IQ-001-03 | team_of_rivals.py | Present | File exists, size > 0 |
| IQ-001-04 | deterministic_verifier.py | Present | File exists, size > 0 |
| IQ-001-05 | verified_extraction_pipeline.py | Present | File exists, size > 0 |
| IQ-001-06 | proof_carrying_numbers.py | Present | File exists, size > 0 |

### IQ-002: Dependency Verification

| Test ID | Dependency | Required Version | Pass Criteria |
|---------|------------|------------------|---------------|
| IQ-002-01 | Python | ≥3.8 | Version check passes |
| IQ-002-02 | re (regex) | Built-in | Import succeeds |
| IQ-002-03 | dataclasses | Built-in | Import succeeds |
| IQ-002-04 | typing | Built-in | Import succeeds |
| IQ-002-05 | math | Built-in | Import succeeds |

### IQ-003: Configuration Verification

| Test ID | Configuration | Expected | Pass Criteria |
|---------|---------------|----------|---------------|
| IQ-003-01 | Pattern library loaded | All patterns | Count > 100 patterns |
| IQ-003-02 | Language support | 10 languages | Config shows 10 |
| IQ-003-03 | Effect types | 9+ types | Config shows ≥9 |

---

## PART 2: OPERATIONAL QUALIFICATION (OQ)

### OQ-001: Hazard Ratio Extraction

**Objective:** Verify correct extraction of hazard ratios in various formats.

| Test ID | Input | Expected Output | Pass Criteria |
|---------|-------|-----------------|---------------|
| OQ-001-01 | "HR 0.75 (95% CI 0.64-0.89)" | HR=0.75, CI=[0.64,0.89] | Exact match |
| OQ-001-02 | "hazard ratio 0.82 (0.71 to 0.95)" | HR=0.82, CI=[0.71,0.95] | Exact match |
| OQ-001-03 | "HR=0.68; 95% CI: 0.55, 0.84" | HR=0.68, CI=[0.55,0.84] | Exact match |
| OQ-001-04 | "adjusted HR 0.91 (95% CI 0.83-0.99)" | HR=0.91, CI=[0.83,0.99] | Exact match |
| OQ-001-05 | "The hazard ratio was 0.77 (CI 0.65-0.91)" | HR=0.77, CI=[0.65,0.91] | Exact match |
| OQ-001-06 | "(HR, 0.72; 95% CI, 0.61 to 0.85)" | HR=0.72, CI=[0.61,0.85] | Exact match |
| OQ-001-07 | "HR 1.23 [95% CI 1.05-1.44]" | HR=1.23, CI=[1.05,1.44] | Exact match |
| OQ-001-08 | "hazard ratio for death: 0.69 (0.58-0.82)" | HR=0.69, CI=[0.58,0.82] | Exact match |

### OQ-002: Odds Ratio Extraction

| Test ID | Input | Expected Output | Pass Criteria |
|---------|-------|-----------------|---------------|
| OQ-002-01 | "OR 1.45 (95% CI 1.12-1.88)" | OR=1.45, CI=[1.12,1.88] | Exact match |
| OQ-002-02 | "odds ratio 0.72 (0.58 to 0.89)" | OR=0.72, CI=[0.58,0.89] | Exact match |
| OQ-002-03 | "adjusted OR=2.15 (95% CI: 1.62, 2.85)" | OR=2.15, CI=[1.62,2.85] | Exact match |
| OQ-002-04 | "(OR 0.89, 95% CI 0.84 to 0.95)" | OR=0.89, CI=[0.84,0.95] | Exact match |
| OQ-002-05 | "OR: 1.56; 95% CI: 1.21-2.01" | OR=1.56, CI=[1.21,2.01] | Exact match |

### OQ-003: Risk Ratio Extraction

| Test ID | Input | Expected Output | Pass Criteria |
|---------|-------|-----------------|---------------|
| OQ-003-01 | "RR 0.81 (95% CI 0.70-0.94)" | RR=0.81, CI=[0.70,0.94] | Exact match |
| OQ-003-02 | "relative risk 0.65 (0.52 to 0.81)" | RR=0.65, CI=[0.52,0.81] | Exact match |
| OQ-003-03 | "risk ratio 0.77; 95% CI, 0.69 to 0.85" | RR=0.77, CI=[0.69,0.85] | Exact match |
| OQ-003-04 | "(RR 0.85, 95% CI 0.79-0.92)" | RR=0.85, CI=[0.79,0.92] | Exact match |

### OQ-004: Mean Difference Extraction

| Test ID | Input | Expected Output | Pass Criteria |
|---------|-------|-----------------|---------------|
| OQ-004-01 | "MD -3.2 (95% CI -4.1 to -2.3)" | MD=-3.2, CI=[-4.1,-2.3] | Exact match |
| OQ-004-02 | "mean difference 8.2 points (5.1 to 11.3)" | MD=8.2, CI=[5.1,11.3] | Exact match |
| OQ-004-03 | "MD -5.2 mmHg (95% CI -7.1 to -3.3)" | MD=-5.2, CI=[-7.1,-3.3] | Exact match |
| OQ-004-04 | "WMD -1.12% (95% CI -1.28 to -0.96)" | MD=-1.12, CI=[-1.28,-0.96] | Exact match |

### OQ-005: Standardized Mean Difference Extraction

| Test ID | Input | Expected Output | Pass Criteria |
|---------|-------|-----------------|---------------|
| OQ-005-01 | "SMD -0.62 (95% CI -0.81 to -0.42)" | SMD=-0.62, CI=[-0.81,-0.42] | Exact match |
| OQ-005-02 | "Cohen's d 0.45 (0.28-0.62)" | SMD=0.45, CI=[0.28,0.62] | Exact match |
| OQ-005-03 | "Hedges' g -0.35 (-0.52 to -0.18)" | SMD=-0.35, CI=[-0.52,-0.18] | Exact match |
| OQ-005-04 | "standardized mean difference -0.88; 95% CI -1.03 to -0.74" | SMD=-0.88, CI=[-1.03,-0.74] | Exact match |

### OQ-006: OCR Error Correction

| Test ID | Input (Degraded) | Expected Correction | Pass Criteria |
|---------|------------------|---------------------|---------------|
| OQ-006-01 | "HR O.74 (95% Cl O.6l-O.89)" | HR 0.74 (95% CI 0.61-0.89) | Extraction succeeds |
| OQ-006-02 | "OR l.56 (95% Cl l.2l-2.Ol)" | OR 1.56 (95% CI 1.21-2.01) | Extraction succeeds |
| OQ-006-03 | "RR O.8l (95% Cl O.7O-O.94)" | RR 0.81 (95% CI 0.70-0.94) | Extraction succeeds |
| OQ-006-04 | "p<O.OOl" | p<0.001 | Correction applied |

### OQ-007: Multi-Language Extraction

| Test ID | Language | Input | Pass Criteria |
|---------|----------|-------|---------------|
| OQ-007-01 | German | "Hazard Ratio 0,78 (95%-KI 0,65-0,94)" | Extraction succeeds |
| OQ-007-02 | French | "Rapport de cotes 1,45 (IC 95% 1,12-1,88)" | Extraction succeeds |
| OQ-007-03 | Spanish | "Razón de riesgo 0,81 (IC 95%: 0,69-0,95)" | Extraction succeeds |
| OQ-007-04 | Chinese | "风险比 0.72 (95% CI 0.58-0.89)" | Extraction succeeds |
| OQ-007-05 | Japanese | "ハザード比 0.68 (95% CI 0.55-0.84)" | Extraction succeeds |
| OQ-007-06 | Korean | "위험비 0.71 (95% CI 0.59-0.86)" | Extraction succeeds |

### OQ-008: Verification Layer

| Test ID | Scenario | Input | Expected Result |
|---------|----------|-------|-----------------|
| OQ-008-01 | Valid CI | HR 0.75 (0.64-0.89) | is_verified=True |
| OQ-008-02 | CI not containing point | HR 0.75 (0.80-0.95) | is_verified=False |
| OQ-008-03 | CI reversed | HR 0.75 (0.89-0.64) | is_verified=False |
| OQ-008-04 | Implausible HR | HR 50.0 (40-60) | Warning flagged |
| OQ-008-05 | Implausible SMD | SMD 10.0 (8-12) | Warning flagged |

### OQ-009: Negative Context Rejection

| Test ID | Input (Should NOT Extract) | Expected | Pass Criteria |
|---------|---------------------------|----------|---------------|
| OQ-009-01 | "assuming HR of 0.75" | No extraction | Nothing extracted |
| OQ-009-02 | "power calculation with OR 1.5" | No extraction | Nothing extracted |
| OQ-009-03 | "sample size to detect RR 0.80" | No extraction | Nothing extracted |
| OQ-009-04 | "previous study reported HR 0.82" | No extraction | Nothing extracted |
| OQ-009-05 | "if the HR is greater than 1.0" | No extraction | Nothing extracted |

---

## PART 3: PERFORMANCE QUALIFICATION (PQ)

### PQ-001: High-Volume Processing

| Test ID | Scenario | Volume | Pass Criteria |
|---------|----------|--------|---------------|
| PQ-001-01 | Single document | 1 | Completes < 1 sec |
| PQ-001-02 | Small batch | 100 | Completes < 30 sec |
| PQ-001-03 | Medium batch | 1,000 | Completes < 5 min |
| PQ-001-04 | Large batch | 10,000 | Completes < 30 min |

### PQ-002: Reproducibility

| Test ID | Scenario | Pass Criteria |
|---------|----------|---------------|
| PQ-002-01 | Same input, 100 runs | All outputs identical |
| PQ-002-02 | Different operator, same input | Output identical |
| PQ-002-03 | After system restart | Output identical |

### PQ-003: Stress Testing

| Test ID | Scenario | Pass Criteria |
|---------|----------|---------------|
| PQ-003-01 | Very long document (100KB) | Completes without error |
| PQ-003-02 | Multiple extractions in one doc | All extracted correctly |
| PQ-003-03 | Mixed languages in one doc | All extracted correctly |
| PQ-003-04 | Heavy OCR degradation | ≥90% extraction rate |

### PQ-004: Edge Case Validation

| Test ID | Edge Case | Pass Criteria |
|---------|-----------|---------------|
| PQ-004-01 | HR = 1.00 exactly | Extracted correctly |
| PQ-004-02 | Very small effect (HR 0.99) | Extracted correctly |
| PQ-004-03 | Very large effect (OR 15.0) | Extracted correctly |
| PQ-004-04 | Negative SMD (-2.5) | Extracted correctly |
| PQ-004-05 | Wide CI (0.10-2.50) | Extracted correctly |
| PQ-004-06 | Narrow CI (0.84-0.86) | Extracted correctly |
| PQ-004-07 | Three decimal places | Extracted correctly |

---

## TEST EXECUTION LOG

| Test ID | Date | Tester | Result | Notes |
|---------|------|--------|--------|-------|
| | | | | |
| | | | | |

---

## APPROVAL

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Test Lead | _________________ | _________________ | ________ |
| QA Review | _________________ | _________________ | ________ |
| Approval | _________________ | _________________ | ________ |
