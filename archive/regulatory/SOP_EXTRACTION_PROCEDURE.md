# Standard Operating Procedure
## Automated Effect Estimate Extraction for Systematic Reviews

**SOP Number:** SOP-RCT-001
**Version:** 1.0
**Effective Date:** 2026-01-29
**Review Date:** 2027-01-29

---

## 1. PURPOSE

This Standard Operating Procedure describes the validated method for automated extraction of effect estimates from randomized controlled trial publications using the RCT Effect Estimate Extractor system.

---

## 2. SCOPE

This SOP applies to:
- Systematic review teams conducting meta-analyses
- Regulatory submission preparation
- Evidence synthesis for health technology assessment
- Living systematic review maintenance

---

## 3. RESPONSIBILITIES

| Role | Responsibilities |
|------|------------------|
| **Extraction Operator** | Execute extraction, review outputs, document results |
| **Quality Reviewer** | Verify extraction accuracy, approve for use |
| **System Administrator** | Maintain system, apply updates, ensure validation status |
| **Project Lead** | Ensure SOP compliance, authorize deviations |

---

## 4. DEFINITIONS

| Term | Definition |
|------|------------|
| **Effect Estimate** | Quantitative measure of treatment effect (HR, OR, RR, MD, SMD, etc.) |
| **Confidence Interval** | Statistical range indicating estimate precision |
| **Verified Extraction** | Extraction that passed all verification checks |
| **Proof-Carrying Number** | Extraction with complete audit trail and verification certificate |

---

## 5. EQUIPMENT AND MATERIALS

### 5.1 Required Software
- RCT Effect Estimate Extractor v4.0.3 or later (validated version)
- Python 3.8 or later

### 5.2 Required Documentation
- This SOP
- Validation Report (VAL-RCT-2026-001)
- System User Guide

---

## 6. PROCEDURE

### 6.1 Pre-Extraction Checks

1. **Verify System Status**
   - Confirm using validated version (v4.0.3+)
   - Check system logs for errors
   - Verify configuration settings

2. **Prepare Input Documents**
   - Convert PDFs to text if needed
   - Note document quality (clear text vs. OCR)
   - Document any known issues with source material

3. **Define Extraction Parameters**
   - Specify effect types of interest
   - Set confidence level threshold (default: 0.85)
   - Configure language settings if non-English

### 6.2 Extraction Execution

```python
# Standard extraction procedure
from src.core.verified_extraction_pipeline import VerifiedExtractionPipeline

# Initialize pipeline
pipeline = VerifiedExtractionPipeline()

# Extract from text
extractions = pipeline.extract(source_text)

# Filter for verified (usable) extractions only
verified_extractions = [e for e in extractions if e.is_usable]
```

### 6.3 Output Review

For each extraction, verify:

| Check | Criterion | Action if Failed |
|-------|-----------|------------------|
| Effect type correct | Matches context | Manual review |
| Value plausible | Within expected range | Manual verification |
| CI contains point | Lower < Value < Upper | Flag for QC |
| Source text accurate | Matches original | Re-extract |

### 6.4 Quality Control

**Mandatory QC Steps:**

1. **Spot Check Sample**
   - Randomly select 10% of extractions (minimum 5)
   - Manually verify against source documents
   - Document any discrepancies

2. **Edge Case Review**
   - Review all extractions with confidence < 0.90
   - Review all extractions flagged with warnings
   - Verify OCR-corrected extractions

3. **Documentation**
   - Record extraction date and operator
   - Save extraction certificates
   - Document any manual corrections

### 6.5 Post-Extraction Actions

1. **Export Results**
   ```python
   # Export with full audit trail
   for extraction in verified_extractions:
       certificate = extraction.get_verification_certificate()
       # Save certificate with results
   ```

2. **Archive Source Documents**
   - Retain original text files
   - Document text extraction method
   - Note any preprocessing applied

3. **Complete Extraction Log**
   - Total documents processed
   - Total extractions obtained
   - QC results summary
   - Deviations noted

---

## 7. ACCEPTANCE CRITERIA

### 7.1 Extraction Acceptance

An extraction is accepted for use when:
- `is_usable = True`
- `is_verified = True`
- Confidence score ≥ 0.85 (or documented justification for lower)
- QC spot check passes

### 7.2 Batch Acceptance

A batch extraction is accepted when:
- ≥95% of extractions pass QC spot check
- No systematic errors identified
- All deviations documented and approved

---

## 8. DOCUMENTATION REQUIREMENTS

### 8.1 Extraction Log Template

| Field | Description |
|-------|-------------|
| Date | Extraction date |
| Operator | Person performing extraction |
| System Version | Software version used |
| Documents | Number of documents processed |
| Extractions | Total extractions obtained |
| Verified | Number passing verification |
| QC Sample | Sample size for QC |
| QC Pass Rate | Percentage passing QC |
| Deviations | Any deviations from SOP |
| Approval | QC reviewer signature |

### 8.2 Required Records

- Extraction log (per batch)
- Verification certificates (per extraction)
- QC documentation
- Deviation reports (if any)

---

## 9. DEVIATIONS

### 9.1 Minor Deviations

Deviations that do not affect data integrity:
- Document and continue
- Review in post-extraction QC
- No approval required

### 9.2 Major Deviations

Deviations that may affect data integrity:
- Stop extraction
- Document deviation
- Obtain Project Lead approval before continuing
- Implement corrective action

---

## 10. TRAINING REQUIREMENTS

| Role | Training Required |
|------|-------------------|
| Extraction Operator | System operation, this SOP, QC procedures |
| Quality Reviewer | This SOP, QC procedures, deviation handling |
| System Administrator | System maintenance, validation procedures |

---

## 11. REFERENCES

- FDA Guidance: Computerized Systems Used in Clinical Investigations
- 21 CFR Part 11: Electronic Records; Electronic Signatures
- GAMP 5: A Risk-Based Approach to Compliant GxP Computerized Systems
- ICH E6(R2): Good Clinical Practice
- PRISMA 2020: Systematic Review Reporting Guidelines

---

## 12. REVISION HISTORY

| Version | Date | Description | Author |
|---------|------|-------------|--------|
| 1.0 | 2026-01-29 | Initial release | QA |

---

## 13. APPROVAL

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Author | _________________ | _________________ | ________ |
| QA Review | _________________ | _________________ | ________ |
| Approval | _________________ | _________________ | ________ |
