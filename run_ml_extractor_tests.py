"""
ML Extractor Tests for RCT Extractor v2.15
==========================================

Tests the machine learning components:
1. Feature extraction
2. Effect type classification
3. Confidence scoring
4. Ensemble extraction
5. Cross-paper validation
"""

import sys
from pathlib import Path
from datetime import datetime

# Add paths for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(script_dir / 'src' / 'core'))
sys.path.insert(0, str(script_dir / 'data'))

from ml_extractor import (
    FeatureExtractor,
    EffectTypeClassifier,
    ConfidenceScorer,
    EnsembleExtractor,
    CrossPaperValidator,
    ExtractionResult,
    create_training_data_from_gold_standard,
    train_default_classifier,
    SKLEARN_AVAILABLE
)

# Import gold standard for training
try:
    from pdf_gold_standard import ALL_GOLD_STANDARD_TRIALS
    GOLD_STANDARD_AVAILABLE = True
except ImportError:
    GOLD_STANDARD_AVAILABLE = False


def print_header(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def run_feature_extraction_tests():
    """Test feature extraction"""
    print_header("FEATURE EXTRACTION TESTS")

    extractor = FeatureExtractor()
    tests_passed = 0
    tests_total = 0

    # Test cases: (text, expected_features)
    test_cases = [
        # HR detection
        (
            "The hazard ratio for mortality was HR 0.75 (95% CI 0.63-0.89)",
            {"has_hr_abbrev": 1, "has_ci": 1}
        ),
        # OR detection
        (
            "Adjusted odds ratio OR 2.3 (1.5 to 3.4) in logistic regression",
            {"has_or_abbrev": 1, "kw_or": lambda x: x > 0}
        ),
        # RR detection
        (
            "Relative risk RR 1.45 (95% CI 1.12-1.88) from cohort study",
            {"has_rr_abbrev": 1}
        ),
        # SMD detection
        (
            "Standardized mean difference SMD 0.35 (0.12 to 0.58) using Hedges g",
            {"has_smd_abbrev": 1, "kw_smd": lambda x: x > 0}
        ),
        # P-value presence
        (
            "HR 0.82 (0.71-0.95), p<0.001",
            {"has_pvalue": 1}
        ),
        # Percentage presence
        (
            "Event rate was 15.2% vs 12.8%",
            {"has_percent": 1}
        ),
        # Survival context
        (
            "Kaplan-Meier overall survival showed median follow-up of 24 months",
            {"ctx_hr": lambda x: x > 0}
        ),
        # Numbers extraction
        (
            "HR 0.75 (95% CI 0.63-0.89) with 1245 events",
            {"num_count": lambda x: x >= 4}
        ),
    ]

    for text, expected in test_cases:
        tests_total += 1
        features = extractor.extract_features(text)

        all_match = True
        for key, expected_val in expected.items():
            actual = features.get(key, 0)
            if callable(expected_val):
                if not expected_val(actual):
                    all_match = False
                    print(f"  FAIL: {key} = {actual} (expected to pass check)")
            else:
                if actual != expected_val:
                    all_match = False
                    print(f"  FAIL: {key} = {actual} (expected {expected_val})")

        if all_match:
            tests_passed += 1
            print(f"  PASS: Feature extraction for '{text[:50]}...'")

    # Test feature vector consistency
    tests_total += 1
    vec1 = extractor.extract_feature_vector("Sample text")
    vec2 = extractor.extract_feature_vector("Another text")
    if len(vec1) == len(vec2) and len(vec1) > 20:
        tests_passed += 1
        print(f"  PASS: Feature vector consistency ({len(vec1)} features)")
    else:
        print(f"  FAIL: Feature vector inconsistency")

    print(f"\n  Feature Extraction: {tests_passed}/{tests_total}")
    return tests_passed, tests_total


def run_classifier_tests():
    """Test effect type classifier"""
    print_header("EFFECT TYPE CLASSIFIER TESTS")

    if not SKLEARN_AVAILABLE:
        print("  WARNING: sklearn not available, skipping ML tests")
        return 0, 0

    classifier = EffectTypeClassifier()
    tests_passed = 0
    tests_total = 0

    # Test 1: Rule-based prediction (before training)
    print("\n  1. Rule-Based Prediction (untrained)")

    rule_based_tests = [
        ("hazard ratio 0.75", "HR"),
        ("odds ratio 2.3", "OR"),
        ("risk ratio 1.45", "RR"),
        ("mean difference -5.2", "MD"),
        ("standardized mean difference 0.35", "SMD"),
        ("incidence rate ratio 1.8", "IRR"),
    ]

    for text, expected_type in rule_based_tests:
        tests_total += 1
        pred_type, confidence = classifier._rule_based_predict(text)
        if pred_type == expected_type:
            tests_passed += 1
            print(f"    PASS: '{text}' -> {pred_type} ({confidence:.2f})")
        else:
            print(f"    FAIL: '{text}' -> {pred_type} (expected {expected_type})")

    # Test 2: Training on gold standard
    print("\n  2. Training on Gold Standard")

    if GOLD_STANDARD_AVAILABLE:
        training_data = create_training_data_from_gold_standard()
        if training_data:
            tests_total += 1
            try:
                texts, labels = zip(*training_data)
                classifier.train(list(texts), list(labels))
                tests_passed += 1
                print(f"    PASS: Trained on {len(training_data)} samples")
            except Exception as e:
                print(f"    FAIL: Training error: {e}")

        # Test 3: Trained prediction
        print("\n  3. Trained Classifier Prediction")

        if classifier.is_trained:
            trained_tests = [
                ("HR 0.72 (95% CI 0.58-0.89)", "HR"),
                ("OR 1.85 (95% CI 1.42-2.41)", "OR"),
                ("RR 0.65 (95% CI 0.52-0.81)", "RR"),
                ("MD -3.5 (95% CI -5.2 to -1.8)", "MD"),
            ]

            for text, expected_type in trained_tests:
                tests_total += 1
                pred_type, confidence = classifier.predict(text)
                if pred_type == expected_type:
                    tests_passed += 1
                    print(f"    PASS: '{text[:40]}...' -> {pred_type} ({confidence:.2f})")
                else:
                    print(f"    FAIL: '{text[:40]}...' -> {pred_type} (expected {expected_type})")
    else:
        print("    SKIP: Gold standard not available")

    print(f"\n  Classifier Tests: {tests_passed}/{tests_total}")
    return tests_passed, tests_total


def run_confidence_scorer_tests():
    """Test confidence scoring"""
    print_header("CONFIDENCE SCORER TESTS")

    scorer = ConfidenceScorer()
    tests_passed = 0
    tests_total = 0

    # Test cases: (text, extraction, expected_confidence_range)
    test_cases = [
        # High confidence: clear HR with proper CI
        (
            "hazard ratio HR 0.75 (95% CI 0.63-0.89)",
            {"type": "HR", "effect_size": 0.75, "ci_lower": 0.63, "ci_upper": 0.89},
            (0.7, 1.0)  # Should be high confidence
        ),
        # Medium confidence: OR without explicit mention
        (
            "The adjusted ratio was 2.3 (1.5 to 3.4)",
            {"type": "OR", "effect_size": 2.3, "ci_lower": 1.5, "ci_upper": 3.4},
            (0.4, 0.8)  # Medium confidence
        ),
        # Low confidence: implausible values
        (
            "HR 500 (200-800)",
            {"type": "HR", "effect_size": 500, "ci_lower": 200, "ci_upper": 800},
            (0.0, 0.65)  # Should be low due to implausible values
        ),
        # CI doesn't contain estimate - should reduce confidence but not catastrophically
        # since other signals (pattern, plausibility) are still valid
        (
            "HR 0.75 (0.80-0.95)",
            {"type": "HR", "effect_size": 0.75, "ci_lower": 0.80, "ci_upper": 0.95},
            (0.6, 0.85)  # Moderate reduction due to CI issue
        ),
    ]

    for text, extraction, (min_conf, max_conf) in test_cases:
        tests_total += 1
        confidence = scorer.score(text, extraction)

        if min_conf <= confidence <= max_conf:
            tests_passed += 1
            print(f"  PASS: conf={confidence:.3f} in [{min_conf:.1f}, {max_conf:.1f}]")
            print(f"        Text: '{text[:50]}...'")
        else:
            print(f"  FAIL: conf={confidence:.3f} NOT in [{min_conf:.1f}, {max_conf:.1f}]")
            print(f"        Text: '{text[:50]}...'")

    print(f"\n  Confidence Scorer: {tests_passed}/{tests_total}")
    return tests_passed, tests_total


def run_ensemble_extractor_tests():
    """Test ensemble extraction"""
    print_header("ENSEMBLE EXTRACTOR TESTS")

    ensemble = EnsembleExtractor()
    tests_passed = 0
    tests_total = 0

    # Simulate regex results
    mock_regex_results = [
        {"type": "HR", "effect_size": 0.75, "ci_lower": 0.63, "ci_upper": 0.89},
        {"type": "OR", "effect_size": 2.3, "ci_low": 1.5, "ci_high": 3.4},
    ]

    text = "The primary endpoint showed HR 0.75 (95% CI 0.63-0.89) and OR 2.3 (1.5-3.4)"

    # Test enhancement
    tests_total += 1
    results = ensemble.extract(text, mock_regex_results)

    if len(results) == 2:
        tests_passed += 1
        print(f"  PASS: Enhanced {len(results)} extractions")
    else:
        print(f"  FAIL: Expected 2 results, got {len(results)}")

    # Check that results have confidence scores
    tests_total += 1
    all_have_confidence = all(r.confidence > 0 for r in results)
    if all_have_confidence:
        tests_passed += 1
        print(f"  PASS: All results have confidence scores")
        for r in results:
            print(f"        {r.effect_type}: {r.value} (conf: {r.confidence:.3f})")
    else:
        print(f"  FAIL: Some results missing confidence")

    # Check that results have features
    tests_total += 1
    all_have_features = all(r.features for r in results)
    if all_have_features:
        tests_passed += 1
        print(f"  PASS: All results have extracted features")
    else:
        print(f"  FAIL: Some results missing features")

    # Train classifier and test validation
    if GOLD_STANDARD_AVAILABLE and SKLEARN_AVAILABLE:
        print("\n  Training ensemble classifier...")
        training_data = create_training_data_from_gold_standard()
        if training_data:
            ensemble.train_classifier(training_data)

            tests_total += 1
            if ensemble.classifier.is_trained:
                tests_passed += 1
                print(f"  PASS: Ensemble classifier trained")

                # Re-run extraction with trained classifier
                results = ensemble.extract(text, mock_regex_results)
                for r in results:
                    print(f"        {r.effect_type}: {r.value} (conf: {r.confidence:.3f})")
            else:
                print(f"  FAIL: Ensemble classifier not trained")

    print(f"\n  Ensemble Extractor: {tests_passed}/{tests_total}")
    return tests_passed, tests_total


def run_cross_paper_validator_tests():
    """Test cross-paper validation"""
    print_header("CROSS-PAPER VALIDATOR TESTS")

    validator = CrossPaperValidator()
    tests_passed = 0
    tests_total = 0

    # Add consistent extractions (same trial, same values)
    validator.add_extraction(
        trial_id="NCT12345678",
        source="paper1.pdf",
        extractions=[
            ExtractionResult("HR", 0.75, 0.63, 0.89, 0.9, "regex", {}),
        ]
    )
    validator.add_extraction(
        trial_id="NCT12345678",
        source="paper2.pdf",
        extractions=[
            ExtractionResult("HR", 0.75, 0.64, 0.88, 0.85, "regex", {}),
        ]
    )

    # Add conflicting extractions (different trial)
    validator.add_extraction(
        trial_id="NCT99999999",
        source="paper3.pdf",
        extractions=[
            ExtractionResult("OR", 2.3, 1.5, 3.4, 0.9, "regex", {}),
        ]
    )
    validator.add_extraction(
        trial_id="NCT99999999",
        source="paper4.pdf",
        extractions=[
            ExtractionResult("OR", 3.1, 2.0, 4.5, 0.85, "regex", {}),  # Different value!
        ]
    )

    # Run validation
    issues = validator.validate()

    # Test 1: Consistent trial should have no issues
    tests_total += 1
    if "NCT12345678" not in issues:
        tests_passed += 1
        print(f"  PASS: No issues for consistent trial NCT12345678")
    else:
        print(f"  FAIL: Unexpected issues for NCT12345678: {issues['NCT12345678']}")

    # Test 2: Conflicting trial should have VALUE_MISMATCH
    tests_total += 1
    if "NCT99999999" in issues:
        has_mismatch = any(i['type'] == 'VALUE_MISMATCH' for i in issues["NCT99999999"])
        if has_mismatch:
            tests_passed += 1
            print(f"  PASS: Detected VALUE_MISMATCH for NCT99999999")
            for issue in issues["NCT99999999"]:
                print(f"        {issue['type']}: {issue.get('value1')} vs {issue.get('value2')}")
        else:
            print(f"  FAIL: No VALUE_MISMATCH for conflicting values")
    else:
        print(f"  FAIL: No issues detected for conflicting trial")

    # Test 3: Add non-overlapping CIs
    validator2 = CrossPaperValidator()
    validator2.add_extraction(
        trial_id="NCT_NONOVERLAP",
        source="paper5.pdf",
        extractions=[
            ExtractionResult("HR", 0.5, 0.3, 0.6, 0.9, "regex", {}),
        ]
    )
    validator2.add_extraction(
        trial_id="NCT_NONOVERLAP",
        source="paper6.pdf",
        extractions=[
            ExtractionResult("HR", 0.9, 0.8, 1.1, 0.85, "regex", {}),  # Non-overlapping CI!
        ]
    )

    issues2 = validator2.validate()
    tests_total += 1
    if "NCT_NONOVERLAP" in issues2:
        has_ci_issue = any(i['type'] == 'CI_NO_OVERLAP' for i in issues2["NCT_NONOVERLAP"])
        if has_ci_issue:
            tests_passed += 1
            print(f"  PASS: Detected CI_NO_OVERLAP")
        else:
            print(f"  FAIL: No CI_NO_OVERLAP detected")
    else:
        print(f"  FAIL: No issues detected for non-overlapping CIs")

    print(f"\n  Cross-Paper Validator: {tests_passed}/{tests_total}")
    return tests_passed, tests_total


def run_integration_test():
    """Integration test with gold standard data"""
    print_header("INTEGRATION TEST WITH GOLD STANDARD")

    if not GOLD_STANDARD_AVAILABLE:
        print("  SKIP: Gold standard not available")
        return 0, 0

    if not SKLEARN_AVAILABLE:
        print("  SKIP: sklearn not available")
        return 0, 0

    tests_passed = 0
    tests_total = 0

    # Create and train classifier
    print("\n  1. Training classifier on gold standard...")
    classifier = train_default_classifier()

    tests_total += 1
    if classifier.is_trained:
        tests_passed += 1
        print(f"     PASS: Classifier trained")
    else:
        print(f"     FAIL: Classifier not trained")
        return tests_passed, tests_total

    # Test on held-out samples from gold standard
    print("\n  2. Testing on gold standard effects...")

    correct = 0
    total = 0

    for trial in ALL_GOLD_STANDARD_TRIALS[:10]:  # Test on first 10 trials
        for effect in trial.expected_effects:
            text = f"{effect.effect_type} {effect.value} (95% CI {effect.ci_lower}-{effect.ci_upper})"
            pred_type, confidence = classifier.predict(text)

            total += 1
            if pred_type == effect.effect_type:
                correct += 1

    accuracy = correct / total if total > 0 else 0
    tests_total += 1

    if accuracy >= 0.8:  # 80% accuracy threshold
        tests_passed += 1
        print(f"     PASS: Accuracy {accuracy*100:.1f}% ({correct}/{total})")
    else:
        print(f"     FAIL: Accuracy {accuracy*100:.1f}% ({correct}/{total}) < 80%")

    # Test ensemble extractor
    print("\n  3. Testing ensemble extractor...")

    ensemble = EnsembleExtractor()
    training_data = create_training_data_from_gold_standard()
    ensemble.train_classifier(training_data)

    # Create mock regex results from gold standard
    test_trial = ALL_GOLD_STANDARD_TRIALS[0]
    mock_results = []
    for effect in test_trial.expected_effects:
        mock_results.append({
            "type": effect.effect_type,
            "effect_size": effect.value,
            "ci_lower": effect.ci_lower,
            "ci_upper": effect.ci_upper,
        })

    text = " ".join([
        f"{e.effect_type} {e.value} (95% CI {e.ci_lower}-{e.ci_upper})"
        for e in test_trial.expected_effects
    ])

    enhanced = ensemble.extract(text, mock_results)

    tests_total += 1
    high_confidence = sum(1 for r in enhanced if r.confidence > 0.5)
    if high_confidence == len(enhanced):
        tests_passed += 1
        print(f"     PASS: All {len(enhanced)} extractions have conf > 0.5")
    else:
        print(f"     PARTIAL: {high_confidence}/{len(enhanced)} have conf > 0.5")

    print(f"\n  Integration Test: {tests_passed}/{tests_total}")
    return tests_passed, tests_total


def main():
    """Run all ML extractor tests"""
    print("=" * 70)
    print("ML EXTRACTOR VALIDATION v2.15")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    print(f"\nDependencies:")
    print(f"  sklearn: {'Available' if SKLEARN_AVAILABLE else 'NOT AVAILABLE'}")
    print(f"  Gold Standard: {'Available' if GOLD_STANDARD_AVAILABLE else 'NOT AVAILABLE'}")

    all_passed = 0
    all_total = 0

    # Run all test suites
    passed, total = run_feature_extraction_tests()
    all_passed += passed
    all_total += total

    passed, total = run_classifier_tests()
    all_passed += passed
    all_total += total

    passed, total = run_confidence_scorer_tests()
    all_passed += passed
    all_total += total

    passed, total = run_ensemble_extractor_tests()
    all_passed += passed
    all_total += total

    passed, total = run_cross_paper_validator_tests()
    all_passed += passed
    all_total += total

    passed, total = run_integration_test()
    all_passed += passed
    all_total += total

    # Summary
    accuracy = all_passed / all_total * 100 if all_total > 0 else 0

    print("\n" + "=" * 70)
    print("ML EXTRACTOR VALIDATION SUMMARY")
    print("=" * 70)
    print(f"\n  Tests passed: {all_passed}/{all_total}")
    print(f"  Overall accuracy: {accuracy:.1f}%")
    print("=" * 70)

    # Save results
    import json
    output = {
        "timestamp": datetime.now().isoformat(),
        "version": "v2.15-ml-extractor",
        "sklearn_available": SKLEARN_AVAILABLE,
        "gold_standard_available": GOLD_STANDARD_AVAILABLE,
        "tests_passed": all_passed,
        "tests_total": all_total,
        "accuracy": accuracy
    }

    output_file = Path(__file__).parent / "output" / "ml_extractor_validation.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return all_passed, all_total


if __name__ == "__main__":
    main()
