"""
Test table extraction on TABLE_ONLY gold standard PDFs.

Diagnoses:
1. Does pdfplumber detect any tables?
2. Does TableEffectExtractor classify them as outcome tables?
3. Does it extract any effects?
4. If not, what do the table headers look like?
"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(__file__).resolve().parents[1]
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
GOLD_FILE = PROJECT_DIR / "gold_data" / "gold_50.jsonl"

sys.path.insert(0, str(PROJECT_DIR))


def main():
    import pdfplumber
    from src.tables.table_effect_extractor import TableEffectExtractor
    from src.tables.table_extractor import TableStructure, TableCell

    tee = TableEffectExtractor()

    # Load gold entries
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    # Filter to zero-extraction entries (TABLE_ONLY candidates)
    zero_entries = [e for e in entries
                    if e.get("gold", {}).get("point_estimate") is None]

    print(f"Testing table extraction on {len(zero_entries)} zero-extraction PDFs\n")
    print("=" * 80)

    total_tables = 0
    total_outcome_tables = 0
    total_effects = 0
    results = []

    for entry in zero_entries:
        sid = entry["study_id"]
        pdf_path = PDF_DIR / entry["pdf_filename"]
        ctype = entry.get("cochrane_outcome_type", "binary")
        ceff = entry.get("cochrane_effect")
        outcome = entry.get("cochrane_outcome", "")[:60]

        print(f"\n--- {sid} (expects {ctype}={ceff}) ---")
        print(f"    Outcome: {outcome}")

        if not pdf_path.exists():
            print("    PDF MISSING")
            continue

        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                pdf_tables = 0
                pdf_outcome_tables = 0
                pdf_effects = 0

                for page_idx, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    if not tables:
                        continue

                    for t_idx, table_data in enumerate(tables):
                        if not table_data or len(table_data) < 2:
                            continue

                        pdf_tables += 1
                        total_tables += 1

                        # Convert to TableStructure
                        num_rows = len(table_data)
                        num_cols = max(len(row) for row in table_data) if table_data else 0
                        cells = []
                        for row_idx, row in enumerate(table_data):
                            for col_idx, cell_text in enumerate(row):
                                cells.append(TableCell(
                                    text=str(cell_text) if cell_text else "",
                                    row=row_idx,
                                    col=col_idx,
                                    is_header=(row_idx == 0),
                                ))

                        from collections import namedtuple
                        _BBox = namedtuple('BBox', ['x0', 'y0', 'x1', 'y1'])

                        ts = TableStructure(
                            cells=cells,
                            num_rows=num_rows,
                            num_cols=num_cols,
                            bbox=_BBox(0, 0, 100, 100),
                            page_num=page_idx,
                        )

                        # Check if outcome table
                        is_outcome, confidence = tee.is_outcome_table(ts)

                        # Show headers
                        headers = [str(c) if c else "" for c in table_data[0]]
                        header_str = " | ".join(headers[:8])
                        if len(headers) > 8:
                            header_str += " | ..."

                        # Try to extract effects
                        effects = tee.extract_from_table(ts)

                        if is_outcome or effects:
                            pdf_outcome_tables += 1
                            total_outcome_tables += 1

                        if effects:
                            pdf_effects += len(effects)
                            total_effects += len(effects)

                        tag = ""
                        if effects:
                            tag = f" ** {len(effects)} EFFECTS **"
                        elif is_outcome:
                            tag = f" [outcome table, conf={confidence:.2f}]"

                        print(f"    Page {page_idx+1}, Table {t_idx+1} ({num_rows}x{num_cols}): {header_str}{tag}")

                        if effects:
                            for eff in effects:
                                ci_str = f"[{eff.ci_lower}, {eff.ci_upper}]" if eff.ci_lower is not None else "[no CI]"
                                print(f"      -> {eff.effect_type}={eff.point_estimate} {ci_str} p={eff.p_value} row={eff.outcome_name}")

                        # For outcome tables without effects, show first 3 data rows
                        if is_outcome and not effects:
                            for r_idx in range(1, min(4, num_rows)):
                                row_cells = [str(c) if c else "" for c in table_data[r_idx]]
                                row_str = " | ".join(row_cells[:8])
                                print(f"      row {r_idx}: {row_str}")

                print(f"  Summary: {pdf_tables} tables, {pdf_outcome_tables} outcome, {pdf_effects} effects")

                results.append({
                    "study_id": sid,
                    "tables_found": pdf_tables,
                    "outcome_tables": pdf_outcome_tables,
                    "effects_extracted": pdf_effects,
                    "cochrane_effect": ceff,
                    "cochrane_type": ctype,
                })

        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"PDFs tested:        {len(zero_entries)}")
    print(f"Total tables found: {total_tables}")
    print(f"Outcome tables:     {total_outcome_tables}")
    print(f"Effects extracted:  {total_effects}")
    print(f"\nPer-PDF breakdown:")
    for r in results:
        status = "OK" if r["effects_extracted"] > 0 else "MISS"
        print(f"  [{status}] {r['study_id']}: {r['tables_found']} tables, {r['effects_extracted']} effects (expects {r['cochrane_type']}={r['cochrane_effect']})")


if __name__ == "__main__":
    main()
