"""
Deterministic Verification Engine for RCT Extractor v4.0
=========================================================

QWED-style formal verification of extracted values.
Uses SymPy (optional) for symbolic mathematics and proves relationships.
Falls back to pure-math implementation when SymPy is not installed.

Verification Types:
1. Mathematical consistency (CI bounds, SE, p-values)
2. Cross-value relationships (transformations between effect types)
3. Plausibility bounds (domain constraints)
4. Provenance verification (tracing back to source)

All verification is deterministic - same input always gives same result.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

# Try importing sympy, fallback to manual implementation
try:
    import sympy as sp
    from sympy import Symbol, log, exp, sqrt, Eq, solve, simplify
    from sympy.logic.boolalg import And, Or
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False


class VerificationLevel(Enum):
    """Levels of verification certainty"""
    PROVEN = "proven"           # Mathematically proven
    CONSISTENT = "consistent"   # No contradictions found
    UNCERTAIN = "uncertain"     # Cannot determine
    VIOLATED = "violated"       # Contradiction detected


@dataclass
class Constraint:
    """A mathematical constraint to verify"""
    name: str
    description: str
    expression: str  # Human-readable expression
    is_satisfied: Optional[bool] = None
    violation_message: str = ""
    is_critical: bool = True


@dataclass
class VerificationProof:
    """Formal proof of verification"""
    theorem: str
    given: List[str]
    steps: List[str]
    conclusion: str
    is_valid: bool
    level: VerificationLevel


@dataclass
class DeterministicVerificationResult:
    """Complete verification result"""
    constraints: List[Constraint]
    proofs: List[VerificationProof]
    overall_level: VerificationLevel
    all_critical_satisfied: bool
    warnings: List[str]
    verification_hash: str  # Deterministic hash of result


# =============================================================================
# SYMBOLIC VERIFICATION ENGINE
# =============================================================================

class SymbolicVerifier:
    """
    Uses SymPy for symbolic verification when available.
    Falls back to numeric verification otherwise.
    """

    def __init__(self):
        self.use_sympy = SYMPY_AVAILABLE

    def verify_ci_contains_point(self, value: float, ci_lower: float, ci_upper: float) -> Constraint:
        """Verify point estimate is within CI"""
        if self.use_sympy:
            v, l, u = sp.Symbol('v'), sp.Symbol('l'), sp.Symbol('u')
            constraint_expr = sp.And(l <= v, v <= u)
            is_satisfied = constraint_expr.subs([(v, value), (l, ci_lower), (u, ci_upper)])
            is_satisfied = bool(is_satisfied)
        else:
            is_satisfied = ci_lower <= value <= ci_upper

        return Constraint(
            name="CI_CONTAINS_POINT",
            description="Point estimate must lie within confidence interval",
            expression=f"{ci_lower} <= {value} <= {ci_upper}",
            is_satisfied=is_satisfied,
            violation_message="" if is_satisfied else f"Point {value} outside CI [{ci_lower}, {ci_upper}]",
            is_critical=True,
        )

    def verify_ci_ordered(self, ci_lower: float, ci_upper: float) -> Constraint:
        """Verify CI bounds are correctly ordered"""
        is_satisfied = ci_lower <= ci_upper

        return Constraint(
            name="CI_ORDERED",
            description="Lower bound must be less than upper bound",
            expression=f"{ci_lower} < {ci_upper}",
            is_satisfied=is_satisfied,
            violation_message="" if is_satisfied else f"CI bounds reversed: {ci_lower} >= {ci_upper}",
            is_critical=True,
        )

    def verify_se_from_ci(self, effect_type: str, ci_lower: float, ci_upper: float,
                          reported_se: Optional[float] = None) -> Tuple[Constraint, Optional[float]]:
        """
        Verify SE is consistent with CI width.
        Also calculates SE if not reported.

        For ratios (HR, OR, RR): SE = (log(upper) - log(lower)) / (2 * 1.96)
        For differences (MD, ARD): SE = (upper - lower) / (2 * 1.96)
        """
        calculated_se = None

        try:
            if effect_type in ['HR', 'OR', 'RR', 'IRR']:
                if ci_lower <= 0 or ci_upper <= 0:
                    return Constraint(
                        name="SE_CONSISTENT",
                        description="SE consistent with CI width",
                        expression="Cannot compute for non-positive CI",
                        is_satisfied=None,
                        is_critical=False,
                    ), None

                if self.use_sympy:
                    l, u = sp.Symbol('l', positive=True), sp.Symbol('u', positive=True)
                    se_expr = (sp.log(u) - sp.log(l)) / (2 * 1.96)
                    calculated_se = float(se_expr.subs([(l, ci_lower), (u, ci_upper)]))
                else:
                    calculated_se = (math.log(ci_upper) - math.log(ci_lower)) / (2 * 1.96)
            else:
                if self.use_sympy:
                    l, u = sp.Symbol('l'), sp.Symbol('u')
                    se_expr = (u - l) / (2 * 1.96)
                    calculated_se = float(se_expr.subs([(l, ci_lower), (u, ci_upper)]))
                else:
                    calculated_se = (ci_upper - ci_lower) / (2 * 1.96)

            # Check against reported SE
            if reported_se is not None:
                tolerance = 0.05 * calculated_se if calculated_se > 0.01 else 0.01
                is_consistent = abs(reported_se - calculated_se) <= tolerance

                return Constraint(
                    name="SE_CONSISTENT",
                    description="Reported SE matches calculated SE",
                    expression=f"|{reported_se} - {calculated_se:.4f}| <= {tolerance:.4f}",
                    is_satisfied=is_consistent,
                    violation_message="" if is_consistent else f"SE mismatch: reported={reported_se}, calculated={calculated_se:.4f}",
                    is_critical=False,
                ), calculated_se

            return Constraint(
                name="SE_CALCULATED",
                description="SE calculated from CI",
                expression=f"SE = {calculated_se:.4f}",
                is_satisfied=True,
                is_critical=False,
            ), calculated_se

        except (ValueError, ZeroDivisionError) as e:
            return Constraint(
                name="SE_CONSISTENT",
                description="SE consistent with CI width",
                expression=f"Error: {e}",
                is_satisfied=None,
                is_critical=False,
            ), None

    def verify_log_symmetry(self, value: float, ci_lower: float, ci_upper: float,
                            tolerance: float = 0.15) -> Constraint:
        """
        Verify CI is symmetric on log scale (for ratio measures).
        Most ratios have symmetric CI on log scale.
        """
        try:
            if value <= 0 or ci_lower <= 0 or ci_upper <= 0:
                return Constraint(
                    name="LOG_SYMMETRIC",
                    description="CI symmetric on log scale",
                    expression="Cannot verify for non-positive values",
                    is_satisfied=None,
                    is_critical=False,
                )

            if self.use_sympy:
                v, l, u = sp.Symbol('v', positive=True), sp.Symbol('l', positive=True), sp.Symbol('u', positive=True)
                log_v = sp.log(v)
                log_l = sp.log(l)
                log_u = sp.log(u)
                dist_lower = (log_v - log_l).subs([(v, value), (l, ci_lower)])
                dist_upper = (log_u - log_v).subs([(v, value), (u, ci_upper)])
                dist_lower = float(dist_lower)
                dist_upper = float(dist_upper)
            else:
                dist_lower = math.log(value) - math.log(ci_lower)
                dist_upper = math.log(ci_upper) - math.log(value)

            avg_dist = (dist_lower + dist_upper) / 2
            if avg_dist == 0:
                asymmetry = 0
            else:
                asymmetry = abs(dist_lower - dist_upper) / avg_dist

            is_satisfied = asymmetry <= tolerance

            return Constraint(
                name="LOG_SYMMETRIC",
                description="CI symmetric on log scale",
                expression=f"asymmetry = {asymmetry:.4f} <= {tolerance}",
                is_satisfied=is_satisfied,
                violation_message="" if is_satisfied else f"Asymmetry {asymmetry:.4f} exceeds tolerance {tolerance}",
                is_critical=False,
            )

        except (ValueError, ZeroDivisionError):
            return Constraint(
                name="LOG_SYMMETRIC",
                description="CI symmetric on log scale",
                expression="Error in calculation",
                is_satisfied=None,
                is_critical=False,
            )

    def verify_p_value_ci_consistency(self, effect_type: str, ci_lower: float, ci_upper: float,
                                       p_value: float) -> Constraint:
        """
        Verify p-value is consistent with CI.
        If CI excludes null, p should be < 0.05.
        If CI includes null, p should be >= 0.05.
        """
        # Determine null value
        if effect_type in ['HR', 'OR', 'RR', 'IRR']:
            null_value = 1.0
        else:
            null_value = 0.0

        ci_excludes_null = not (ci_lower <= null_value <= ci_upper)
        p_significant = p_value < 0.05

        # These should generally match
        consistent = ci_excludes_null == p_significant

        # Allow borderline cases
        if not consistent:
            if 0.03 <= p_value <= 0.07:
                consistent = True
                note = " (borderline p-value)"
            elif effect_type in ['HR', 'OR', 'RR', 'IRR']:
                if 0.90 <= ci_lower <= 1.10 or 0.90 <= ci_upper <= 1.10:
                    consistent = True
                    note = " (borderline CI)"
            else:
                if -0.1 <= ci_lower <= 0.1 or -0.1 <= ci_upper <= 0.1:
                    consistent = True
                    note = " (borderline CI)"

        return Constraint(
            name="P_VALUE_CI_CONSISTENT",
            description="P-value consistent with CI relative to null",
            expression=f"p={p_value}, CI=[{ci_lower}, {ci_upper}], null={null_value}",
            is_satisfied=consistent,
            violation_message="" if consistent else f"p={p_value} inconsistent with CI excluding null={ci_excludes_null}",
            is_critical=False,
        )


# =============================================================================
# PLAUSIBILITY VERIFIER
# =============================================================================

class PlausibilityVerifier:
    """Verifies values are within plausible ranges"""

    # Domain constraints for each effect type
    BOUNDS = {
        'HR': {'min': 0.01, 'max': 50.0, 'null': 1.0},
        'OR': {'min': 0.01, 'max': 100.0, 'null': 1.0},
        'RR': {'min': 0.01, 'max': 50.0, 'null': 1.0},
        'IRR': {'min': 0.01, 'max': 100.0, 'null': 1.0},
        'MD': {'min': -1000.0, 'max': 1000.0, 'null': 0.0},
        'SMD': {'min': -10.0, 'max': 10.0, 'null': 0.0},
        'ARD': {'min': -100.0, 'max': 100.0, 'null': 0.0},  # Allows both decimal and percentage scale
        'NNT': {'min': 1.0, 'max': 10000.0, 'null': None},
        'NNH': {'min': 1.0, 'max': 10000.0, 'null': None},
    }

    def verify_range(self, effect_type: str, value: float) -> Constraint:
        """Verify value is within plausible range"""
        if effect_type not in self.BOUNDS:
            return Constraint(
                name="RANGE_PLAUSIBLE",
                description="Value within plausible range",
                expression=f"No bounds defined for {effect_type}",
                is_satisfied=None,
                is_critical=False,
            )

        bounds = self.BOUNDS[effect_type]
        is_satisfied = bounds['min'] <= value <= bounds['max']

        return Constraint(
            name="RANGE_PLAUSIBLE",
            description="Value within plausible range",
            expression=f"{bounds['min']} <= {value} <= {bounds['max']}",
            is_satisfied=is_satisfied,
            violation_message="" if is_satisfied else f"Value {value} outside range [{bounds['min']}, {bounds['max']}]",
            is_critical=True,
        )

    def verify_ratio_positive(self, effect_type: str, value: float, ci_lower: float, ci_upper: float) -> Constraint:
        """Verify ratio measures are positive"""
        if effect_type not in ['HR', 'OR', 'RR', 'IRR']:
            return Constraint(
                name="RATIO_POSITIVE",
                description="Ratio measures must be positive",
                expression="Not applicable",
                is_satisfied=None,
                is_critical=False,
            )

        all_positive = value > 0 and ci_lower > 0 and ci_upper > 0

        return Constraint(
            name="RATIO_POSITIVE",
            description="Ratio measures must be positive",
            expression=f"{value} > 0, {ci_lower} > 0, {ci_upper} > 0",
            is_satisfied=all_positive,
            violation_message="" if all_positive else "Ratio values must be positive",
            is_critical=True,
        )


# =============================================================================
# CROSS-VALUE VERIFIER
# =============================================================================

class CrossValueVerifier:
    """
    Verifies relationships between different effect measures.
    For example: OR to RR conversion, NNT from ARD, etc.
    """

    def verify_nnt_from_ard(self, nnt: float, ard: float, tolerance: float = 0.1) -> Constraint:
        """
        Verify NNT = 1/|ARD|
        """
        if abs(ard) < 0.001:
            return Constraint(
                name="NNT_ARD_CONSISTENT",
                description="NNT = 1/|ARD|",
                expression="ARD too small to verify",
                is_satisfied=None,
                is_critical=False,
            )

        expected_nnt = 1.0 / abs(ard)
        relative_error = abs(nnt - expected_nnt) / expected_nnt

        is_consistent = relative_error <= tolerance

        return Constraint(
            name="NNT_ARD_CONSISTENT",
            description="NNT = 1/|ARD|",
            expression=f"NNT={nnt}, expected=1/{abs(ard)}={expected_nnt:.2f}",
            is_satisfied=is_consistent,
            violation_message="" if is_consistent else f"NNT {nnt} != 1/|ARD| = {expected_nnt:.2f}",
            is_critical=False,
        )

    def verify_or_to_rr_approximation(self, or_value: float, rr_value: float,
                                       baseline_risk: float, tolerance: float = 0.15) -> Constraint:
        """
        Verify OR to RR conversion is approximately correct.
        RR ≈ OR / (1 - baseline_risk + baseline_risk * OR)
        """
        if baseline_risk <= 0 or baseline_risk >= 1:
            return Constraint(
                name="OR_RR_CONSISTENT",
                description="OR to RR conversion valid",
                expression="Invalid baseline risk",
                is_satisfied=None,
                is_critical=False,
            )

        expected_rr = or_value / (1 - baseline_risk + baseline_risk * or_value)
        relative_error = abs(rr_value - expected_rr) / expected_rr if expected_rr > 0 else float('inf')

        is_consistent = relative_error <= tolerance

        return Constraint(
            name="OR_RR_CONSISTENT",
            description="OR to RR conversion valid",
            expression=f"RR={rr_value}, expected={expected_rr:.3f} (baseline={baseline_risk})",
            is_satisfied=is_consistent,
            violation_message="" if is_consistent else f"RR {rr_value} inconsistent with OR {or_value}",
            is_critical=False,
        )


# =============================================================================
# PROOF BUILDER
# =============================================================================

class ProofBuilder:
    """Builds formal proofs for verifications"""

    def build_ci_proof(self, value: float, ci_lower: float, ci_upper: float) -> VerificationProof:
        """Build proof that point estimate is within CI"""
        given = [
            f"Point estimate v = {value}",
            f"95% CI lower bound l = {ci_lower}",
            f"95% CI upper bound u = {ci_upper}",
        ]

        steps = [
            f"Step 1: Verify l < u: {ci_lower} < {ci_upper} = {ci_lower < ci_upper}",
            f"Step 2: Verify l <= v: {ci_lower} <= {value} = {ci_lower <= value}",
            f"Step 3: Verify v <= u: {value} <= {ci_upper} = {value <= ci_upper}",
        ]

        is_valid = ci_lower < ci_upper and ci_lower <= value <= ci_upper

        conclusion = f"Point estimate {value} {'is' if is_valid else 'is NOT'} within CI [{ci_lower}, {ci_upper}]"

        return VerificationProof(
            theorem="CI_CONTAINS_POINT",
            given=given,
            steps=steps,
            conclusion=conclusion,
            is_valid=is_valid,
            level=VerificationLevel.PROVEN if is_valid else VerificationLevel.VIOLATED,
        )

    def build_se_proof(self, effect_type: str, ci_lower: float, ci_upper: float,
                       calculated_se: float) -> VerificationProof:
        """Build proof for SE calculation"""
        if effect_type in ['HR', 'OR', 'RR', 'IRR']:
            formula = "SE = (log(u) - log(l)) / (2 * 1.96)"
            given = [
                f"Effect type: {effect_type} (ratio measure)",
                f"95% CI: [{ci_lower}, {ci_upper}]",
                "Z-value for 95% CI: 1.96",
            ]
            steps = [
                f"Step 1: log(u) = log({ci_upper}) = {math.log(ci_upper):.4f}",
                f"Step 2: log(l) = log({ci_lower}) = {math.log(ci_lower):.4f}",
                f"Step 3: log(u) - log(l) = {math.log(ci_upper) - math.log(ci_lower):.4f}",
                f"Step 4: SE = {math.log(ci_upper) - math.log(ci_lower):.4f} / 3.92 = {calculated_se:.4f}",
            ]
        else:
            formula = "SE = (u - l) / (2 * 1.96)"
            given = [
                f"Effect type: {effect_type} (difference measure)",
                f"95% CI: [{ci_lower}, {ci_upper}]",
                "Z-value for 95% CI: 1.96",
            ]
            steps = [
                f"Step 1: u - l = {ci_upper} - {ci_lower} = {ci_upper - ci_lower:.4f}",
                f"Step 2: SE = {ci_upper - ci_lower:.4f} / 3.92 = {calculated_se:.4f}",
            ]

        return VerificationProof(
            theorem="SE_FROM_CI",
            given=given,
            steps=steps,
            conclusion=f"Standard Error = {calculated_se:.4f}",
            is_valid=True,
            level=VerificationLevel.PROVEN,
        )


# =============================================================================
# MAIN VERIFIER
# =============================================================================

class DeterministicVerifier:
    """
    Main verification engine combining all verification types.
    """

    def __init__(self):
        self.symbolic = SymbolicVerifier()
        self.plausibility = PlausibilityVerifier()
        self.cross_value = CrossValueVerifier()
        self.proof_builder = ProofBuilder()

    def verify(self, effect_type: str, value: float, ci_lower: float, ci_upper: float,
               p_value: Optional[float] = None,
               reported_se: Optional[float] = None) -> DeterministicVerificationResult:
        """
        Run complete verification on an extraction.
        """
        constraints = []
        proofs = []
        warnings = []

        # Core constraints
        constraints.append(self.symbolic.verify_ci_ordered(ci_lower, ci_upper))
        constraints.append(self.symbolic.verify_ci_contains_point(value, ci_lower, ci_upper))
        constraints.append(self.plausibility.verify_range(effect_type, value))

        # Ratio-specific checks
        if effect_type in ['HR', 'OR', 'RR', 'IRR']:
            constraints.append(self.plausibility.verify_ratio_positive(effect_type, value, ci_lower, ci_upper))
            constraints.append(self.symbolic.verify_log_symmetry(value, ci_lower, ci_upper))

        # SE verification
        se_constraint, calculated_se = self.symbolic.verify_se_from_ci(
            effect_type, ci_lower, ci_upper, reported_se
        )
        constraints.append(se_constraint)

        # P-value verification
        if p_value is not None:
            constraints.append(self.symbolic.verify_p_value_ci_consistency(
                effect_type, ci_lower, ci_upper, p_value
            ))

        # Build proofs
        proofs.append(self.proof_builder.build_ci_proof(value, ci_lower, ci_upper))
        if calculated_se is not None:
            proofs.append(self.proof_builder.build_se_proof(effect_type, ci_lower, ci_upper, calculated_se))

        # Determine overall level
        evaluated_critical = [
            c for c in constraints
            if c.is_critical and c.is_satisfied is not None
        ]
        critical_satisfied = (
            len(evaluated_critical) > 0
            and all(c.is_satisfied for c in evaluated_critical)
        )

        has_violations = any(
            c.is_satisfied is False for c in constraints if c.is_critical
        )

        if has_violations:
            overall_level = VerificationLevel.VIOLATED
        elif critical_satisfied:
            overall_level = VerificationLevel.PROVEN
        else:
            overall_level = VerificationLevel.UNCERTAIN

        # Collect warnings
        for c in constraints:
            if c.is_satisfied is False and not c.is_critical:
                warnings.append(c.violation_message)

        # Compute deterministic hash
        hash_input = f"{effect_type}|{value}|{ci_lower}|{ci_upper}|{overall_level.value}"
        import hashlib
        verification_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        return DeterministicVerificationResult(
            constraints=constraints,
            proofs=proofs,
            overall_level=overall_level,
            all_critical_satisfied=critical_satisfied,
            warnings=warnings,
            verification_hash=verification_hash,
        )

    def verify_batch(self, extractions: List[Dict]) -> List[DeterministicVerificationResult]:
        """Verify a batch of extractions"""
        results = []
        for ext in extractions:
            result = self.verify(
                effect_type=ext.get('effect_type', ''),
                value=ext.get('value', 0),
                ci_lower=ext.get('ci_lower', 0),
                ci_upper=ext.get('ci_upper', 0),
                p_value=ext.get('p_value'),
                reported_se=ext.get('standard_error'),
            )
            results.append(result)
        return results


# =============================================================================
# INTERFACE FUNCTIONS
# =============================================================================

def verify_extraction(effect_type: str, value: float, ci_lower: float, ci_upper: float,
                      p_value: Optional[float] = None,
                      reported_se: Optional[float] = None) -> DeterministicVerificationResult:
    """
    Main interface: Verify a single extraction.

    Returns DeterministicVerificationResult with:
    - constraints: List of checked constraints
    - proofs: Formal proofs
    - overall_level: PROVEN, CONSISTENT, UNCERTAIN, or VIOLATED
    - all_critical_satisfied: Whether all critical constraints passed
    """
    verifier = DeterministicVerifier()
    return verifier.verify(effect_type, value, ci_lower, ci_upper, p_value, reported_se)


def is_verified(effect_type: str, value: float, ci_lower: float, ci_upper: float) -> bool:
    """
    Quick check: Is extraction verified?
    """
    result = verify_extraction(effect_type, value, ci_lower, ci_upper)
    return result.overall_level in [VerificationLevel.PROVEN, VerificationLevel.CONSISTENT]
