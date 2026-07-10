#!/usr/bin/env python3
"""Download the open-access gold-standard PDFs from the PMC OA service.

Reads gold_data/gold_50.jsonl, and for every record with a pmcid fetches the
CC-licensed article package from the PMC Open Access service and extracts its
PDF into the target directory (default test_pdfs/gold_standard, which is
gitignored -- these PDFs are NOT committed). Idempotent (skips PDFs already
present) and rate-limited (NCBI asks for <= 3 requests/second).

    python scripts/download_gold_pdfs.py
    python scripts/download_gold_pdfs.py --gold gold_data/gold_50.jsonl --out test_pdfs/gold_standard
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tarfile
import time
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

OA_FCGI = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}"
UA = "rct-extractor-gold-fetch/1.0 (mailto:research@example.org)"


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _package_href(pmcid: str) -> Optional[str]:
    """Return the https package URL for a pmcid, or None if not OA-available."""
    try:
        xml = _get(OA_FCGI.format(pmcid=pmcid), timeout=30).decode("utf-8", "replace")
    except Exception as exc:
        print(f"  {pmcid}: OA query failed ({exc})", file=sys.stderr)
        return None
    if "idIsNotOpenAccess" in xml or "<error" in xml:
        return None
    m = re.search(r'href="(ftp://[^"]+\.tar\.gz)"', xml) or re.search(r'href="(https://[^"]+\.tar\.gz)"', xml)
    if not m:
        return None
    href = m.group(1)
    # The FTP host also serves over HTTPS; prefer it (more reliable through proxies).
    return href.replace("ftp://ftp.ncbi.nlm.nih.gov", "https://ftp.ncbi.nlm.nih.gov")


def _pdf_from_tarball(blob: bytes) -> Optional[bytes]:
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        pdfs = [m for m in tar.getmembers() if m.name.lower().endswith(".pdf")]
        if not pdfs:
            return None
        pdfs.sort(key=lambda m: m.size, reverse=True)   # main article = largest PDF
        f = tar.extractfile(pdfs[0])
        return f.read() if f else None


def download_one(pmcid: str, out_dir: Path) -> Tuple[str, str]:
    dest = out_dir / f"{pmcid}.pdf"
    if dest.exists() and dest.stat().st_size > 1000:
        return pmcid, "skip_exists"
    href = _package_href(pmcid)
    if not href:
        return pmcid, "not_open_access"
    try:
        blob = _get(href, timeout=90)
    except Exception as exc:
        return pmcid, f"download_failed:{exc}"
    pdf = _pdf_from_tarball(blob)
    if not pdf:
        return pmcid, "no_pdf_in_package"
    dest.write_bytes(pdf)
    return pmcid, f"ok:{len(pdf)}"


def _load_pmcids(gold: Path) -> List[str]:
    ids: List[str] = []
    for line in gold.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        pmc = rec.get("pmcid")
        if pmc and pmc not in ids:
            ids.append(pmc)
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold", type=Path, default=Path("gold_data/gold_50.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("test_pdfs/gold_standard"))
    parser.add_argument("--delay", type=float, default=0.4, help="seconds between OA requests")
    parser.add_argument("--limit", type=int, default=0, help="cap number downloaded (0 = all)")
    args = parser.parse_args()

    if not args.gold.exists():
        print(f"ERROR: gold not found: {args.gold}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    pmcids = _load_pmcids(args.gold)
    if args.limit:
        pmcids = pmcids[: args.limit]
    print(f"{len(pmcids)} pmcids -> {args.out}")

    counts: dict = {}
    for i, pmcid in enumerate(pmcids, 1):
        pmcid_, status = download_one(pmcid, args.out)
        tag = status.split(":")[0]
        counts[tag] = counts.get(tag, 0) + 1
        print(f"  [{i:>2}/{len(pmcids)}] {pmcid_:14} {status}")
        if tag not in ("skip_exists",):
            time.sleep(args.delay)   # be polite to NCBI
    print("-" * 50)
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k:20} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
