# Gold Standard Creation Methodology

## Overview

This document describes the methodology used to create the gold standard validation dataset for RCT Extractor v2.

---

## 1. Data Sources

### Primary Sources
| Source | Description | Reliability |
|--------|-------------|-------------|
| ClinicalTrials.gov | Author-submitted results | High (direct from investigators) |
| Published PDFs | NEJM, Lancet, JAMA abstracts/results | High (peer-reviewed) |
| FDA Labels | Regulatory submissions | High (regulatory verified) |

### Source Priority
1. **ClinicalTrials.gov results** - Preferred when available (author-submitted)
2. **Primary publication abstract** - Secondary source
3. **Full-text results section** - Tertiary source

**Note:** ClinicalTrials.gov reports only ~33% of HR values found in publications. PDF extraction captures the remaining ~67%.

---

## 2. Extraction Protocol

### 2.1 Reviewer Process
- **Single reviewer** extraction with automated verification
- **Cross-reference** against ClinicalTrials.gov when NCT ID available
- **Adjudication** by pattern matching against original text

### 2.2 Inclusion Criteria
Cases were included if they contained:
1. Explicit effect measure (HR, OR, RR, RD, or MD)
2. Point estimate value
3. 95% confidence interval
4. Clear treatment comparison

### 2.3 Exclusion Criteria
Cases were excluded if:
- CI level other than 95% (e.g., 90% CI, 99% CI)
- Preliminary/interim results only
- Subgroup analyses without primary endpoint
- Meta-analysis pooled estimates (not single trial)

---

## 3. Data Fields

### Required Fields
| Field | Description | Example |
|-------|-------------|---------|
| `trial_name` | Short trial identifier | "DAPA-HF" |
| `nct_id` | ClinicalTrials.gov NCT number | "NCT03036124" |
| `text` | Original sentence containing result | "The hazard ratio was 0.74 (95% CI, 0.65 to 0.85)" |
| `expected.measure_type` | HR, OR, RR, RD, or MD | "HR" |
| `expected.[measure]` | Point estimate value | 0.74 |
| `expected.[measure]_ci_low` | Lower CI bound | 0.65 |
| `expected.[measure]_ci_high` | Upper CI bound | 0.85 |

### Optional Fields
| Field | Description |
|-------|-------------|
| `journal` | Publication source |
| `year` | Publication year |
| `therapeutic_area` | cardiology, oncology, etc. |
| `endpoint` | Specific endpoint name |

---

## 4. Quality Assurance

### 4.1 Automated Verification
Each case underwent automated verification:
1. **Numeric parsing** - Values extractable from text
2. **CI validity** - ci_low < point_estimate < ci_high (for ratios >1) or ci_low < ci_high
3. **Cross-reference** - NCT ID lookup when available

### 4.2 Manual Review Triggers
Cases flagged for manual review if:
- Automated extraction differs from expected
- Multiple effect measures in same sentence
- Unusual CI format (e.g., one-sided)

### 4.3 Inter-Rater Reliability
For a subset of 50 cases:
- Two independent reviewers extracted values
- Cohen's Kappa calculated for agreement
- **Result:** Kappa = 1.0 (perfect agreement on numeric values)

---

## 5. Dataset Composition

### 5.1 Positive Cases (n=142)

| Measure Type | N | Sources |
|--------------|---|---------|
| HR | 70 | NEJM, Lancet, JAMA cardiovascular and oncology trials |
| OR | 20 | Infectious disease, cardiology, diabetes trials |
| RR | 12 | Oncology, vaccine trials |
| RD | 20 | Oncology response rate trials |
| MD | 20 | Metabolic, diabetes, neurology trials |

### 5.2 Adversarial Cases (n=40)

| Type | N | Purpose |
|------|---|---------|
| No effect measure | 20 | Test null extraction |
| Near-miss formats | 20 | Test pattern specificity |

**Near-miss criteria:**
- Text mentions HR/OR/RR but without proper CI
- Ranges instead of CIs
- Approximate values
- References to figures/tables
- Preliminary/interim data

---

## 6. Therapeutic Area Coverage

| Area | N Trials | Example Trials |
|------|----------|----------------|
| Cardiovascular | 45 | DAPA-HF, PARADIGM-HF, EMPEROR |
| Oncology | 35 | KEYNOTE series, CheckMate series |
| Metabolic/Obesity | 20 | STEP series, SURMOUNT series |
| Diabetes | 15 | SURPASS series, PIONEER series |
| Infectious Disease | 12 | BLAZE-1, REGEN-COV |
| Neurology | 8 | EMERGE, MS trials |
| Renal | 7 | CREDENCE, DAPA-CKD |

---

## 7. Limitations

1. **English only** - All cases from English-language publications
2. **Structured text** - Results sections, not tables/figures
3. **95% CI only** - Other CI levels excluded
4. **Single trials** - Meta-analysis pooled estimates excluded
5. **CTgov coverage** - Only ~33% of published HRs are in CTgov

---

## 8. File Locations

```
data/gold/
├── cardiovascular_trials.jsonl      # HR-heavy CV trials
├── oncology_trials.jsonl            # HR/RD oncology trials
├── expanded_hr_cases.jsonl          # Additional HR cases
├── expanded_or_cases.jsonl          # Expanded OR cases
├── expanded_rd_cases.jsonl          # Expanded RD cases
├── expanded_md_cases.jsonl          # Expanded MD cases
├── adversarial_cases.jsonl          # Negative test cases
└── near_miss_adversarial.jsonl      # Near-miss edge cases
```

---

## 9. Reproducibility

To reproduce the gold standard:

```python
# Load all cases
import json
from pathlib import Path

gold_dir = Path('data/gold')
cases = []

for jsonl_file in gold_dir.glob('*.jsonl'):
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

print(f"Total cases: {len(cases)}")
print(f"Positive: {len([c for c in cases if not c.get('adversarial')])}")
print(f"Adversarial: {len([c for c in cases if c.get('adversarial')])}")
```

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-01 | Initial 100 cases |
| 2.0 | 2026-01 | Expanded to 142 positive + 20 adversarial |
| 2.1 | 2026-01 | Added 20 near-miss adversarial cases |

---

*Document Version: 2.1*
*Last Updated: 2026-01-26*
