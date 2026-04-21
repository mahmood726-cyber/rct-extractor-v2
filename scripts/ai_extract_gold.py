"""
AI-assisted gold standard extraction for PDFs that regex can't handle.

For each zero-extraction PDF:
1. Parse the full text
2. Send to Claude API with the Cochrane outcome context
3. Ask it to find the specific effect estimate or explain why it can't

Requires: ANTHROPIC_API_KEY environment variable
"""
import io
import json
import os
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(__file__).resolve().parents[1]
PDF_DIR = PROJECT_DIR / "test_pdfs" / "gold_standard"
GOLD_FILE = PROJECT_DIR / "gold_data" / "gold_50.jsonl"
OUTPUT_FILE = PROJECT_DIR / "gold_data" / "ai_extraction_results.json"

sys.path.insert(0, str(PROJECT_DIR))


def extract_text(pdf_path):
    """Extract text from PDF."""
    from src.pdf.pdf_parser import PDFParser
    parser = PDFParser()
    content = parser.parse(str(pdf_path))
    pages = {}
    for p in content.pages:
        text = p.full_text if hasattr(p, 'full_text') else str(p)
        pages[p.page_num] = text
    full_text = "\n".join(pages.values())
    return full_text, pages


def ask_claude(text, entry):
    """Ask Claude to extract the effect estimate from the paper text."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: pip install anthropic")
        return None

    client = anthropic.Anthropic()

    cochrane_outcome = entry.get("cochrane_outcome", "")
    cochrane_effect = entry.get("cochrane_effect")
    cochrane_type = entry.get("cochrane_outcome_type", "binary")
    study_id = entry["study_id"]

    # Truncate text to fit context (keep first and last parts, focus on Results)
    if len(text) > 25000:
        # Try to find Results section
        results_start = None
        for marker in ["Results", "RESULTS", "3. Results", "3 Results"]:
            idx = text.find(marker)
            if idx > 0:
                results_start = idx
                break

        if results_start:
            # Keep abstract + results section + conclusion
            abstract_end = min(3000, results_start)
            results_chunk = text[results_start:results_start + 15000]
            end_chunk = text[-3000:]
            text = text[:abstract_end] + "\n...[TRIMMED]...\n" + results_chunk + "\n...[TRIMMED]...\n" + end_chunk
        else:
            text = text[:15000] + "\n...[TRIMMED]...\n" + text[-5000:]

    prompt = f"""You are extracting effect estimates from an RCT paper for a gold standard dataset.

Study: {study_id}
Cochrane outcome: {cochrane_outcome}
Cochrane expected effect type: {cochrane_type}
Cochrane computed value: {cochrane_effect}

Note: The Cochrane value is computed from raw 2×2 tables (for binary) or means/SDs (for continuous).
The paper may report the SAME outcome differently (adjusted vs unadjusted, different scale, etc.)
or may only report raw data (event counts, means±SD) from which Cochrane computed the effect.

TASK: Find the PRIMARY effect estimate for this outcome in the paper text below.

If the paper reports a labeled effect (OR, RR, HR, MD, SMD, etc.) with a confidence interval:
  Return the exact values as reported in the paper.

If the paper only reports raw data (n/N events, means±SD per group):
  Report what data is available and note "COUNTS_ONLY - Cochrane computed the effect from raw data"

If you cannot find any data related to this outcome:
  Explain what the paper actually reports and note "NOT_FOUND"

Return your answer as JSON:
{{
  "effect_type": "OR|RR|HR|MD|SMD|ARD|RD|null",
  "point_estimate": <number or null>,
  "ci_lower": <number or null>,
  "ci_upper": <number or null>,
  "p_value": <number or null>,
  "source_text": "<exact quote from paper, max 200 chars>",
  "page_hint": "<which section/table this is from>",
  "category": "LABELED_EFFECT|COUNTS_ONLY|NOT_FOUND",
  "notes": "<brief explanation>"
}}

PAPER TEXT:
{text}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        print(f"  API ERROR: {e}")
        return None


def parse_ai_response(response_text):
    """Parse Claude's JSON response."""
    if not response_text:
        return None

    # Extract JSON from response
    import re
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {"raw_response": response_text[:500]}


def main():
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    # Filter to zero-extraction entries
    zero_entries = [e for e in entries
                    if e.get("gold", {}).get("point_estimate") is None]

    print(f"AI extraction for {len(zero_entries)} zero-extraction PDFs\n")

    results = []
    stats = {"labeled": 0, "counts": 0, "not_found": 0, "error": 0}

    for i, entry in enumerate(zero_entries):
        sid = entry["study_id"]
        pdf_path = PDF_DIR / entry["pdf_filename"]

        print(f"  [{i+1}/{len(zero_entries)}] {sid}...", end=" ", flush=True)

        if not pdf_path.exists():
            print("PDF MISSING")
            results.append({"study_id": sid, "error": "PDF_MISSING"})
            stats["error"] += 1
            continue

        # Extract text
        try:
            full_text, pages = extract_text(pdf_path)
        except Exception as e:
            print(f"PARSE ERROR: {e}")
            results.append({"study_id": sid, "error": str(e)})
            stats["error"] += 1
            continue

        # Ask Claude
        response = ask_claude(full_text, entry)
        parsed = parse_ai_response(response)

        if parsed:
            category = parsed.get("category", "UNKNOWN")
            effect = parsed.get("point_estimate")
            etype = parsed.get("effect_type")
            notes = parsed.get("notes", "")[:100]

            if category == "LABELED_EFFECT" and effect is not None:
                stats["labeled"] += 1
                ci_str = f"[{parsed.get('ci_lower')}, {parsed.get('ci_upper')}]" if parsed.get('ci_lower') else "[no CI]"
                print(f"LABELED: {etype}={effect} {ci_str}")
            elif category == "COUNTS_ONLY":
                stats["counts"] += 1
                print(f"COUNTS: {notes[:60]}")
            else:
                stats["not_found"] += 1
                print(f"NOT_FOUND: {notes[:60]}")

            results.append({
                "study_id": sid,
                "ai_extraction": parsed,
                "cochrane_effect": entry.get("cochrane_effect"),
                "cochrane_type": entry.get("cochrane_outcome_type"),
            })
        else:
            print("NO RESPONSE")
            results.append({"study_id": sid, "error": "no_response"})
            stats["error"] += 1

        # Rate limiting
        time.sleep(1)

    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*70}")
    print(f"AI EXTRACTION SUMMARY")
    print(f"{'='*70}")
    print(f"Labeled effects found: {stats['labeled']}")
    print(f"Counts only:           {stats['counts']}")
    print(f"Not found:             {stats['not_found']}")
    print(f"Errors:                {stats['error']}")
    print(f"\nResults saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
