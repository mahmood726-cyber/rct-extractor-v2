"""
Real PDF Validation for RCT Extractor v2

Tests extraction on actual PDF files, not synthetic text.
Validates against ClinicalTrials.gov ground truth data.
"""
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.extractor import NumericParser
from src.pdf.pdf_parser import PDFParser

CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"


# Known trial PDFs with matching NCT IDs
# Format: (filename pattern, NCT ID, trial name)
KNOWN_PDF_TRIALS = [
    ("NEJMoa2307563", "NCT04564742", "SELECT"),       # Semaglutide CV
    ("NEJMoa2107519", "NCT03982381", "EMPEROR-Pooled"),
    ("NEJMoa2107038", "NCT03036124", "DAPA-HF extended"),
    ("NEJMoa2206286", "NCT03619213", "DELIVER"),
    ("NEJMoa1814052", "NCT03057977", "PARTNER 3"),    # May have results
    ("NEJMoa1816885", "NCT02701283", "Evolut Low Risk"),
    ("NEJMoa1514616", "NCT01586910", "SURTAVI"),
    ("NEJMoa1700456", "NCT02032017", "PARTNER 2A"),
    ("NEJMoa2400685", "NCT04614402", "TRISCEND II"),
    ("NEJMoa070635", "NCT00007657", "COURAGE"),
    # Additional cardiovascular trials
    ("okazaki", None, "JAPAN-ACS"),
    ("hiro-et-al", None, "JAPAN-ACS2"),
    ("tsujita", None, "PRECISE-IVUS"),
    ("nicholls", None, "GLAGOV"),
]

# Plausibility filters for effect estimates
def is_plausible_hr(value: float) -> bool:
    """HR should typically be between 0.1 and 10"""
    return 0.05 <= value <= 20

def is_plausible_or(value: float) -> bool:
    """OR should typically be between 0.1 and 50"""
    return 0.05 <= value <= 50

def is_plausible_rr(value: float) -> bool:
    """RR should typically be between 0.1 and 10"""
    return 0.05 <= value <= 20


def find_pdf_files(search_dirs: List[Path]) -> Dict[str, Path]:
    """Find PDF files matching known trials"""
    found = {}

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        for pdf_file in search_dir.rglob("*.pdf"):
            filename = pdf_file.stem

            for pattern, nct_id, trial_name in KNOWN_PDF_TRIALS:
                if pattern.lower() in filename.lower():
                    key = f"{trial_name}|{nct_id or 'NO_NCT'}"
                    if key not in found:
                        found[key] = pdf_file
                        print(f"  Found: {trial_name} -> {pdf_file.name}")

    return found


def fetch_ctgov_effects(nct_id: str) -> List[Dict]:
    """Fetch effect estimates from CTgov API"""
    try:
        url = f"{CTGOV_API}/{nct_id}"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'RCT-Extractor-Validation/2.0')

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        results = []
        results_section = data.get('resultsSection', {})
        outcome_measures = results_section.get('outcomeMeasuresModule', {})
        outcome_list = outcome_measures.get('outcomeMeasures', [])

        for outcome in outcome_list:
            title = outcome.get('title', '')

            for analysis in outcome.get('analyses', []):
                stat_method = analysis.get('statisticalMethod', '')
                param_value = analysis.get('paramValue', '')
                ci_lower = analysis.get('ciLowerLimit', '')
                ci_upper = analysis.get('ciUpperLimit', '')

                measure_type = None
                stat_lower = stat_method.lower()

                if 'hazard' in stat_lower or 'cox' in stat_lower:
                    measure_type = 'HR'
                elif 'odds' in stat_lower:
                    measure_type = 'OR'
                elif 'risk ratio' in stat_lower:
                    measure_type = 'RR'

                if measure_type and param_value:
                    try:
                        results.append({
                            'measure_type': measure_type,
                            'value': float(param_value),
                            'ci_low': float(ci_lower) if ci_lower else None,
                            'ci_high': float(ci_upper) if ci_upper else None,
                            'outcome': title[:80]
                        })
                    except ValueError:
                        pass

        return results
    except:
        return []


def extract_all_matches(text: str, patterns: List[str], measure_key: str) -> List[Dict]:
    """Extract all matches for a set of patterns"""
    results = []
    seen_values = set()  # Avoid duplicates

    # Normalize text (handle middle dots, unicode)
    text = text.replace('·', '.').replace('−', '-').replace('–', '-')

    # Plausibility check based on measure type
    def is_plausible(value: float, ci_low: float, ci_high: float) -> bool:
        if measure_key == 'HR':
            return is_plausible_hr(value)
        elif measure_key == 'OR':
            return is_plausible_or(value)
        elif measure_key == 'RR':
            return is_plausible_rr(value)
        return True

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            groups = match.groups()
            try:
                value = float(groups[0])
                ci_low = float(groups[2]) if len(groups) > 2 and groups[2] else None
                ci_high = float(groups[3]) if len(groups) > 3 and groups[3] else None

                # Skip invalid values
                if value <= 0:
                    continue
                if ci_low and ci_high and ci_low >= ci_high:
                    continue

                # Skip implausible values
                if not is_plausible(value, ci_low, ci_high):
                    continue

                # Skip if CI values are implausible (likely not CIs)
                if ci_low and ci_low > 100:
                    continue
                if ci_high and ci_high > 100:
                    continue

                # Skip duplicates
                key = (round(value, 3), round(ci_low or 0, 3), round(ci_high or 0, 3))
                if key in seen_values:
                    continue
                seen_values.add(key)

                results.append({
                    'measure_type': measure_key,
                    'value': value,
                    'ci_low': ci_low,
                    'ci_high': ci_high,
                    'text_match': match.group(0)[:100]
                })
            except (ValueError, IndexError):
                continue

    return results


def extract_from_pdf(pdf_path: Path) -> Tuple[str, List[Dict]]:
    """Extract text and effect estimates from PDF"""
    parser = PDFParser()

    try:
        content = parser.parse(str(pdf_path))
    except Exception as e:
        return "", []

    # Combine all page text
    full_text = "\n".join(page.full_text for page in content.pages)

    # Extract all effect estimates using patterns from NumericParser
    extracted = []

    # HR patterns
    extracted.extend(extract_all_matches(full_text, NumericParser.HR_PATTERNS, 'HR'))

    # OR patterns
    extracted.extend(extract_all_matches(full_text, NumericParser.OR_PATTERNS, 'OR'))

    # RR patterns
    extracted.extend(extract_all_matches(full_text, NumericParser.RR_PATTERNS, 'RR'))

    return full_text, extracted


def match_values(extracted: float, expected: float, tolerance: float = 0.05) -> bool:
    """Check if values match within tolerance"""
    if extracted is None or expected is None:
        return False
    if expected == 0:
        return abs(extracted) < tolerance
    return abs(extracted - expected) / abs(expected) <= tolerance


def validate_extraction(pdf_extracted: List[Dict], ctgov_expected: List[Dict]) -> Dict:
    """Validate extracted values against CTgov ground truth"""
    results = {
        'total_expected': len(ctgov_expected),
        'total_extracted': len(pdf_extracted),
        'matched': 0,
        'unmatched_expected': [],
        'extra_extracted': []
    }

    matched_expected = set()
    matched_extracted = set()

    for i, expected in enumerate(ctgov_expected):
        for j, extracted in enumerate(pdf_extracted):
            if j in matched_extracted:
                continue

            if expected['measure_type'] == extracted['measure_type']:
                if match_values(extracted['value'], expected['value']):
                    # Check CI match if available
                    ci_match = True
                    if expected['ci_low'] and extracted['ci_low']:
                        ci_match = ci_match and match_values(extracted['ci_low'], expected['ci_low'])
                    if expected['ci_high'] and extracted['ci_high']:
                        ci_match = ci_match and match_values(extracted['ci_high'], expected['ci_high'])

                    if ci_match:
                        results['matched'] += 1
                        matched_expected.add(i)
                        matched_extracted.add(j)
                        break

    for i, expected in enumerate(ctgov_expected):
        if i not in matched_expected:
            results['unmatched_expected'].append(expected)

    return results


def main():
    print("=" * 70)
    print("RCT EXTRACTOR v2 - REAL PDF VALIDATION")
    print("=" * 70)
    print("\nTests extraction on actual PDF files (not synthetic text)")

    # Search directories for PDFs
    search_dirs = [
        Path("C:/Users/user/Downloads"),
        Path("C:/Users/user/Downloads/TAVI"),
        Path("C:/Users/user/Downloads/Papers SAPT_DAPT"),
    ]

    print("\n" + "-" * 70)
    print("Phase 1: Finding PDF files...")
    print("-" * 70)

    found_pdfs = find_pdf_files(search_dirs)
    print(f"\n  Found {len(found_pdfs)} matching PDF files")

    # Also scan all NEJM and medical PDFs for broader testing
    print("\nScanning for additional medical PDFs...")
    medical_patterns = ["NEJM", "Lancet", "JAMA", "trial", "study", "et-al"]
    for pdf_file in Path("C:/Users/user/Downloads").glob("*.pdf"):
        for pattern in medical_patterns:
            if pattern.lower() in pdf_file.name.lower():
                key = f"{pdf_file.stem}|SCAN"
                if key not in found_pdfs and pdf_file.stem not in [p.stem for p in found_pdfs.values()]:
                    found_pdfs[key] = pdf_file
                break
        if len(found_pdfs) >= 30:  # Limit to 30 PDFs for testing
            break

    print("\n" + "-" * 70)
    print("Phase 2: Extracting from PDFs...")
    print("-" * 70)

    all_results = []
    total_pdfs = 0
    pdfs_with_effects = 0
    total_hrs_extracted = 0
    total_ors_extracted = 0
    total_rrs_extracted = 0

    for key, pdf_path in found_pdfs.items():
        total_pdfs += 1
        parts = key.split("|")
        trial_name = parts[0] if parts else pdf_path.stem
        nct_id = parts[1] if len(parts) > 1 and parts[1] != "NO_NCT" else None

        print(f"\n  Processing: {pdf_path.name}")

        # Extract from PDF
        full_text, extracted = extract_from_pdf(pdf_path)

        if not full_text:
            print(f"    -> Failed to extract text")
            continue

        print(f"    -> Extracted {len(full_text):,} chars of text")

        # Count by type
        hrs = [e for e in extracted if e['measure_type'] == 'HR']
        ors = [e for e in extracted if e['measure_type'] == 'OR']
        rrs = [e for e in extracted if e['measure_type'] == 'RR']

        total_hrs_extracted += len(hrs)
        total_ors_extracted += len(ors)
        total_rrs_extracted += len(rrs)

        if extracted:
            pdfs_with_effects += 1
            print(f"    -> Found {len(hrs)} HR, {len(ors)} OR, {len(rrs)} RR")

            # Show first few extracted
            for e in extracted[:3]:
                val = e['value']
                ci_str = ""
                if e['ci_low'] and e['ci_high']:
                    ci_str = f" (95% CI: {e['ci_low']:.2f}-{e['ci_high']:.2f})"
                print(f"       {e['measure_type']}: {val:.2f}{ci_str}")

            if len(extracted) > 3:
                print(f"       ... and {len(extracted) - 3} more")
        else:
            print(f"    -> No effect estimates found")

        # Validate against CTgov if NCT ID available
        if nct_id:
            print(f"    -> Validating against CTgov ({nct_id})...")
            ctgov_effects = fetch_ctgov_effects(nct_id)

            if ctgov_effects:
                validation = validate_extraction(extracted, ctgov_effects)
                print(f"    -> CTgov has {len(ctgov_effects)} effects, matched {validation['matched']}")

                all_results.append({
                    'trial': trial_name,
                    'nct_id': nct_id,
                    'pdf': pdf_path.name,
                    'pdf_extracted': len(extracted),
                    'ctgov_expected': len(ctgov_effects),
                    'matched': validation['matched']
                })
            else:
                print(f"    -> No effect data in CTgov results")

        time.sleep(0.2)

    # Summary
    print("\n" + "=" * 70)
    print("REAL PDF VALIDATION SUMMARY")
    print("=" * 70)

    print(f"""
PDFs Processed: {total_pdfs}
  - With effect estimates: {pdfs_with_effects}
  - Failed to parse: {total_pdfs - pdfs_with_effects}

Effects Extracted:
  - Hazard Ratios (HR): {total_hrs_extracted}
  - Odds Ratios (OR): {total_ors_extracted}
  - Relative Risks (RR): {total_rrs_extracted}
  - Total: {total_hrs_extracted + total_ors_extracted + total_rrs_extracted}
""")

    if all_results:
        total_expected = sum(r['ctgov_expected'] for r in all_results)
        total_matched = sum(r['matched'] for r in all_results)

        if total_expected > 0:
            accuracy = total_matched / total_expected * 100
            print(f"CTgov Validation (where NCT ID available):")
            print(f"  - Expected outcomes: {total_expected}")
            print(f"  - Matched in PDF: {total_matched}")
            print(f"  - Match rate: {accuracy:.1f}%")

    # Save results
    output_file = Path(__file__).parent / 'output' / 'real_pdf_validation.json'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'pdfs_processed': total_pdfs,
                'pdfs_with_effects': pdfs_with_effects,
                'total_hrs': total_hrs_extracted,
                'total_ors': total_ors_extracted,
                'total_rrs': total_rrs_extracted,
            },
            'results': all_results
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
