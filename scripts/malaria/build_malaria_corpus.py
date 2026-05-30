"""
Build the malaria RCT corpus index from PubMed.

Queries PubMed E-utilities for malaria randomized controlled trials, then
enriches each record with:
  - abstract (cross-validation ground truth for reported effect sizes)
  - PMCID + DOI (via the NCBI ID Converter) -> tells us which have an OA PDF
  - NCT id(s) (via efetch DataBank/AccessionNumber) -> links to ClinicalTrials.gov/AACT

Output: data/field_portability/malaria/malaria_matched.jsonl
  one JSON object per study:
  {study_id, pmid, pmcid, doi, nct_id, title, journal, year, abstract, has_pdf}

No third-party deps (urllib + stdlib xml only). Rate-limited and resumable.

Usage:
  python scripts/malaria/build_malaria_corpus.py --retmax 3000
  python scripts/malaria/build_malaria_corpus.py --retmax 5000 --email you@x.org
"""
import argparse
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

# Only reassign stdout when run as a script. Doing it at import time double-wraps
# the stream for any importer and closes it at exit (lessons.md: module-level
# sys.stdout reassignment). Importers should set PYTHONUTF8=1 instead.
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_DIR / "data" / "field_portability" / "malaria"
OUT_FILE = OUT_DIR / "malaria_matched.jsonl"

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
IDCONV = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"

DEFAULT_TERM = (
    '(malaria[Title/Abstract] OR plasmodium[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def _get(url, tool_email, retries=3, sleep=0.34):
    """Rate-limited GET returning bytes, with bounded retry/backoff."""
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}tool=rct-extractor-malaria&email={urllib.parse.quote(tool_email)}"
    headers = {"User-Agent": f"rct-extractor-malaria (mailto:{tool_email})"}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            time.sleep(sleep)  # NCBI: <=3 req/s without key
            return data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5 * (attempt + 1))
            else:
                time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def esearch_pmids(term, retmax, email):
    """Return list of PMIDs for the query (newest first)."""
    url = (f"{EUTILS}/esearch.fcgi?db=pubmed&retmode=json&sort=date"
           f"&retmax={retmax}&term={urllib.parse.quote(term)}")
    data = _get(url, email)
    if not data:
        return []
    obj = json.loads(data.decode("utf-8", "replace"))
    return obj.get("esearchresult", {}).get("idlist", [])


def _text(el):
    return "".join(el.itertext()).strip() if el is not None else ""


def efetch_records(pmids, email):
    """Fetch title/abstract/journal/year/NCT for a batch of PMIDs."""
    out = {}
    url = f"{EUTILS}/efetch.fcgi?db=pubmed&retmode=xml&id={','.join(pmids)}"
    data = _get(url, email)
    if not data:
        return out
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return out
    for art in root.findall(".//PubmedArticle"):
        pmid_el = art.find(".//PMID")
        pmid = _text(pmid_el)
        if not pmid:
            continue
        title = _text(art.find(".//ArticleTitle"))
        journal = _text(art.find(".//Journal/Title"))
        year = _text(art.find(".//JournalIssue/PubDate/Year")) or \
            _text(art.find(".//JournalIssue/PubDate/MedlineDate"))[:4]
        # Abstract may be split into labelled sections
        abstract_parts = []
        for ab in art.findall(".//Abstract/AbstractText"):
            label = ab.get("Label")
            txt = _text(ab)
            abstract_parts.append(f"{label}: {txt}" if label else txt)
        abstract = "\n".join(p for p in abstract_parts if p)
        # NCT ids: DataBank accession numbers + any AccessionNumber NCT*
        ncts = set()
        for db in art.findall(".//DataBankList/DataBank"):
            name = _text(db.find("DataBankName")).lower()
            if "clinicaltrials" in name:
                for acc in db.findall(".//AccessionNumber"):
                    val = _text(acc).upper()
                    if val.startswith("NCT"):
                        ncts.add(val)
        for acc in art.findall(".//AccessionNumber"):
            val = _text(acc).upper()
            if val.startswith("NCT"):
                ncts.add(val)
        # Other registry IDs (ISRCTN, PACTR) appear in DataBanks or free text.
        # These registries have no posted numeric results, but the ID is useful
        # provenance linking each extraction back to its trial registration.
        other_reg = set()
        blob = f"{title}\n{abstract}"
        for db in art.findall(".//DataBankList/DataBank"):
            name = _text(db.find("DataBankName")).upper()
            for acc in db.findall(".//AccessionNumber"):
                val = _text(acc).upper()
                if val.startswith("ISRCTN") or val.startswith("PACTR"):
                    other_reg.add(val)
        for m in re.findall(r"\b(ISRCTN\d{8}|PACTR\d{12,16})\b", blob, re.IGNORECASE):
            other_reg.add(m.upper())
        out[pmid] = {
            "title": title,
            "journal": journal,
            "year": year,
            "abstract": abstract,
            "nct_id": sorted(ncts)[0] if ncts else None,
            "nct_ids": sorted(ncts),
            "other_registry_ids": sorted(other_reg),
        }
    return out


def idconv_batch(pmids, email):
    """Map PMID -> {pmcid, doi} via the NCBI ID Converter (<=200 ids)."""
    out = {}
    ids = ",".join(pmids)
    url = f"{IDCONV}?ids={ids}&format=json"
    data = _get(url, email)
    if not data:
        return out
    try:
        obj = json.loads(data.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return out
    for rec in obj.get("records", []):
        pmid = rec.get("pmid")
        if pmid is not None:
            # idconv returns pmid as an int; our PMID keys are strings
            out[str(pmid)] = {"pmcid": rec.get("pmcid"), "doi": rec.get("doi")}
    return out


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main():
    ap = argparse.ArgumentParser(description="Build malaria RCT corpus index")
    ap.add_argument("--term", default=DEFAULT_TERM, help="PubMed query")
    ap.add_argument("--retmax", type=int, default=3000, help="Max PMIDs")
    ap.add_argument("--email", default="research@example.org")
    ap.add_argument("--batch", type=int, default=180, help="efetch/idconv batch size")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"esearch: {args.term!r}")
    pmids = esearch_pmids(args.term, args.retmax, args.email)
    print(f"  PMIDs returned: {len(pmids)}")
    if not pmids:
        print("No PMIDs; aborting.")
        sys.exit(1)

    records = {}
    for bi, batch in enumerate(chunks(pmids, args.batch)):
        meta = efetch_records(batch, args.email)
        idmap = idconv_batch(batch, args.email)
        for pmid in batch:
            m = meta.get(pmid)
            if not m:
                continue
            ids = idmap.get(pmid, {})
            pmcid = ids.get("pmcid")
            records[pmid] = {
                "study_id": f"PMID{pmid}",
                "pmid": pmid,
                "pmcid": pmcid,
                "doi": ids.get("doi"),
                "nct_id": m["nct_id"],
                "nct_ids": m["nct_ids"],
                "other_registry_ids": m.get("other_registry_ids", []),
                "title": m["title"],
                "journal": m["journal"],
                "year": m["year"],
                "abstract": m["abstract"],
                "has_pdf": bool(pmcid),
            }
        n_pdf = sum(1 for r in records.values() if r["has_pdf"])
        n_nct = sum(1 for r in records.values() if r["nct_id"])
        print(f"  batch {bi+1}: total={len(records)} with_pmcid={n_pdf} with_nct={n_nct}")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for r in records.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_pdf = sum(1 for r in records.values() if r["has_pdf"])
    n_nct = sum(1 for r in records.values() if r["nct_id"])
    n_abs = sum(1 for r in records.values() if r["abstract"])
    print("=" * 60)
    print(f"Wrote {len(records)} records -> {OUT_FILE}")
    print(f"  with downloadable PMC PDF: {n_pdf}")
    print(f"  with NCT id (AACT-linkable): {n_nct}")
    print(f"  with abstract (cross-val): {n_abs}")


if __name__ == "__main__":
    main()
