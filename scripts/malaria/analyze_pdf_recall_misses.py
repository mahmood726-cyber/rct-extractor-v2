"""
Diagnose abstract->PDF recall misses: an effect is in the abstract but our
extractor did not recover it from the full-text PDF. For each miss on a PDF that
DID yield some effects (so the PDF parsed fine), locate the missed value in the
PDF text and print the surrounding context -- revealing the format we miss.
"""
import io
import json
import re
import sys
import glob
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rct_extractor._engine.pdf.pdf_parser import PDFParser

MAL = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "malaria"
PDFS = {os.path.basename(p).split("_PMC")[0]: p
        for p in glob.glob(str(MAL / "rct_trial_pdfs" / "*.pdf"))}


def main():
    recs = [json.loads(l) for l in open(MAL / "cross_check.jsonl", encoding="utf-8")]
    misses = []
    for r in recs:
        if r["n_pdf_effects"] == 0:
            continue  # focus on format gaps, not parse/scan failures
        for d in r.get("abstract_vs_pdf", []):
            if not d["matched"]:
                misses.append((r["study_id"], d["type"], d["ref_value"]))

    parser = PDFParser()
    in_text = 0
    not_in_text = 0
    shown = 0
    cache = {}
    for sid, typ, val in misses[:60]:
        pdf = PDFS.get(sid)
        if not pdf:
            continue
        if sid not in cache:
            try:
                c = parser.parse(pdf)
                cache[sid] = "\n".join(p.full_text for p in c.pages)
            except Exception:
                cache[sid] = ""
        txt = cache[sid]
        vs = f"{val:g}"
        # find the value as a token in the text
        m = re.search(r"[^\d.](" + re.escape(vs) + r")(?:\D|$)", txt)
        if m and re.search(r"95\s*%", txt[max(0, m.start() - 90):m.end() + 90]):
            in_text += 1
            if shown < 22:
                ctx = re.sub(r"\s+", " ", txt[max(0, m.start() - 60):m.end() + 80]).strip()
                print(f"[{typ} {val}] {sid}: ...{ctx}...")
                shown += 1
        else:
            not_in_text += 1

    print("=" * 60)
    print(f"format-gap misses examined: {min(len(misses), 60)}")
    print(f"  value present in PDF text near a 95% CI (fixable format gap): {in_text}")
    print(f"  value NOT near a CI in PDF text (reported differently): {not_in_text}")


if __name__ == "__main__":
    main()
