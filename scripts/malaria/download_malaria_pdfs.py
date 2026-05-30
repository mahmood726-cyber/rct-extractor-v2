"""
Download OA malaria RCT PDFs via the PMC Open Access service (reliable, resumable).

The PMC OA web frontend (europepmc render / ncbi /pdf/) rate-limits and often
serves HTML, so this uses the official PMC OA Web Service:
  oa.fcgi?id=PMC#  ->  a direct 'pdf' link and/or a 'tgz' package link (FTP).
We prefer the direct PDF; otherwise we download the .tar.gz and extract the PDF
inside. FTP hrefs are fetched over the https mirror (not throttled like the web
frontend). Moderate concurrency; verifies the %PDF magic header.

PDFs -> data/field_portability/malaria/rct_trial_pdfs/<study_id>_<pmcid>.pdf
Log  -> data/field_portability/malaria/download_log.jsonl (flushed live)

Usage:
  python scripts/malaria/download_malaria_pdfs.py --workers 4 --batch 3000 --resume
"""
import argparse
import io
import json
import re
import sys
import tarfile
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).resolve().parents[2]
MAL_DIR = PROJECT_DIR / "data" / "field_portability" / "malaria"
MATCHED = MAL_DIR / "malaria_matched.jsonl"
PDF_DIR = MAL_DIR / "rct_trial_pdfs"
LOG = MAL_DIR / "download_log.jsonl"

EPMC = "https://europepmc.org/articles/{}?pdf=render"
OA = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={}"
_log_lock = threading.Lock()
_log_fh = None
HDR = {"User-Agent": "rct-extractor-malaria (mailto:research@example.org)"}


def _get(url, timeout=45):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=timeout) as r:
        return r.read()


def download_pmc_pdf(pmcid, out_path, max_retries=3):
    """EuropePMC rendered PDF with 429 backoff; OA tgz fallback. Verifies %PDF."""
    for attempt in range(max_retries):
        try:
            d = _get(EPMC.format(pmcid))
            if d[:4] == b"%PDF":
                out_path.write_bytes(d)
                return True, len(d), "europepmc"
            break  # got HTML, not a PDF -> try fallback
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(6 * (attempt + 1))  # back off on rate limit
                continue
            break
        except Exception:
            time.sleep(2)
    # Fallback: PMC OA package -> extract PDF from the tarball
    try:
        x = _get(OA.format(pmcid), timeout=30).decode("utf-8", "replace")
        links = dict(re.findall(r'<link\s+format="(\w+)"[^>]*href="([^"]+)"', x))
        if "tgz" in links:
            blob = _get(links["tgz"], timeout=90)
            with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
                for m in tf.getmembers():
                    if m.name.lower().endswith(".pdf"):
                        f = tf.extractfile(m)
                        data = f.read() if f else b""
                        if data[:4] == b"%PDF":
                            out_path.write_bytes(data)
                            return True, len(data), "oa_tgz"
    except Exception:
        pass
    return False, 0, "failed"


def log_attempt(rec):
    with _log_lock:
        _log_fh.write(json.dumps(rec) + "\n")
        _log_fh.flush()


def worker(entry):
    pmcid = entry["pmcid"]
    safe = entry["study_id"].replace(" ", "_").replace("/", "_")
    out_path = PDF_DIR / f"{safe}_{pmcid}.pdf"
    if out_path.exists() and out_path.stat().st_size > 1000:
        return ("skip", 0)
    success, size, method = download_pmc_pdf(pmcid, out_path)
    log_attempt({
        "study_id": entry["study_id"], "pmid": entry.get("pmid"), "pmcid": pmcid,
        "nct_id": entry.get("nct_id"), "success": success,
        "size_bytes": size, "method": method,
    })
    return ("ok" if success else "fail", size)


def main():
    global _log_fh
    ap = argparse.ArgumentParser(description="PMC OA malaria PDF downloader")
    ap.add_argument("--batch", type=int, default=3000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    entries = [e for e in (json.loads(l) for l in open(MATCHED, encoding="utf-8"))
               if e.get("pmcid")]
    print(f"OA entries with PMCID: {len(entries)}")

    done = set()
    if args.resume and LOG.exists():
        for line in open(LOG, encoding="utf-8"):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("success"):
                done.add(rec["study_id"])
    done |= {p.stem.split("_PMC")[0] for p in PDF_DIR.glob("*.pdf")}
    print(f"Already done (log+disk): {len(done)}")

    todo = [e for e in entries if e["study_id"] not in done][:args.batch]
    print(f"To download this run: {len(todo)}  (workers={args.workers})")
    print("=" * 60)

    _log_fh = open(LOG, "a", encoding="utf-8")
    ok = fail = skip = total = 0
    t0 = time.time()
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(worker, e) for e in todo]
            for i, fut in enumerate(as_completed(futs)):
                status, size = fut.result()
                if status == "ok":
                    ok += 1; total += size
                elif status == "fail":
                    fail += 1
                else:
                    skip += 1
                if (i + 1) % 25 == 0:
                    rate = (i + 1) / max(time.time() - t0, 1)
                    print(f"  {i+1}/{len(todo)}  ok={ok} fail={fail} "
                          f"({total/1e6:.0f} MB, {rate:.1f}/s)", flush=True)
    finally:
        _log_fh.close()

    print("=" * 60)
    print(f"Done. ok={ok} fail={fail} skip={skip}  {total/1e6:.1f} MB")
    print(f"PDFs on disk: {len(list(PDF_DIR.glob('*.pdf')))}")


if __name__ == "__main__":
    main()
