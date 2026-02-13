#!/usr/bin/env python3
"""Add existing PDFs from other directories into the batch manifest."""
import json
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
manifest_path = ROOT / "data" / "batch_rct_manifest.json"

with open(manifest_path) as f:
    manifest = json.load(f)

existing_pmcids = {e["pmcid"] for e in manifest["entries"]}
print(f"Manifest already has {len(existing_pmcids)} entries")

other_dirs = [
    "test_pdfs/real_pdfs",
    "test_pdfs/open_access_rcts",
    "test_pdfs/oa_rct_corpus",
    "test_pdfs/oa_rct_corpus_v2",
    "test_pdfs/validated_rcts",
]

new_entries = []
for d in other_dirs:
    dp = ROOT / d
    if not dp.exists():
        continue
    for pdf in dp.rglob("*.pdf"):
        m = re.match(r"(PMC\d+)", pdf.stem)
        if not m:
            continue
        pmcid = m.group(1)
        if pmcid in existing_pmcids:
            continue
        existing_pmcids.add(pmcid)

        with open(pdf, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()

        area = "existing_corpus"
        parts = pdf.parts
        for p in parts:
            if p in ("cardiology", "oncology", "diabetes", "infectious",
                     "neurology", "respiratory", "rheumatology"):
                area = p
                break
            elif p == "oa_rct_corpus_v2":
                area = "oa_corpus_v2"
            elif p == "open_access_rcts":
                area = "open_access"

        new_entries.append({
            "pmcid": pmcid,
            "pmid": "",
            "title": "",
            "journal": "",
            "year": "",
            "area": area,
            "pdf_path": str(pdf),
            "file_size": pdf.stat().st_size,
            "sha256": sha,
            "download_date": "pre-existing",
            "classification": None,
        })

manifest["entries"].extend(new_entries)
manifest["total_entries"] = len(manifest["entries"])
manifest["total_downloaded"] = sum(1 for e in manifest["entries"] if e.get("pdf_path"))

with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)

print(f"Added {len(new_entries)} existing PDFs")
print(f"Total manifest entries: {len(manifest['entries'])}")
