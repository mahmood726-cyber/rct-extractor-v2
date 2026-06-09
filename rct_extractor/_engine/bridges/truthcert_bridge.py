"""
TruthCert Bridge - ClinicalTrials.gov Verification
Validates extracted effect measures against CTGov reported results.

Based on TruthCert.js verification approach for ground truth comparison.
"""

from __future__ import annotations
import re
import json
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import logging

logger = logging.getLogger(__name__)

# CTGov API base URL
CTGOV_API_BASE = "https://clinicaltrials.gov/api/v2"


@dataclass
class CTGovOutcome:
    """Outcome from ClinicalTrials.gov"""
    title: str
    description: str = ""
    time_frame: str = ""
    outcome_type: str = ""  # PRIMARY, SECONDARY, OTHER

    # Result values
    value: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    p_value: Optional[float] = None
    measure_type: str = ""  # HR, OR, RR, MD, etc.

    # Arm data
    arm_results: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CTGovTrial:
    """Trial data from ClinicalTrials.gov"""
    nct_id: str
    brief_title: str = ""
    official_title: str = ""
    phase: str = ""
    enrollment: int = 0

    # Study design
    study_type: str = ""
    allocation: str = ""
    intervention_model: str = ""
    masking: str = ""

    # Arms
    arms: List[Dict[str, str]] = field(default_factory=list)

    # Outcomes
    primary_outcomes: List[CTGovOutcome] = field(default_factory=list)
    secondary_outcomes: List[CTGovOutcome] = field(default_factory=list)

    # Results (if posted)
    has_results: bool = False
    results_first_posted: str = ""


@dataclass
class VerificationResult:
    """Result of verification against CTGov"""
    nct_id: str
    endpoint: str

    # Extracted vs CTGov values
    extracted_value: Optional[float] = None
    ctgov_value: Optional[float] = None
    extracted_ci: Optional[Tuple[float, float]] = None
    ctgov_ci: Optional[Tuple[float, float]] = None

    # Verification status
    is_verified: bool = False
    value_match: bool = False
    ci_match: bool = False
    error_percent: Optional[float] = None

    # Match details
    matched_outcome: Optional[str] = None
    verification_notes: str = ""


# ============================================================
# CTGov API CLIENT
# ============================================================

class CTGovClient:
    """Client for ClinicalTrials.gov API v2"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.base_url = CTGOV_API_BASE

    def fetch_trial(self, nct_id: str) -> Optional[CTGovTrial]:
        """
        Fetch trial data from CTGov API.

        Args:
            nct_id: NCT identifier (e.g., NCT01234567)

        Returns:
            CTGovTrial or None if not found
        """
        # Normalize NCT ID
        nct_id = self._normalize_nct_id(nct_id)
        if not nct_id:
            return None

        url = f"{self.base_url}/studies/{nct_id}"

        try:
            req = Request(url, headers={'Accept': 'application/json'})
            with urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
                return self._parse_trial_data(data, nct_id)

        except HTTPError as e:
            if e.code == 404:
                logger.warning(f"Trial not found: {nct_id}")
            else:
                logger.error(f"HTTP error fetching {nct_id}: {e}")
            return None
        except URLError as e:
            logger.error(f"URL error fetching {nct_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {nct_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching trial {nct_id}: {e}")
            return None

    def _normalize_nct_id(self, nct_id: str) -> Optional[str]:
        """Normalize NCT ID format"""
        if not nct_id:
            return None

        # Extract NCT number
        match = re.search(r'NCT\s*(\d{8})', nct_id, re.IGNORECASE)
        if match:
            return f"NCT{match.group(1)}"

        # Try just digits
        match = re.search(r'(\d{8})', nct_id)
        if match:
            return f"NCT{match.group(1)}"

        return None

    def _parse_trial_data(self, data: Dict, nct_id: str) -> CTGovTrial:
        """Parse CTGov API response into CTGovTrial"""
        protocol = data.get('protocolSection', {})
        results = data.get('resultsSection', {})

        # Basic info
        id_module = protocol.get('identificationModule', {})
        design_module = protocol.get('designModule', {})
        arms_module = protocol.get('armsInterventionsModule', {})
        outcomes_module = protocol.get('outcomesModule', {})

        trial = CTGovTrial(
            nct_id=nct_id,
            brief_title=id_module.get('briefTitle', ''),
            official_title=id_module.get('officialTitle', ''),
            phase=self._get_phase(design_module),
            enrollment=design_module.get('enrollmentInfo', {}).get('count', 0),
            study_type=design_module.get('studyType', ''),
            allocation=design_module.get('designInfo', {}).get('allocation', ''),
            intervention_model=design_module.get('designInfo', {}).get('interventionModel', ''),
            masking=design_module.get('designInfo', {}).get('maskingInfo', {}).get('masking', ''),
            has_results=bool(results)
        )

        # Parse arms
        for arm in arms_module.get('armGroups', []):
            trial.arms.append({
                'label': arm.get('label', ''),
                'type': arm.get('type', ''),
                'description': arm.get('description', '')
            })

        # Parse outcomes from protocol
        for outcome in outcomes_module.get('primaryOutcomes', []):
            trial.primary_outcomes.append(CTGovOutcome(
                title=outcome.get('measure', ''),
                description=outcome.get('description', ''),
                time_frame=outcome.get('timeFrame', ''),
                outcome_type='PRIMARY'
            ))

        for outcome in outcomes_module.get('secondaryOutcomes', []):
            trial.secondary_outcomes.append(CTGovOutcome(
                title=outcome.get('measure', ''),
                description=outcome.get('description', ''),
                time_frame=outcome.get('timeFrame', ''),
                outcome_type='SECONDARY'
            ))

        # Parse results if available
        if results:
            trial = self._parse_results(trial, results)

        return trial

    def _get_phase(self, design_module: Dict) -> str:
        """Extract phase from design module"""
        phases = design_module.get('phases', [])
        if phases:
            return ', '.join(phases)
        return ''

    def _parse_results(self, trial: CTGovTrial, results: Dict) -> CTGovTrial:
        """Parse results section"""
        outcome_measures = results.get('outcomeMeasuresModule', {})

        for measure in outcome_measures.get('outcomeMeasures', []):
            outcome = self._parse_outcome_measure(measure)

            if outcome.outcome_type == 'PRIMARY':
                # Update existing or add
                self._merge_outcome(trial.primary_outcomes, outcome)
            elif outcome.outcome_type == 'SECONDARY':
                self._merge_outcome(trial.secondary_outcomes, outcome)

        return trial

    def _parse_outcome_measure(self, measure: Dict) -> CTGovOutcome:
        """Parse individual outcome measure with results"""
        outcome = CTGovOutcome(
            title=measure.get('title', ''),
            description=measure.get('description', ''),
            time_frame=measure.get('timeFrame', ''),
            outcome_type=measure.get('type', 'OTHER')
        )

        # Parse analysis results for effect measures
        for analysis in measure.get('analyses', []):
            stat_method = analysis.get('statisticalMethod', '').lower()

            # Try to get effect estimate
            param_value = analysis.get('paramValue')
            if param_value:
                try:
                    outcome.value = float(param_value)
                except (ValueError, TypeError):
                    pass

            # Get CI
            ci_low = analysis.get('ciLowerLimit')
            ci_high = analysis.get('ciUpperLimit')
            if ci_low and ci_high:
                try:
                    outcome.ci_low = float(ci_low)
                    outcome.ci_high = float(ci_high)
                except (ValueError, TypeError):
                    pass

            # Get p-value
            p_value = analysis.get('pValue')
            if p_value:
                try:
                    outcome.p_value = float(p_value.replace('<', '').replace('>', ''))
                except (ValueError, TypeError):
                    pass

            # Infer measure type from statistical method
            if 'hazard' in stat_method or 'cox' in stat_method:
                outcome.measure_type = 'HR'
            elif 'odds' in stat_method or 'logistic' in stat_method:
                outcome.measure_type = 'OR'
            elif 'risk ratio' in stat_method or 'relative risk' in stat_method:
                outcome.measure_type = 'RR'
            elif 'risk difference' in stat_method:
                outcome.measure_type = 'RD'
            elif 'mean difference' in stat_method:
                outcome.measure_type = 'MD'

        # Parse arm-level results
        for group in measure.get('classes', []):
            for category in group.get('categories', []):
                for measurement in category.get('measurements', []):
                    outcome.arm_results.append({
                        'group': measurement.get('groupId', ''),
                        'value': measurement.get('value'),
                        'spread': measurement.get('spread'),
                        'lower_limit': measurement.get('lowerLimit'),
                        'upper_limit': measurement.get('upperLimit')
                    })

        return outcome

    def _merge_outcome(self, outcomes: List[CTGovOutcome], new_outcome: CTGovOutcome):
        """Merge new outcome data with existing outcome list"""
        # Find matching outcome by title
        for i, existing in enumerate(outcomes):
            if self._titles_match(existing.title, new_outcome.title):
                # Update with result data
                if new_outcome.value is not None:
                    existing.value = new_outcome.value
                if new_outcome.ci_low is not None:
                    existing.ci_low = new_outcome.ci_low
                if new_outcome.ci_high is not None:
                    existing.ci_high = new_outcome.ci_high
                if new_outcome.p_value is not None:
                    existing.p_value = new_outcome.p_value
                if new_outcome.measure_type:
                    existing.measure_type = new_outcome.measure_type
                if new_outcome.arm_results:
                    existing.arm_results = new_outcome.arm_results
                return

        # No match, add new
        outcomes.append(new_outcome)

    def _titles_match(self, title1: str, title2: str) -> bool:
        """Check if two outcome titles match"""
        if not title1 or not title2:
            return False

        # Normalize
        t1 = re.sub(r'\s+', ' ', title1.lower().strip())
        t2 = re.sub(r'\s+', ' ', title2.lower().strip())

        # Exact match
        if t1 == t2:
            return True

        # Substring match
        if t1 in t2 or t2 in t1:
            return True

        # Word overlap
        words1 = set(t1.split())
        words2 = set(t2.split())
        overlap = len(words1 & words2) / max(len(words1), len(words2))

        return overlap > 0.6


# ============================================================
# TRUTHCERT VERIFICATION
# ============================================================

class TruthCertBridge:
    """
    Bridge for verifying extracted values against ClinicalTrials.gov.

    Implements TruthCert verification logic from TruthCert.js.
    """

    def __init__(self, tolerance: float = 0.05):
        """
        Args:
            tolerance: Acceptable relative error (default 5%)
        """
        self.client = CTGovClient()
        self.tolerance = tolerance

    def verify_extraction(
        self,
        nct_id: str,
        extracted_results: List[Dict[str, Any]]
    ) -> List[VerificationResult]:
        """
        Verify extracted results against CTGov.

        Args:
            nct_id: NCT identifier
            extracted_results: List of extracted results in ensemble format

        Returns:
            List of VerificationResult objects
        """
        # Fetch trial data
        trial = self.client.fetch_trial(nct_id)
        if not trial:
            logger.warning(f"Could not fetch trial data for {nct_id}")
            return [VerificationResult(
                nct_id=nct_id,
                endpoint='ALL',
                is_verified=False,
                verification_notes=f"Trial {nct_id} not found in CTGov"
            )]

        if not trial.has_results:
            logger.info(f"Trial {nct_id} has no posted results")
            return [VerificationResult(
                nct_id=nct_id,
                endpoint='ALL',
                is_verified=False,
                verification_notes=f"Trial {nct_id} has no posted results"
            )]

        # Verify each extracted result
        verifications = []
        all_outcomes = trial.primary_outcomes + trial.secondary_outcomes

        for result in extracted_results:
            verification = self._verify_single_result(
                nct_id, result, all_outcomes
            )
            verifications.append(verification)

        return verifications

    def _verify_single_result(
        self,
        nct_id: str,
        result: Dict[str, Any],
        outcomes: List[CTGovOutcome]
    ) -> VerificationResult:
        """Verify a single extracted result"""
        endpoint = result.get('endpoint', 'UNKNOWN')
        extracted_value = result.get('value')
        extracted_ci_low = result.get('ci_low')
        extracted_ci_high = result.get('ci_high')
        measure_type = result.get('measure_type', '')

        verification = VerificationResult(
            nct_id=nct_id,
            endpoint=endpoint,
            extracted_value=extracted_value,
            extracted_ci=(extracted_ci_low, extracted_ci_high) if extracted_ci_low and extracted_ci_high else None
        )

        # Find matching outcome in CTGov
        best_match = None
        best_score = 0

        for outcome in outcomes:
            score = self._match_score(endpoint, measure_type, outcome)
            if score > best_score:
                best_score = score
                best_match = outcome

        if not best_match or best_match.value is None:
            verification.verification_notes = "No matching outcome with results in CTGov"
            return verification

        verification.matched_outcome = best_match.title
        verification.ctgov_value = best_match.value

        if best_match.ci_low and best_match.ci_high:
            verification.ctgov_ci = (best_match.ci_low, best_match.ci_high)

        # Compare values
        if extracted_value is not None and best_match.value is not None:
            error = abs(extracted_value - best_match.value)
            if best_match.value != 0:
                verification.error_percent = (error / abs(best_match.value)) * 100
            else:
                verification.error_percent = error * 100

            verification.value_match = verification.error_percent <= (self.tolerance * 100)

        # Compare CIs
        if verification.extracted_ci and verification.ctgov_ci:
            ci_low_match = self._values_match(
                verification.extracted_ci[0], verification.ctgov_ci[0]
            )
            ci_high_match = self._values_match(
                verification.extracted_ci[1], verification.ctgov_ci[1]
            )
            verification.ci_match = ci_low_match and ci_high_match

        # Overall verification
        verification.is_verified = verification.value_match

        if verification.is_verified:
            verification.verification_notes = f"Verified: extracted {extracted_value:.3f} matches CTGov {best_match.value:.3f}"
        else:
            verification.verification_notes = f"Mismatch: extracted {extracted_value:.3f} vs CTGov {best_match.value:.3f} (error: {verification.error_percent:.1f}%)"

        return verification

    def _match_score(
        self,
        endpoint: str,
        measure_type: str,
        outcome: CTGovOutcome
    ) -> float:
        """Calculate match score between extracted endpoint and CTGov outcome"""
        score = 0.0

        endpoint_lower = endpoint.lower()
        title_lower = outcome.title.lower()

        # Measure type match
        if measure_type and outcome.measure_type:
            if measure_type == outcome.measure_type:
                score += 0.3

        # Primary outcome bonus
        if outcome.outcome_type == 'PRIMARY':
            score += 0.2

        # Keyword matching
        endpoint_keywords = {
            'ALL_CAUSE_DEATH': ['death', 'mortality', 'survival'],
            'CV_DEATH': ['cardiovascular death', 'cv death', 'cardiac death'],
            'HF_HOSPITALIZATION': ['heart failure', 'hospitalization', 'hf'],
            'MI': ['myocardial infarction', 'mi', 'heart attack'],
            'STROKE': ['stroke', 'cerebrovascular'],
            'MACE': ['mace', 'major adverse', 'composite'],
            'PRIMARY_OUTCOME': ['primary']
        }

        keywords = endpoint_keywords.get(endpoint, [endpoint_lower])
        for keyword in keywords:
            if keyword in title_lower:
                score += 0.5
                break

        return score

    def _values_match(self, val1: float, val2: float) -> bool:
        """Check if two values match within tolerance"""
        if val1 is None or val2 is None:
            return False

        if val2 == 0:
            return abs(val1) < self.tolerance

        return abs(val1 - val2) / abs(val2) <= self.tolerance

    def extract_to_ensemble_format(
        self,
        nct_id: str,
        verifications: List[VerificationResult] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract CTGov data in ensemble format (as E4 extractor).

        Returns:
            List of dicts compatible with ExtractorResult
        """
        trial = self.client.fetch_trial(nct_id)
        if not trial or not trial.has_results:
            return []

        results = []

        for outcome in trial.primary_outcomes + trial.secondary_outcomes:
            if outcome.value is not None:
                result = {
                    'extractor_id': 'E4',
                    'endpoint': self._infer_endpoint(outcome.title),
                    'value': outcome.value,
                    'ci_low': outcome.ci_low,
                    'ci_high': outcome.ci_high,
                    'measure_type': outcome.measure_type or 'UNKNOWN',
                    'has_provenance': True,
                    'provenance_text': f"CTGov {nct_id}: {outcome.title}",
                    'confidence_score': 0.99 if outcome.outcome_type == 'PRIMARY' else 0.95,
                    'is_verified': True,  # CTGov is ground truth
                    'ctgov_outcome_type': outcome.outcome_type,
                    'ctgov_time_frame': outcome.time_frame
                }
                results.append(result)

        return results

    def _infer_endpoint(self, title: str) -> str:
        """Infer endpoint name from CTGov outcome title"""
        title_lower = title.lower()

        endpoint_patterns = {
            'ALL_CAUSE_DEATH': ['all-cause death', 'all cause death', 'mortality', 'death from any cause'],
            'CV_DEATH': ['cardiovascular death', 'cv death', 'cardiac death'],
            'HF_HOSPITALIZATION': ['heart failure hospitalization', 'hospitalization for heart failure', 'hfh'],
            'MI': ['myocardial infarction', ' mi ', 'heart attack'],
            'STROKE': ['stroke', 'cerebrovascular'],
            'MACE_3PT': ['mace', 'major adverse cardiovascular'],
            'COMPOSITE': ['composite', 'primary composite']
        }

        for endpoint, patterns in endpoint_patterns.items():
            for pattern in patterns:
                if pattern in title_lower:
                    return endpoint

        return 'PRIMARY_OUTCOME' if 'primary' in title_lower else 'SECONDARY_OUTCOME'


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def verify_against_ctgov(
    nct_id: str,
    extracted_results: List[Dict[str, Any]],
    tolerance: float = 0.05
) -> List[VerificationResult]:
    """
    Convenience function to verify extracted results against CTGov.

    Args:
        nct_id: NCT identifier
        extracted_results: Extracted results in ensemble format
        tolerance: Acceptable relative error

    Returns:
        List of VerificationResult objects
    """
    bridge = TruthCertBridge(tolerance=tolerance)
    return bridge.verify_extraction(nct_id, extracted_results)


def fetch_ctgov_results(nct_id: str) -> Optional[CTGovTrial]:
    """
    Convenience function to fetch trial data from CTGov.

    Args:
        nct_id: NCT identifier

    Returns:
        CTGovTrial or None
    """
    client = CTGovClient()
    return client.fetch_trial(nct_id)


if __name__ == "__main__":
    # Test with a known trial (EMPEROR-Reduced)
    nct_id = "NCT03057977"

    print(f"Fetching trial: {nct_id}")
    client = CTGovClient()
    trial = client.fetch_trial(nct_id)

    if trial:
        print(f"\nTitle: {trial.brief_title}")
        print(f"Enrollment: {trial.enrollment}")
        print(f"Has Results: {trial.has_results}")
        print(f"\nPrimary Outcomes ({len(trial.primary_outcomes)}):")
        for outcome in trial.primary_outcomes:
            print(f"  - {outcome.title}")
            if outcome.value:
                print(f"    Value: {outcome.value} ({outcome.ci_low}, {outcome.ci_high})")
    else:
        print("Trial not found")
