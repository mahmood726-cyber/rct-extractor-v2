#!/usr/bin/env python3
"""
Find Correct PMC IDs for Validation Trials
==========================================

Uses Europe PMC API to search for correct open-access RCT papers.
"""

import urllib.request
import urllib.parse
import json
import time
from pathlib import Path

# Trials we need to find
TRIALS_TO_FIND = [
    # Trial name, search terms, expected journal/year
    ("DAPA-HF", "DAPA-HF dapagliflozin heart failure", "NEJM 2019"),
    ("EMPEROR-Reduced", "EMPEROR-Reduced empagliflozin heart failure", "NEJM 2020"),
    ("PARADIGM-HF", "PARADIGM-HF sacubitril valsartan", "NEJM 2014"),
    ("EMPA-REG OUTCOME", "EMPA-REG OUTCOME empagliflozin", "NEJM 2015"),
    ("CANVAS", "CANVAS canagliflozin cardiovascular", "NEJM 2017"),
    ("DECLARE-TIMI", "DECLARE-TIMI dapagliflozin diabetes", "NEJM 2018"),
    ("FOURIER", "FOURIER evolocumab cardiovascular", "NEJM 2017"),
    ("SUSTAIN-6", "SUSTAIN-6 semaglutide cardiovascular", "NEJM 2016"),
    ("SELECT", "SELECT semaglutide obesity cardiovascular", "NEJM 2023"),
    ("CREDENCE", "CREDENCE canagliflozin kidney", "NEJM 2019"),
    ("SCORED", "SCORED sotagliflozin diabetes", "NEJM 2021"),
    ("SOLOIST-WHF", "SOLOIST-WHF sotagliflozin heart failure", "NEJM 2021"),
    ("VERTIS-CV", "VERTIS-CV ertugliflozin cardiovascular", "2020"),
]


def search_europepmc(query: str, limit: int = 5) -> list:
    """Search Europe PMC for papers matching query"""
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": query + " AND (OPEN_ACCESS:Y OR IN_PMC:Y)",
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
        print(f"  Error: {e}")
        return []


def main():
    print("=" * 70)
    print("SEARCHING FOR CORRECT PMC IDs")
    print("=" * 70)

    results = []

    for trial_name, search_terms, expected in TRIALS_TO_FIND:
        print(f"\n{trial_name} ({expected})")
        print("-" * 40)

        papers = search_europepmc(search_terms)
        time.sleep(0.5)  # Rate limit

        if not papers:
            print("  No results found")
            results.append({
                "trial": trial_name,
                "pmc_id": None,
                "pmid": None,
                "title": None,
                "note": "No open-access version found"
            })
            continue

        # Show top results
        found_match = False
        for p in papers[:3]:
            pmcid = p.get("pmcid", "")
            pmid = p.get("pmid", "")
            title = p.get("title", "")[:70]
            journal = p.get("journalTitle", "")
            year = p.get("pubYear", "")

            print(f"  {pmcid or 'NO-PMC'} | PMID:{pmid} | {year}")
            print(f"    {title}...")
            print(f"    {journal}")

            # Check if this looks like primary results paper
            title_lower = title.lower()
            is_primary = any(term in title_lower for term in [
                "versus", "compared with", "in patients with",
                "outcomes", "efficacy", "safety", trial_name.lower()
            ])

            if pmcid and is_primary and not found_match:
                results.append({
                    "trial": trial_name,
                    "pmc_id": pmcid,
                    "pmid": pmid,
                    "title": title,
                    "journal": journal,
                    "year": year
                })
                found_match = True
                print(f"    ^^^ SELECTED")

        if not found_match:
            results.append({
                "trial": trial_name,
                "pmc_id": None,
                "pmid": papers[0].get("pmid") if papers else None,
                "title": papers[0].get("title", "")[:70] if papers else None,
                "note": "Primary results not in PMC (paywalled)"
            })

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    available = [r for r in results if r.get("pmc_id")]
    print(f"\nTrials with PMC access: {len(available)} / {len(results)}")

    if available:
        print("\nAvailable for download:")
        for r in available:
            print(f"  {r['trial']}: {r['pmc_id']}")

    not_available = [r for r in results if not r.get("pmc_id")]
    if not_available:
        print("\nNOT available (paywalled or no PMC):")
        for r in not_available:
            print(f"  {r['trial']}: {r.get('note', 'Unknown')}")

    # Save results
    output_path = Path(__file__).parent.parent / "output" / "pmc_search_results.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
