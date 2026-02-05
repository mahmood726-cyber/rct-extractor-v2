#!/usr/bin/env python3
"""
ClinicalTrials.gov Results Scraper
Downloads and parses effect estimates from CTG for validation.

Usage:
    python scripts/ctg_scraper.py --nct NCT02653482
    python scripts/ctg_scraper.py --search "heart failure" --max 100
    python scripts/ctg_scraper.py --file nct_ids.txt
"""

import argparse
import json
import re
import time
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("Warning: requests not installed. Run: pip install requests")

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("Warning: beautifulsoup4 not installed. Run: pip install beautifulsoup4")


# ClinicalTrials.gov API endpoints
CTG_API_BASE = "https://clinicaltrials.gov/api/v2"
CTG_STUDY_URL = f"{CTG_API_BASE}/studies"


@dataclass
class OutcomeMeasure:
    """Outcome measure from CTG"""
    title: str
    description: str
    time_frame: str
    outcome_type: str  # primary, secondary, other
    population: str
    units: str


@dataclass
class EffectEstimate:
    """Extracted effect estimate from CTG"""
    outcome_title: str
    outcome_type: str
    effect_type: str  # HR, OR, RR, MD, etc.
    value: float
    ci_lower: Optional[float]
    ci_upper: Optional[float]
    p_value: Optional[float]
    arm1_name: str
    arm1_n: Optional[int]
    arm1_value: Optional[float]
    arm2_name: str
    arm2_n: Optional[int]
    arm2_value: Optional[float]
    analysis_method: str
    source_text: str


@dataclass
class CTGStudy:
    """Clinical trial study from CTG"""
    nct_id: str
    title: str
    status: str
    phase: str
    conditions: List[str]
    interventions: List[str]
    enrollment: int
    start_date: str
    completion_date: str
    sponsor: str
    has_results: bool
    outcomes: List[OutcomeMeasure]
    effect_estimates: List[EffectEstimate]


class CTGScraper:
    """Scraper for ClinicalTrials.gov results"""

    def __init__(self, rate_limit: float = 0.5):
        """
        Initialize scraper.

        Args:
            rate_limit: Minimum seconds between API calls
        """
        self.rate_limit = rate_limit
        self.last_request = 0

        if not HAS_REQUESTS:
            raise ImportError("requests library required")

    def _rate_limit_wait(self):
        """Wait to respect rate limit"""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

    def fetch_study(self, nct_id: str) -> Optional[CTGStudy]:
        """
        Fetch study details and results from CTG.

        Args:
            nct_id: NCT identifier (e.g., NCT02653482)

        Returns:
            CTGStudy object or None if not found
        """
        self._rate_limit_wait()

        # Normalize NCT ID
        nct_id = nct_id.upper().strip()
        if not nct_id.startswith("NCT"):
            nct_id = f"NCT{nct_id}"

        # Fetch study data - request all fields to get results section
        url = f"{CTG_STUDY_URL}/{nct_id}"
        params = {
            "format": "json"
            # No field filter - get all data including results
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 404:
                print(f"  Study not found: {nct_id}")
                return None

            response.raise_for_status()
            data = response.json()

        except requests.RequestException as e:
            print(f"  Error fetching {nct_id}: {e}")
            return None

        # Parse study data
        study = self._parse_study(data, nct_id)

        # If has results, fetch detailed results
        if study and study.has_results:
            self._fetch_results(study)

        return study

    def _parse_study(self, data: dict, nct_id: str) -> Optional[CTGStudy]:
        """Parse study JSON from API"""
        try:
            protocol = data.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})
            conditions_module = protocol.get("conditionsModule", {})
            interventions_module = protocol.get("armsInterventionsModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            outcomes_module = protocol.get("outcomesModule", {})

            # Check for results
            results_section = data.get("resultsSection", {})
            has_results = bool(results_section)

            # Parse outcomes
            outcomes = []
            for outcome in outcomes_module.get("primaryOutcomes", []):
                outcomes.append(OutcomeMeasure(
                    title=outcome.get("measure", ""),
                    description=outcome.get("description", ""),
                    time_frame=outcome.get("timeFrame", ""),
                    outcome_type="primary",
                    population="",
                    units=""
                ))

            for outcome in outcomes_module.get("secondaryOutcomes", []):
                outcomes.append(OutcomeMeasure(
                    title=outcome.get("measure", ""),
                    description=outcome.get("description", ""),
                    time_frame=outcome.get("timeFrame", ""),
                    outcome_type="secondary",
                    population="",
                    units=""
                ))

            return CTGStudy(
                nct_id=nct_id,
                title=id_module.get("briefTitle", ""),
                status=status_module.get("overallStatus", ""),
                phase=", ".join(design_module.get("phases", [])),
                conditions=conditions_module.get("conditions", []),
                interventions=[i.get("name", "") for i in interventions_module.get("interventions", [])],
                enrollment=design_module.get("enrollmentInfo", {}).get("count", 0),
                start_date=status_module.get("startDateStruct", {}).get("date", ""),
                completion_date=status_module.get("completionDateStruct", {}).get("date", ""),
                sponsor=sponsor_module.get("leadSponsor", {}).get("name", ""),
                has_results=has_results,
                outcomes=outcomes,
                effect_estimates=[]
            )

        except Exception as e:
            print(f"  Error parsing study data: {e}")
            return None

    def _fetch_results(self, study: CTGStudy):
        """Fetch and parse detailed results for a study"""
        self._rate_limit_wait()

        url = f"{CTG_STUDY_URL}/{study.nct_id}"
        params = {"format": "json"}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("resultsSection", {})
            if not results:
                return

            # Parse outcome measures from results
            outcome_measures = results.get("outcomeMeasuresModule", {})
            for measure in outcome_measures.get("outcomeMeasures", []):
                self._parse_outcome_measure(study, measure)

        except requests.RequestException as e:
            print(f"  Error fetching results for {study.nct_id}: {e}")

    def _parse_outcome_measure(self, study: CTGStudy, measure: dict):
        """Parse an outcome measure and extract effect estimates"""
        title = measure.get("title", "")
        outcome_type = measure.get("type", "").lower()
        units = measure.get("unitOfMeasure", "")
        param_type = measure.get("paramType", "")

        # Get analysis results
        analyses = measure.get("analyses", [])

        for analysis in analyses:
            effect = self._parse_analysis(analysis, title, outcome_type)
            if effect:
                study.effect_estimates.append(effect)

        # Also check group data for direct comparisons
        groups = measure.get("groups", [])
        classes = measure.get("classes", [])

        if len(groups) >= 2 and classes:
            for cls in classes:
                categories = cls.get("categories", [])
                for cat in categories:
                    measurements = cat.get("measurements", [])
                    if len(measurements) >= 2:
                        effect = self._extract_from_measurements(
                            measurements, groups, title, outcome_type, units
                        )
                        if effect:
                            study.effect_estimates.append(effect)

    def _parse_analysis(self, analysis: dict, title: str, outcome_type: str) -> Optional[EffectEstimate]:
        """Parse statistical analysis to extract effect estimate"""
        stat_method = analysis.get("statisticalMethod", "")
        param_type = analysis.get("paramType", "")
        param_value = analysis.get("paramValue", "")
        ci_lower = analysis.get("ciLowerLimit")
        ci_upper = analysis.get("ciUpperLimit")
        p_value = analysis.get("pValue")

        # Determine effect type from method
        effect_type = self._infer_effect_type(stat_method, param_type)

        # v4.3: Fallback - if we have a numeric value but couldn't infer effect type,
        # try to infer from the analysis title/description or param_type
        if not effect_type and param_value:
            title_lower = title.lower()
            if "hazard" in title_lower or "survival" in title_lower or "time to" in title_lower:
                effect_type = "HR"
            elif "odds" in title_lower:
                effect_type = "OR"
            elif "risk ratio" in title_lower or "relative risk" in title_lower:
                effect_type = "RR"
            elif "rate ratio" in title_lower or "incidence" in title_lower:
                effect_type = "IRR"
            elif "mean" in title_lower or "change" in title_lower or "score" in title_lower:
                effect_type = "MD"
            elif param_type:
                # Additional inference from param_type
                param_lower = param_type.lower()
                if "hazard" in param_lower:
                    effect_type = "HR"
                elif "odds" in param_lower:
                    effect_type = "OR"
                elif "ratio" in param_lower:
                    effect_type = "RR"
                elif "difference" in param_lower or "mean" in param_lower:
                    effect_type = "MD"

        if not effect_type or not param_value:
            return None

        try:
            value = float(param_value)
            ci_low = float(ci_lower) if ci_lower else None
            ci_high = float(ci_upper) if ci_upper else None

            # Parse p-value
            p_val = None
            if p_value:
                p_value = p_value.replace("<", "").replace(">", "").strip()
                try:
                    p_val = float(p_value)
                except ValueError:
                    pass

            # Get group info
            groups = analysis.get("groupIds", [])
            arm1 = groups[0] if len(groups) > 0 else ""
            arm2 = groups[1] if len(groups) > 1 else ""

            return EffectEstimate(
                outcome_title=title,
                outcome_type=outcome_type,
                effect_type=effect_type,
                value=value,
                ci_lower=ci_low,
                ci_upper=ci_high,
                p_value=p_val,
                arm1_name=arm1,
                arm1_n=None,
                arm1_value=None,
                arm2_name=arm2,
                arm2_n=None,
                arm2_value=None,
                analysis_method=stat_method,
                source_text=f"{effect_type} {value} ({ci_low}-{ci_high})" if ci_low and ci_high else f"{effect_type} {value}"
            )

        except (ValueError, TypeError):
            return None

    def _infer_effect_type(self, method: str, param_type: str) -> Optional[str]:
        """Infer effect type from statistical method"""
        method_lower = method.lower()
        param_lower = param_type.lower()

        if "hazard" in method_lower or "cox" in method_lower:
            return "HR"
        elif "odds" in method_lower or "logistic" in method_lower:
            return "OR"
        elif "risk ratio" in method_lower or "relative risk" in method_lower:
            return "RR"
        elif "mean difference" in method_lower or "difference in means" in method_lower:
            return "MD"
        elif "standardized" in method_lower:
            return "SMD"
        elif "rate ratio" in method_lower or "incidence" in method_lower:
            return "IRR"
        elif "risk difference" in param_lower:
            return "ARD"
        elif "ratio" in param_lower:
            return "RR"
        elif "difference" in param_lower:
            return "MD"

        return None

    def _extract_from_measurements(
        self,
        measurements: list,
        groups: list,
        title: str,
        outcome_type: str,
        units: str
    ) -> Optional[EffectEstimate]:
        """Extract effect from group measurements"""
        # This extracts raw values for potential manual calculation
        # Not a direct effect estimate but useful for validation

        if len(measurements) < 2 or len(groups) < 2:
            return None

        try:
            m1 = measurements[0]
            m2 = measurements[1]

            val1 = float(m1.get("value", 0))
            val2 = float(m2.get("value", 0))

            # Calculate simple difference or ratio
            if "rate" in units.lower() or "percent" in units.lower():
                if val2 > 0:
                    ratio = val1 / val2
                    return EffectEstimate(
                        outcome_title=title,
                        outcome_type=outcome_type,
                        effect_type="RR",
                        value=round(ratio, 3),
                        ci_lower=None,
                        ci_upper=None,
                        p_value=None,
                        arm1_name=groups[0].get("title", ""),
                        arm1_n=int(m1.get("numSubjects", 0)) if m1.get("numSubjects") else None,
                        arm1_value=val1,
                        arm2_name=groups[1].get("title", ""),
                        arm2_n=int(m2.get("numSubjects", 0)) if m2.get("numSubjects") else None,
                        arm2_value=val2,
                        analysis_method="calculated",
                        source_text=f"Calculated RR: {ratio:.3f}"
                    )
            else:
                diff = val1 - val2
                return EffectEstimate(
                    outcome_title=title,
                    outcome_type=outcome_type,
                    effect_type="MD",
                    value=round(diff, 3),
                    ci_lower=None,
                    ci_upper=None,
                    p_value=None,
                    arm1_name=groups[0].get("title", ""),
                    arm1_n=int(m1.get("numSubjects", 0)) if m1.get("numSubjects") else None,
                    arm1_value=val1,
                    arm2_name=groups[1].get("title", ""),
                    arm2_n=int(m2.get("numSubjects", 0)) if m2.get("numSubjects") else None,
                    arm2_value=val2,
                    analysis_method="calculated",
                    source_text=f"Calculated MD: {diff:.3f}"
                )

        except (ValueError, TypeError, ZeroDivisionError):
            return None

    def search_studies(
        self,
        query: str,
        max_results: int = 100,
        has_results: bool = True,
        phase: Optional[str] = None
    ) -> List[str]:
        """
        Search for studies matching query.

        Args:
            query: Search query
            max_results: Maximum number of results
            has_results: Only return studies with results
            phase: Filter by phase (e.g., "PHASE3")

        Returns:
            List of NCT IDs
        """
        self._rate_limit_wait()

        params = {
            "format": "json",
            "query.term": query,
            "pageSize": min(max_results, 100),
            "fields": "NCTId"
        }

        if has_results:
            params["filter.advanced"] = "AREA[ResultsFirstPostDate]RANGE[MIN,MAX]"

        if phase:
            params["query.term"] += f" AND AREA[Phase]{phase}"

        try:
            response = requests.get(CTG_STUDY_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            studies = data.get("studies", [])
            nct_ids = []

            for study in studies:
                nct_id = study.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
                if nct_id:
                    nct_ids.append(nct_id)

            return nct_ids[:max_results]

        except requests.RequestException as e:
            print(f"Error searching: {e}")
            return []

    def fetch_multiple(self, nct_ids: List[str]) -> List[CTGStudy]:
        """Fetch multiple studies"""
        studies = []

        for i, nct_id in enumerate(nct_ids):
            print(f"[{i+1}/{len(nct_ids)}] Fetching {nct_id}...")
            study = self.fetch_study(nct_id)
            if study:
                studies.append(study)

        return studies


def save_studies(studies: List[CTGStudy], output_path: str):
    """Save studies to JSON file"""
    data = {
        "count": len(studies),
        "studies": [asdict(s) for s in studies]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Saved {len(studies)} studies to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="ClinicalTrials.gov Results Scraper")
    parser.add_argument("--nct", type=str, help="Single NCT ID to fetch")
    parser.add_argument("--search", type=str, help="Search query")
    parser.add_argument("--file", type=str, help="File with NCT IDs (one per line)")
    parser.add_argument("--max", type=int, default=100, help="Max results for search")
    parser.add_argument("--output", type=str, default="ctg_studies.json", help="Output file")
    parser.add_argument("--phase", type=str, help="Filter by phase (e.g., PHASE3)")

    args = parser.parse_args()

    if not HAS_REQUESTS:
        print("Error: requests library required. Install with: pip install requests")
        sys.exit(1)

    scraper = CTGScraper()
    studies = []

    if args.nct:
        # Fetch single study
        study = scraper.fetch_study(args.nct)
        if study:
            studies.append(study)
            print(f"\nStudy: {study.title}")
            print(f"Status: {study.status}")
            print(f"Has Results: {study.has_results}")
            print(f"Effect Estimates: {len(study.effect_estimates)}")

            for effect in study.effect_estimates:
                ci_str = f"({effect.ci_lower}-{effect.ci_upper})" if effect.ci_lower and effect.ci_upper else ""
                print(f"  {effect.effect_type}: {effect.value} {ci_str} - {effect.outcome_title[:50]}")

    elif args.search:
        # Search for studies
        print(f"Searching for: {args.search}")
        nct_ids = scraper.search_studies(args.search, max_results=args.max, phase=args.phase)
        print(f"Found {len(nct_ids)} studies with results")

        studies = scraper.fetch_multiple(nct_ids)

    elif args.file:
        # Read NCT IDs from file
        with open(args.file) as f:
            nct_ids = [line.strip() for line in f if line.strip()]

        print(f"Fetching {len(nct_ids)} studies from file")
        studies = scraper.fetch_multiple(nct_ids)

    else:
        parser.print_help()
        sys.exit(1)

    # Save results
    if studies:
        save_studies(studies, args.output)

        # Summary
        total_effects = sum(len(s.effect_estimates) for s in studies)
        with_effects = sum(1 for s in studies if s.effect_estimates)

        print(f"\n=== Summary ===")
        print(f"Studies fetched: {len(studies)}")
        print(f"Studies with effects: {with_effects}")
        print(f"Total effect estimates: {total_effects}")


if __name__ == "__main__":
    main()
