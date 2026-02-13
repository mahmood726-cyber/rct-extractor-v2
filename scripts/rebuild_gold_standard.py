"""
Rebuild gold standard with outcome-aware PubMed search.
Uses Cochrane outcome keywords + author + year to find the CORRECT paper.
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

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
GOLD_DIR = PROJECT_DIR / "gold_data"
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
GOLD_FILE = GOLD_DIR / "gold_50.jsonl"
CANDIDATES_FILE = GOLD_DIR / "candidates.json"
NEW_GOLD_FILE = GOLD_DIR / "gold_v2.jsonl"

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def extract_outcome_keywords(outcome_text):
    """Extract searchable keywords from Cochrane outcome name."""
    # Remove common non-specific words
    stop_words = {'outcome', 'versus', 'control', 'treatment', 'intervention',
                  'post', 'pre', 'measure', 'total', 'score', 'rate', 'mean',
                  'number', 'change', 'from', 'baseline', 'difference',
                  'post-treatment', 'follow-up', 'months', 'weeks', 'days',
                  'hours', 'year', 'years', 'month', 'week', 'day', 'hour',
                  'primary', 'secondary', 'endpoint', 'group', 'arm',
                  'reported', 'overall', 'any', 'all', 'with', 'without',
                  'after', 'before', 'during', 'between', 'within',
                  'studies', 'study', 'trials', 'trial',
                  'high', 'low', 'moderate', 'severe', 'mild',
                  '(0.5', '(1', '(2', '(3', '(4', '(6', '(12', '(24',
                  'vas)', 'mm)', '(vas)', '(mm)',
                  'person', 'patient', 'participants', 'women', 'men',
                  'children', 'adults', 'infants',
                  }

    # Split on non-alphanumeric
    words = re.split(r'[^a-zA-Z]+', outcome_text.lower())
    keywords = [w for w in words if len(w) > 3 and w not in stop_words]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            unique.append(w)

    return unique[:4]  # Max 4 keywords


def search_pubmed_with_outcome(author_name, year, outcome_keywords, cochrane_type):
    """Search PubMed using author + year + outcome keywords."""
    # Parse first author surname
    parts = author_name.split('_')
    surname = parts[0] if parts else author_name

    results = []

    # Strategy 1: author + year + first outcome keyword
    for kw in outcome_keywords[:2]:
        query = f'{surname}[1au] AND {year}[dp] AND {kw}[tiab]'
        pmids = _esearch(query)
        if pmids:
            results.extend(pmids)

    # Strategy 2: author + year + "randomized" + outcome keyword
    if not results and outcome_keywords:
        query = f'{surname}[1au] AND {year}[dp] AND randomized[tiab] AND {outcome_keywords[0]}[tiab]'
        pmids = _esearch(query)
        results.extend(pmids)

    # Strategy 3: broader author + outcome keyword (no year restriction of 1 year)
    if not results and outcome_keywords:
        yr = int(year)
        query = f'{surname}[au] AND {yr-1}:{yr+1}[dp] AND {outcome_keywords[0]}[tiab]'
        pmids = _esearch(query)
        results.extend(pmids)

    # Deduplicate
    seen = set()
    unique = []
    for pmid in results:
        if pmid not in seen:
            seen.add(pmid)
            unique.append(pmid)

    return unique[:5]  # Max 5 candidates


def _esearch(query):
    """Run PubMed search."""
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": query,
        "retmax": "5",
        "retmode": "json",
    })
    url = f"{ESEARCH_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RCTExtractor/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []


def fetch_article_info(pmid):
    """Fetch article metadata from PubMed."""
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
            return None

        title_el = article.find('.//ArticleTitle')
        title = title_el.text if title_el is not None and title_el.text else ""

        abstract_el = article.find('.//Abstract')
        abstract = ""
        if abstract_el is not None:
            for at in abstract_el.findall('.//AbstractText'):
                text = at.text or ''
                abstract += f" {text}"

        # PMC ID
        pmc_id = None
        for aid in root.findall('.//ArticleId'):
            if aid.get('IdType') == 'pmc':
                pmc_id = aid.text

        # Publication types
        pub_types = []
        for pt in article.findall('.//PublicationType'):
            if pt.text:
                pub_types.append(pt.text)

        return {
            "pmid": pmid,
            "pmcid": pmc_id,
            "title": title.strip(),
            "abstract": abstract.strip()[:500],
            "pub_types": pub_types,
        }
    except Exception:
        return None


def score_candidate(info, outcome_keywords, cochrane_type):
    """Score a candidate paper for relevance."""
    if info is None:
        return -1

    combined = (info["title"] + " " + info["abstract"]).lower()
    score = 0

    # Outcome keyword matches (most important)
    for kw in outcome_keywords:
        if kw in combined:
            score += 3

    # RCT publication type
    rct_types = {'Randomized Controlled Trial', 'Clinical Trial', 'Clinical Trial, Phase III',
                 'Clinical Trial, Phase II'}
    bad_types = {'Review', 'Meta-Analysis', 'Systematic Review', 'Protocol'}
    for pt in info["pub_types"]:
        if pt in rct_types:
            score += 5
        if pt in bad_types:
            score -= 10

    # Protocol in title = bad
    if 'protocol' in info["title"].lower():
        score -= 8

    # Review/meta in title = bad
    if 'systematic review' in info["title"].lower() or 'meta-analysis' in info["title"].lower():
        score -= 8

    # RCT keywords in abstract
    for kw in ['randomized', 'randomised', 'double-blind', 'placebo']:
        if kw in combined:
            score += 1

    # Has PMC (we need OA full text)
    if info["pmcid"]:
        score += 2

    return score


def download_pdf(pmcid, output_path):
    """Download PDF from Europe PMC."""
    if output_path.exists():
        return True

    url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/pdf",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            if len(content) < 5000 or not content[:5] == b'%PDF-':
                return False
            with open(output_path, 'wb') as f:
                f.write(content)
            return True
    except Exception:
        return False


def main():
    # Load current gold entries
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    # Load verification results
    verify_file = GOLD_DIR / "pmid_verification.json"
    verify_data = {}
    if verify_file.exists():
        with open(verify_file) as f:
            for v in json.load(f):
                verify_data[v["study_id"]] = v["verify"]

    print(f"Rebuilding gold standard: {len(entries)} entries")
    print(f"{'='*70}\n")

    new_entries = []
    stats = {"kept": 0, "replaced": 0, "dropped": 0, "downloaded": 0}

    for i, entry in enumerate(entries):
        study_id = entry["study_id"]
        verdict = verify_data.get(study_id, {}).get("verdict", "CHECK_MANUALLY")
        outcome = entry.get("cochrane_outcome", "")
        cochrane_type = entry.get("cochrane_outcome_type", "binary")

        print(f"  [{i+1:2d}] {study_id:25s} [{verdict}]", end=" ")

        # Keep good entries
        if verdict == "GOOD":
            print("-> KEEP")
            new_entries.append(entry)
            stats["kept"] += 1
            continue

        # Try to find the correct paper
        author_year = study_id.split("_")
        if len(author_year) >= 2:
            author = author_year[0]
            year = author_year[-1]
        else:
            print("-> DROP (can't parse author/year)")
            stats["dropped"] += 1
            continue

        outcome_kw = extract_outcome_keywords(outcome)
        if not outcome_kw:
            print(f"-> DROP (no outcome keywords from: {outcome[:40]})")
            stats["dropped"] += 1
            continue

        print(f"searching [{', '.join(outcome_kw[:3])}]...", end=" ")

        # Search PubMed with outcome keywords
        pmids = search_pubmed_with_outcome(author, year, outcome_kw, cochrane_type)
        time.sleep(0.4)

        if not pmids:
            print("-> DROP (no results)")
            stats["dropped"] += 1
            continue

        # Score candidates
        best_info = None
        best_score = -999

        for pmid in pmids:
            info = fetch_article_info(pmid)
            time.sleep(0.35)
            if info is None:
                continue
            score = score_candidate(info, outcome_kw, cochrane_type)
            if score > best_score:
                best_score = score
                best_info = info

        if best_info is None or best_score < 3:
            print(f"-> DROP (best score={best_score})")
            stats["dropped"] += 1
            continue

        # Check if it has PMC ID for PDF download
        if not best_info["pmcid"]:
            print(f"-> DROP (no PMC: {best_info['title'][:40]})")
            stats["dropped"] += 1
            continue

        pmcid = best_info["pmcid"]
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"

        # Is this the same paper we already have?
        if pmcid == entry.get("pmcid"):
            print(f"-> KEEP (same PMC)")
            new_entries.append(entry)
            stats["kept"] += 1
            continue

        # New paper — download PDF
        pdf_filename = f"{pmcid}_{study_id}.pdf"
        pdf_path = PDF_DIR / pdf_filename

        downloaded = download_pdf(pmcid, pdf_path)
        time.sleep(0.3)

        if not downloaded:
            print(f"-> DROP (download failed: {pmcid})")
            stats["dropped"] += 1
            continue

        # Update entry with new paper
        old_pmcid = entry.get("pmcid", "?")
        entry["pmcid"] = pmcid
        entry["pmid"] = best_info["pmid"]
        entry["pdf_filename"] = pdf_filename
        new_entries.append(entry)
        stats["replaced"] += 1
        stats["downloaded"] += 1

        short_title = best_info["title"][:50]
        print(f"-> REPLACED ({old_pmcid} -> {pmcid}: {short_title}...)")

    # Save new gold standard
    with open(NEW_GOLD_FILE, 'w') as f:
        for entry in new_entries:
            # Clean up any verify metadata
            clean = {k: v for k, v in entry.items() if not k.startswith('_')}
            f.write(json.dumps(clean) + "\n")

    print(f"\n{'='*70}")
    print(f"REBUILD SUMMARY")
    print(f"{'='*70}")
    print(f"  Original entries:  {len(entries)}")
    print(f"  Kept (correct):    {stats['kept']}")
    print(f"  Replaced (new PDF):{stats['replaced']}")
    print(f"  Dropped:           {stats['dropped']}")
    print(f"  New PDFs downloaded:{stats['downloaded']}")
    print(f"  Final entries:     {len(new_entries)}")
    print(f"\n  Saved to: {NEW_GOLD_FILE}")


if __name__ == "__main__":
    main()
