#!/usr/bin/env python3
"""
Search PubMed for RCT Publications with Free Full Text
========================================================

Searches PubMed/PMC for randomized controlled trial publications
that have free full text available for download.

Filters:
- Publication type: Randomized Controlled Trial
- Has effect estimates (HR, OR, RR) in abstract
- Free full text available
- Major journals: NEJM, Lancet, JAMA, BMJ
- Phase 3 trials with NCT IDs

Usage:
    python scripts/search_rct_publications.py
    python scripts/search_rct_publications.py --max 100
    python scripts/search_rct_publications.py --condition "heart failure" --max 50
    python scripts/search_rct_publications.py --journals-only
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("Warning: requests not installed. Run: pip install requests")

try:
    from xml.etree import ElementTree as ET
    HAS_XML = True
except ImportError:
    HAS_XML = False


# NCBI E-utilities endpoints
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"

# Rate limiting: 3 requests/second without API key, 10/second with
REQUEST_DELAY = 0.35

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"


@dataclass
class RCTPublication:
    """A found RCT publication"""
    pmid: str
    pmc_id: Optional[str]
    title: str
    journal: str
    year: int
    nct_id: Optional[str]
    has_effect_estimate: bool
    abstract_snippet: str
    doi: Optional[str]


class PubMedSearcher:
    """Search PubMed for RCT publications"""

    # Major medical journals for high-quality RCTs
    MAJOR_JOURNALS = [
        "N Engl J Med",
        "NEJM",
        "Lancet",
        "JAMA",
        "BMJ",
        "Ann Intern Med",
        "Circulation",
        "Eur Heart J",
        "J Clin Oncol",
        "Lancet Oncol",
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize searcher.

        Args:
            api_key: NCBI API key (optional, increases rate limit)
        """
        self.api_key = api_key
        self.session = requests.Session()
        self._last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def _build_query(
        self,
        condition: Optional[str] = None,
        journals_only: bool = False,
        year_start: int = 2018,
        year_end: int = 2025,
        require_nct: bool = True,
        require_effect_estimate: bool = True,
    ) -> str:
        """Build PubMed search query"""
        parts = []

        # Publication type: RCT
        parts.append('("randomized controlled trial"[pt])')

        # Free full text
        parts.append("free full text[filter]")

        # Date range
        parts.append(f"{year_start}:{year_end}[pdat]")

        # Condition filter
        if condition:
            parts.append(f'("{condition}"[tiab])')

        # Effect estimate keywords (likely to have results)
        if require_effect_estimate:
            effect_terms = [
                '"hazard ratio"[tiab]',
                '"odds ratio"[tiab]',
                '"relative risk"[tiab]',
                '"risk ratio"[tiab]',
                '"mean difference"[tiab]',
            ]
            parts.append(f'({" OR ".join(effect_terms)})')

        # NCT ID filter
        if require_nct:
            parts.append('NCT[tiab]')

        # Major journals filter
        if journals_only:
            journal_terms = [f'"{j}"[journal]' for j in self.MAJOR_JOURNALS]
            parts.append(f'({" OR ".join(journal_terms)})')

        return " AND ".join(parts)

    def search(
        self,
        query: Optional[str] = None,
        condition: Optional[str] = None,
        max_results: int = 100,
        journals_only: bool = False,
        year_start: int = 2018,
        year_end: int = 2025,
        require_nct: bool = True,
        require_effect_estimate: bool = True,
    ) -> List[str]:
        """
        Search PubMed for RCTs matching criteria.

        Returns:
            List of PMIDs
        """
        if query is None:
            query = self._build_query(
                condition=condition,
                journals_only=journals_only,
                year_start=year_start,
                year_end=year_end,
                require_nct=require_nct,
                require_effect_estimate=require_effect_estimate,
            )

        print(f"Search query: {query[:100]}...")

        self._rate_limit()

        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "usehistory": "n",
        }

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = self.session.get(ESEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            result = data.get("esearchresult", {})
            pmids = result.get("idlist", [])
            total = int(result.get("count", 0))

            print(f"Found {total} total results, returning {len(pmids)}")
            return pmids

        except requests.RequestException as e:
            print(f"Search error: {e}")
            return []

    def get_pmids_with_pmc(self, pmids: List[str]) -> Dict[str, str]:
        """
        Get PMC IDs for given PMIDs.

        Returns:
            Dict mapping PMID -> PMC ID
        """
        if not pmids:
            return {}

        pmc_map = {}

        # Process in batches
        batch_size = 100
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i+batch_size]
            self._rate_limit()

            params = {
                "dbfrom": "pubmed",
                "db": "pmc",
                "id": ",".join(batch),
                "retmode": "json",
            }

            if self.api_key:
                params["api_key"] = self.api_key

            try:
                response = self.session.get(ELINK_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                linksets = data.get("linksets", [])
                for linkset in linksets:
                    pmid = str(linkset.get("ids", [""])[0])
                    linksetdbs = linkset.get("linksetdbs", [])
                    for lsdb in linksetdbs:
                        if lsdb.get("dbto") == "pmc":
                            links = lsdb.get("links", [])
                            if links:
                                pmc_map[pmid] = f"PMC{links[0]}"

            except requests.RequestException as e:
                print(f"ELink error: {e}")

        return pmc_map

    def fetch_article_details(self, pmids: List[str]) -> List[RCTPublication]:
        """
        Fetch article details for PMIDs.

        Returns:
            List of RCTPublication objects
        """
        if not pmids:
            return []

        publications = []

        # Get PMC mappings first
        print("Fetching PMC IDs...")
        pmc_map = self.get_pmids_with_pmc(pmids)
        print(f"Found {len(pmc_map)} articles with PMC IDs")

        # Fetch article metadata
        batch_size = 50
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i+batch_size]
            self._rate_limit()

            params = {
                "db": "pubmed",
                "id": ",".join(batch),
                "rettype": "xml",
                "retmode": "xml",
            }

            if self.api_key:
                params["api_key"] = self.api_key

            try:
                response = self.session.get(EFETCH_URL, params=params, timeout=60)
                response.raise_for_status()

                # Parse XML
                root = ET.fromstring(response.content)

                for article in root.findall(".//PubmedArticle"):
                    pub = self._parse_article(article, pmc_map)
                    if pub:
                        publications.append(pub)

            except Exception as e:
                print(f"Fetch error: {e}")

        return publications

    def _parse_article(self, article_elem, pmc_map: Dict[str, str]) -> Optional[RCTPublication]:
        """Parse a PubmedArticle XML element"""
        try:
            medline = article_elem.find(".//MedlineCitation")
            if medline is None:
                return None

            pmid_elem = medline.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""

            article = medline.find(".//Article")
            if article is None:
                return None

            # Title
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else ""

            # Journal
            journal_elem = article.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else ""

            # Year
            year = 0
            year_elem = article.find(".//PubDate/Year")
            if year_elem is not None and year_elem.text:
                try:
                    year = int(year_elem.text)
                except ValueError:
                    pass

            # Abstract
            abstract_elem = article.find(".//Abstract/AbstractText")
            abstract = abstract_elem.text if abstract_elem is not None else ""
            if not abstract:
                # Try concatenated abstract
                abstract_parts = article.findall(".//Abstract/AbstractText")
                abstract = " ".join([p.text or "" for p in abstract_parts])

            # DOI
            doi = None
            for id_elem in article.findall(".//ArticleIdList/ArticleId"):
                if id_elem.get("IdType") == "doi":
                    doi = id_elem.text
                    break

            # Extract NCT ID from abstract
            nct_id = None
            if abstract:
                import re
                nct_match = re.search(r'NCT\d{8}', abstract, re.IGNORECASE)
                if nct_match:
                    nct_id = nct_match.group(0).upper()

            # Check for effect estimates in abstract
            has_effect = bool(re.search(
                r'(?:hazard|odds|risk|rate)\s+ratio|mean\s+difference',
                abstract, re.IGNORECASE
            )) if abstract else False

            # Get PMC ID
            pmc_id = pmc_map.get(pmid)

            return RCTPublication(
                pmid=pmid,
                pmc_id=pmc_id,
                title=title[:200] if title else "",
                journal=journal,
                year=year,
                nct_id=nct_id,
                has_effect_estimate=has_effect,
                abstract_snippet=abstract[:500] if abstract else "",
                doi=doi,
            )

        except Exception as e:
            print(f"Parse error: {e}")
            return None


def save_results(publications: List[RCTPublication], output_path: Path):
    """Save search results to JSON"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Filter to those with PMC IDs
    with_pmc = [p for p in publications if p.pmc_id]
    with_nct = [p for p in with_pmc if p.nct_id]

    data = {
        "version": "4.3.0",
        "generated": datetime.now().isoformat(),
        "summary": {
            "total_found": len(publications),
            "with_pmc_id": len(with_pmc),
            "with_nct_id": len(with_nct),
            "with_effect_estimate": len([p for p in with_pmc if p.has_effect_estimate]),
        },
        "publications": [asdict(p) for p in with_pmc],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved {len(with_pmc)} publications to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Search PubMed for RCT publications with free full text"
    )
    parser.add_argument(
        "--max", type=int, default=100,
        help="Maximum number of results"
    )
    parser.add_argument(
        "--condition", type=str,
        help="Condition to search for (e.g., 'heart failure')"
    )
    parser.add_argument(
        "--journals-only", action="store_true",
        help="Limit to major medical journals only"
    )
    parser.add_argument(
        "--year-start", type=int, default=2018,
        help="Start year for search"
    )
    parser.add_argument(
        "--year-end", type=int, default=2025,
        help="End year for search"
    )
    parser.add_argument(
        "--api-key", type=str,
        help="NCBI API key (increases rate limit)"
    )
    parser.add_argument(
        "--output", type=Path,
        default=OUTPUT_DIR / "pubmed_rct_search.json",
        help="Output file path"
    )
    parser.add_argument(
        "--no-nct", action="store_true",
        help="Don't require NCT ID in abstract"
    )
    parser.add_argument(
        "--no-effect", action="store_true",
        help="Don't require effect estimate keywords"
    )

    args = parser.parse_args()

    if not HAS_REQUESTS:
        print("Error: requests library required")
        sys.exit(1)

    searcher = PubMedSearcher(api_key=args.api_key)

    # Search
    print("\nSearching PubMed...")
    pmids = searcher.search(
        condition=args.condition,
        max_results=args.max,
        journals_only=args.journals_only,
        year_start=args.year_start,
        year_end=args.year_end,
        require_nct=not args.no_nct,
        require_effect_estimate=not args.no_effect,
    )

    if not pmids:
        print("No results found")
        sys.exit(0)

    # Fetch details
    print("\nFetching article details...")
    publications = searcher.fetch_article_details(pmids)

    # Save results
    save_results(publications, args.output)

    # Print summary
    print("\n" + "=" * 60)
    print("SEARCH RESULTS SUMMARY")
    print("=" * 60)

    with_pmc = [p for p in publications if p.pmc_id]
    with_nct = [p for p in with_pmc if p.nct_id]

    print(f"Total found: {len(publications)}")
    print(f"With PMC ID: {len(with_pmc)}")
    print(f"With NCT ID: {len(with_nct)}")
    print(f"With effect estimate: {len([p for p in with_pmc if p.has_effect_estimate])}")

    if with_pmc:
        print("\nSample publications:")
        for pub in with_pmc[:5]:
            print(f"  {pub.pmid}: {pub.title[:60]}...")
            print(f"    Journal: {pub.journal}, Year: {pub.year}")
            if pub.nct_id:
                print(f"    NCT: {pub.nct_id}")
            print(f"    PMC: {pub.pmc_id}")

    print("=" * 60)


if __name__ == "__main__":
    main()
