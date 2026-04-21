"""
Verify PMIDs by checking if the paper title/abstract matches the Cochrane outcome.
Uses PubMed E-utilities to fetch article metadata.
"""
import io
import json
import re
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(__file__).resolve().parents[1]
GOLD_DIR = PROJECT_DIR / "gold_data"
GOLD_FILE = GOLD_DIR / "gold_50.jsonl"

EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def fetch_pubmed_info(pmid):
    """Fetch title and abstract from PubMed."""
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml",
    })
    url = f"{EFETCH_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RCTExtractor/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode('utf-8')
        root = ET.fromstring(data)
        article = root.find('.//Article')
        if article is None:
            return None, None, None
        title_el = article.find('.//ArticleTitle')
        title = title_el.text if title_el is not None and title_el.text else ""
        abstract_el = article.find('.//Abstract')
        abstract = ""
        if abstract_el is not None:
            for at in abstract_el.findall('.//AbstractText'):
                label = at.get('Label', '')
                text = at.text or ''
                if label:
                    abstract += f" {label}: {text}"
                else:
                    abstract += f" {text}"
        # Check publication types
        pub_types = []
        for pt in article.findall('.//PublicationType'):
            if pt.text:
                pub_types.append(pt.text)
        return title.strip(), abstract.strip(), pub_types
    except Exception as e:
        return None, None, None


def is_rct_paper(title, abstract, pub_types):
    """Check if paper is likely an RCT results paper."""
    combined = (title + " " + abstract).lower()

    # Publication type check
    rct_pub_types = {'Randomized Controlled Trial', 'Clinical Trial', 'Clinical Trial, Phase III',
                     'Clinical Trial, Phase II', 'Comparative Study'}
    non_rct_pub_types = {'Review', 'Meta-Analysis', 'Systematic Review', 'Practice Guideline',
                         'Published Erratum', 'Editorial', 'Comment', 'Letter'}

    is_rct_type = any(pt in rct_pub_types for pt in pub_types)
    is_non_rct_type = any(pt in non_rct_pub_types for pt in pub_types)

    # Title keywords
    is_protocol = 'protocol' in title.lower() and 'result' not in title.lower()
    is_review = any(kw in title.lower() for kw in ['systematic review', 'meta-analysis', 'scoping review'])

    has_rct_kw = any(kw in combined for kw in ['randomized', 'randomised', 'random allocation',
                                                  'double-blind', 'placebo-controlled', 'clinical trial'])

    if is_non_rct_type or is_review:
        return "REVIEW/META"
    if is_protocol:
        return "PROTOCOL"
    if is_rct_type:
        return "RCT"
    if has_rct_kw and not is_protocol:
        return "LIKELY_RCT"
    return "UNKNOWN"


def outcome_relevance(title, abstract, cochrane_outcome):
    """Check if paper seems related to the Cochrane outcome."""
    combined = (title + " " + abstract).lower()

    # Extract key terms from Cochrane outcome
    outcome_lower = cochrane_outcome.lower()
    # Split into significant words (>3 chars)
    key_words = [w for w in re.split(r'[,;:/\s]+', outcome_lower) if len(w) > 3
                 and w not in ('outcome', 'versus', 'control', 'treatment', 'intervention',
                               'post', 'pre', 'measure', 'total', 'score')]

    if not key_words:
        return "NO_KEYWORDS"

    matches = sum(1 for w in key_words if w in combined)
    ratio = matches / len(key_words)

    if ratio >= 0.5:
        return f"RELEVANT ({matches}/{len(key_words)} keywords)"
    elif ratio > 0:
        return f"WEAK ({matches}/{len(key_words)} keywords)"
    return f"NO_MATCH (0/{len(key_words)} keywords: {key_words[:5]})"


def main():
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    print(f"Verifying {len(entries)} PMIDs against Cochrane outcomes...\n")

    results = {"RCT": 0, "LIKELY_RCT": 0, "PROTOCOL": 0, "REVIEW/META": 0, "UNKNOWN": 0, "FETCH_FAILED": 0}
    relevance = {"RELEVANT": 0, "WEAK": 0, "NO_MATCH": 0, "NO_KEYWORDS": 0, "FETCH_FAILED": 0}

    verified_entries = []

    for i, entry in enumerate(entries):
        pmid = entry.get("pmid", "")
        study_id = entry["study_id"]
        outcome = entry.get("cochrane_outcome", "")

        title, abstract, pub_types = fetch_pubmed_info(pmid)
        time.sleep(0.35)

        if title is None:
            paper_type = "FETCH_FAILED"
            rel = "FETCH_FAILED"
            title = "?"
            pub_types = []
        else:
            paper_type = is_rct_paper(title, abstract or "", pub_types)
            rel = outcome_relevance(title, abstract or "", outcome)

        results[paper_type] = results.get(paper_type, 0) + 1
        rel_cat = rel.split(" ")[0]
        relevance[rel_cat] = relevance.get(rel_cat, 0) + 1

        # Determine verdict
        if paper_type in ("RCT", "LIKELY_RCT") and "RELEVANT" in rel:
            verdict = "GOOD"
        elif paper_type in ("RCT", "LIKELY_RCT"):
            verdict = "RCT_WRONG_OUTCOME"
        elif paper_type == "PROTOCOL":
            verdict = "WRONG_PROTOCOL"
        elif paper_type == "REVIEW/META":
            verdict = "WRONG_REVIEW"
        elif paper_type == "FETCH_FAILED":
            verdict = "CHECK_MANUALLY"
        else:
            verdict = "CHECK_MANUALLY"

        short_title = title[:60] + "..." if len(title) > 60 else title
        print(f"  [{i+1:2d}] {study_id:25s} | {paper_type:12s} | {rel:40s} | {verdict}")
        if verdict != "GOOD":
            print(f"        Title: {short_title}")
            if pub_types:
                print(f"        PubTypes: {', '.join(pub_types[:3])}")

        entry["_verify"] = {
            "paper_type": paper_type,
            "relevance": rel,
            "verdict": verdict,
            "title": title,
            "pub_types": pub_types,
        }
        verified_entries.append(entry)

    # Summary
    print(f"\n{'='*60}")
    print("PMID VERIFICATION SUMMARY")
    print(f"{'='*60}")
    print(f"\nPaper type distribution:")
    for k, v in sorted(results.items(), key=lambda x: -x[1]):
        print(f"  {k:20s}: {v}")

    print(f"\nOutcome relevance:")
    for k, v in sorted(relevance.items(), key=lambda x: -x[1]):
        print(f"  {k:20s}: {v}")

    verdicts = {}
    for e in verified_entries:
        v = e["_verify"]["verdict"]
        verdicts[v] = verdicts.get(v, 0) + 1

    print(f"\nVerdicts:")
    for k, v in sorted(verdicts.items(), key=lambda x: -x[1]):
        print(f"  {k:25s}: {v}")

    # Save verification results
    verify_file = GOLD_DIR / "pmid_verification.json"
    with open(verify_file, 'w') as f:
        json.dump([{
            "study_id": e["study_id"],
            "pmid": e.get("pmid"),
            "pmcid": e.get("pmcid"),
            "verify": e["_verify"],
        } for e in verified_entries], f, indent=2)
    print(f"\nSaved to {verify_file}")


if __name__ == "__main__":
    main()
