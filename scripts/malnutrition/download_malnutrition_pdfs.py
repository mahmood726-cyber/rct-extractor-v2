"""
Download OA malnutrition RCT PDFs (reuses the malaria PMC-OA downloader, malnutrition paths).

Usage:
  python scripts/malnutrition/download_malnutrition_pdfs.py --workers 3 --batch 3000 --resume
"""
import argparse
import io
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from scripts.malaria import download_malaria_pdfs as M

MALN_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "malnutrition"
MATCHED = MALN_DIR / "malnutrition_matched.jsonl"
PDF_DIR = MALN_DIR / "rct_trial_pdfs"
LOG = MALN_DIR / "download_log.jsonl"

_log_lock = threading.Lock()
_log_fh = None


def worker(entry):
    pmcid = entry["pmcid"]
    safe = entry["study_id"].replace(" ", "_").replace("/", "_")
    out_path = PDF_DIR / f"{safe}_{pmcid}.pdf"
    if out_path.exists() and out_path.stat().st_size > 1000:
        return ("skip", 0)
    ok, size, method = M.download_pmc_pdf(pmcid, out_path)
    with _log_lock:
        _log_fh.write(json.dumps({"study_id": entry["study_id"], "pmcid": pmcid,
                                  "nct_id": entry.get("nct_id"), "success": ok,
                                  "size_bytes": size, "method": method}) + "\n")
        _log_fh.flush()
    return ("ok" if ok else "fail", size)


def main():
    global _log_fh
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=3000)
    ap.add_argument("--workers", type=int, default=3)
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
    todo = [e for e in entries if e["study_id"] not in done][:args.batch]
    print(f"To download: {len(todo)} (workers={args.workers})")

    _log_fh = open(LOG, "a", encoding="utf-8")
    ok = fail = skip = total = 0
    t0 = time.time()
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for i, fut in enumerate(as_completed([ex.submit(worker, e) for e in todo])):
                status, size = fut.result()
                ok += status == "ok"; fail += status == "fail"; skip += status == "skip"
                total += size
                if (i + 1) % 25 == 0:
                    print(f"  {i+1}/{len(todo)} ok={ok} fail={fail} "
                          f"({total/1e6:.0f}MB, {(i+1)/max(time.time()-t0,1):.1f}/s)", flush=True)
    finally:
        _log_fh.close()
    print(f"Done. ok={ok} fail={fail} skip={skip}  PDFs on disk: {len(list(PDF_DIR.glob('*.pdf')))}")


if __name__ == "__main__":
    main()
