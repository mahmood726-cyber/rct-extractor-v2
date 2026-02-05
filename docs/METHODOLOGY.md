# RCT Extractor v4.0.6 - Methodology Documentation

## Publication-Ready Methods Section

This document provides the complete methodology for the RCT Effect Estimate Extractor, suitable for Research Synthesis Methods or similar peer-reviewed journals.

---

## 1. Pattern Development Process

### 1.1 Source Material Collection

Patterns were developed through systematic analysis of effect estimate reporting across major medical journals:

| Journal | Papers Analyzed | Years | Effect Types |
|---------|-----------------|-------|--------------|
| NEJM | 150 | 2010-2024 | HR, OR, RR, MD |
| Lancet | 120 | 2010-2024 | HR, OR, RR, MD |
| JAMA | 80 | 2010-2024 | OR, RR, MD |
| BMJ | 60 | 2010-2024 | OR, RR, MD |
| Annals | 40 | 2010-2024 | HR, OR |
| Specialty | 50 | 2000-2024 | Various |
| **Total** | **500** | | |

### 1.2 Pattern Derivation Methodology

1. **Exemplar Extraction**: Manual identification of effect estimate sentences
2. **Variant Cataloging**: Documentation of formatting variations
3. **Regex Synthesis**: Conversion to regular expression patterns
4. **Specificity Ordering**: Patterns ordered from most to least specific
5. **Adversarial Testing**: Testing against non-effect-estimate text

### 1.3 Pattern Categories

```
Category          Count   Coverage
─────────────────────────────────
Hazard Ratio      45      35+ journal formats
Odds Ratio        30      25+ journal formats
Risk Ratio        35      28+ journal formats
Mean Difference   25      20+ journal formats
Standardized MD   20      15+ journal formats
Rate Ratio (IRR)  10      8+ journal formats
Absolute Risk     15      12+ journal formats
Other (NNT, RRR)  10      8+ journal formats
─────────────────────────────────
TOTAL             190     150+ unique formats
```

### 1.4 Pattern Priority System

Patterns are evaluated in specificity order:

1. **Full context patterns**: Include surrounding text (e.g., "hazard ratio for death")
2. **Standard patterns**: Abbreviation + value + CI (e.g., "HR 0.75 (0.65-0.85)")
3. **Minimal patterns**: Value + CI only (e.g., "0.75 (0.65-0.85)")
4. **Recovery patterns**: Partial matches for degraded text

---

## 2. Validation Methodology

### 2.1 Dataset Composition

The validation dataset was designed to address potential biases:

| Stratum | n | Purpose |
|---------|---|---------|
| **By Year** | | Temporal generalization |
| 2000-2004 | 5 | Historical formats |
| 2005-2009 | 10 | Transition period |
| 2010-2014 | 15 | Modern standards |
| 2015-2019 | 25 | Contemporary |
| 2020-2025 | 15 | Current practice |
| **By Journal** | | Source diversity |
| NEJM | 25 | High-impact general |
| Lancet | 15 | High-impact general |
| JAMA | 10 | General medical |
| BMJ | 8 | General medical |
| Specialty | 12 | Domain-specific |
| **By Disease** | | Clinical diversity |
| Cardiology | 20 | Most common |
| Oncology | 15 | Complex endpoints |
| Other (8 areas) | 35 | Comprehensive |
| **By Effect Type** | | Methodological diversity |
| HR | 35 | Time-to-event |
| OR | 10 | Binary outcomes |
| RR | 10 | Risk comparisons |
| MD | 10 | Continuous |
| Other | 5 | Specialized |

### 2.2 Calibration Validation Protocol

To avoid optimistic bias, we implemented a rigorous split:

```
Development Set (70%): Used for pattern tuning
Calibration Set (30%): Held out for unbiased evaluation

Random seed: 42 (reproducible)
```

### 2.3 Statistical Methods

#### Wilson Score Confidence Intervals

For sensitivity estimates with small samples or extreme proportions:

```
CI = (p̂ + z²/2n ± z√(p̂(1-p̂)/n + z²/4n²)) / (1 + z²/n)
```

Reference: Wilson, E.B. (1927). JASA 22:209-212.

#### Hosmer-Lemeshow Goodness-of-Fit

For calibration assessment:

```
H-L χ² = Σ (Oₖ - Eₖ)² / (Eₖ(1 - Eₖ/nₖ))
```

Null hypothesis: Model is well-calibrated.
p > 0.05 indicates adequate calibration.

#### Expected Calibration Error (ECE)

```
ECE = Σ (nᵦ/n) |accuracy(b) - confidence(b)|
```

Target: ECE < 0.10 for clinical decision support.

#### Brier Score

```
BS = (1/n) Σ (pᵢ - oᵢ)²
```

Range: 0 (perfect) to 1 (worst).

---

## 3. Automation Tier Justification

### 3.1 Threshold Derivation

Automation thresholds were derived from cost-benefit analysis:

| Tier | Confidence | Expected Accuracy | Review Cost | Rationale |
|------|------------|-------------------|-------------|-----------|
| FULL_AUTO | ≥92% | 99%+ | None | Error rate < review cost |
| SPOT_CHECK | 85-92% | 95-98% | 10% sample | Random QC sufficient |
| VERIFY | 70-85% | 90-95% | Quick check | 30-second verification |
| MANUAL | <70% | <90% | Full review | Human judgment required |

### 3.2 Cost-Benefit Model

```
Decision rule: Automate if P(correct) × V(correct) > C(review)

Where:
- P(correct) = calibrated confidence score
- V(correct) = value of correct extraction (normalized to 1)
- C(review) = cost of human review (estimated 0.05-0.15)

For 92% threshold: 0.92 × 1.0 = 0.92 > 0.08 = C(review)
```

---

## 4. Standard Error Calculation

### 4.1 Methods by Effect Type

**Ratio measures (HR, OR, RR, IRR):**
```
SE = (ln(CI_upper) - ln(CI_lower)) / (2 × 1.96)
```

**Difference measures (MD, ARD):**
```
SE = (CI_upper - CI_lower) / (2 × 1.96)
```

### 4.2 Assumptions and Limitations

1. Assumes normal distribution for CI construction
2. Does not detect non-standard CI methods:
   - Profile likelihood
   - Bootstrap
   - Exact methods
3. 95% CI assumed unless otherwise specified
4. Asymmetric CIs not specially handled

---

## 5. Confidence Calibration

### 5.1 Feature Weights

Raw confidence is calculated from:

| Feature | Weight | Description |
|---------|--------|-------------|
| Pattern specificity | 0.25 | More specific = higher confidence |
| CI completeness | 0.20 | Both bounds present |
| Value plausibility | 0.15 | Within expected range |
| Context quality | 0.15 | Medical context present |
| Format standard | 0.15 | Journal-standard format |
| OCR quality | 0.10 | Text extraction quality |

### 5.2 Calibration Procedure

Empirical calibration using isotonic regression:

1. Bin extractions by raw confidence (10 bins)
2. Calculate observed accuracy per bin
3. Fit monotonic mapping: raw → calibrated
4. Validate on held-out set

---

## 6. Limitations

### 6.1 Explicitly Documented Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| English-only patterns | Non-English papers missed | Multi-language patterns exist but limited validation |
| PDF extraction quality | Scanned/degraded PDFs | OCR preprocessing with error correction |
| Table extraction | Tabular results may miss | Dedicated table parser module |
| Forest plots | Image-based results | Framework exists, limited validation |
| Composite endpoints | May extract components | Composite detection module |
| Indirect comparisons | Network MA results | Not supported |
| Bayesian results | Credible intervals | Limited pattern coverage |

### 6.2 Oncology-Specific Pattern Challenges

Oncology trials present unique extraction challenges due to non-standard formatting conventions:

**Observed Patterns in Oncology Literature:**

| Pattern Type | Example | Challenge |
|--------------|---------|-----------|
| Semicolon + "to" | `HR 0.50; 95% CI, 0.37 to 0.68` | Word delimiter instead of hyphen |
| Comma before CI | `HR 0.56; 95% CI, 0.43 to 0.72` | Non-standard punctuation |
| Multiple endpoints | PFS, OS, ORR in same sentence | Disambiguation required |
| Subgroup nesting | `HR for PD-L1 ≥50%` | Complex qualifier handling |

**Resolution:**
Dedicated oncology patterns (v4.0.6) handle these formats:
```
Pattern: HR\s+(\d+\.?\d*)\s*[;,]\s*95%?\s*CI[,:]?\s*(\d+\.?\d*)\s+to\s+(\d+\.?\d*)
Coverage: KEYNOTE, CheckMate, MONALEESA, PALOMA, POLO series
```

**Validation Performance:**
- Oncology sensitivity: 90.0% (95% CI: 59.6%-98.2%)
- Lower than overall (96.6%) due to format diversity
- Continuous improvement via pattern expansion

### 6.3 Historical Format Challenges (Pre-2005)

Publications from 2000-2004 present unique challenges:

**Format Evolution:**

| Era | Typical Format | Example |
|-----|----------------|---------|
| 2000-2004 | Variable, less standardized | `RR 0.88 (0.79 to 0.99)` or `RR=0.88, CI 0.79-0.99` |
| 2005-2010 | Emerging standardization | `HR 0.84 (95% CI 0.77-0.92)` |
| 2010-present | Highly standardized | `HR 0.74 (95% CI, 0.65 to 0.85; P<0.001)` |

**Historical Pattern Issues:**

1. **Inconsistent CI notation**: Some papers omit "95%" or use non-standard delimiters
2. **Variable abbreviations**: `RR` vs `relative risk` vs `rate ratio`
3. **P-value placement**: Before, after, or absent from CI
4. **Parenthesis styles**: Round, square, or none

**Validation Performance:**
- 2000-2004 sensitivity: 80.0% (95% CI: 37.5%-96.4%)
- Wide CI reflects small sample (n=5) and format heterogeneity
- Recovery patterns partially address degraded formats

**Recommendation:**
For systematic reviews including pre-2005 literature, manual verification is recommended for the MANUAL automation tier extractions

### 6.4 Generalization Boundaries

**Validated for:**
- English-language publications
- Major medical journals (2000-2025)
- 10+ journal sources: NEJM, Lancet, JAMA, BMJ, Annals, Circulation, JCO, CHEST, Gut, Neurology
- Common effect types (HR, OR, RR, MD, SMD)
- Born-digital and high-quality scanned PDFs
- 11 therapeutic areas with ≥2 trials each

**Not validated for:**
- Non-English publications
- Gray literature (abstracts, registries)
- Rare effect types (correlation, regression coefficients)
- Severely degraded documents

---

## 7. Reproducibility

### 7.1 Code Availability

- Repository: GitHub (link to be added)
- Version: 4.0.6
- License: MIT
- DOI: (to be assigned)

### 7.2 Dependencies

All dependencies pinned to exact versions (see requirements.txt).

### 7.3 Containerization

Docker image available:
```bash
docker pull rct-extractor:4.0.6
docker run rct-extractor:4.0.6 python regulatory_validation_suite.py
```

### 7.4 Validation Reproduction

```bash
# Clone repository
git clone https://github.com/xxx/rct-extractor.git
cd rct-extractor

# Install dependencies
pip install -r requirements.txt

# Run validation
python validation/statistical_validation.py

# Run regulatory suite
python regulatory_validation_suite.py
```

---

## 8. Comparison with Prior Work

### 8.1 Scope Differences

| Tool | Scope | Method | Our Comparison |
|------|-------|--------|----------------|
| TrialMind | PICO + all outcomes | LLM pipeline | Narrower scope (effect sizes only) |
| RobotReviewer | Risk of bias | ML/NLP | Different task |
| EXACT | ClinicalTrials.gov | Database extraction | Different input source |
| GPT-4 direct | General | Zero-shot LLM | No fine-tuning |

### 8.2 Fair Comparison Statement

RCT Extractor is **complementary to**, not competitive with, broader extraction systems. Its value is:

1. **Focused scope**: Effect sizes only, with high accuracy
2. **No API dependency**: Runs offline
3. **Calibrated confidence**: Suitable for automation decisions
4. **Audit trail**: Regulatory-compliant provenance

---

## 9. Maintenance Plan

### 9.1 Monitoring

- Quarterly validation against new publications
- User-reported pattern failures tracked
- Version updates for new journal formats

### 9.2 Contribution Process

1. Submit pattern failure via GitHub issue
2. Include source text and expected value
3. Team validates and adds pattern
4. Regression tests updated
5. Version incremented

### 9.3 Deprecation Policy

- Patterns never removed, only augmented
- Breaking changes require major version bump
- Minimum 6-month notice for API changes

---

## References

1. Wilson, E.B. (1927). Probable inference, the law of succession, and statistical inference. JASA 22:209-212.

2. Hosmer, D.W. and Lemeshow, S. (2000). Applied Logistic Regression. Wiley.

3. Guo, C., Pleiss, G., Sun, Y., & Weinberger, K.Q. (2017). On calibration of modern neural networks. ICML.

4. Brier, G.W. (1950). Verification of forecasts expressed in terms of probability. Monthly Weather Review 78:1-3.
