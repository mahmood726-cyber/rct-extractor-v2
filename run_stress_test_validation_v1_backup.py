"""
Stress Test Validation for RCT Extractor
=========================================

Tests edge cases, unusual formatting, and challenging extractions:
1. Unicode characters and special formatting
2. Various journal formatting styles
3. Ambiguous cases and near-misses
4. Multi-language numeric formats
5. Complex nested results
"""
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'src'))


# ============================================================================
# STRESS TEST CASES
# ============================================================================

STRESS_TEST_CASES = [
    # Unicode and special characters
    {
        "category": "Unicode",
        "text": "hazard ratio, 0·82; 95% CI, 0·73 to 0·92",  # Middle dot (NEJM style)
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },
    {
        "category": "Unicode",
        "text": "HR 0.74 (95% CI: 0.65–0.85)",  # En-dash
        "expected": {"type": "HR", "value": 0.74, "ci_low": 0.65, "ci_high": 0.85}
    },
    {
        "category": "Unicode",
        "text": "hazard ratio = 0.82 (95% CI, 0.73—0.92)",  # Em-dash
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },
    {
        "category": "Unicode",
        "text": "HR: 0.82 [95% CI: 0.73−0.92]",  # Minus sign (U+2212)
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },

    # NEJM style formatting
    {
        "category": "NEJM Style",
        "text": "The hazard ratio for death from cardiovascular causes was 0.86 (95% confidence interval [CI], 0.74 to 0.99; P=0.04)",
        "expected": {"type": "HR", "value": 0.86, "ci_low": 0.74, "ci_high": 0.99}
    },
    {
        "category": "NEJM Style",
        "text": "hazard ratio, 0.74; 95% CI, 0.65 to 0.85; P<0.001",
        "expected": {"type": "HR", "value": 0.74, "ci_low": 0.65, "ci_high": 0.85}
    },
    {
        "category": "NEJM Style",
        "text": "hazard ratio for the primary outcome, 0.82; 95% confidence interval, 0.73 to 0.92",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },

    # Lancet style formatting
    {
        "category": "Lancet Style",
        "text": "HR 0·79 (95% CI 0·69–0·90; p<0·0001)",
        "expected": {"type": "HR", "value": 0.79, "ci_low": 0.69, "ci_high": 0.90}
    },
    {
        "category": "Lancet Style",
        "text": "hazard ratio 0·82 (0·73–0·92)",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },

    # JAMA style formatting
    {
        "category": "JAMA Style",
        "text": "Hazard Ratio, 0.82 (95% CI, 0.73-0.92)",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },
    {
        "category": "JAMA Style",
        "text": "HR, 0.74 [95% CI, 0.65-0.85]",
        "expected": {"type": "HR", "value": 0.74, "ci_low": 0.65, "ci_high": 0.85}
    },

    # Odds ratios
    {
        "category": "OR Formats",
        "text": "odds ratio, 0.72; 95% CI, 0.58 to 0.89",
        "expected": {"type": "OR", "value": 0.72, "ci_low": 0.58, "ci_high": 0.89}
    },
    {
        "category": "OR Formats",
        "text": "OR 1.45 (95% CI: 1.12-1.88)",
        "expected": {"type": "OR", "value": 1.45, "ci_low": 1.12, "ci_high": 1.88}
    },
    {
        "category": "OR Formats",
        "text": "The odds ratio was 2.31 (95% confidence interval, 1.54 to 3.47)",
        "expected": {"type": "OR", "value": 2.31, "ci_low": 1.54, "ci_high": 3.47}
    },

    # Risk ratios
    {
        "category": "RR Formats",
        "text": "relative risk, 0.85; 95% CI, 0.74 to 0.98",
        "expected": {"type": "RR", "value": 0.85, "ci_low": 0.74, "ci_high": 0.98}
    },
    {
        "category": "RR Formats",
        "text": "RR 0.65 (95% CI: 0.52-0.81)",
        "expected": {"type": "RR", "value": 0.65, "ci_low": 0.52, "ci_high": 0.81}
    },
    {
        "category": "RR Formats",
        "text": "risk ratio 1.23 (1.05-1.44)",
        "expected": {"type": "RR", "value": 1.23, "ci_low": 1.05, "ci_high": 1.44}
    },

    # Edge values
    {
        "category": "Edge Values",
        "text": "HR 0.10 (0.05-0.20)",  # Very low HR
        "expected": {"type": "HR", "value": 0.10, "ci_low": 0.05, "ci_high": 0.20}
    },
    {
        "category": "Edge Values",
        "text": "HR 5.67 (3.21-10.02)",  # High HR
        "expected": {"type": "HR", "value": 5.67, "ci_low": 3.21, "ci_high": 10.02}
    },
    {
        "category": "Edge Values",
        "text": "OR 0.05 (0.01-0.25)",  # Very protective OR
        "expected": {"type": "OR", "value": 0.05, "ci_low": 0.01, "ci_high": 0.25}
    },
    {
        "category": "Edge Values",
        "text": "OR 15.4 (8.2-28.9)",  # High OR
        "expected": {"type": "OR", "value": 15.4, "ci_low": 8.2, "ci_high": 28.9}
    },

    # Precision variations
    {
        "category": "Precision",
        "text": "HR 0.8 (0.7-0.9)",  # 1 decimal
        "expected": {"type": "HR", "value": 0.8, "ci_low": 0.7, "ci_high": 0.9}
    },
    {
        "category": "Precision",
        "text": "HR 0.823 (0.731-0.924)",  # 3 decimals
        "expected": {"type": "HR", "value": 0.823, "ci_low": 0.731, "ci_high": 0.924}
    },
    {
        "category": "Precision",
        "text": "HR 1 (0.85-1.18)",  # Integer point estimate
        "expected": {"type": "HR", "value": 1.0, "ci_low": 0.85, "ci_high": 1.18}
    },

    # Complex sentences
    {
        "category": "Complex",
        "text": "In the intention-to-treat population, the hazard ratio for the primary composite outcome of cardiovascular death or hospitalization for heart failure was 0.82 (95% CI, 0.73 to 0.92; P<0.001)",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },
    {
        "category": "Complex",
        "text": "After adjustment for baseline characteristics, treatment with dapagliflozin resulted in a hazard ratio of 0.74 (95% confidence interval [CI], 0.65 to 0.85) for the primary endpoint",
        "expected": {"type": "HR", "value": 0.74, "ci_low": 0.65, "ci_high": 0.85}
    },

    # Subgroup results (should still extract)
    {
        "category": "Subgroups",
        "text": "In patients with diabetes, HR 0.85 (0.72-1.01); in those without diabetes, HR 0.79 (0.68-0.92)",
        "expected": {"type": "HR", "value": 0.85, "ci_low": 0.72, "ci_high": 1.01}  # First one
    },

    # Table-like formatting
    {
        "category": "Table Format",
        "text": "Primary endpoint    0.82    (0.73-0.92)    <0.001",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },

    # With "of" construction
    {
        "category": "With Of",
        "text": "hazard ratio of 0.82 (95% CI, 0.73 to 0.92)",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },
    {
        "category": "With Of",
        "text": "an odds ratio of 1.45 (95% CI: 1.12-1.88)",
        "expected": {"type": "OR", "value": 1.45, "ci_low": 1.12, "ci_high": 1.88}
    },

    # Semicolon separators
    {
        "category": "Semicolons",
        "text": "HR: 0.82; 95% CI: 0.73-0.92; P<0.001",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },

    # Square brackets
    {
        "category": "Brackets",
        "text": "HR 0.82 [95% CI 0.73-0.92]",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },
    {
        "category": "Brackets",
        "text": "HR 0.82 [0.73, 0.92]",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },

    # European decimal format (comma as decimal)
    {
        "category": "European Format",
        "text": "HR 0,82 (0,73-0,92)",  # Comma decimal
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },

    # Specific trial results (ground truth)
    {
        "category": "DELIVER Trial",
        "text": "The hazard ratio for the primary outcome was 0.82 (95% CI, 0.73 to 0.92; P<0.001)",
        "expected": {"type": "HR", "value": 0.82, "ci_low": 0.73, "ci_high": 0.92}
    },
    {
        "category": "DAPA-HF Trial",
        "text": "hazard ratio, 0.74; 95% CI, 0.65 to 0.85",
        "expected": {"type": "HR", "value": 0.74, "ci_low": 0.65, "ci_high": 0.85}
    },
    {
        "category": "EMPEROR-Reduced",
        "text": "HR 0.75 (95% CI: 0.65-0.86; P<0.001)",
        "expected": {"type": "HR", "value": 0.75, "ci_low": 0.65, "ci_high": 0.86}
    },
    {
        "category": "EMPA-REG OUTCOME",
        "text": "hazard ratio in the empagliflozin group, 0.86; 95% confidence interval, 0.74 to 0.99",
        "expected": {"type": "HR", "value": 0.86, "ci_low": 0.74, "ci_high": 0.99}
    },
]

# Adversarial cases (should NOT extract or should handle correctly)
ADVERSARIAL_CASES = [
    {
        "category": "Not Effect Estimate",
        "text": "The heart rate was 82 (73-92) bpm",
        "should_extract_hr": False
    },
    {
        "category": "Not Effect Estimate",
        "text": "Blood pressure 120/80 (110-130/70-90) mmHg",
        "should_extract_hr": False
    },
    {
        "category": "Invalid CI",
        "text": "HR 0.82 (0.92-0.73)",  # CI reversed
        "should_extract_hr": False
    },
    {
        "category": "Implausible Value",
        "text": "HR 150 (120-180)",  # Way too high
        "should_extract_hr": False
    },
    {
        "category": "Year Range",
        "text": "From 2020 (2018-2022), we enrolled patients",
        "should_extract_hr": False
    },
    {
        "category": "Sample Size",
        "text": "N=500 (450-550 expected)",
        "should_extract_hr": False
    },
]


def normalize_text(text: str) -> str:
    """Normalize unicode and special characters"""
    # Replace unicode middle dots with periods
    text = text.replace('\xb7', '.')  # Middle dot ·
    text = text.replace('\u00b7', '.')  # Middle dot ·
    text = text.replace('\u2027', '.')  # Hyphenation point ‧
    text = text.replace('\u2219', '.')  # Bullet operator ∙
    text = text.replace('·', '.')  # Direct middle dot

    # Replace various dashes with hyphen
    text = text.replace('\u2013', '-')  # En-dash –
    text = text.replace('\u2014', '-')  # Em-dash —
    text = text.replace('\u2212', '-')  # Minus sign −
    text = text.replace('\u2010', '-')  # Hyphen ‐
    text = text.replace('\u2011', '-')  # Non-breaking hyphen ‑
    text = text.replace('–', '-')  # Direct en-dash
    text = text.replace('—', '-')  # Direct em-dash

    # Handle European decimal format (comma as decimal separator)
    # Only in specific patterns like "0,82" not in CI separators
    import re
    # Replace comma decimals: match digit,digit pattern
    text = re.sub(r'(\d),(\d)', r'\1.\2', text)

    return text


def extract_effects(text: str) -> List[Dict]:
    """Extract effect estimates from text"""
    text = normalize_text(text)
    results = []
    seen = set()

    patterns = {
        'HR': [
            # "hazard ratio, 0.82; 95% CI, 0.73 to 0.92"
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s\[]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "hazard ratio 0.82 (95% CI, 0.73 to 0.92)" or "hazard ratio 0.82 (0.73-0.92)"
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "hazard ratio of 0.82 (95% CI, 0.73 to 0.92)" or "hazard ratio was 0.82 (...)"
            r'hazard\s*ratio\s+(?:of|was|for\s+\w+\s+was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "hazard ratio for X was 0.82 (95% CI, 0.73 to 0.92)"
            r'hazard\s*ratio\s+(?:for\s+)?[\w\s]+?was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "HR 0.82 (0.73-0.92)" or "HR 0.82 [0.73-0.92]"
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
            # "HR: 0.82; 95% CI: 0.73-0.92"
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # "Hazard Ratio, 0.82 (95% CI, 0.73-0.92)"
            r'Hazard\s+Ratio[,;:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # "hazard ratio in the X group, 0.82; 95% confidence, 0.73 to 0.92"
            r'hazard\s*ratio\s+in\s+[\w\s]+[,;]\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:confidence|CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "resulted in a hazard ratio of 0.74 (95% confidence interval [CI], 0.65 to 0.85)"
            r'hazard\s*ratio\s+of\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval)?[\s\[\]CI,]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "hazard ratio for X, 0.82; 95% confidence interval, 0.73 to 0.92"
            r'hazard\s*ratio\s+(?:for\s+)?[\w\s]+[,;]\s*(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:confidence\s*interval|CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "hazard ratio for X was 0.86 (95% confidence interval [CI], 0.74 to 0.99)"
            r'hazard\s*ratio[\w\s]+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval)?[\s\[\]CI,]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "HR 0.75 (95% CI: 0.65-0.86)" with colon after CI
            r'\bHR\b[,;:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # Table format: just numbers with parentheses
            r'(\d+\.?\d*)\s+\(\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)\s*\)',
        ],
        'OR': [
            # "odds ratio, 0.72; 95% CI, 0.58 to 0.89"
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "odds ratio 0.72 (95% CI, 0.58 to 0.89)"
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "odds ratio of/was 0.72 (95% CI, 0.58 to 0.89)"
            r'odds\s*ratio\s+(?:of|was)\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|confidence)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "odds ratio was 2.31 (95% confidence interval, 1.54 to 3.47)"
            r'odds\s*ratio\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:confidence\s*interval|CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "OR 0.72 (0.58-0.89)"
            r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
        ],
        'RR': [
            # "relative risk, 0.85; 95% CI, 0.74 to 0.98"
            r'relative\s+risk[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "risk ratio 0.85 (95% CI, 0.74 to 0.98)"
            r'(?:relative\s+)?risk\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # "RR 0.85 (0.74-0.98)"
            r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
        ],
    }

    plausibility = {
        'HR': lambda v, l, h: 0.05 <= v <= 20 and l < v < h and l >= 0.01,
        'OR': lambda v, l, h: 0.01 <= v <= 50 and l < v < h and l >= 0.001,
        'RR': lambda v, l, h: 0.05 <= v <= 20 and l < v < h and l >= 0.01,
    }

    for measure, pattern_list in patterns.items():
        for pattern in pattern_list:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                    ci_low = float(match.group(2))
                    ci_high = float(match.group(3))

                    if not plausibility[measure](value, ci_low, ci_high):
                        continue

                    key = (measure, round(value, 3), round(ci_low, 3), round(ci_high, 3))
                    if key in seen:
                        continue
                    seen.add(key)

                    results.append({
                        'type': measure,
                        'value': value,
                        'ci_low': ci_low,
                        'ci_high': ci_high
                    })
                except (ValueError, IndexError):
                    continue

    return results


def run_stress_tests():
    """Run all stress tests"""
    print("=" * 80)
    print("STRESS TEST VALIDATION")
    print("=" * 80)

    # Positive tests
    print("\n" + "-" * 80)
    print("POSITIVE TESTS (Should Extract)")
    print("-" * 80)

    by_category = defaultdict(lambda: {"passed": 0, "failed": 0, "cases": []})

    for case in STRESS_TEST_CASES:
        category = case["category"]
        expected = case["expected"]

        results = extract_effects(case["text"])

        passed = False
        for r in results:
            if (r["type"] == expected["type"] and
                abs(r["value"] - expected["value"]) < 0.01 and
                abs(r["ci_low"] - expected["ci_low"]) < 0.01 and
                abs(r["ci_high"] - expected["ci_high"]) < 0.01):
                passed = True
                break

        if passed:
            by_category[category]["passed"] += 1
        else:
            by_category[category]["failed"] += 1
            by_category[category]["cases"].append({
                "text": case["text"][:60] + "...",
                "expected": f"{expected['type']} {expected['value']} ({expected['ci_low']}-{expected['ci_high']})",
                "got": results
            })

    total_passed = sum(c["passed"] for c in by_category.values())
    total_failed = sum(c["failed"] for c in by_category.values())
    total = total_passed + total_failed

    print(f"\nResults by category:")
    for category in sorted(by_category.keys()):
        stats = by_category[category]
        total_cat = stats["passed"] + stats["failed"]
        pct = stats["passed"] / total_cat * 100 if total_cat > 0 else 0
        status = "[OK]" if stats["failed"] == 0 else "[FAIL]"
        print(f"  {status} {category}: {stats['passed']}/{total_cat} ({pct:.0f}%)")
        for fail in stats["cases"]:
            print(f"      FAILED: {fail['text']}")
            print(f"        Expected: {fail['expected']}")
            print(f"        Got: {fail['got']}")

    # Adversarial tests
    print("\n" + "-" * 80)
    print("ADVERSARIAL TESTS (Should NOT Extract)")
    print("-" * 80)

    adv_passed = 0
    adv_failed = 0

    for case in ADVERSARIAL_CASES:
        results = extract_effects(case["text"])
        hr_found = any(r["type"] == "HR" for r in results)

        if case["should_extract_hr"] == hr_found:
            adv_passed += 1
            status = "[OK]"
        else:
            adv_failed += 1
            status = "[FAIL]"

        print(f"  {status} {case['category']}: '{case['text'][:50]}...'")
        if status == "[FAIL]":
            print(f"        Should extract HR: {case['should_extract_hr']}, Found: {results}")

    # Summary
    print("\n" + "=" * 80)
    print("STRESS TEST SUMMARY")
    print("=" * 80)

    pos_acc = total_passed / total * 100 if total > 0 else 0
    adv_acc = adv_passed / (adv_passed + adv_failed) * 100 if (adv_passed + adv_failed) > 0 else 0

    print(f"""
  POSITIVE TESTS:
    Total: {total}
    Passed: {total_passed}
    Failed: {total_failed}
    Accuracy: {pos_acc:.1f}%

  ADVERSARIAL TESTS:
    Total: {adv_passed + adv_failed}
    Passed: {adv_passed}
    Failed: {adv_failed}
    Accuracy: {adv_acc:.1f}%

  OVERALL ACCURACY: {(total_passed + adv_passed) / (total + adv_passed + adv_failed) * 100:.1f}%
""")

    # Save results
    output = {
        "positive_tests": {
            "total": total,
            "passed": total_passed,
            "failed": total_failed,
            "accuracy": pos_acc,
            "by_category": {k: {"passed": v["passed"], "failed": v["failed"]} for k, v in by_category.items()}
        },
        "adversarial_tests": {
            "total": adv_passed + adv_failed,
            "passed": adv_passed,
            "failed": adv_failed,
            "accuracy": adv_acc
        }
    }

    output_file = Path(__file__).parent / "output" / "stress_test_validation.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  Results saved to: {output_file}")
    print("=" * 80)

    return total_passed, total_failed, adv_passed, adv_failed


if __name__ == "__main__":
    run_stress_tests()
