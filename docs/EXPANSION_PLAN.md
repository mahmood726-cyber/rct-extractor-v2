# RCT Extractor - Validation Expansion and Training Plan

## Executive Summary

This plan outlines systematic expansion from the current 49-trial validation corpus to a production-ready system validated on 500+ trials with multi-source ground truth, true inter-rater reliability, and comprehensive pattern coverage.

---

## Phase 1: Corpus Expansion (Target: 200 trials)

### 1.1 Effect Type Balancing

**Current State**:
| Type | Count | Target |
|------|-------|--------|
| HR | 50 (81%) | 100 (50%) |
| RR | 8 (13%) | 40 (20%) |
| OR | 1 (2%) | 30 (15%) |
| MD | 3 (5%) | 30 (15%) |

**Acquisition Strategy**:

#### OR-heavy sources (n=30 needed):
- Psychiatric trials (depression, anxiety, schizophrenia)
- Diagnostic accuracy studies
- Case-control nested in cohorts
- Vaccine side effect studies

Search: `"odds ratio" AND "randomized" AND ("psychiatric" OR "depression" OR "anxiety") AND free full text[filter]`

#### MD-heavy sources (n=30 needed):
- Pain trials (VAS scores)
- HbA1c reduction trials
- Blood pressure trials
- Quality of life (SF-36, EQ-5D)
- Cognitive function (MMSE, ADAS-Cog)

Search: `"mean difference" AND "randomized controlled" AND ("pain" OR "HbA1c" OR "blood pressure") AND free full text[filter]`

#### RR-heavy sources (n=35 needed):
- Vaccine efficacy trials
- Infection prevention trials
- Cancer screening trials
- Mortality risk reduction studies

Search: `"relative risk" AND "randomized" AND ("vaccine" OR "prevention") AND free full text[filter]`

### 1.2 Journal Diversification

**Current**: 90% NEJM
**Target**: <40% any single journal

| Journal Tier | Target % | Sources |
|--------------|----------|---------|
| Top 4 (NEJM, Lancet, JAMA, BMJ) | 40% | Current + expansion |
| Specialty (Circulation, JCO, Diabetes Care) | 30% | PubMed search |
| Regional/Open Access | 20% | PMC OA subset |
| Non-English (translated) | 10% | Cochrane translations |

### 1.3 Temporal Expansion

**Current**: 78% from 2014-2023
**Target**: Uniform distribution 1995-2025

| Period | Current | Target | Notes |
|--------|---------|--------|-------|
| 1995-2004 | 2% | 15% | Older reporting formats |
| 2005-2014 | 20% | 25% | CONSORT adoption era |
| 2015-2024 | 78% | 50% | Modern standards |
| 2025+ | 0% | 10% | Latest conventions |

### 1.4 Difficulty Stratification

**Target Distribution**:
| Difficulty | Current | Target | Characteristics |
|------------|---------|--------|-----------------|
| Easy | 57% | 30% | Clear format, single primary |
| Moderate | 22% | 30% | Multiple effects, some ambiguity |
| Hard | 12% | 25% | Tables, complex formatting |
| Very Hard | 8% | 15% | OCR issues, non-standard |

---

## Phase 2: Ground Truth Enhancement

### 2.1 True Dual Independent Extraction

**Protocol**:
1. Recruit 2 trained extractors (epidemiology background)
2. Provide extraction form with fields:
   - Effect type (HR/OR/RR/MD/SMD)
   - Point estimate
   - CI lower/upper
   - p-value (if reported)
   - Outcome description
   - Analysis type (ITT/per-protocol)
   - Source location (abstract/results/table)

3. Blinded independent extraction (no communication)
4. Calculate pre-adjudication agreement
5. Third extractor adjudicates disagreements
6. Report:
   - Raw agreement rate
   - Cohen's kappa with 95% CI
   - Gwet's AC1 (for high-agreement scenarios)

**Target**: κ > 0.80 (substantial agreement)

### 2.2 Complete Effect Enumeration

For each trial, extract ALL reported effects, not just primary:
- Primary endpoint
- Key secondary endpoints
- Subgroup analyses (pre-specified)
- Sensitivity analyses

This eliminates the "extra extraction = false positive" artifact.

### 2.3 Multi-Source Verification

| Source | Purpose | Coverage |
|--------|---------|----------|
| Manual extraction | Gold standard | 100% |
| ClinicalTrials.gov | Automated verification | ~70% (NCT-linked) |
| Cochrane CENTRAL | Cross-reference | ~40% |
| FDA/EMA reviews | Regulatory verification | ~20% |

---

## Phase 3: Negative Control Expansion

### 3.1 Target: 100 Negative Controls

| Category | Current | Target | Sources |
|----------|---------|--------|---------|
| Protocol papers | 2 | 15 | clinicaltrials.gov protocols |
| Meta-analyses | 0 | 20 | Cochrane, JAMA MA |
| Observational | 4 | 15 | Cohort studies |
| Reviews | 2 | 15 | Narrative reviews |
| Guidelines | 0 | 10 | ESC, ACC, NICE |
| Editorials | 1 | 10 | Journal commentaries |
| Methods papers | 2 | 10 | Statistical tutorials |
| Non-medical | 2 | 5 | Economics, sports |

### 3.2 Adversarial Negative Controls

Intentionally challenging cases:
- Protocols with "expected HR of 0.75"
- Methods papers with "example: HR 0.80 (0.70-0.91)"
- Guidelines citing "DAPA-HF showed HR 0.74"
- Meta-analyses with pooled estimates

---

## Phase 4: Pattern Training Pipeline

### 4.1 Failure-Driven Pattern Development

```
1. Run extraction on new corpus
2. Identify false negatives (missed extractions)
3. Extract source text context
4. Analyze pattern gaps
5. Develop new patterns
6. Validate on held-out set
7. Regression test on existing corpus
```

### 4.2 Pattern Quality Metrics

For each pattern, track:
- **Precision**: True matches / Total matches
- **Recall**: True matches / Expected matches
- **Specificity**: Correct rejections / Total negatives

Remove patterns with precision < 80% or contributing < 1% of extractions.

### 4.3 Confidence Calibration

Train calibration model on:
- Pattern match quality
- Context features (section, surrounding text)
- Value plausibility (within typical ranges)
- CI consistency

Target: Expected Calibration Error (ECE) < 0.05

---

## Phase 5: Full-Text PDF Validation

### 5.1 PDF Processing Pipeline

```
PDF → Text Extraction → Normalization → Effect Extraction → Validation
         ↓
    [PyMuPDF/pdfplumber]
         ↓
    [Section detection]
         ↓
    [Table extraction]
```

### 5.2 Validation Tiers

| Tier | Input | Purpose |
|------|-------|---------|
| Tier 1 | Curated snippets | Pattern development |
| Tier 2 | Full abstract | Abstract extraction |
| Tier 3 | Results section | Section-specific |
| Tier 4 | Full PDF text | End-to-end |

### 5.3 Error Analysis by Source

Track extraction failures by:
- PDF quality (native vs scanned)
- Text extraction method
- Section of origin
- Table vs prose

---

## Phase 6: Automation Tiers and Confidence

### 6.1 Production Automation Levels

| Tier | Confidence | Action | Use Case |
|------|------------|--------|----------|
| FULL_AUTO | >95% | Accept without review | Screening |
| SPOT_CHECK | 85-95% | 10% random review | Rapid review |
| VERIFY | 70-85% | Quick human check | Standard SR |
| MANUAL | <70% | Full manual review | Regulatory |

### 6.2 Confidence Features

Train on:
- Pattern match strength
- CI consistency (lower < point < upper)
- Value range plausibility
- Context quality (methods vs results)
- Multi-extraction agreement

---

## Phase 7: Continuous Validation

### 7.1 Regression Test Suite

```python
# tests/test_extraction_accuracy.py
def test_corpus_recall_minimum():
    assert recall >= 0.85

def test_corpus_precision_minimum():
    assert precision >= 0.70

def test_negative_control_fp_rate():
    assert fp_rate <= 0.15

def test_per_type_recall():
    for effect_type in ['HR', 'OR', 'RR', 'MD']:
        assert type_recall[effect_type] >= 0.75
```

### 7.2 Monitoring Dashboard

Track over time:
- Recall by effect type
- Precision on negative controls
- CI completion rate
- Pattern hit rates
- Extraction time

### 7.3 Quarterly Validation

Every 3 months:
1. Add 20 new trials to corpus
2. Run full validation
3. Compare to baseline
4. Update patterns if degraded
5. Publish validation report

---

## Resource Requirements

### Personnel
| Role | Time | Purpose |
|------|------|---------|
| Epidemiologist (2) | 40 hrs each | Dual extraction |
| Data scientist | 80 hrs | Pattern development |
| QA specialist | 20 hrs | Validation review |

### Data
| Source | Trials | Cost |
|--------|--------|------|
| PMC OA | 150 | Free |
| PubMed abstracts | 200 | Free |
| Licensed journals | 50 | ~$500 |
| Cochrane | 100 | Subscription |

### Compute
- Pattern matching: CPU-bound, ~5 sec/trial
- Full PDF processing: ~30 sec/PDF
- Total validation run: ~1 hour for 500 trials

---

## Success Criteria

### Minimum Viable Validation (v5.0)
- [ ] 200+ trials in corpus
- [ ] True dual extraction with κ > 0.80
- [ ] All effect types n ≥ 20
- [ ] Negative controls n ≥ 50
- [ ] Recall ≥ 85% across all types
- [ ] FP rate ≤ 15% on negative controls

### Production Ready (v6.0)
- [ ] 500+ trials in corpus
- [ ] Full PDF validation pipeline
- [ ] Confidence calibration ECE < 0.05
- [ ] Automation tiers validated
- [ ] Continuous monitoring deployed
- [ ] External validation on held-out corpus

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1: Corpus expansion | 4 weeks | 200 trials |
| Phase 2: Ground truth | 6 weeks | True dual extraction |
| Phase 3: Negative controls | 2 weeks | 100 controls |
| Phase 4: Pattern training | 4 weeks | Updated patterns |
| Phase 5: PDF validation | 4 weeks | Full pipeline |
| Phase 6: Automation | 2 weeks | Confidence model |
| Phase 7: Continuous | Ongoing | Monitoring |

**Total**: ~22 weeks to production-ready (v6.0)

---

## Appendix: Data Sources

### PubMed Search Strategies

**OR-heavy trials**:
```
("odds ratio"[tiab]) AND ("randomized controlled trial"[pt]) AND
("2015"[pdat] : "2025"[pdat]) AND free full text[filter] AND
("depression"[mesh] OR "anxiety"[mesh] OR "schizophrenia"[mesh])
```

**MD-heavy trials**:
```
("mean difference"[tiab]) AND ("randomized controlled trial"[pt]) AND
("pain"[mesh] OR "blood pressure"[mesh] OR "HbA1c"[tiab]) AND
free full text[filter]
```

**Older trials (pre-2010)**:
```
("randomized controlled trial"[pt]) AND ("1995"[pdat] : "2005"[pdat]) AND
("hazard ratio"[tiab] OR "relative risk"[tiab]) AND free full text[filter]
```

### Cochrane CENTRAL Access
- Register for Cochrane Library access
- Export CENTRAL records with PMC IDs
- Cross-reference with PMC OA subset

### ClinicalTrials.gov API
- Query: `https://clinicaltrials.gov/api/v2/studies`
- Filter: `resultsFirstSubmitDate` not null
- Extract: outcome measures with statistical analyses
