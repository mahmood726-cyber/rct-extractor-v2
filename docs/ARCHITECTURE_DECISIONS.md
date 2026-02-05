# Architecture Decision Records (ADR)

## RCT Extractor v4.0.6

This document records the key architectural decisions made during development.

---

## ADR-001: Regex-Based Extraction vs. Machine Learning

### Status
Accepted

### Context
Effect estimate extraction could be approached with:
1. Rule-based regex patterns
2. Named Entity Recognition (NER) models
3. Large Language Models (LLMs)
4. Hybrid approaches

### Decision
**Primary: Regex-based patterns with optional ML validation**

### Rationale
1. **Determinism**: Same input always produces same output (critical for regulatory)
2. **Explainability**: Each extraction traceable to specific pattern
3. **No API dependency**: Works offline, no cost per extraction
4. **Speed**: Milliseconds per document vs. seconds for LLMs
5. **Maintenance**: Patterns easier to update than retrain models

### Consequences
- (+) Reproducible, auditable extractions
- (+) No external dependencies
- (+) Fast execution
- (-) Requires manual pattern development
- (-) May miss novel formats
- (-) Language-specific patterns needed

### Alternatives Considered
- **LLM-only**: Rejected due to non-determinism and API costs
- **NER models**: Rejected due to training data requirements
- **Hybrid with LLM fallback**: Considered for future version

---

## ADR-002: Confidence Calibration Method

### Status
Accepted

### Context
Automation decisions require calibrated confidence scores. Options:
1. Heuristic scoring
2. Platt scaling
3. Isotonic regression
4. Temperature scaling

### Decision
**Empirical binning with isotonic regression**

### Rationale
1. Binning matches our automation tier structure
2. Isotonic regression guarantees monotonicity
3. Empirical approach fits diverse pattern types
4. Simple to validate and interpret

### Consequences
- (+) Well-calibrated scores (ECE < 0.05)
- (+) Interpretable tier assignments
- (-) Requires held-out calibration set
- (-) May need recalibration for new domains

---

## ADR-003: Tiered Automation Framework

### Status
Accepted

### Context
Full automation risks errors; full manual review is expensive. Need graduated approach.

### Decision
**Four-tier system based on confidence thresholds**

| Tier | Threshold | Action |
|------|-----------|--------|
| FULL_AUTO | ≥92% | No review |
| SPOT_CHECK | 85-92% | 10% random sample |
| VERIFY | 70-85% | Quick verification |
| MANUAL | <70% | Full review |

### Rationale
1. Cost-benefit optimization
2. Matches real-world workflow
3. Thresholds validated empirically
4. Conservative for clinical applications

### Consequences
- (+) 97% automation rate at 99% accuracy
- (+) Clear workflow guidance
- (-) Threshold calibration domain-specific
- (-) Some false negatives at high thresholds

---

## ADR-004: Provenance Tracking

### Status
Accepted

### Context
Regulatory compliance (21 CFR Part 11) requires audit trails.

### Decision
**Full provenance tracking for every extraction**

Recorded for each extraction:
- Source text (character positions)
- Pattern that matched
- Raw and calibrated confidence
- Timestamp
- Extractor version

### Rationale
1. Regulatory requirement for FDA submissions
2. Debugging and error analysis
3. Reproducibility verification
4. Quality improvement tracking

### Consequences
- (+) Full audit trail
- (+) Debugging capability
- (-) Increased storage requirements
- (-) Slight performance overhead

---

## ADR-005: Multi-Extractor Ensemble

### Status
Accepted

### Context
Single extractor may have blind spots. Ensemble could improve coverage.

### Decision
**"Team of Rivals" approach with 4 extractors**

1. Primary enhanced extractor (patterns)
2. Continuous outcome extractor
3. Specialty-specific extractors
4. ML validation layer

### Rationale
1. Different extractors catch different patterns
2. Consensus voting improves confidence
3. Disagreement flags uncertain cases
4. Redundancy for critical applications

### Consequences
- (+) Higher sensitivity
- (+) Built-in uncertainty detection
- (-) Increased complexity
- (-) Conflict resolution needed

---

## ADR-006: PDF Processing Pipeline

### Status
Accepted

### Context
PDFs vary widely in quality and structure.

### Decision
**Multi-stage pipeline with fallbacks**

```
PDF → pdfplumber → text extraction
  ├── Success → pattern matching
  └── Failure → PyMuPDF fallback
        ├── Success → pattern matching
        └── Failure → OCR (Tesseract)
              └── preprocessing → pattern matching
```

### Rationale
1. pdfplumber handles most born-digital PDFs
2. PyMuPDF catches edge cases
3. OCR necessary for scanned documents
4. Preprocessing improves OCR quality

### Consequences
- (+) Handles diverse PDF types
- (+) Graceful degradation
- (-) OCR significantly slower
- (-) OCR quality affects accuracy

---

## ADR-007: Pattern Ordering Strategy

### Status
Accepted

### Context
Multiple patterns may match the same text. Order affects results.

### Decision
**Specificity-ordered pattern matching**

Order: Most specific → Least specific
- Full context patterns first
- Abbreviation patterns second
- Minimal patterns last
- Recovery patterns as fallback

### Rationale
1. More specific matches are more reliable
2. Prevents spurious matches from generic patterns
3. Recovery patterns catch degraded text
4. Deterministic ordering for reproducibility

### Consequences
- (+) Higher precision
- (+) Predictable behavior
- (-) Pattern order maintenance burden
- (-) New patterns must be correctly positioned

---

## ADR-008: Standard Error Calculation

### Status
Accepted

### Context
Meta-analysis requires standard errors, often not reported.

### Decision
**Calculate SE from CI using normal approximation**

For ratios: `SE = (ln(upper) - ln(lower)) / (2 × 1.96)`
For differences: `SE = (upper - lower) / (2 × 1.96)`

### Rationale
1. Most CIs use normal approximation
2. Simple, widely understood method
3. Matches meta-analysis software expectations
4. Documented limitation for non-normal CIs

### Consequences
- (+) SE available for all extractions
- (+) Compatible with meta-analysis tools
- (-) Assumes normal CI construction
- (-) May be inaccurate for small samples

---

## ADR-009: OCR Error Correction

### Status
Accepted

### Context
OCR introduces systematic errors (O→0, l→1, etc.).

### Decision
**Rule-based correction with validation**

Corrections applied:
- `Cl` → `CI` (confidence interval)
- `O.xx` → `0.xx` (leading zero)
- `l.xx` → `1.xx` (one)
- Unicode normalization (dashes, dots)

### Rationale
1. Systematic errors are predictable
2. Corrections validated against expected patterns
3. Original text preserved for audit
4. Improves extraction from scanned documents

### Consequences
- (+) +15% accuracy on scanned PDFs
- (+) Traceable corrections
- (-) Risk of over-correction
- (-) Language-specific rules needed

---

## ADR-010: Validation Dataset Design

### Status
Accepted (v4.0.6)

### Context
Validation set design affects generalization claims.

### Decision
**Stratified validation with held-out calibration**

Stratification:
- Publication year (5-year blocks)
- Journal source (5+ journals)
- Therapeutic area (10+ areas)
- Effect type (8 types)

Split: 70% development, 30% calibration

### Rationale
1. Addresses editorial concerns about bias
2. Temporal validation for generalization
3. Held-out set for unbiased calibration
4. Comprehensive coverage

### Consequences
- (+) Unbiased performance estimates
- (+) Generalization evidence
- (-) Reduced development set size
- (-) More complex validation process

---

## Decision Log

| ADR | Date | Status | Author |
|-----|------|--------|--------|
| 001 | 2024-01 | Accepted | Core Team |
| 002 | 2024-01 | Accepted | Core Team |
| 003 | 2024-01 | Accepted | Core Team |
| 004 | 2024-01 | Accepted | Core Team |
| 005 | 2024-02 | Accepted | Core Team |
| 006 | 2024-02 | Accepted | Core Team |
| 007 | 2024-03 | Accepted | Core Team |
| 008 | 2024-03 | Accepted | Core Team |
| 009 | 2024-06 | Accepted | Core Team |
| 010 | 2026-01 | Accepted | v4.0.6 |
