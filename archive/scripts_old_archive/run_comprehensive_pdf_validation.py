"""
Comprehensive Real PDF Validation for RCT Extractor v2

Extracts from actual PDFs and creates a detailed report for verification.
"""
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.extractor import NumericParser
from src.pdf.pdf_parser import PDFParser


def extract_all_hrs(text: str) -> List[Dict]:
    """Extract all hazard ratios from text"""
    text = text.replace('·', '.').replace('−', '-').replace('–', '-')
    results = []
    seen = set()

    for pattern in NumericParser.HR_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            groups = match.groups()
            try:
                hr = float(groups[0])
                ci_low = float(groups[2]) if len(groups) > 2 and groups[2] else None
                ci_high = float(groups[3]) if len(groups) > 3 and groups[3] else None

                # Plausibility check
                if hr <= 0 or hr > 20:
                    continue
                if ci_low and ci_high and ci_low >= ci_high:
                    continue

                key = (round(hr, 3), round(ci_low or 0, 3), round(ci_high or 0, 3))
                if key in seen:
                    continue
                seen.add(key)

                # Get context (surrounding text)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace('\n', ' ')

                results.append({
                    'hr': hr,
                    'ci_low': ci_low,
                    'ci_high': ci_high,
                    'match': match.group(0),
                    'context': context
                })
            except (ValueError, IndexError):
                continue

    return results


def main():
    print("=" * 70)
    print("COMPREHENSIVE PDF EXTRACTION VALIDATION")
    print("=" * 70)

    # PDFs with known primary outcomes for manual verification
    test_pdfs = {
        "NEJMoa2206286.pdf": {
            "trial": "DELIVER",
            "expected": [
                {"hr": 0.82, "ci_low": 0.73, "ci_high": 0.92, "endpoint": "Primary (CV death or worsening HF)"}
            ]
        },
        "NEJMoa2107038.pdf": {
            "trial": "DAPA-HF Extended",
            "expected": [
                {"hr": 0.73, "ci_low": 0.61, "ci_high": 0.88, "endpoint": "CV death"},
                {"hr": 0.71, "ci_low": 0.60, "ci_high": 0.83, "endpoint": "HF hospitalization"}
            ]
        },
        "NEJMoa2307563.pdf": {
            "trial": "SELECT (Semaglutide)",
            "expected": [
                {"hr": 0.80, "ci_low": 0.72, "ci_high": 0.90, "endpoint": "Primary MACE"}
            ]
        },
        "NEJMoa1814052.pdf": {
            "trial": "PARTNER 3 (TAVR vs SAVR)",
            "expected": [
                {"hr": 0.54, "ci_low": 0.37, "ci_high": 0.79, "endpoint": "Primary composite (death/stroke/rehosp)"}
            ]
        },
        "IvabradineandoutcomesinchronicheartfailureSHIFT-arandomisedplacebo-controlledstudy.pdf": {
            "trial": "SHIFT (Ivabradine)",
            "expected": [
                {"hr": 0.82, "ci_low": 0.75, "ci_high": 0.90, "endpoint": "Primary composite"}
            ]
        }
    }

    parser = PDFParser()
    downloads = Path("C:/Users/user/Downloads")

    total_expected = 0
    total_matched = 0
    results = []

    for pdf_name, info in test_pdfs.items():
        pdf_path = downloads / pdf_name
        if not pdf_path.exists():
            # Try finding the file
            matches = list(downloads.glob(f"*{pdf_name.split('.')[0]}*"))
            if matches:
                pdf_path = matches[0]
            else:
                print(f"\n[SKIP] {pdf_name} - not found")
                continue

        print(f"\n{'='*70}")
        print(f"Trial: {info['trial']}")
        print(f"PDF: {pdf_path.name}")
        print("=" * 70)

        try:
            content = parser.parse(str(pdf_path))
            full_text = "\n".join(page.full_text for page in content.pages)
        except Exception as e:
            print(f"  [ERROR] Failed to parse: {e}")
            continue

        extracted = extract_all_hrs(full_text)

        print(f"\nExtracted {len(extracted)} hazard ratios:")
        for i, e in enumerate(extracted[:10]):
            ci_str = f"({e['ci_low']:.2f}-{e['ci_high']:.2f})" if e['ci_low'] and e['ci_high'] else ""
            print(f"  {i+1}. HR {e['hr']:.2f} {ci_str}")

        if len(extracted) > 10:
            print(f"  ... and {len(extracted) - 10} more")

        print(f"\nExpected primary outcomes:")
        matched_count = 0
        for exp in info['expected']:
            total_expected += 1
            found = False
            for ext in extracted:
                if abs(ext['hr'] - exp['hr']) < 0.02:  # 2% tolerance
                    if ext['ci_low'] and ext['ci_high']:
                        if abs(ext['ci_low'] - exp['ci_low']) < 0.02 and abs(ext['ci_high'] - exp['ci_high']) < 0.02:
                            found = True
                            break
                    else:
                        found = True
                        break

            status = "[OK] FOUND" if found else "[X] MISSING"
            ci_str = f"({exp['ci_low']:.2f}-{exp['ci_high']:.2f})" if 'ci_low' in exp else ""
            print(f"  {status}: HR {exp['hr']:.2f} {ci_str} - {exp['endpoint']}")

            if found:
                matched_count += 1
                total_matched += 1

        results.append({
            'trial': info['trial'],
            'pdf': pdf_path.name,
            'extracted': len(extracted),
            'expected': len(info['expected']),
            'matched': matched_count
        })

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    print(f"\nTrials validated: {len(results)}")
    print(f"Primary outcomes expected: {total_expected}")
    print(f"Primary outcomes matched: {total_matched}")

    if total_expected > 0:
        accuracy = total_matched / total_expected * 100
        print(f"Match rate: {accuracy:.1f}%")

    print("\nPer-trial results:")
    for r in results:
        status = "[OK]" if r['matched'] == r['expected'] else "[X]"
        print(f"  {status} {r['trial']}: {r['matched']}/{r['expected']} matched ({r['extracted']} total extracted)")

    # Save
    output_file = Path(__file__).parent / 'output' / 'comprehensive_pdf_validation.json'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'trials': len(results),
                'expected': total_expected,
                'matched': total_matched,
                'accuracy': total_matched / total_expected if total_expected > 0 else 0
            },
            'results': results
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
