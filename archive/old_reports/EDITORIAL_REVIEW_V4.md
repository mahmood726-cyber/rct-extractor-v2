# Editorial Review: RCT Extractor v4.0
## Research Synthesis Methods

**Manuscript ID:** RSM-2026-0128-V4
**Title:** Verified Effect Estimate Extraction with Proof-Carrying Numbers and Multi-Extractor Consensus
**Version:** 4.0
**Review Date:** 2026-01-28
**Editor:** Associate Editor, Methods Development
**Submission Type:** Major Methods Paper (Follow-up to RSM-2026-0128-R4)

---

## EXECUTIVE SUMMARY

This manuscript presents a significant methodological advancement building upon the accepted v3.0 extractor. The authors introduce a novel "verified extraction" architecture incorporating three theoretical pillars: Proof-Carrying Numbers (PCN), Team-of-Rivals consensus extraction, and deterministic mathematical verification. While the conceptual framework is innovative and addresses important concerns about extraction reliability, there are notable gaps between the theoretical ambitions and empirical performance.

---

## SUMMARY RECOMMENDATION

**Decision: MAJOR REVISION REQUIRED**

The theoretical framework is compelling, but performance regressions from v3.0 and incomplete validation require substantial revision before acceptance.

---

## DETAILED REVIEW

### 1. THEORETICAL CONTRIBUTION

**Assessment: STRONG**

The manuscript makes three notable theoretical contributions:

#### 1.1 Proof-Carrying Numbers (PCN)
The concept of numbers that "carry their own proof of correctness" is elegant and addresses a real gap in automated extraction. The fail-closed principle (unverified values cannot be rendered) provides a strong safety guarantee.

**Strengths:**
- Clear provenance tracking
- Integrity hashing for tamper detection
- Well-defined verification checks

**Concerns:**
- The "proof" is not a formal mathematical proof but rather a set of heuristic checks
- The term "proof-carrying" may overstate the rigor; "verification-carrying" would be more accurate

#### 1.2 Team-of-Rivals Architecture
Multiple independent extractors with consensus is a sound approach to reducing false positives and increasing reliability.

**Strengths:**
- Diversity of extraction methods (regex, grammar, FSM, chunking)
- Consensus mechanism with critic for disagreement resolution
- Negative context filtering across all extractors

**Concerns:**
- No unanimous agreement achieved in validation (0/4 unanimous)
- Heavy reliance on PatternExtractor undermines independence
- GrammarExtractor and ChunkExtractor appear to contribute false positives

#### 1.3 Deterministic Verification
The mathematical verification layer using SymPy is well-conceived.

**Strengths:**
- Formal proofs for CI containment and SE calculation
- Clear verification levels (PROVEN, VIOLATED, etc.)
- Cross-value consistency checks

**Concerns:**
- SymPy is optional, degrading to heuristic checks without it
- Some checks (log symmetry) are non-critical warnings only

---

### 2. EMPIRICAL PERFORMANCE

**Assessment: CONCERNING**

#### 2.1 Sensitivity Regression

| Dataset | v3.0 | v4.0 | Change |
|---------|------|------|--------|
| Original (167) | 100% | 91.0% | **-9.0%** |
| Held-out (53) | 100% | 81.1% | **-18.9%** |
| Combined | 100% | 88.6% | **-11.4%** |

**Critical Issue:** The v4.0 architecture achieves substantially lower sensitivity than v3.0. This regression must be explained and addressed.

**Questions for Authors:**
1. Why does the Team-of-Rivals approach lose 11.4% sensitivity compared to the single-extractor v3.0?
2. Which extractor(s) are failing to detect the missed cases?
3. Is the consensus requirement (50% agreement) too stringent?

#### 2.2 False Positive Rate

| Metric | v3.0 | v4.0 | Change |
|--------|------|------|--------|
| FPR | 0.0% | 9.3% | **+9.3%** |
| Specificity | 100% | 90.7% | **-9.3%** |

**Critical Issue:** v3.0 achieved 0% FPR on the same negative test set. The v4.0 architecture introduces false positives that were previously avoided.

**Questions for Authors:**
1. What is causing the new false positives?
2. The categories with FP (interpretation: 2, other_study: 5, power_calc: 2, adversarial: 1) suggest the negative context filtering is incomplete
3. Why does the multi-extractor approach perform worse than single-extractor for specificity?

#### 2.3 Consensus Analysis

The validation reports 0% unanimous agreement (0/4 extractors agreed completely). This raises concerns about the independence and accuracy of the non-pattern extractors.

**Required Analysis:**
- Breakdown of which extractors agree/disagree
- Accuracy of each extractor independently
- Analysis of cases where Pattern agrees but others disagree (or vice versa)

---

### 3. METHODOLOGICAL CONCERNS

#### 3.1 Comparison Baseline
The manuscript should include direct comparison with v3.0 on identical test cases, showing which specific cases are lost/gained.

#### 3.2 Fail-Closed Trade-offs
The fail-closed principle is admirable for safety but creates a usability trade-off. If 11.4% of valid extractions are rejected, this significantly impacts practical utility.

**Question:** What is the false rejection rate (valid extractions marked as unverified)?

#### 3.3 Verification vs. Detection
The architecture conflates two distinct problems:
1. **Detection:** Finding effect estimates in text
2. **Verification:** Confirming extracted values are correct

The current approach uses verification to filter detection, which may explain the sensitivity loss.

#### 3.4 Missing Ablation Studies
The manuscript lacks ablation studies showing contribution of each component:
- Performance with only PatternExtractor + verification
- Performance with Team-of-Rivals but no verification
- Performance with different consensus thresholds

---

### 4. SPECIFIC TECHNICAL ISSUES

#### 4.1 GrammarExtractor Limitations
The grammar-based approach appears to parse incompletely. Example from validation:
```
"hazard ratio 0.71; 95% confidence interval 0.58-0.87"
```
Does the grammar handle semicolon-separated formats?

#### 4.2 ChunkExtractor False Positives
The sliding window approach may extract spurious number triplets. What constraints prevent extracting unrelated numbers?

#### 4.3 Negative Context Patterns
The negative context list appears incomplete. Cases like "In a previous meta-analysis, HR was 0.72..." are still triggering false positives.

**Recommendation:** Expand negative context patterns:
- "In a previous..."
- "A recent study found..."
- "Literature suggests..."
- "Published data show..."

#### 4.4 SE Calculation Verification
The SE verification allows 5% tolerance. Is this appropriate? Some studies report SE with high precision.

---

### 5. DOCUMENTATION AND REPRODUCIBILITY

**Assessment: GOOD**

The documentation is comprehensive:
- `V4_IMPLEMENTATION_SUMMARY.md` provides clear architecture overview
- Code is well-structured with clear module separation
- Validation script is reproducible

**Minor Issues:**
- API documentation not updated for v4.0 classes
- README.md still references v3.0

---

## REQUIRED REVISIONS

### Critical (Must Address)

1. **Explain Sensitivity Regression**
   - Provide detailed analysis of 24 missed cases in original validation
   - Provide detailed analysis of 10 missed cases in held-out validation
   - Identify which extractor(s) fail and why

2. **Eliminate False Positives**
   - v3.0 achieved 0% FPR; v4.0 should match or explain why regression is acceptable
   - Expand negative context patterns
   - Consider requiring Pattern extractor agreement for verified status

3. **Ablation Studies**
   - Test each extractor independently
   - Test consensus thresholds (25%, 50%, 75%, 100%)
   - Test verification alone vs. consensus alone

4. **Performance Comparison Table**
   - Side-by-side v3.0 vs v4.0 on all test sets
   - Show what is gained (verified provenance) vs. what is lost (sensitivity)

### Major (Should Address)

5. **Improve Non-Pattern Extractors**
   - GrammarExtractor needs expanded grammar rules
   - StateMachineExtractor needs more state transitions
   - ChunkExtractor needs tighter constraints

6. **Clarify Terminology**
   - "Proof-Carrying" suggests formal proofs; consider "Verification-Carrying"
   - Distinguish between "verified" (passed checks) and "correct" (matches ground truth)

7. **Add Confidence Interval Analysis**
   - Report 95% CI for sensitivity and specificity estimates
   - Perform bootstrap analysis for robustness

### Minor (Consider Addressing)

8. Update API documentation for v4.0 classes
9. Update README.md to reflect v4.0 architecture
10. Add timing benchmarks (v4.0 presumably slower due to multiple extractors)

---

## STATISTICAL REPORTING REQUIREMENTS

The revision must include:

| Metric | Required |
|--------|----------|
| Sensitivity | Point estimate + 95% CI |
| Specificity | Point estimate + 95% CI |
| Per-extractor accuracy | For all 4 extractors |
| Agreement rates | Pairwise between extractors |
| Calibration (ECE) | Not reported in v4.0 |

---

## COMPARISON WITH v3.0

| Criterion | v3.0 | v4.0 | Assessment |
|-----------|------|------|------------|
| Sensitivity | 100% | 88.6% | **Regression** |
| Specificity | 100% | 90.7% | **Regression** |
| ECE | 0.012 | Not reported | **Missing** |
| Provenance | Basic | Comprehensive | **Improvement** |
| Verification | None | Mathematical | **Improvement** |
| Architecture | Single | Multi-extractor | **Innovation** |

---

## EDITORIAL ASSESSMENT

### Strengths
1. Novel theoretical framework with practical applications
2. Fail-closed principle addresses real safety concerns
3. Comprehensive provenance tracking
4. Well-documented implementation

### Weaknesses
1. Performance regression from v3.0 not adequately explained
2. False positives reintroduced
3. No unanimous consensus achieved
4. Missing ablation studies

### Potential Impact
If the performance issues are resolved, this architecture could set a new standard for verified automated extraction in systematic reviews.

---

## DECISION

**MAJOR REVISION REQUIRED**

The theoretical contribution is significant, but the empirical performance regressions must be addressed before publication. The authors should:

1. Achieve sensitivity ≥95% (within 5% of v3.0)
2. Achieve FPR ≤2% (close to v3.0's 0%)
3. Provide ablation studies demonstrating value of each component
4. Report calibration metrics (ECE, MCE)

The manuscript has potential for high impact but requires substantial additional work.

---

## TIMELINE

The authors are requested to submit a revised manuscript within **60 days** addressing all critical and major revisions.

---

*Review completed by Associate Editor, Methods Development*
*Research Synthesis Methods*
*Date: 2026-01-28*
