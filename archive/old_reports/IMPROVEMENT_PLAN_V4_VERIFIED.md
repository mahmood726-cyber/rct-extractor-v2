# RCT Extractor v4.0 - Verified Extraction Architecture
## Proof-Carrying Numbers + Team-of-Rivals + Deterministic Verification

**Date:** 2026-01-28
**Approach:** No GPU, No LLM - Pure Deterministic Verification
**Inspired by:** PCN, QWED, Team-of-Rivals, FoVer patterns

---

## Executive Summary

Transform RCT Extractor from "pattern matching with confidence scores" to **mechanically verified extraction** where every number carries proof of correctness. This eliminates the "numeric hallucination" failure mode that is catastrophic for meta-analysis.

---

## Core Architecture: Three Pillars

```
                    ┌─────────────────────────────────────────┐
                    │         PROOF-CARRYING NUMBERS          │
                    │  "No number accepted without proof"     │
                    └─────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
        ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
        │ TEAM OF       │   │ DETERMINISTIC │   │ CROSS-VALUE   │
        │ RIVALS        │   │ VERIFICATION  │   │ CONSISTENCY   │
        │               │   │ (QWED-style)  │   │ CHECKER       │
        │ Multiple      │   │               │   │               │
        │ independent   │   │ SymPy/Math    │   │ CI contains   │
        │ extractors    │   │ verification  │   │ point est?    │
        │ must agree    │   │ of all        │   │ SE matches    │
        └───────────────┘   │ relationships │   │ CI width?     │
                            └───────────────┘   └───────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────┐
                    │         VERIFIED EXTRACTION             │
                    │  Only outputs that pass ALL checks      │
                    └─────────────────────────────────────────┘
```

---

## Pillar 1: Proof-Carrying Numbers (PCN)

### Concept
Every extracted number must carry a **proof certificate** that demonstrates:
1. Where it came from (provenance)
2. How it was parsed (method)
3. Why it's correct (verification)

### Implementation

```python
@dataclass
class ProofCertificate:
    """Certificate proving a number's validity"""
    # Provenance
    source_text: str
    char_start: int
    char_end: int
    extraction_method: str  # "pattern_HR_01", "pattern_CI_03"

    # Verification checks passed
    checks_passed: List[str]
    # - "SYNTAX_VALID": Matches expected number format
    # - "RANGE_PLAUSIBLE": Within domain bounds
    # - "CI_CONTAINS_POINT": Point estimate within CI
    # - "CI_ORDERED": Lower < Upper
    # - "SE_CONSISTENT": SE matches CI width
    # - "RIVALS_AGREE": Multiple extractors agree

    # Verification failures
    checks_failed: List[str]

    # Cryptographic hash of source + value
    integrity_hash: str

    @property
    def is_verified(self) -> bool:
        """Only verified if ALL critical checks pass"""
        critical_checks = {"CI_CONTAINS_POINT", "CI_ORDERED", "RANGE_PLAUSIBLE"}
        return critical_checks.issubset(set(self.checks_passed))


@dataclass
class ProofCarryingNumber:
    """A number that carries its own proof of correctness"""
    value: float
    certificate: ProofCertificate

    def render(self) -> str:
        """Only render if verified - refuse otherwise"""
        if not self.certificate.is_verified:
            raise VerificationError(
                f"Cannot render unverified number. "
                f"Failed checks: {self.certificate.checks_failed}"
            )
        return str(self.value)
```

### Verification Checks

| Check | Description | Implementation |
|-------|-------------|----------------|
| `SYNTAX_VALID` | Number matches expected format | Regex + type coercion |
| `RANGE_PLAUSIBLE` | Within domain bounds | HR: 0.01-50, OR: 0.01-100, etc. |
| `CI_CONTAINS_POINT` | Point estimate within CI | `ci_low <= value <= ci_high` |
| `CI_ORDERED` | CI bounds correct order | `ci_low < ci_high` |
| `CI_WIDTH_REASONABLE` | CI not impossibly narrow/wide | Width vs effect size ratio |
| `SE_CONSISTENT` | SE matches CI width | `SE ≈ (ci_high - ci_low) / 3.92` |
| `P_VALUE_CONSISTENT` | P-value matches CI | `p<0.05 ↔ CI excludes null` |
| `RIVALS_AGREE` | Multiple extractors agree | Team-of-Rivals consensus |

---

## Pillar 2: Team-of-Rivals Extraction

### Concept
Multiple **independent extractors** with different approaches must agree before accepting an extraction. Disagreements trigger detailed analysis.

### Architecture

```python
class TeamOfRivals:
    """Multiple independent extractors that must reach consensus"""

    def __init__(self):
        self.extractors = [
            PatternExtractor(),       # Regex-based (current v3.0)
            GrammarExtractor(),       # CFG-based parsing
            StateMachineExtractor(),  # FSM-based extraction
            ChunkExtractor(),         # Sliding window + rules
        ]
        self.critic = ExtractionCritic()

    def extract(self, text: str) -> List[VerifiedExtraction]:
        # Phase 1: Independent extraction
        all_extractions = {}
        for extractor in self.extractors:
            extractions = extractor.extract(text)
            all_extractions[extractor.name] = extractions

        # Phase 2: Find consensus
        consensus = self.find_consensus(all_extractions)

        # Phase 3: Critic review of disagreements
        for disagreement in self.find_disagreements(all_extractions):
            resolution = self.critic.resolve(disagreement, text)
            if resolution.confident:
                consensus.append(resolution.extraction)
            else:
                # Flag for human review
                consensus.append(resolution.extraction.with_flag("RIVALS_DISAGREE"))

        return consensus

    def find_consensus(self, all_extractions: Dict) -> List[VerifiedExtraction]:
        """Find extractions where majority agree"""
        consensus = []

        # Group by (effect_type, value, ci_low, ci_high)
        votes = defaultdict(list)
        for extractor_name, extractions in all_extractions.items():
            for ext in extractions:
                key = self.extraction_key(ext)
                votes[key].append(extractor_name)

        # Require majority agreement
        threshold = len(self.extractors) // 2 + 1
        for key, voters in votes.items():
            if len(voters) >= threshold:
                ext = self.key_to_extraction(key)
                ext.certificate.checks_passed.append("RIVALS_AGREE")
                ext.certificate.agreement_count = len(voters)
                consensus.append(ext)

        return consensus
```

### Extractor Types

#### 1. Pattern Extractor (Current)
- 180+ regex patterns
- Fast, precise for known formats
- Weakness: Misses novel formats

#### 2. Grammar Extractor (New)
```python
class GrammarExtractor:
    """Context-free grammar based extraction"""

    # Grammar for effect estimates
    GRAMMAR = """
    effect_statement: effect_type value ci_clause?
    effect_type: HR | OR | RR | MD | SMD | ARD
    value: NUMBER
    ci_clause: ci_marker ci_bounds
    ci_marker: "95%" "CI" | "CI" | "confidence interval"
    ci_bounds: "(" NUMBER separator NUMBER ")"
              | "[" NUMBER separator NUMBER "]"
    separator: "-" | "to" | ","
    NUMBER: /\d+\.?\d*/
    """

    def extract(self, text: str) -> List[Extraction]:
        # Use Lark or similar parser
        parser = Lark(self.GRAMMAR, start='effect_statement')
        # Find all matches in text
        ...
```

#### 3. State Machine Extractor (New)
```python
class StateMachineExtractor:
    """Finite state machine for extraction"""

    # States: START -> EFFECT_TYPE -> VALUE -> CI_START -> CI_LOW -> CI_HIGH -> ACCEPT

    def extract(self, text: str) -> List[Extraction]:
        state = "START"
        current = {}

        for token in self.tokenize(text):
            if state == "START" and token.is_effect_type:
                state = "EFFECT_TYPE"
                current['type'] = token.value
            elif state == "EFFECT_TYPE" and token.is_number:
                state = "VALUE"
                current['value'] = token.value
            # ... state transitions
```

#### 4. Chunk Extractor (New)
```python
class ChunkExtractor:
    """Sliding window with rule-based extraction"""

    def extract(self, text: str) -> List[Extraction]:
        results = []
        # Slide window of 50-100 chars
        for chunk in self.sliding_window(text, size=100, step=20):
            # Look for effect type keyword
            if self.contains_effect_keyword(chunk):
                # Extract numbers in chunk
                numbers = self.extract_numbers(chunk)
                # Apply rules to identify value, CI
                if extraction := self.apply_rules(chunk, numbers):
                    results.append(extraction)
        return results
```

### Critic Module

```python
class ExtractionCritic:
    """Analyzes disagreements and provides resolution"""

    def resolve(self, disagreement: Disagreement, text: str) -> Resolution:
        # 1. Analyze what each extractor found
        analyses = []
        for ext in disagreement.extractions:
            analyses.append(self.analyze_extraction(ext, text))

        # 2. Apply tie-breaking rules
        # Rule 1: More context wins (longer source_text)
        # Rule 2: More specific pattern wins
        # Rule 3: Better CI match wins
        winner = self.apply_tiebreakers(analyses)

        # 3. Determine confidence
        confidence = self.calculate_confidence(analyses, winner)

        return Resolution(
            extraction=winner,
            confident=confidence > 0.8,
            reasoning=self.explain_decision(analyses, winner)
        )
```

---

## Pillar 3: Deterministic Verification Engine (QWED-style)

### Concept
Treat ALL extractions as **untrusted** until verified by deterministic mathematical checks. Use SymPy/math for formal verification.

### Implementation

```python
import sympy as sp
from sympy import Symbol, solve, Eq, log, exp

class DeterministicVerifier:
    """Formal verification of extracted values"""

    def verify_extraction(self, ext: Extraction) -> VerificationResult:
        checks = []

        # Check 1: CI contains point estimate
        checks.append(self.verify_ci_contains_point(ext))

        # Check 2: SE consistent with CI (for ratios, on log scale)
        checks.append(self.verify_se_consistency(ext))

        # Check 3: P-value consistent with CI
        if ext.p_value:
            checks.append(self.verify_p_value_consistency(ext))

        # Check 4: Mathematical relationships hold
        checks.append(self.verify_mathematical_consistency(ext))

        return VerificationResult(
            passed=all(c.passed for c in checks),
            checks=checks
        )

    def verify_se_consistency(self, ext: Extraction) -> Check:
        """Verify SE matches CI width using formal math"""
        if ext.effect_type in [EffectType.HR, EffectType.OR, EffectType.RR]:
            # For ratios: SE on log scale
            # CI = exp(log(value) ± 1.96 * SE)
            # Therefore: SE = (log(ci_high) - log(ci_low)) / (2 * 1.96)

            expected_se = (log(ext.ci.upper) - log(ext.ci.lower)) / (2 * 1.96)

            if ext.standard_error:
                # Verify reported SE matches expected
                tolerance = 0.01 * expected_se  # 1% tolerance
                matches = abs(ext.standard_error - expected_se) < tolerance
                return Check(
                    name="SE_CONSISTENT",
                    passed=matches,
                    expected=float(expected_se),
                    actual=ext.standard_error
                )

        return Check(name="SE_CONSISTENT", passed=True, note="SE calculated, not verified")

    def verify_p_value_consistency(self, ext: Extraction) -> Check:
        """Verify p-value consistent with CI"""
        # If p < 0.05, CI should exclude null (1.0 for ratios, 0 for differences)

        if ext.effect_type in [EffectType.HR, EffectType.OR, EffectType.RR]:
            null_value = 1.0
        else:
            null_value = 0.0

        ci_excludes_null = not (ext.ci.lower <= null_value <= ext.ci.upper)
        p_significant = ext.p_value < 0.05

        # These should match
        consistent = ci_excludes_null == p_significant

        return Check(
            name="P_VALUE_CONSISTENT",
            passed=consistent,
            note=f"CI excludes null: {ci_excludes_null}, p<0.05: {p_significant}"
        )

    def verify_mathematical_consistency(self, ext: Extraction) -> Check:
        """Use SymPy to verify mathematical relationships"""

        # For HR/OR/RR: verify CI is symmetric on log scale
        if ext.effect_type in [EffectType.HR, EffectType.OR, EffectType.RR]:
            log_value = sp.log(ext.point_estimate)
            log_lower = sp.log(ext.ci.lower)
            log_upper = sp.log(ext.ci.upper)

            # Distance from value to bounds should be equal (symmetric CI)
            dist_lower = float(log_value - log_lower)
            dist_upper = float(log_upper - log_value)

            # Allow 5% asymmetry
            symmetric = abs(dist_lower - dist_upper) < 0.05 * (dist_lower + dist_upper) / 2

            return Check(
                name="LOG_SYMMETRIC",
                passed=symmetric,
                note=f"Lower dist: {dist_lower:.4f}, Upper dist: {dist_upper:.4f}"
            )

        return Check(name="MATH_CONSISTENT", passed=True)
```

### Cross-Value Consistency Checker

```python
class CrossValueChecker:
    """Check consistency across multiple extracted values"""

    def check_study_consistency(self, extractions: List[Extraction]) -> List[Issue]:
        issues = []

        # Check 1: Multiple HRs should have consistent direction
        hrs = [e for e in extractions if e.effect_type == EffectType.HR]
        if len(hrs) > 1:
            directions = [1 if e.point_estimate > 1 else -1 for e in hrs]
            if len(set(directions)) > 1:
                issues.append(Issue(
                    "INCONSISTENT_DIRECTION",
                    "HRs have mixed directions (some >1, some <1)"
                ))

        # Check 2: Primary outcome should have narrower CI than secondary
        # (More events typically)

        # Check 3: If NNT reported, should match ARD
        # NNT = 1 / ARD
        nnts = [e for e in extractions if e.effect_type == EffectType.NNT]
        ards = [e for e in extractions if e.effect_type == EffectType.ARD]
        if nnts and ards:
            for nnt in nnts:
                expected_ard = 1 / nnt.point_estimate
                for ard in ards:
                    if abs(ard.point_estimate - expected_ard) > 0.01:
                        issues.append(Issue(
                            "NNT_ARD_MISMATCH",
                            f"NNT {nnt.point_estimate} implies ARD {expected_ard:.3f}, "
                            f"but found ARD {ard.point_estimate}"
                        ))

        return issues
```

---

## Integration: Verified Extraction Pipeline

```python
class VerifiedExtractionPipeline:
    """Complete pipeline with all three pillars"""

    def __init__(self):
        self.rivals = TeamOfRivals()
        self.verifier = DeterministicVerifier()
        self.cross_checker = CrossValueChecker()

    def extract(self, text: str) -> VerifiedOutput:
        # Step 1: Team-of-Rivals extraction
        candidate_extractions = self.rivals.extract(text)

        # Step 2: Deterministic verification of each extraction
        verified_extractions = []
        rejected_extractions = []

        for ext in candidate_extractions:
            verification = self.verifier.verify_extraction(ext)

            if verification.passed:
                # Create proof-carrying number
                pcn = self.create_pcn(ext, verification)
                verified_extractions.append(pcn)
            else:
                ext.rejection_reason = verification.failed_checks
                rejected_extractions.append(ext)

        # Step 3: Cross-value consistency check
        consistency_issues = self.cross_checker.check_study_consistency(
            [e.extraction for e in verified_extractions]
        )

        # Step 4: Flag any consistency issues
        if consistency_issues:
            for issue in consistency_issues:
                # Find affected extractions and flag them
                self.flag_related_extractions(verified_extractions, issue)

        return VerifiedOutput(
            verified=verified_extractions,
            rejected=rejected_extractions,
            consistency_issues=consistency_issues,
            audit_log=self.create_audit_log()
        )

    def create_pcn(self, ext: Extraction, verification: VerificationResult) -> ProofCarryingExtraction:
        """Create proof-carrying extraction"""
        certificate = ProofCertificate(
            source_text=ext.source_text,
            char_start=ext.char_start,
            char_end=ext.char_end,
            extraction_method=ext.extraction_method,
            checks_passed=[c.name for c in verification.checks if c.passed],
            checks_failed=[c.name for c in verification.checks if not c.passed],
            integrity_hash=self.compute_hash(ext)
        )

        return ProofCarryingExtraction(
            extraction=ext,
            certificate=certificate
        )
```

---

## New Validation Framework

### Verification-Aware Metrics

```python
@dataclass
class VerificationMetrics:
    """Metrics for verified extraction"""

    # Extraction performance
    sensitivity: float          # True positives / All positives
    specificity: float          # True negatives / All negatives

    # Verification performance
    verification_rate: float    # Verified / Total extracted
    false_verification: float   # Verified but wrong / Verified
    rejection_rate: float       # Rejected / Total extracted
    false_rejection: float      # Rejected but correct / Rejected

    # Consensus metrics
    full_consensus: float       # All 4 extractors agree
    majority_consensus: float   # 3+ extractors agree
    split_decision: float       # 2-2 split

    # Consistency metrics
    cross_value_issues: int     # Number of consistency issues found
```

### Test Cases for Verification

```python
VERIFICATION_TEST_CASES = [
    # Should PASS verification
    VerificationCase(
        text="HR 0.74 (95% CI 0.65-0.85)",
        expected_checks_pass=["CI_CONTAINS_POINT", "CI_ORDERED", "LOG_SYMMETRIC"],
    ),

    # Should FAIL: CI doesn't contain point estimate
    VerificationCase(
        text="HR 0.50 (95% CI 0.65-0.85)",  # 0.50 not in [0.65, 0.85]
        expected_checks_fail=["CI_CONTAINS_POINT"],
    ),

    # Should FAIL: CI bounds reversed
    VerificationCase(
        text="HR 0.74 (95% CI 0.85-0.65)",  # 0.85 > 0.65
        expected_checks_fail=["CI_ORDERED"],
    ),

    # Should FAIL: P-value inconsistent with CI
    VerificationCase(
        text="HR 0.95 (95% CI 0.80-1.12, P=0.001)",  # CI includes 1.0 but p<0.05
        expected_checks_fail=["P_VALUE_CONSISTENT"],
    ),

    # Should FLAG: Highly asymmetric CI on log scale
    VerificationCase(
        text="HR 0.50 (95% CI 0.10-0.90)",  # Very asymmetric
        expected_checks_fail=["LOG_SYMMETRIC"],
    ),
]
```

---

## Implementation Roadmap

### Phase 1: Proof-Carrying Numbers (Week 1-2)
| Task | Deliverable |
|------|-------------|
| Design PCN data structures | `ProofCertificate`, `ProofCarryingNumber` |
| Implement verification checks | 8+ deterministic checks |
| Add rendering gate | Numbers only render if verified |
| Create verification test suite | 50+ verification cases |

### Phase 2: Team-of-Rivals (Week 3-5)
| Task | Deliverable |
|------|-------------|
| Implement Grammar Extractor | Lark-based CFG parser |
| Implement State Machine Extractor | FSM extraction |
| Implement Chunk Extractor | Sliding window extraction |
| Build consensus algorithm | Majority voting |
| Implement Critic module | Disagreement resolution |

### Phase 3: Deterministic Verification (Week 6-7)
| Task | Deliverable |
|------|-------------|
| Integrate SymPy | Mathematical verification |
| Implement cross-value checks | Consistency validation |
| Build rejection pipeline | Verified vs rejected outputs |

### Phase 4: Integration & Validation (Week 8)
| Task | Deliverable |
|------|-------------|
| Integrate all pillars | `VerifiedExtractionPipeline` |
| Comprehensive validation | Test on all 220+ cases |
| Performance benchmarking | Latency, accuracy metrics |
| Documentation | Updated API docs |

---

## Expected Outcomes

### Accuracy Improvements

| Metric | v3.0 | v4.0 Target | Method |
|--------|------|-------------|--------|
| False positives | 0% | 0% | Maintained via verification |
| Verified correct | N/A | 99%+ | PCN ensures correctness |
| Unverified (flagged) | N/A | <5% | Human review queue |
| Consistency issues caught | N/A | 95%+ | Cross-value checking |

### Trust Improvements

| Aspect | v3.0 | v4.0 |
|--------|------|------|
| Provenance | Source text only | Full certificate |
| Verification | Confidence score | Deterministic proof |
| Auditability | Limited | Complete audit trail |
| Reproducibility | Good | Perfect (deterministic) |

---

## Dependencies (No GPU/LLM)

```
# Core (existing)
python >= 3.9

# New dependencies
sympy >= 1.12        # Mathematical verification
lark >= 1.1          # Grammar parsing
```

**Total new dependencies: 2 packages**

---

## Conclusion

This architecture transforms RCT Extractor from a "best-effort" system to a **verified extraction platform** where:

1. **Every number carries proof** - Cannot render unverified values
2. **Multiple independent methods must agree** - Team-of-Rivals consensus
3. **Mathematical consistency is enforced** - Deterministic verification
4. **Cross-value relationships are checked** - Catches impossible combinations

This eliminates the "numeric hallucination" failure mode that is catastrophic for meta-analysis, **without requiring GPU or LLM**.

---

*Plan created: 2026-01-28*
*Approach: PCN + Team-of-Rivals + QWED-style verification*
*No GPU, No LLM, Pure Deterministic*
