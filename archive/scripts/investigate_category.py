#!/usr/bin/env python3
"""
Category Investigation Script - Phase 3 of IMPROVEMENT_PLAN_V8

Investigates why certain categories (respiratory, diabetes) have low extraction yields.
Analyzes PDFs to identify pattern gaps.

Usage:
    python scripts/investigate_category.py test_pdfs/real_pdfs/respiratory/
    python scripts/investigate_category.py test_pdfs/real_pdfs/diabetes/ --deep
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# Effect-related terms to search for in PDFs
EFFECT_TERMS = {
    # General effect terms
    "general": [
        r'\b(?:hazard|odds|risk)\s+ratio',
        r'\bHR\b',
        r'\bOR\b',
        r'\bRR\b',
        r'mean\s+difference',
        r'\bMD\b',
        r'\bSMD\b',
        r'relative\s+risk',
        r'absolute\s+(?:risk\s+)?(?:reduction|difference)',
        r'number\s+needed\s+to\s+treat',
        r'\bNNT\b',
        r'95%?\s*(?:CI|confidence)',
        r'p\s*[<>=]\s*0\.\d+',
        r'statistically\s+significant',
    ],

    # Respiratory-specific terms
    "respiratory": [
        r'\bFEV1?\b',
        r'forced\s+expiratory',
        r'forced\s+vital\s+capacity',
        r'\bFVC\b',
        r'peak\s+(?:expiratory\s+)?flow',
        r'\bPEF\b',
        r'exacerbation\s+rate',
        r'\bAECOPD\b',
        r'\bSGRQ\b',
        r'St\.?\s*George',
        r'\bCAT\b\s+(?:score)?',
        r'COPD\s+assessment',
        r'dyspnea',
        r'breathlessness',
        r'6-?minute\s+walk',
        r'\b6MWD?\b',
        r'oxygen\s+(?:saturation|therapy)',
        r'\bSpO2\b',
        r'bronchodilat',
        r'inhaler',
        r'pulmonary\s+function',
    ],

    # Diabetes-specific terms
    "diabetes": [
        r'\bHbA1c\b',
        r'\bA1[Cc]\b',
        r'glycated\s+h[ae]moglobin',
        r'fasting\s+(?:plasma\s+)?glucose',
        r'\bFPG\b',
        r'postprandial\s+glucose',
        r'\bPPG\b',
        r'time\s+in\s+range',
        r'\bTIR\b',
        r'hypoglyc[ae]mi',
        r'body\s+weight',
        r'weight\s+(?:loss|reduction|change)',
        r'\bBMI\b',
        r'waist\s+circumference',
        r'MACE',
        r'major\s+adverse\s+cardiovascular',
        r'cardiovascular\s+(?:death|event|outcome)',
        r'GLP-?1',
        r'SGLT-?2',
        r'insulin\s+(?:dose|requirement)',
        r'ketoacidosis',
        r'\bDKA\b',
    ],

    # Cardiology-specific terms
    "cardiology": [
        r'ejection\s+fraction',
        r'\bEF\b',
        r'\bLVEF\b',
        r'cardiac\s+output',
        r'stroke\s+volume',
        r'blood\s+pressure',
        r'systolic\s+BP',
        r'diastolic\s+BP',
        r'\bSBP\b',
        r'\bDBP\b',
        r'heart\s+(?:rate|failure)',
        r'myocardial\s+infarction',
        r'\bMI\b',
        r'atrial\s+fibrillation',
        r'\bAF\b',
        r'stroke',
        r'thromboembol',
        r'NT-?proBNP',
        r'\bBNP\b',
        r'troponin',
        r'cholesterol',
        r'\bLDL\b',
        r'\bHDL\b',
    ],

    # Oncology-specific terms
    "oncology": [
        r'overall\s+survival',
        r'\bOS\b',
        r'progression-?free\s+survival',
        r'\bPFS\b',
        r'disease-?free\s+survival',
        r'\bDFS\b',
        r'response\s+rate',
        r'objective\s+response',
        r'\bORR\b',
        r'complete\s+response',
        r'\bCR\b',
        r'partial\s+response',
        r'\bPR\b',
        r'stable\s+disease',
        r'\bSD\b',
        r'progressive\s+disease',
        r'\bPD\b',
        r'time\s+to\s+progression',
        r'\bTTP\b',
        r'median\s+survival',
        r'tumor\s+(?:response|size|burden)',
    ],
}

# Patterns that commonly contain numeric effect estimates
EFFECT_PATTERNS = [
    # HR patterns
    (r'(?:HR|hazard\s+ratio)[,;:\s=]+(\d+\.?\d*)\s*[\(\[]', "HR with CI"),
    (r'(?:HR|hazard\s+ratio)[,;:\s=]+(\d+\.?\d*)\s*[,;]', "HR with separator"),

    # OR patterns
    (r'(?:OR|odds\s+ratio)[,;:\s=]+(\d+\.?\d*)\s*[\(\[]', "OR with CI"),
    (r'(?:OR|odds\s+ratio)[,;:\s=]+(\d+\.?\d*)\s*[,;]', "OR with separator"),

    # RR patterns
    (r'(?:RR|relative\s+risk|risk\s+ratio)[,;:\s=]+(\d+\.?\d*)\s*[\(\[]', "RR with CI"),

    # MD patterns
    (r'(?:MD|mean\s+difference)[,;:\s=]+(-?\d+\.?\d*)\s*[\(\[]', "MD with CI"),
    (r'(?:MD|mean\s+difference)[,;:\s=]+(-?\d+\.?\d*)\s*(?:kg|%|mmHg)', "MD with units"),
    (r'difference\s+(?:was|of)\s+(-?\d+\.?\d*)', "difference was X"),

    # SMD patterns
    (r'(?:SMD|standardized\s+mean\s+difference)[,;:\s=]+(-?\d+\.?\d*)', "SMD"),
    (r"Cohen'?s?\s+d[,;:\s=]+(-?\d+\.?\d*)", "Cohen's d"),

    # CI patterns (to find potential effects)
    (r'(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[,:\s]+(\d+\.?\d*)\s*[-–—to]\s*(\d+\.?\d*)', "X (95% CI Y-Z)"),
    (r'(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)\s*\)', "X (Y-Z) simple"),

    # P-value patterns
    (r'[Pp]\s*[<>=]\s*(0\.\d+)', "p-value"),
    (r'[Pp]\s*=\s*(\.\d+)', "p-value decimal"),
]


def extract_text_from_pdf(pdf_path: str, max_pages: int = 50) -> str:
    """Extract full text from PDF."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text_parts = []
            for i in range(min(max_pages, len(doc))):
                text_parts.append(doc[i].get_text())
            doc.close()
            return "\n".join(text_parts)
        except Exception as e2:
            print(f"  Error: {e2}")
            return ""


def analyze_pdf(pdf_path: str, category: str = "general", deep: bool = False) -> dict:
    """
    Analyze a single PDF for effect-related content.

    Args:
        pdf_path: Path to PDF
        category: Category for domain-specific terms
        deep: Include full context snippets

    Returns:
        Analysis results dict
    """
    text = extract_text_from_pdf(pdf_path)

    if not text:
        return {"error": "Could not extract text", "pdf": Path(pdf_path).name}

    result = {
        "pdf": Path(pdf_path).name,
        "text_length": len(text),
        "term_matches": {},
        "pattern_matches": [],
        "potential_effects": [],
        "recommendations": [],
    }

    # Search for effect terms
    search_categories = ["general"]
    if category in EFFECT_TERMS:
        search_categories.append(category)

    for cat in search_categories:
        for term_pattern in EFFECT_TERMS.get(cat, []):
            matches = list(re.finditer(term_pattern, text, re.IGNORECASE))
            if matches:
                key = term_pattern[:50] + "..." if len(term_pattern) > 50 else term_pattern
                result["term_matches"][key] = len(matches)

    # Search for effect patterns
    for pattern, name in EFFECT_PATTERNS:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if matches:
            result["pattern_matches"].append({
                "pattern": name,
                "count": len(matches),
                "examples": [m.group(0)[:100] for m in matches[:3]] if deep else []
            })

    # Look for potential unextracted effects (numbers in CI format)
    ci_pattern = r'(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI[,:\s]+)?(\d+\.?\d*)\s*(?:[-–—]|to)\s*(\d+\.?\d*)'
    ci_matches = list(re.finditer(ci_pattern, text, re.IGNORECASE))

    for match in ci_matches[:20]:  # Limit to 20
        context_start = max(0, match.start() - 50)
        context_end = min(len(text), match.end() + 20)
        context = text[context_start:context_end].replace('\n', ' ')

        # Check if this looks like an effect estimate
        pre_context = text[max(0, match.start()-100):match.start()].lower()
        is_effect = any(term in pre_context for term in
                       ['ratio', 'hr', 'or', 'rr', 'difference', 'md', 'smd',
                        'effect', 'relative', 'absolute', 'risk'])

        result["potential_effects"].append({
            "value": match.group(1),
            "ci_lower": match.group(2),
            "ci_upper": match.group(3),
            "context": context,
            "likely_effect": is_effect
        })

    # Generate recommendations
    if len(result["term_matches"]) < 3:
        result["recommendations"].append("Few effect terms found - may not be RCT results")

    if not result["pattern_matches"]:
        result["recommendations"].append("No standard effect patterns matched - investigate text format")
    elif result["potential_effects"] and not any(p["count"] > 0 for p in result["pattern_matches"]):
        result["recommendations"].append("CI patterns found but effect patterns don't match - add new patterns")

    # Category-specific recommendations
    if category == "respiratory":
        respiratory_terms = sum(1 for k in result["term_matches"] if any(
            t in k.lower() for t in ['fev', 'fvc', 'sgrq', 'exacerbation', '6mw']))
        if respiratory_terms < 2:
            result["recommendations"].append("Few respiratory-specific terms - may not be pulmonology RCT")
        else:
            result["recommendations"].append("Has respiratory terms - check for FEV1/exacerbation rate patterns")

    elif category == "diabetes":
        diabetes_terms = sum(1 for k in result["term_matches"] if any(
            t in k.lower() for t in ['hba1c', 'a1c', 'glucose', 'weight', 'mace']))
        if diabetes_terms < 2:
            result["recommendations"].append("Few diabetes-specific terms - may not be diabetes RCT")
        else:
            result["recommendations"].append("Has diabetes terms - check for HbA1c/weight change patterns")

    return result


def investigate_category(pdf_dir: str, category: str = None, deep: bool = False,
                        output_path: str = None, verbose: bool = True) -> dict:
    """
    Investigate all PDFs in a category directory.

    Args:
        pdf_dir: Directory with PDFs
        category: Category name (auto-detected from path if not provided)
        deep: Include detailed analysis
        output_path: Path for JSON output
        verbose: Print progress

    Returns:
        Investigation results
    """
    pdf_dir = Path(pdf_dir)

    # Auto-detect category from path
    if category is None:
        category = pdf_dir.name.lower()
        if category not in EFFECT_TERMS:
            category = "general"

    results = {
        "investigation_date": datetime.now().isoformat(),
        "directory": str(pdf_dir),
        "category": category,
        "summary": {
            "total_pdfs": 0,
            "pdfs_with_effects": 0,
            "pdfs_without_effects": 0,
            "common_terms": {},
            "pattern_hit_rates": {},
            "recommendations": [],
        },
        "analyses": []
    }

    # Find PDFs
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    results["summary"]["total_pdfs"] = len(pdf_files)

    if verbose:
        print(f"Investigating {len(pdf_files)} PDFs in {pdf_dir}")
        print(f"Category: {category}")
        print("=" * 60)

    all_terms = defaultdict(int)
    all_patterns = defaultdict(int)

    for i, pdf_path in enumerate(pdf_files):
        if verbose:
            print(f"[{i+1}/{len(pdf_files)}] {pdf_path.name}...")

        analysis = analyze_pdf(str(pdf_path), category, deep)
        results["analyses"].append(analysis)

        # Aggregate term matches
        for term, count in analysis.get("term_matches", {}).items():
            all_terms[term] += count

        # Aggregate pattern matches
        for p in analysis.get("pattern_matches", []):
            all_patterns[p["pattern"]] += p["count"]

        # Count effects
        if analysis.get("pattern_matches"):
            results["summary"]["pdfs_with_effects"] += 1
        else:
            results["summary"]["pdfs_without_effects"] += 1

        if verbose and analysis.get("recommendations"):
            for rec in analysis["recommendations"][:2]:
                print(f"  -> {rec}")

    # Summarize
    results["summary"]["common_terms"] = dict(sorted(all_terms.items(),
                                                      key=lambda x: x[1],
                                                      reverse=True)[:20])
    results["summary"]["pattern_hit_rates"] = dict(sorted(all_patterns.items(),
                                                          key=lambda x: x[1],
                                                          reverse=True))

    # Generate overall recommendations
    if results["summary"]["pdfs_without_effects"] > results["summary"]["pdfs_with_effects"]:
        results["summary"]["recommendations"].append(
            f"Majority ({results['summary']['pdfs_without_effects']}/{results['summary']['total_pdfs']}) "
            "PDFs have no effect extractions - investigate text formats"
        )

    missing_patterns = []
    for term in results["summary"]["common_terms"]:
        if "ratio" in term.lower() or "difference" in term.lower():
            # Check if we have pattern coverage
            has_pattern = any(term.split('\\')[0] in p.lower()
                            for p in results["summary"]["pattern_hit_rates"])
            if not has_pattern:
                missing_patterns.append(term)

    if missing_patterns:
        results["summary"]["recommendations"].append(
            f"Terms without pattern coverage: {missing_patterns[:5]}"
        )

    # Print summary
    if verbose:
        print("\n" + "=" * 60)
        print("INVESTIGATION SUMMARY")
        print("=" * 60)
        print(f"PDFs with effect patterns: {results['summary']['pdfs_with_effects']}/{results['summary']['total_pdfs']}")
        print(f"\nMost common terms found:")
        for term, count in list(results["summary"]["common_terms"].items())[:10]:
            term_short = term[:40] + "..." if len(term) > 40 else term
            print(f"  {count:4d}x {term_short}")
        print(f"\nPattern hit rates:")
        for pattern, count in list(results["summary"]["pattern_hit_rates"].items())[:10]:
            print(f"  {count:4d}x {pattern}")
        print(f"\nRecommendations:")
        for rec in results["summary"]["recommendations"]:
            print(f"  • {rec}")

    # Save output
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        if verbose:
            print(f"\nResults saved to: {output_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Investigate PDF category for pattern gaps")
    parser.add_argument("pdf_dir", help="Directory containing PDFs")
    parser.add_argument("--category", "-c", help="Category name (auto-detected if not provided)")
    parser.add_argument("--deep", "-d", action="store_true", help="Include detailed context")
    parser.add_argument("--output", "-o", help="Output JSON path")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")

    args = parser.parse_args()

    if not os.path.isdir(args.pdf_dir):
        print(f"Error: {args.pdf_dir} is not a directory")
        sys.exit(1)

    investigate_category(args.pdf_dir, args.category, args.deep,
                        args.output, verbose=not args.quiet)


if __name__ == "__main__":
    main()
