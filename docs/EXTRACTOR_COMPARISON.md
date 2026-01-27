# RCT Extractor Comparison & Ensemble Strategy

## 1. Comparison: RCT Extractor v2 (Python) vs v4.8 (JavaScript)

### Feature Matrix

| Feature | v4.8 JS | v2 Python | Winner |
|---------|---------|-----------|--------|
| **Core Extraction** |
| HR/RR/OR patterns | 15+ patterns | 15+ patterns | Tie |
| MD/RD/NNT patterns | Full | Full | Tie |
| Unicode normalization | Yes | Yes | Tie |
| Context extraction | ±50 chars | Full sentence | **v2** |
| **Advanced Features** |
| SE calculation from CI | Yes | No | **v4.8** |
| Log-transformed values | Yes | No | **v4.8** |
| Primary/Secondary detection | Yes | Partial | **v4.8** |
| Subgroup analysis detection | Yes | No | **v4.8** |
| Sensitivity analysis detection | Yes | No | **v4.8** |
| Continuous outcomes (Mean±SD) | Yes | No | **v4.8** |
| Effect direction classification | Yes | Partial | **v4.8** |
| Statistical significance flags | Yes | No | **v4.8** |
| **PDF Processing** |
| Table detection | Via pdfplumber | pdfplumber + ML | **v2** |
| OCR fallback | No | Yes (Tesseract) | **v2** |
| Scanned PDF support | No | Yes | **v2** |
| Page image extraction | No | Yes | **v2** |
| **Validation & QC** |
| Pydantic schema validation | No | Yes | **v2** |
| Provenance tracking | Partial (context) | Full (page, bbox) | **v2** |
| Review queue | No | Yes | **v2** |
| Two-pass verification | No | Yes | **v2** |
| CI contains point estimate | Runtime | Construction-time | **v2** |
| events ≤ n validation | No | Yes | **v2** |
| P-value/CI consistency | Runtime | Yes | **v2** |
| **Infrastructure** |
| CLI interface | No | Yes | **v2** |
| Evaluation framework | Via TruthCert | Built-in | **v2** |
| Gold standard format | JSON | JSONL | **v2** |
| Batch processing | No | Yes | **v2** |

### Good Aspects from v4.8 to Carry Over

1. **SE Calculation from CI**
```javascript
// From v4.8: Calculate SE for meta-analysis
result.logValue = Math.log(result.value);
result.se = (Math.log(result.ciHi) - Math.log(result.ciLo)) / 3.92;
result.variance = result.se * result.se;
```

2. **Primary Outcome Detection** (wide context search)
```javascript
// v4.8 searches 400 chars BEFORE the match for "primary outcome"
const wideStart = Math.max(0, match.index - 400);
const wideContext = text.slice(wideStart, wideEnd).toLowerCase();
result.isPrimary = wideContext.includes('primary outcome');
```

3. **Subgroup Analysis Detection**
```javascript
// v4.8 detects prespecified vs exploratory subgroups
// Extracts interaction p-values
// Identifies common subgroup variables
```

4. **Continuous Outcomes Extraction**
```javascript
// v4.8 extracts Mean ± SD for meta-analysis
// Calculates SE = SD/sqrt(N) when N is available
```

5. **Effect Direction Classification**
```javascript
result.direction = result.value < 1 ? 'favors_treatment' :
                   result.value > 1 ? 'favors_control' : 'neutral';
result.statisticallySignificant = result.ciHi < 1 || result.ciLo > 1;
result.clinicallyMeaningful = result.ciHi < 0.8 || result.ciLo > 1.25;
```

6. **Derived Measures** (NNT from RD)
```javascript
// Auto-calculate NNT when only RD is available
result.nnt = Math.abs(Math.round(100 / rd.value));
```

---

## 2. Ideas from Wasserstein KM Extractor

The Wasserstein folder contains sophisticated survival analysis tools:

### Key Innovations

1. **Wasserstein Distance for Validation**
   - W₁ = ∫|S₁(t) - S₂(t)|dt (area between curves)
   - W₂ uses quantile functions for full distributional comparison
   - More robust than pointwise KM comparison

2. **IPD Reconstruction Algorithms**
   - Guyot standard algorithm
   - Guyot enhanced (iterative refinement)
   - Wei-Royston piecewise exponential
   - Hybrid ensemble of methods

3. **Grading System** (from VALIDATION_CRITERIA.txt)
   - Grade A: MAE(S(t)) < 0.02, HR error < 5%
   - Grade B: MAE(S(t)) < 0.05, HR error < 10%
   - Grade C: MAE(S(t)) < 0.10, HR error < 20%

4. **Data Fabrication Detection**
   - Statistical tests for implausible patterns
   - Digit preference analysis
   - Timeline consistency checks

### Applicable to RCT Extraction

- **Use grading system for confidence levels**
- **Apply distributional comparison for table validation**
- **Ensemble approach (multiple algorithms, merge results)**

---

## 3. TruthCert Validation System

TruthCert provides independent validation using ClinicalTrials.gov:

### Key Features

1. **Independent Ground Truth**
   - Fetches data from CTGov API v2
   - No circular validation (doesn't use training data)
   - Caches API responses

2. **NCT ID Extraction**
   - Multiple patterns (NCT\d{8}, with hyphens, in parentheses)
   - Normalizes to standard format

3. **Verification Workflow**
   ```
   PDF → Extract NCT ID → Fetch CTGov data → Extract from PDF → Compare
   ```

4. **Metrics**
   - Precision, Recall, F1
   - With confidence intervals
   - Value tolerance: 1%, CI tolerance: 2%

---

## 4. Proposed Ensemble Architecture

### Four Extractors

| Extractor | Strengths | Use Case |
|-----------|-----------|----------|
| **E1: v2 Python (Structure)** | Tables, validation, provenance | Born-digital PDFs |
| **E2: v4.8 JS (Text)** | Comprehensive patterns, meta-analysis fields | Text extraction |
| **E3: Wasserstein (Survival)** | IPD reconstruction, KM curves | Time-to-event data |
| **E4: TruthCert (Verify)** | Independent validation, CTGov ground truth | QC layer |

### Ensemble Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: PDF                                                  │
└─────────────────────────────────────────────────────────────┘
         │
         ├────────────────┬────────────────┬────────────────┐
         ▼                ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ E1: v2 Py   │  │ E2: v4.8 JS │  │ E3: Wasser  │  │ E4: TruthC  │
│ Structure   │  │ Text        │  │ Survival    │  │ CTGov       │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
         │                │                │                │
         └────────────────┼────────────────┴────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  MERGER: Weighted Voting                                     │
│  - Agreement score (2+ extractors agree)                     │
│  - Provenance quality bonus                                  │
│  - TruthCert verification bonus                              │
│  - Wasserstein grade bonus                                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT: Merged extraction with confidence                   │
│  - HIGH: 3+ agree + TruthCert verified                      │
│  - MEDIUM: 2+ agree OR provenance complete                  │
│  - REVIEW: Disagreement OR validation fails                 │
└─────────────────────────────────────────────────────────────┘
```

### Merger Algorithm

```python
def merge_extractions(e1_results, e2_results, e3_results, e4_truth):
    merged = []

    for endpoint in all_endpoints:
        votes = []

        # Collect votes from each extractor
        if endpoint in e1_results:
            votes.append(('E1', e1_results[endpoint], e1_provenance))
        if endpoint in e2_results:
            votes.append(('E2', e2_results[endpoint], e2_context))
        if endpoint in e3_results:
            votes.append(('E3', e3_results[endpoint], e3_wasserstein_grade))

        # Count agreement
        hr_values = [v[1].hr for v in votes if v[1].hr]
        agreement = count_agreement(hr_values, tolerance=0.02)

        # TruthCert verification
        verified = endpoint in e4_truth and values_match(hr_values[0], e4_truth[endpoint])

        # Confidence scoring
        confidence = calculate_confidence(
            agreement_count=agreement,
            has_provenance=any(v[2] for v in votes),
            truthcert_verified=verified,
            wasserstein_grade=get_wasserstein_grade(votes)
        )

        # Select best value (prefer verified, then highest agreement)
        best_value = select_best(votes, verified, agreement)

        merged.append({
            'endpoint': endpoint,
            'value': best_value,
            'confidence': confidence,
            'sources': [v[0] for v in votes],
            'agreement': agreement,
            'verified': verified
        })

    return merged
```

### Confidence Grading (Ensemble)

| Grade | Criteria | Action |
|-------|----------|--------|
| **A** | 3+ agree + TruthCert verified + provenance | Auto-accept |
| **B** | 2+ agree + provenance OR TruthCert verified | Auto-accept with note |
| **C** | 2+ agree OR provenance complete | Manual spot-check |
| **D** | Single extractor only | Manual review required |
| **F** | Disagreement OR validation fails | Flag for expert review |

---

## 5. Implementation Plan

### Phase 1: Enhance v2 with v4.8 Features
- Add SE calculation from CI
- Add primary outcome detection
- Add subgroup analysis detection
- Add continuous outcomes (Mean±SD)
- Add effect direction classification

### Phase 2: Create Ensemble Merger
- Python bridge to v4.8 JS (via subprocess or transpile)
- Wasserstein integration
- TruthCert integration
- Weighted voting algorithm

### Phase 3: Validation Suite
- Use Wasserstein validation datasets (lung, colon, veteran, etc.)
- TruthCert independent test set
- Report ensemble accuracy vs individual extractors

### Expected Accuracy Improvement

| Extractor | Estimated Accuracy |
|-----------|-------------------|
| E1 alone | 70-80% (PDF) |
| E2 alone | 95-100% (text) |
| E3 alone | 90-95% (KM curves) |
| **Ensemble** | **95-99% (all sources)** |

---

## 6. Next Steps

1. **Carry over v4.8 features** to v2 Python (SE calc, primary detection, subgroups)
2. **Create merger module** with weighted voting
3. **Integrate TruthCert** as verification layer
4. **Benchmark ensemble** on independent test set
5. **Grade extractions** using Wasserstein criteria (A/B/C/D/F)
