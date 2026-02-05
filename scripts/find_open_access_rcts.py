#!/usr/bin/env python3
"""
Find Open-Access RCT Results Papers
===================================

Searches Europe PMC for actual RCT results papers with open access.
Focuses on papers with "hazard ratio" or "odds ratio" in abstract.
"""

import urllib.request
import urllib.parse
import json
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent


def search_europepmc(query: str, limit: int = 25) -> list:
    """Search Europe PMC for papers"""
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": query,
        "format": "json",
        "pageSize": limit,
        "resultType": "lite"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get("resultList", {}).get("result", [])
    except Exception as e:
        print(f"Error: {e}")
        return []


def main():
    print("=" * 70)
    print("FINDING OPEN-ACCESS RCT RESULTS PAPERS")
    print("=" * 70)

    # Search queries targeting actual RCT results papers
    searches = [
        # Heart failure RCTs
        '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"hazard ratio" AND ABSTRACT:"heart failure" AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',

        # Diabetes RCTs
        '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"hazard ratio" AND ABSTRACT:"type 2 diabetes" AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',

        # Oncology RCTs
        '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"hazard ratio" AND ABSTRACT:"overall survival" AND IN_PMC:Y AND PUB_YEAR:[2020 TO 2025]',

        # Vaccine trials
        '(TITLE:"randomized" OR TITLE:"randomised") AND ABSTRACT:"vaccine efficacy" AND IN_PMC:Y AND PUB_YEAR:[2020 TO 2025]',

        # SGLT2 inhibitor trials (many have author manuscripts in PMC)
        'ABSTRACT:"SGLT2" AND ABSTRACT:"hazard ratio" AND ABSTRACT:"cardiovascular" AND IN_PMC:Y AND PUB_YEAR:[2018 TO 2025]',
    ]

    all_papers = []
    seen_pmcids = set()

    for i, query in enumerate(searches, 1):
        print(f"\nSearch {i}/{len(searches)}...")
        print(f"  Query: {query[:60]}...")

        papers = search_europepmc(query, limit=15)
        time.sleep(0.5)

        for p in papers:
            pmcid = p.get("pmcid")
            if not pmcid or pmcid in seen_pmcids:
                continue

            seen_pmcids.add(pmcid)

            # Check if this looks like a primary results paper (not review/meta-analysis)
            title = p.get("title", "").lower()
            is_review = any(term in title for term in [
                "review", "meta-analysis", "systematic", "pooled",
                "commentary", "editorial", "guidelines"
            ])

            if not is_review:
                all_papers.append({
                    "pmcid": pmcid,
                    "pmid": p.get("pmid"),
                    "title": p.get("title", "")[:100],
                    "journal": p.get("journalTitle", ""),
                    "year": p.get("pubYear"),
                    "doi": p.get("doi"),
                })
                print(f"  + {pmcid}: {p.get('title', '')[:50]}...")

    print(f"\n\nFound {len(all_papers)} potential RCT results papers")

    # Deduplicate and sort by year
    all_papers.sort(key=lambda x: x.get("year", ""), reverse=True)

    # Save list
    output_path = PROJECT_ROOT / "output" / "open_access_rcts.json"
    with open(output_path, "w") as f:
        json.dump({
            "search_date": datetime.now().isoformat(),
            "total_papers": len(all_papers),
            "papers": all_papers[:50]  # Top 50
        }, f, indent=2)

    print(f"\nSaved to: {output_path}")

    # Print top papers
    print("\n" + "=" * 70)
    print("TOP 20 PAPERS FOR VALIDATION")
    print("=" * 70)

    for i, p in enumerate(all_papers[:20], 1):
        print(f"\n{i}. {p['pmcid']}")
        print(f"   {p['title']}")
        print(f"   {p['journal']} ({p['year']})")


if __name__ == "__main__":
    main()
