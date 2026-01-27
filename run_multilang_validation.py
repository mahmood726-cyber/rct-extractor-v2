"""
Multi-Language Pattern Validation for RCT Extractor v2

Validates extraction accuracy across supported languages:
- English, Spanish, French, German, Italian, Portuguese, Chinese, Japanese
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.multilang_patterns import (
    MultiLanguageExtractor,
    get_supported_languages,
    get_language_name
)
from src.benchmark.statistics import clopper_pearson_ci


def load_multilang_cases() -> List[Dict]:
    """Load multi-language test cases"""
    gold_file = Path(__file__).parent / 'data' / 'gold' / 'multilang_cases.jsonl'
    cases = []

    if not gold_file.exists():
        print(f"Warning: {gold_file} not found")
        return cases

    with open(gold_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    return cases


def check_match(extracted: float, expected: float, tolerance: float = 0.05) -> bool:
    """Check if values match within tolerance"""
    if extracted is None and expected is None:
        return True
    if extracted is None or expected is None:
        return False
    if expected == 0:
        return abs(extracted) < tolerance
    return abs(extracted - expected) / abs(expected) <= tolerance


def run_validation():
    print("=" * 70)
    print("RCT EXTRACTOR v2 - MULTI-LANGUAGE VALIDATION")
    print("=" * 70)

    # Show supported languages
    print("\nSupported Languages:")
    for code in get_supported_languages():
        print(f"  - {code}: {get_language_name(code)}")

    # Load test cases
    cases = load_multilang_cases()
    print(f"\nLoaded {len(cases)} multi-language test cases")

    if not cases:
        print("No test cases found. Creating sample validation...")
        return

    # Initialize extractor
    extractor = MultiLanguageExtractor()

    # Track results by language
    results_by_lang = {}
    total_correct = 0
    total_cases = 0

    print("\n" + "-" * 70)
    print("Running Extraction Tests...")
    print("-" * 70)

    for case in cases:
        trial_name = case.get('trial_name', 'Unknown')
        text = case.get('text', '')
        expected = case.get('expected', {})
        language = case.get('language', 'en')
        is_adversarial = case.get('adversarial', False)

        measure_type = expected.get('measure_type', 'HR')

        # Get expected value
        expected_value = None
        if measure_type == 'HR':
            expected_value = expected.get('hr')
        elif measure_type == 'OR':
            expected_value = expected.get('or')
        elif measure_type == 'RR':
            expected_value = expected.get('rr')
        elif measure_type == 'RD':
            expected_value = expected.get('rd')
        elif measure_type == 'MD':
            expected_value = expected.get('md')

        # Extract
        result = None
        extracted_value = None

        if measure_type == 'HR':
            result = extractor.extract_hazard_ratio(text, language)
            if result:
                extracted_value = result.get('hr')
        elif measure_type == 'OR':
            result = extractor.extract_odds_ratio(text, language)
            if result:
                extracted_value = result.get('or')
        elif measure_type == 'RR':
            result = extractor.extract_relative_risk(text, language)
            if result:
                extracted_value = result.get('rr')
        elif measure_type == 'RD':
            result = extractor.extract_risk_difference(text, language)
            if result:
                extracted_value = result.get('rd')
        elif measure_type == 'MD':
            result = extractor.extract_mean_difference(text, language)
            if result:
                extracted_value = result.get('md')

        # Evaluate
        if is_adversarial:
            # For adversarial: correct = no extraction
            correct = extracted_value is None
        else:
            # For positive: correct = value matches
            correct = check_match(extracted_value, expected_value)

        total_cases += 1
        if correct:
            total_correct += 1

        # Track by language
        if language not in results_by_lang:
            results_by_lang[language] = {'correct': 0, 'total': 0}
        results_by_lang[language]['total'] += 1
        if correct:
            results_by_lang[language]['correct'] += 1

        # Print result
        status = "OK" if correct else "FAIL"
        if is_adversarial:
            print(f"  [{status}] {trial_name} ({language}): adversarial - extracted={extracted_value}")
        else:
            print(f"  [{status}] {trial_name} ({language}): expected={expected_value}, extracted={extracted_value}")

    # Summary
    print("\n" + "=" * 70)
    print("MULTI-LANGUAGE VALIDATION SUMMARY")
    print("=" * 70)

    accuracy = total_correct / total_cases if total_cases > 0 else 0
    ci_low, ci_high = clopper_pearson_ci(total_correct, total_cases)

    print(f"\nOverall Results:")
    print(f"  Accuracy: {accuracy*100:.1f}% ({total_correct}/{total_cases})")
    print(f"  95% CI: [{ci_low*100:.1f}%, {ci_high*100:.1f}%]")

    print(f"\nResults by Language:")
    print("-" * 50)
    print(f"{'Language':<15} {'Accuracy':<15} {'Correct/Total':<15}")
    print("-" * 50)

    for lang, data in sorted(results_by_lang.items()):
        lang_acc = data['correct'] / data['total'] if data['total'] > 0 else 0
        lang_name = get_language_name(lang)
        print(f"{lang_name:<15} {lang_acc*100:.1f}%{'':<9} {data['correct']}/{data['total']}")

    print("-" * 50)

    # Conclusion
    print(f"\nConclusion:")
    if accuracy >= 0.95:
        print(f"  [PASS] Multi-language extraction achieves >=95% accuracy")
    else:
        print(f"  [WARN] Multi-language extraction below 95% target")

    print("\n" + "=" * 70)

    return accuracy


if __name__ == "__main__":
    run_validation()
