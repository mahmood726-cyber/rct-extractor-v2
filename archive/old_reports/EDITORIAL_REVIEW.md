# Editorial Review: RCT Extractor v2.15

**Journal:** Research Synthesis Methods
**Manuscript Type:** Software/Methods Paper
**Review Date:** 2026-01-28
**Reviewer:** Editor-in-Chief (Simulated)

---

## Executive Summary

RCT Extractor v2.15 represents a substantial contribution to automated data extraction for systematic reviews and meta-analyses. The tool demonstrates impressive accuracy (100% on 1,118 test cases) and addresses several critical methodological challenges in evidence synthesis. However, several areas require attention before the tool can be recommended for production use in high-stakes systematic reviews.

**Recommendation:** Major Revision Required

---

## Strengths

### 1. Comprehensive Effect Measure Support (Excellent)

The tool correctly handles 14 effect measure types:
- Ratio measures: HR, OR, RR, IRR, sHR, csHR
- Difference measures: MD, SMD, RD
- Novel measures: Win Ratio, RMST, DOR, LR, correlation

This coverage exceeds most commercial tools (e.g., Covidence, DistillerSR) and addresses the needs of modern clinical trials using composite endpoints and competing risks frameworks.

### 2. SE/SD Confusion Detection (Innovative)

The implementation of CV-based heuristics to detect SE misreported as SD directly addresses the most common error in published meta-analyses (Gøtzsche et al., 2007; IntHout et al., 2016). The biomarker-specific CV ranges are well-calibrated:

```
LDL-C: CV 0.15-0.40
HbA1c: CV 0.08-0.20
eGFR: CV 0.20-0.40
```

**Recommendation:** Publish the CV reference ranges as supplementary material for community validation.

### 3. Composite Endpoint Standardization (Novel)

The MACE/MAKE/HF-COMPOSITE definitions align with FDA and EMA guidance. The component standardization mapping (40+ synonyms) addresses a significant pain point in cardiovascular meta-analyses where endpoint definitions vary across trials.

### 4. Cross-Paper Validation (Important)

Detection of value mismatches across publications reporting the same trial (e.g., ATTR-ACT in NEJM vs. EHJ) is a valuable quality control feature that most extraction tools lack.

### 5. Rigorous Testing

The 1,118 test cases across 9 validation suites demonstrate thorough coverage:
- Real clinical trials (32 gold standard)
- R package datasets (metafor, meta, netmeta)
- Adversarial edge cases
- Multi-language journal formats

---

## Critical Concerns

### 1. External Validation Gap (Major)

**Issue:** All validation is against curated test cases, not prospectively collected real-world PDFs.

**Evidence:**
- Gold standard dataset uses simplified text generation, not actual PDF parsing
- No inter-rater reliability assessment for gold standard curation
- No comparison with manual extraction by trained reviewers

**Required:**
1. Prospective validation on 100+ PDFs with dual manual extraction
2. Bland-Altman plots comparing automated vs. manual extraction
3. Inter-rater reliability (Cohen's kappa) for gold standard curation
4. Sensitivity/specificity by effect type and journal source

### 2. Training Data Circularity (Major)

**Issue:** The ML classifier is trained and tested on similar synthetic patterns.

**Evidence:**
```python
# Training data generation
text = f"{effect.effect_type} {effect.value} (95% CI {effect.ci_lower}-{effect.ci_upper})"
```

This creates patterns like "HR 0.75 (95% CI 0.63-0.89)" which are then tested with similar patterns. Real PDFs contain:
- Tables with merged cells
- Forest plots without text
- Multi-column layouts
- OCR errors from scanned documents

**Required:**
1. Separate training/test split with stratification
2. Include negative examples in training (text that looks like effects but isn't)
3. Test on raw PDF text with OCR artifacts

### 3. Confidence Calibration (Major)

**Issue:** Confidence scores are not empirically calibrated.

**Current Implementation:**
```python
# Weighted combination with arbitrary weights
weighted_score = pattern_score * 0.3 + plausibility_score * 0.25 +
                 context_score * 0.25 + ci_score * 0.2
```

A confidence of 0.8 should mean the extraction is correct 80% of the time. Without calibration:
- Users cannot make informed decisions about which extractions to verify
- Systematic over/under-confidence may introduce bias

**Required:**
1. Calibration plots (predicted probability vs. observed accuracy)
2. Empirical threshold selection (e.g., 0.7 = 95% accuracy)
3. Expected calibration error (ECE) metric

### 4. Missing Extraction Metadata (Moderate)

**Issue:** Extracted effects lack provenance information.

**Not Captured:**
- Page number and location in PDF
- Surrounding context (3-5 sentences)
- Table/figure reference
- Comparison arms (treatment vs. control names)
- Analysis population (ITT, per-protocol, mITT)
- Timepoint (if multiple reported)

**Required:**
1. Capture source location for audit trail
2. Extract comparison arm labels
3. Flag ITT vs. per-protocol analysis

### 5. Subgroup Analysis Handling (Moderate)

**Issue:** Subgroup effects may be extracted without context.

**Risk:** Including subgroup analyses in a meta-analysis as if they were primary results:
- Inflates heterogeneity
- Introduces selection bias
- Violates pre-specification

**Required:**
1. Flag subgroup analyses explicitly
2. Capture pre-specification status if stated
3. Extract interaction p-values

### 6. Limited Multi-Language Support (Moderate)

**Issue:** Testing focused on English-language patterns.

**Evidence:** NEJM, Lancet, JAMA, BMJ formats are well-covered, but:
- No German, French, Spanish, Portuguese patterns
- No Chinese/Japanese character handling
- European number formats (comma as decimal) not consistently handled

**Required:**
1. Expand test suite to non-English journals
2. Handle locale-specific number formats

---

## Methodological Recommendations

### 1. PRISMA-S Compliance

Automated extraction tools should report:
- Extraction algorithm description (PRISMA-S Item 15)
- Validation methodology (PRISMA-S Item 16)
- Limitations and failure modes

### 2. PROBAST Assessment

For ML components, report:
- Risk of bias in participant selection (training data representativeness)
- Risk of bias in predictors (feature leakage)
- Risk of bias in outcome (gold standard quality)
- Applicability concerns

### 3. Uncertainty Quantification

Consider Bayesian approaches:
- Posterior predictive intervals for extracted values
- Model uncertainty vs. data uncertainty
- Ensemble disagreement as uncertainty signal

### 4. Reproducibility

**Positive:** Dependencies are well-documented (sklearn, numpy)

**Needed:**
- Fixed random seeds for all stochastic components
- Version pinning for dependencies
- Docker container for exact reproduction

---

## Feature Recommendations

### High Priority

1. **PDF Coordinate Extraction**
   - Return bounding boxes for extracted values
   - Enable visual verification in PDF viewers

2. **Network Meta-Analysis Support**
   - Multi-arm trial correlation structure
   - Contrast matrix generation
   - Treatment code standardization

3. **Risk of Bias Integration**
   - Extract RoB 2.0 domain judgments if present
   - Flag high-risk trials for sensitivity analysis

### Medium Priority

4. **GRADE Certainty Extraction**
   - Detect GRADE symbols (circles)
   - Extract certainty ratings from summary tables

5. **Individual Patient Data Signals**
   - Detect IPD availability statements
   - Extract data sharing repository links

6. **Pre-registration Detection**
   - Extract protocol registration numbers
   - Flag deviations from pre-specified analyses

---

## Statistical Considerations

### 1. Effect Measure Selection

The tool extracts what is reported, but meta-analysts need guidance on:
- When to convert OR to RR (and vice versa)
- Handling of adjusted vs. unadjusted estimates
- Selection among multiple reported timepoints

### 2. Correlation Assumptions

For composite endpoints, component-level extraction is valuable, but:
- Correlations between components are not extracted
- Joint distributions are needed for multivariate meta-analysis

### 3. Zero-Cell Handling

No explicit handling for studies with zero events:
- Continuity corrections
- Exact methods
- Bayesian approaches

---

## Comparison with Existing Tools

| Feature | RCT Extractor | Covidence | DistillerSR | ExaCT |
|---------|---------------|-----------|-------------|-------|
| Effect Types | 14 | 6 | 8 | 4 |
| SE/SD Detection | Yes | No | No | No |
| Composite Parsing | Yes | No | Limited | No |
| ML Confidence | Yes | No | No | Limited |
| Cross-Paper Validation | Yes | No | No | No |
| PDF Coordinates | No | No | Yes | Yes |
| Multi-Language | Limited | Yes | Yes | Limited |

---

## Conclusion

RCT Extractor v2.15 introduces several methodologically important features for automated data extraction, particularly SE/SD confusion detection and composite endpoint standardization. The 100% accuracy on internal validation is impressive but must be tempered by the need for external validation on real-world PDFs.

The tool is suitable for:
- Pilot/screening extraction with manual verification
- Quality control of manual extraction
- Identifying potential errors in existing datasets

The tool is NOT YET suitable for:
- Fully automated extraction without human verification
- Regulatory submissions requiring audit trails
- High-stakes clinical guideline development

### Required Revisions

1. **External validation study** with prospective PDF collection and dual manual extraction
2. **Confidence calibration** with empirical threshold determination
3. **Provenance metadata** including source location and comparison arm labels
4. **PRISMA-S compliant reporting** of methods and limitations

### Minor Revisions

5. Multi-language testing expansion
6. Subgroup analysis flagging
7. Reproducibility documentation (Docker, version pins)

---

## References

1. Gøtzsche PC, et al. (2007). "Data extraction errors in meta-analyses that use standardized mean differences." JAMA.
2. IntHout J, et al. (2016). "Small studies are more heterogeneous than large ones: a meta-meta-analysis." J Clin Epidemiol.
3. Cochrane Handbook for Systematic Reviews of Interventions, Version 6.4.
4. PRISMA-S Extension for Reporting Literature Searches in Systematic Reviews.
5. PROBAST: A Tool to Assess the Risk of Bias and Applicability of Prediction Model Studies.

---

*Reviewer: Research Synthesis Methods (Simulated Editorial Review)*
*This review is generated for quality improvement purposes.*
