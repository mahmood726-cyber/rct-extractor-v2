# RCT Extractor v2.12 - Improvement Roadmap

## Current State
- **Accuracy:** 922/922 (100%)
- **Effect Types:** HR, OR, RR, IRR, SMD, MD
- **Validation:** Comprehensive test suite

---

## Gap Analysis Summary

Based on codebase analysis and literature review of [common meta-analysis errors](https://pmc.ncbi.nlm.nih.gov/articles/PMC11795887/):

| Category | Current | Gap | Priority |
|----------|---------|-----|----------|
| Effect Types | 6 types | Missing 8+ types | High |
| Validation | Pattern-based | No cross-validation | High |
| Ambiguity | Flags only | No resolution | High |
| LLM Integration | None | Hybrid approach | Medium |
| Real-world PDFs | Limited | More validation | Medium |
| SE/SD Confusion | Manual flag | Auto-detect | High |

---

## Phase 1: Critical Improvements (High Priority)

### 1.1 SE vs SD Confusion Detection
**Problem:** [Most common error in meta-analyses](https://onlinelibrary.wiley.com/doi/full/10.1002/cesm.70013) - 75% of influential meta-analyses have errors.

**Implementation:**
```python
class DispersionValidator:
    """Detect SE/SD confusion using statistical heuristics"""

    def validate_dispersion(self, value, n, mean):
        # SE should be much smaller than SD
        # SD = SE * sqrt(n)
        # If reported "SD" is suspiciously small, likely SE

        cv = value / abs(mean) if mean != 0 else float('inf')

        # Typical CV for most biomarkers: 0.1 - 0.5
        # If CV < 0.05, likely SE reported as SD
        if cv < 0.05 and n > 30:
            return ValidationResult(
                is_valid=False,
                warning="Suspiciously small 'SD' - likely SE misreported",
                suggested_sd=value * math.sqrt(n)
            )
```

**Test Cases Needed:**
- LDL-C: mean=100, "SD"=2 (likely SE with n=500)
- HbA1c: mean=7.5, "SD"=0.1 (likely SE)
- Weight: mean=80, "SD"=0.5 (likely SE)

---

### 1.2 Multi-Arm Trial Handling
**Problem:** Current extractor only handles pairwise comparisons.

**Implementation:**
```python
@dataclass
class MultiArmResult:
    trial_id: str
    arms: List[str]  # ["Placebo", "Drug A 10mg", "Drug A 20mg"]
    comparisons: List[PairwiseComparison]
    reference_arm: str

def extract_multiarm(text: str) -> MultiArmResult:
    """Extract all arms and their comparisons"""
    # Pattern: "Drug A 10mg vs placebo: HR 0.75; Drug A 20mg vs placebo: HR 0.65"
    # Returns structured multi-arm result
```

**Test Cases Needed:**
- 3-arm: Placebo vs Low-dose vs High-dose
- 4-arm: Factorial design (2x2)
- Active comparator designs

---

### 1.3 Timepoint Disambiguation
**Problem:** Multiple timepoints extracted but no primary selection.

**Implementation:**
```python
class TimepointResolver:
    """Select primary timepoint from multiple candidates"""

    PRIORITY_KEYWORDS = [
        ("primary endpoint", 10),
        ("primary outcome", 10),
        ("primary analysis", 9),
        ("at the end of", 8),
        ("final analysis", 8),
        ("median follow-up", 7),
        ("at week", 5),
        ("at month", 5),
        ("interim", -5),  # Deprioritize interim
        ("exploratory", -3),
    ]

    def resolve(self, timepoints: List[Timepoint]) -> Timepoint:
        # Score each timepoint by context keywords
        # Return highest-scored as primary
```

---

### 1.4 Additional Effect Types

**Missing Types to Add:**

| Effect Type | Pattern Example | Use Case |
|-------------|-----------------|----------|
| **Subdistribution HR** | "sHR 0.72 (95% CI 0.58-0.89)" | Competing risks |
| **Cause-specific HR** | "csHR 0.65 (0.52-0.81)" | Competing risks |
| **Rate Difference** | "RD -5.2% (95% CI -8.1 to -2.3)" | Absolute measures |
| **Win Ratio** | "WR 1.28 (95% CI 1.14-1.44)" | Composite endpoints |
| **Restricted Mean ST** | "RMST diff 2.3 months (1.1-3.5)" | Time-to-event |
| **Likelihood Ratio** | "LR+ 5.2 (3.8-7.1)" | Diagnostic studies |
| **Diagnostic OR** | "DOR 12.5 (8.2-19.0)" | Diagnostic accuracy |
| **Correlation** | "r = 0.65 (95% CI 0.52-0.75)" | Continuous outcomes |

---

## Phase 2: LLM Hybrid Approach (Medium Priority)

### 2.1 Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    Input Text/PDF                        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              PASS 1: Regex Extraction                    │
│              (Current v2.12 - 100% on known patterns)    │
└─────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        Found (95%)              Not Found (5%)
              │                         │
              ▼                         ▼
┌─────────────────────┐   ┌─────────────────────────────┐
│  Validate & Return  │   │    PASS 2: LLM Extraction   │
│                     │   │    (Claude Haiku - fast)    │
└─────────────────────┘   └─────────────────────────────┘
                                        │
                                        ▼
                          ┌─────────────────────────────┐
                          │   PASS 3: Cross-Validate    │
                          │   (Regex + LLM must agree)  │
                          └─────────────────────────────┘
```

### 2.2 LLM Fallback Implementation
```python
class HybridExtractor:
    def __init__(self):
        self.regex_extractor = RCTExtractor()  # Current v2.12
        self.llm_client = anthropic.Anthropic()

    def extract(self, text: str) -> List[EffectEstimate]:
        # PASS 1: Regex (fast, free, 100% on known patterns)
        regex_results = self.regex_extractor.extract(text)

        if regex_results:
            return regex_results

        # PASS 2: LLM for unknown patterns (fallback)
        llm_results = self._llm_extract(text)

        # PASS 3: Validate LLM results
        validated = self._validate_llm_results(llm_results, text)

        return validated

    def _llm_extract(self, text: str) -> List[dict]:
        response = self.llm_client.messages.create(
            model="claude-3-haiku-20240307",  # Fast, cheap
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""Extract effect estimates from this clinical trial text.

Return JSON array with:
- effect_type: HR, OR, RR, etc.
- effect_size: numeric value
- ci_lower: lower CI bound
- ci_upper: upper CI bound
- p_value: if available

Text: {text[:2000]}

JSON:"""
            }]
        )
        return json.loads(response.content[0].text)
```

### 2.3 Cost Analysis
| Scenario | Regex Only | Hybrid (5% LLM) | Full LLM |
|----------|------------|-----------------|----------|
| 1,000 papers | $0 | ~$0.50 | ~$10 |
| 10,000 papers | $0 | ~$5 | ~$100 |
| Speed | <1ms/paper | ~1ms/paper | ~500ms/paper |

---

## Phase 3: Advanced Validation (Medium Priority)

### 3.1 Cross-Paper Validation
```python
class CrossPaperValidator:
    """Detect duplicate/conflicting data across papers"""

    def validate_trial_consistency(self, extractions: List[Extraction]):
        # Group by trial ID (NCT number, trial name)
        trials = self._group_by_trial(extractions)

        for trial_id, papers in trials.items():
            # Check if same trial reported differently
            if len(papers) > 1:
                self._check_consistency(papers)
                # Flag: "ATTR-ACT reported HR 0.70 in NEJM but HR 0.68 in EHJ"
```

### 3.2 Statistical Consistency Checks
```python
def validate_statistical_consistency(hr, ci_lower, ci_upper, p_value, events_tx, events_ctrl, n_tx, n_ctrl):
    """Cross-validate extracted values"""

    # 1. CI should contain HR
    if not (ci_lower < hr < ci_upper):
        return Error("HR outside CI bounds")

    # 2. P-value consistency with CI
    if p_value >= 0.05 and not (ci_lower <= 1.0 <= ci_upper):
        return Warning("P>=0.05 but CI doesn't cross 1.0")

    # 3. Events should be plausible given n
    if events_tx > n_tx or events_ctrl > n_ctrl:
        return Error("Events exceed sample size")

    # 4. Recalculate OR from 2x2 table
    calculated_or = (events_tx * (n_ctrl - events_ctrl)) / \
                    ((n_tx - events_tx) * events_ctrl)
    if abs(calculated_or - reported_or) / reported_or > 0.1:
        return Warning(f"Reported OR {reported_or} vs calculated {calculated_or}")
```

---

## Phase 4: Real-World PDF Validation (Medium Priority)

### 4.1 Create Gold Standard Dataset
**Sources:**
1. Download 100 open-access RCTs from PubMed Central
2. Manually annotate all effect estimates
3. Include challenging cases:
   - Multi-arm trials
   - Forest plots only (no text)
   - Tables with merged cells
   - Supplementary appendices

### 4.2 PDF Edge Cases to Test
| Case | Example | Current Status |
|------|---------|----------------|
| Scanned PDF | Old NEJM papers | Not tested |
| Two-column layout | Most journals | Tested |
| Table spanning pages | Supplement tables | Not tested |
| Forest plot only | Some Cochrane | Tested (basic) |
| Embedded formulas | Statistical papers | Not tested |
| Non-English | European journals | Limited |

---

## Phase 5: New Features (Lower Priority)

### 5.1 Network Meta-Analysis Support
```python
@dataclass
class NetworkMAResult:
    treatments: List[str]
    direct_comparisons: List[PairwiseComparison]
    indirect_comparisons: List[IndirectComparison]
    network_graph: nx.Graph
```

### 5.2 Bayesian Intervals
```python
# Detect credible vs confidence intervals
BAYESIAN_PATTERNS = [
    r'(?:95%?\s*)?(?:credible|CrI|posterior)[,:\s]+(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)',
    r'posterior\s+(?:median|mean)[,:\s]+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)',
]
```

### 5.3 GRADE Quality Assessment
```python
class GRADEExtractor:
    """Extract GRADE certainty ratings"""

    PATTERNS = [
        r'(?:GRADE|certainty)[:\s]+(high|moderate|low|very low)',
        r'(⊕⊕⊕⊕|⊕⊕⊕◯|⊕⊕◯◯|⊕◯◯◯)',  # Circle symbols
    ]
```

---

## Implementation Priority Matrix

| Feature | Impact | Effort | Priority Score |
|---------|--------|--------|----------------|
| SE/SD confusion detection | High | Low | **10** |
| Multi-arm handling | High | Medium | **8** |
| Timepoint disambiguation | High | Medium | **8** |
| LLM hybrid fallback | Medium | Medium | **6** |
| Additional effect types | Medium | Low | **7** |
| Cross-paper validation | Medium | High | **5** |
| Real PDF validation | High | High | **6** |
| Network MA support | Low | High | **3** |
| Bayesian intervals | Low | Low | **4** |
| GRADE extraction | Low | Low | **4** |

---

## Recommended Development Order

### Sprint 1 (Immediate - 1 week) ✅ COMPLETE
1. ✅ SE/SD confusion detection (8/8 = 100%)
2. ✅ Add 8 new effect types (sHR, csHR, WR, RMST, RD, DOR, LR, r)
3. ✅ Timepoint priority scoring (5/5 = 100%)
4. ✅ Multi-arm trial detection (3/3 = 100%)
5. ✅ Statistical consistency validation (6/6 = 100%)

### Sprint 2 (Short-term - 2 weeks) ✅ COMPLETE
6. ✅ Composite endpoint standardization (35/38 = 92.1%)
7. ✅ 32 trial gold standard dataset (94/94 = 100%)

### Sprint 3 (Medium-term - 1 month) ✅ COMPLETE
8. ✅ ML-based extraction (NO LLM) - sklearn ensemble classifiers
   - Feature extraction (29 features)
   - Effect type classifier (RF + LR + GB ensemble)
   - Confidence scoring (pattern, plausibility, context, CI)
   - 34/34 tests passing (100%)
9. ✅ Cross-paper validation
   - Detects value mismatches (>5% difference)
   - Detects non-overlapping CIs
   - Groups by trial ID (NCT number)
10. ⏳ Expand gold standard to 100+ trials (32/100 = 32%)

### Sprint 4 (Long-term - 2 months)
11. Network MA support
12. Full 500 PDF validation
13. API/CLI polish
14. Optional: LLM hybrid integration (deferred per user preference)

---

## Success Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Test cases | 1,118 (922+32+38+94+34) | 1,500+ | 75% |
| Effect types | 14 (6 + 8) | 14+ | ✅ 100% |
| Gold standard trials | 32 | 100+ | 32% |
| Gold standard effects | 94/94 (100%) | 95%+ | ✅ Done |
| Composite endpoint | 35/38 (92.1%) | 90%+ | ✅ Done |
| SE/SD confusion detection | 100% | 95%+ | ✅ Done |
| Multi-arm support | 100% | 100% | ✅ Done |
| Statistical consistency | 100% | 95%+ | ✅ Done |
| Timepoint priority | 100% | 95%+ | ✅ Done |
| ML extraction | 34/34 (100%) | 90%+ | ✅ Done |
| Cross-paper validation | 3/3 (100%) | 90%+ | ✅ Done |
| Confidence scoring | 4/4 (100%) | 90%+ | ✅ Done |
| LLM fallback coverage | N/A | Deferred | User preference |
| Overall accuracy | 100% | 100% | ✅ Done |

---

## References

1. [Common Statistical Errors in Meta-Analyses](https://onlinelibrary.wiley.com/doi/full/10.1002/cesm.70013)
2. [Data Extraction Errors with SMD](https://www.researchgate.net/publication/6187045)
3. [Application Errors in Pairwise Meta-Analyses](https://www.sciencedirect.com/science/article/pii/S0895435624000866)
4. [Covidence Data Extraction Guide](https://www.covidence.org/wp-content/uploads/2024/01/A_practical_guide-Data-Extraction_for_Intervention_Systematic_Reviews_2024.pdf)
