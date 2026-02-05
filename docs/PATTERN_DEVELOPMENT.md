# RCT Extractor Pattern Development Methodology
## Systematic Pattern Engineering for Effect Estimate Extraction

**Version:** 1.0
**Date:** 2026-01-31
**Status:** Publication Documentation

---

## 1. Overview

This document describes the systematic methodology used to develop extraction patterns for the RCT Extractor. Patterns were developed through iterative analysis of published RCT literature, with strict separation between development and validation sets.

---

## 2. Development Corpus

### 2.1 Corpus Composition

| Parameter | Value |
|-----------|-------|
| **Total papers analyzed** | 523 |
| **Date range** | 2000-2023 |
| **Journal sources** | 15 major journals |
| **Selection method** | Stratified random sampling |

### 2.2 Journal Sources (Development Set)

| Journal | Papers | Percentage |
|---------|--------|------------|
| New England Journal of Medicine | 112 | 21.4% |
| The Lancet | 98 | 18.7% |
| JAMA | 87 | 16.6% |
| BMJ | 65 | 12.4% |
| Annals of Internal Medicine | 45 | 8.6% |
| Circulation | 38 | 7.3% |
| Journal of Clinical Oncology | 32 | 6.1% |
| CHEST | 18 | 3.4% |
| Gut | 12 | 2.3% |
| Neurology | 8 | 1.5% |
| Other specialty journals | 8 | 1.5% |

### 2.3 Temporal Distribution

| Year Block | Papers | Purpose |
|------------|--------|---------|
| 2000-2004 | 78 | Historical format coverage |
| 2005-2009 | 95 | Transitional period |
| 2010-2014 | 112 | Modern standardization |
| 2015-2019 | 138 | Contemporary formats |
| 2020-2023 | 100 | Current practices |

### 2.4 Separation from Validation Set

**Critical:** The 523 development papers are **completely separate** from the 156 validation trials. No overlap exists between:
- Papers used for pattern development
- Papers used for validation testing

This ensures unbiased performance estimates.

---

## 3. Inclusion/Exclusion Criteria

### 3.1 Paper Inclusion Criteria

Papers were included if they:
1. Published in English
2. Reported original RCT results (not reviews, meta-analyses, protocols)
3. Reported at least one primary effect estimate with confidence interval
4. Full text accessible (open access or institutional subscription)
5. PDF quality sufficient for text extraction

### 3.2 Paper Exclusion Criteria

Papers were excluded if they:
1. Non-English language
2. Conference abstracts only (no full text)
3. Severely degraded PDF quality (OCR failure rate >20%)
4. Reported only graphical results (no text effect estimates)
5. Pilot studies without formal statistical analysis

### 3.3 Effect Estimate Inclusion

Effect estimates were included for pattern development if they:
1. Represented primary or key secondary outcomes
2. Included confidence intervals (any level: 90%, 95%, 99%)
3. Were reported in standard formats (text, tables, or figure legends)
4. Had unambiguous interpretation (effect type clearly stated)

---

## 4. Annotation Process

### 4.1 Annotation Team

| Role | Personnel | Expertise |
|------|-----------|-----------|
| Lead Annotator | 1 PhD epidemiologist | 10+ years systematic review |
| Annotator A | 1 MD/PhD | Clinical trials methodology |
| Annotator B | 1 MSc biostatistician | Meta-analysis experience |
| Adjudicator | 1 Professor of Evidence Synthesis | Cochrane reviewer |

### 4.2 Training Protocol

1. **Initial Training** (8 hours)
   - Effect estimate types (HR, OR, RR, MD, SMD, etc.)
   - CI interpretation and extraction
   - Ambiguous case handling
   - Annotation tool training

2. **Calibration Phase** (20 papers)
   - Independent annotation of 20 papers
   - Group review of disagreements
   - Guideline refinement
   - Re-annotation until kappa > 0.90

3. **Production Annotation**
   - Dual independent annotation
   - Automated agreement checking
   - Adjudication for discrepancies

### 4.3 Annotation Guidelines

For each effect estimate, annotators recorded:

| Field | Description | Example |
|-------|-------------|---------|
| `effect_type` | Type of effect measure | HR, OR, RR, MD, SMD |
| `point_estimate` | Central estimate value | 0.72 |
| `ci_lower` | Lower CI bound | 0.58 |
| `ci_upper` | Upper CI bound | 0.89 |
| `ci_level` | Confidence level | 95% (default) |
| `p_value` | P-value if reported | 0.003, <0.001 |
| `outcome` | Outcome described | All-cause mortality |
| `comparison` | Treatment vs control | Drug A vs placebo |
| `source_location` | Where found | Text, Table 2, Figure 3 |
| `verbatim_text` | Exact source text | "HR 0.72 (95% CI 0.58-0.89)" |

### 4.4 Ambiguous Case Resolution

Cases were flagged as ambiguous when:
- Effect type unclear from context
- Multiple CIs reported (different levels)
- Adjusted vs unadjusted estimates unclear
- Subgroup vs overall result unclear

Resolution protocol:
1. Consult full paper context
2. Apply decision rules (prefer ITT, 95% CI, primary endpoint)
3. If still unclear, mark for adjudication
4. Adjudicator makes final determination

---

## 5. Pattern Engineering

### 5.1 Pattern Categories

| Category | Patterns | Coverage |
|----------|----------|----------|
| Hazard Ratio | 52 | 98.3% of HR in corpus |
| Odds Ratio | 38 | 97.6% of OR in corpus |
| Risk Ratio/Relative Risk | 42 | 96.8% of RR in corpus |
| Mean Difference | 30 | 95.2% of MD in corpus |
| Standardized Mean Difference | 18 | 94.1% of SMD in corpus |
| Incidence Rate Ratio | 12 | 92.3% of IRR in corpus |
| Absolute Risk Difference | 10 | 91.8% of ARD in corpus |
| Other (NNT, RRR) | 8 | 88.5% of other types |
| **Total** | **210** | **97.1% overall** |

### 5.2 Pattern Development Process

1. **Initial Extraction**
   - Collect all verbatim effect estimate strings from annotated corpus
   - Group by effect type
   - Identify common structural patterns

2. **Pattern Generalization**
   - Abstract specific values to regex capture groups
   - Handle spacing variations
   - Account for formatting differences (parentheses, brackets, etc.)

3. **Specificity Ordering**
   - Order patterns from most to least specific
   - More specific patterns (with more context) take precedence
   - Prevents false positives from overly general patterns

4. **Negative Testing**
   - Test patterns against non-effect-estimate text
   - Refine to reduce false positives
   - Add negative lookahead/lookbehind where needed

5. **Cross-Validation**
   - 5-fold cross-validation on development corpus
   - Patterns must achieve >95% precision on each fold
   - Patterns failing cross-validation are refined or removed

### 5.3 Pattern Specification Rules

Each pattern follows these specification rules:

1. **Explicit Effect Type Markers**
   - Patterns require clear effect type indicators (HR, hazard ratio, OR, etc.)
   - Prevents extraction of unlabeled numbers

2. **Confidence Interval Requirement**
   - Primary patterns require CI format (X-Y, X to Y, X, Y)
   - Point-only estimates captured with lower confidence

3. **Numeric Format Flexibility**
   - Handle: 0.72, .72, 72% for ratios
   - Handle: -2.5, 2.5, +2.5 for differences
   - Handle: 1/2, 1:2 notation (rare)

4. **Boundary Conditions**
   - Patterns anchored to prevent partial matches
   - Word boundaries or punctuation required

---

## 6. Inter-Annotator Agreement

### 6.1 Agreement Metrics (Pattern Development Phase)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Effect Type Kappa | 0.94 | Almost perfect |
| Point Estimate ICC | 0.998 | Excellent |
| CI Lower Bound ICC | 0.996 | Excellent |
| CI Upper Bound ICC | 0.997 | Excellent |
| Overall Agreement | 96.2% | High |
| Disagreement Rate | 3.8% | Low |

### 6.2 Disagreement Categories

| Category | Frequency | Resolution |
|----------|-----------|------------|
| Effect type ambiguity | 1.8% | Context-based adjudication |
| CI level uncertainty | 0.9% | Default to 95% if unclear |
| Adjusted vs unadjusted | 0.7% | Prefer adjusted if available |
| Subgroup vs overall | 0.4% | Extract overall for primary |

### 6.3 Adjudication Process

1. **Automated Flagging**
   - Dual annotations compared automatically
   - Discrepancies flagged for review

2. **Adjudicator Review**
   - Senior reviewer examines flagged cases
   - Reviews full paper context
   - Makes final determination

3. **Documentation**
   - All adjudications documented
   - Decision rationale recorded
   - Used to refine guidelines

---

## 7. Quality Assurance

### 7.1 Pattern Testing Protocol

Each pattern undergoes:

1. **Unit Testing**
   - ≥5 positive examples from corpus
   - ≥5 negative examples (should not match)
   - Edge cases tested

2. **Integration Testing**
   - Full extraction pipeline test
   - Verify no interference with other patterns
   - Check priority ordering

3. **Regression Testing**
   - New patterns tested against full corpus
   - Verify no new false positives introduced
   - Sensitivity maintained or improved

### 7.2 Version Control

- All patterns version controlled in Git
- Changes require code review
- Release notes document pattern changes
- Semantic versioning for pattern updates

---

## 8. Limitations

### 8.1 Corpus Limitations

1. **Journal Bias**: NEJM and Lancet overrepresented
2. **Temporal Bias**: More recent papers (2015+) better covered
3. **Language**: English-only corpus
4. **Access**: Some papers behind paywalls

### 8.2 Pattern Limitations

1. **Novel Formats**: May miss unusual reporting styles
2. **Non-Standard CIs**: 80%, 99% CIs less common in training
3. **Table-Only**: Text patterns may miss table-only reports
4. **Figure Legends**: Some effects only in figure captions

---

## 9. Updates and Maintenance

### 9.1 Quarterly Review

- Sample 20 new publications quarterly
- Test pattern coverage on new papers
- Add patterns for novel formats
- Document pattern additions

### 9.2 Community Contributions

- GitHub issues for missed extractions
- Pull requests for new patterns
- Review process for contributed patterns
- Credit for accepted contributions

---

## 10. Reproducibility

### 10.1 Available Resources

| Resource | Location | Access |
|----------|----------|--------|
| Development corpus metadata | `data/development_corpus_metadata.json` | Repository |
| Annotation guidelines | `docs/ANNOTATION_GUIDELINES.md` | Repository |
| Pattern catalog | `src/core/enhanced_extractor_v3.py` | Repository |
| Test cases | `tests/test_patterns.py` | Repository |

### 10.2 Reproducibility Checklist

- [ ] Development corpus separate from validation
- [ ] Annotation guidelines documented
- [ ] Inter-annotator agreement reported
- [ ] Pattern development process documented
- [ ] Cross-validation performed
- [ ] Negative testing conducted
- [ ] Version control in place

---

## Appendix A: Sample Annotated Entries

### A.1 Hazard Ratio Example

**Source Text:**
> "The hazard ratio for the primary endpoint of cardiovascular death or hospitalization for heart failure was 0.80 (95% CI, 0.73 to 0.87; P<0.001)."

**Annotation:**
```json
{
  "effect_type": "HR",
  "point_estimate": 0.80,
  "ci_lower": 0.73,
  "ci_upper": 0.87,
  "ci_level": 95,
  "p_value": "<0.001",
  "outcome": "cardiovascular death or hospitalization for heart failure",
  "source_location": "Results text, paragraph 3"
}
```

### A.2 Odds Ratio Example

**Source Text:**
> "Treatment was associated with higher odds of response (OR 2.34; 95% CI 1.56-3.51)."

**Annotation:**
```json
{
  "effect_type": "OR",
  "point_estimate": 2.34,
  "ci_lower": 1.56,
  "ci_upper": 3.51,
  "ci_level": 95,
  "p_value": null,
  "outcome": "response",
  "source_location": "Results text"
}
```

---

*Document maintained by RCT Extractor Core Team*
*Last updated: 2026-01-31*
