"""
Statistical Functions for Benchmark Evaluation

Includes:
- Cohen's Kappa with confidence intervals
- Clopper-Pearson confidence intervals
- CI extraction metrics
- Agreement statistics
"""

from typing import List, Tuple, Optional, Dict
import math


# ============================================================
# AGREEMENT STATISTICS
# ============================================================

def cohens_kappa(
    ratings1: List[int],
    ratings2: List[int],
    categories: List[int] = None
) -> Tuple[float, float, float]:
    """
    Calculate Cohen's Kappa with 95% confidence interval.

    Args:
        ratings1: First rater's ratings
        ratings2: Second rater's ratings
        categories: List of possible category values

    Returns:
        Tuple of (kappa, ci_low, ci_high)
    """
    if len(ratings1) != len(ratings2):
        raise ValueError("Rating lists must have same length")

    n = len(ratings1)
    if n == 0:
        return (0.0, 0.0, 0.0)

    if categories is None:
        categories = sorted(set(ratings1 + ratings2))

    # Build contingency table
    k = len(categories)
    cat_to_idx = {c: i for i, c in enumerate(categories)}

    # Count agreements and marginals
    observed_agreement = sum(1 for r1, r2 in zip(ratings1, ratings2) if r1 == r2) / n

    # Marginal probabilities
    p1 = [sum(1 for r in ratings1 if r == c) / n for c in categories]
    p2 = [sum(1 for r in ratings2 if r == c) / n for c in categories]

    # Expected agreement by chance
    expected_agreement = sum(p1[i] * p2[i] for i in range(k))

    # Kappa
    if expected_agreement == 1.0:
        kappa = 1.0
    else:
        kappa = (observed_agreement - expected_agreement) / (1 - expected_agreement)

    # Standard error (Fleiss et al. formula)
    pe = expected_agreement
    po = observed_agreement

    if pe == 1.0:
        se = 0.0
    else:
        # Simplified SE calculation
        se = math.sqrt(po * (1 - po) / (n * (1 - pe) ** 2))

    # 95% CI
    z = 1.96
    ci_low = max(-1.0, kappa - z * se)
    ci_high = min(1.0, kappa + z * se)

    return (kappa, ci_low, ci_high)


def fleiss_kappa(
    ratings: List[List[int]],
    categories: List[int] = None
) -> Tuple[float, float, float]:
    """
    Calculate Fleiss' Kappa for multiple raters.

    Args:
        ratings: List of ratings per subject (each inner list is ratings from all raters)
        categories: List of possible category values

    Returns:
        Tuple of (kappa, ci_low, ci_high)
    """
    n = len(ratings)  # Number of subjects
    if n == 0:
        return (0.0, 0.0, 0.0)

    k_raters = len(ratings[0])  # Number of raters

    if categories is None:
        all_ratings = [r for subj in ratings for r in subj]
        categories = sorted(set(all_ratings))

    q = len(categories)  # Number of categories

    # Count ratings per category per subject
    counts = []
    for subj_ratings in ratings:
        cat_counts = [sum(1 for r in subj_ratings if r == c) for c in categories]
        counts.append(cat_counts)

    # Calculate P_i (agreement for each subject)
    P_i = []
    for cat_counts in counts:
        agreement = sum(c * (c - 1) for c in cat_counts) / (k_raters * (k_raters - 1)) if k_raters > 1 else 0
        P_i.append(agreement)

    P_bar = sum(P_i) / n  # Mean observed agreement

    # Category proportions
    p_j = [sum(counts[i][j] for i in range(n)) / (n * k_raters) for j in range(q)]

    # Expected agreement
    P_e = sum(p ** 2 for p in p_j)

    # Kappa
    if P_e == 1.0:
        kappa = 1.0
    else:
        kappa = (P_bar - P_e) / (1 - P_e)

    # SE (simplified)
    if P_e == 1.0:
        se = 0.0
    else:
        se = math.sqrt(2 * P_e * (1 - P_e) / (n * k_raters * (k_raters - 1) * (1 - P_e) ** 2))

    z = 1.96
    ci_low = max(-1.0, kappa - z * se)
    ci_high = min(1.0, kappa + z * se)

    return (kappa, ci_low, ci_high)


def interpret_kappa(kappa: float) -> str:
    """Interpret kappa value according to Landis & Koch (1977)."""
    if kappa < 0:
        return "Poor (less than chance)"
    elif kappa < 0.20:
        return "Slight"
    elif kappa < 0.40:
        return "Fair"
    elif kappa < 0.60:
        return "Moderate"
    elif kappa < 0.80:
        return "Substantial"
    else:
        return "Almost Perfect"


# ============================================================
# CONFIDENCE INTERVALS
# ============================================================

def clopper_pearson_ci(
    successes: int,
    trials: int,
    confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate Clopper-Pearson exact confidence interval for binomial proportion.

    Args:
        successes: Number of successes
        trials: Total number of trials
        confidence: Confidence level (default 0.95)

    Returns:
        Tuple of (ci_low, ci_high)
    """
    if trials == 0:
        return (0.0, 1.0)

    alpha = 1 - confidence

    # Use beta distribution quantiles
    # For exact CI: Beta(x, n-x+1) and Beta(x+1, n-x)
    from scipy.stats import beta

    if successes == 0:
        ci_low = 0.0
    else:
        ci_low = beta.ppf(alpha / 2, successes, trials - successes + 1)

    if successes == trials:
        ci_high = 1.0
    else:
        ci_high = beta.ppf(1 - alpha / 2, successes + 1, trials - successes)

    return (ci_low, ci_high)


def wilson_ci(
    successes: int,
    trials: int,
    confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate Wilson score confidence interval for binomial proportion.

    Args:
        successes: Number of successes
        trials: Total number of trials
        confidence: Confidence level (default 0.95)

    Returns:
        Tuple of (ci_low, ci_high)
    """
    if trials == 0:
        return (0.0, 1.0)

    from scipy.stats import norm

    z = norm.ppf(1 - (1 - confidence) / 2)
    p = successes / trials

    denominator = 1 + z ** 2 / trials

    center = (p + z ** 2 / (2 * trials)) / denominator
    spread = z * math.sqrt((p * (1 - p) + z ** 2 / (4 * trials)) / trials) / denominator

    ci_low = max(0.0, center - spread)
    ci_high = min(1.0, center + spread)

    return (ci_low, ci_high)


# ============================================================
# CI EXTRACTION METRICS
# ============================================================

def calculate_ci_extraction_metrics(
    extracted: List[Dict],
    expected: List[Dict],
    tolerance: float = 0.05
) -> Dict[str, float]:
    """
    Calculate separate metrics for CI extraction.

    Args:
        extracted: List of extracted results with ci_low, ci_high
        expected: List of expected results with ci_low, ci_high
        tolerance: Relative tolerance for matching

    Returns:
        Dict with ci_low_accuracy, ci_high_accuracy, ci_both_accuracy, ci_coverage
    """
    n_total = len(expected)
    if n_total == 0:
        return {
            'ci_low_accuracy': 0.0,
            'ci_high_accuracy': 0.0,
            'ci_both_accuracy': 0.0,
            'ci_coverage': 0.0
        }

    ci_low_correct = 0
    ci_high_correct = 0
    ci_both_correct = 0
    ci_extracted = 0

    for ext, exp in zip(extracted, expected):
        ext_ci_low = ext.get('ci_low')
        ext_ci_high = ext.get('ci_high')
        exp_ci_low = exp.get('hr_ci_low') or exp.get('or_ci_low') or exp.get('rr_ci_low') or exp.get('rd_ci_low') or exp.get('md_ci_low')
        exp_ci_high = exp.get('hr_ci_high') or exp.get('or_ci_high') or exp.get('rr_ci_high') or exp.get('rd_ci_high') or exp.get('md_ci_high')

        if ext_ci_low is not None or ext_ci_high is not None:
            ci_extracted += 1

        if exp_ci_low is not None and ext_ci_low is not None:
            if _values_match(ext_ci_low, exp_ci_low, tolerance):
                ci_low_correct += 1

        if exp_ci_high is not None and ext_ci_high is not None:
            if _values_match(ext_ci_high, exp_ci_high, tolerance):
                ci_high_correct += 1

        if (exp_ci_low is not None and exp_ci_high is not None and
            ext_ci_low is not None and ext_ci_high is not None):
            if (_values_match(ext_ci_low, exp_ci_low, tolerance) and
                _values_match(ext_ci_high, exp_ci_high, tolerance)):
                ci_both_correct += 1

    n_with_ci = sum(1 for e in expected if
                   (e.get('hr_ci_low') is not None or e.get('or_ci_low') is not None or
                    e.get('rr_ci_low') is not None or e.get('rd_ci_low') is not None or
                    e.get('md_ci_low') is not None))

    return {
        'ci_low_accuracy': ci_low_correct / n_with_ci if n_with_ci > 0 else 0.0,
        'ci_high_accuracy': ci_high_correct / n_with_ci if n_with_ci > 0 else 0.0,
        'ci_both_accuracy': ci_both_correct / n_with_ci if n_with_ci > 0 else 0.0,
        'ci_coverage': ci_extracted / n_total if n_total > 0 else 0.0
    }


def _values_match(val1: float, val2: float, tolerance: float = 0.05) -> bool:
    """Check if two values match within relative tolerance."""
    if val1 is None or val2 is None:
        return False
    if val2 == 0:
        return abs(val1) < tolerance
    return abs(val1 - val2) / abs(val2) <= tolerance


# ============================================================
# SUMMARY STATISTICS
# ============================================================

def calculate_mae(predicted: List[float], actual: List[float]) -> float:
    """Calculate Mean Absolute Error."""
    if not predicted or not actual:
        return 0.0

    n = min(len(predicted), len(actual))
    total = sum(abs(p - a) for p, a in zip(predicted[:n], actual[:n])
                if p is not None and a is not None)
    count = sum(1 for p, a in zip(predicted[:n], actual[:n])
                if p is not None and a is not None)

    return total / count if count > 0 else 0.0


def calculate_mre(predicted: List[float], actual: List[float]) -> float:
    """Calculate Mean Relative Error."""
    if not predicted or not actual:
        return 0.0

    errors = []
    for p, a in zip(predicted, actual):
        if p is not None and a is not None and a != 0:
            errors.append(abs(p - a) / abs(a))

    return sum(errors) / len(errors) if errors else 0.0


def calculate_rmse(predicted: List[float], actual: List[float]) -> float:
    """Calculate Root Mean Square Error."""
    if not predicted or not actual:
        return 0.0

    n = min(len(predicted), len(actual))
    squared_errors = [(p - a) ** 2 for p, a in zip(predicted[:n], actual[:n])
                      if p is not None and a is not None]

    if not squared_errors:
        return 0.0

    return math.sqrt(sum(squared_errors) / len(squared_errors))


# ============================================================
# ROC AND PRECISION-RECALL ANALYSIS
# ============================================================

def calculate_roc_curve(
    labels: List[int],
    scores: List[float],
    n_thresholds: int = 100
) -> Dict[str, List[float]]:
    """
    Calculate ROC curve data points.

    Args:
        labels: Binary ground truth (1=positive, 0=negative)
        scores: Continuous confidence/probability scores
        n_thresholds: Number of threshold points

    Returns:
        Dict with 'fpr', 'tpr', 'thresholds', 'auc'
    """
    if not labels or not scores or len(labels) != len(scores):
        return {'fpr': [], 'tpr': [], 'thresholds': [], 'auc': 0.0}

    # Sort by scores descending
    sorted_pairs = sorted(zip(scores, labels), key=lambda x: -x[0])
    scores_sorted = [p[0] for p in sorted_pairs]
    labels_sorted = [p[1] for p in sorted_pairs]

    n_positive = sum(labels)
    n_negative = len(labels) - n_positive

    if n_positive == 0 or n_negative == 0:
        return {'fpr': [0, 1], 'tpr': [0, 1], 'thresholds': [1, 0], 'auc': 0.5}

    # Generate thresholds
    min_score = min(scores)
    max_score = max(scores)
    thresholds = [max_score + 0.01]  # Start with all negative
    thresholds.extend([max_score - i * (max_score - min_score) / (n_thresholds - 1)
                       for i in range(n_thresholds)])
    thresholds.append(min_score - 0.01)  # End with all positive

    fpr_list = []
    tpr_list = []

    for thresh in thresholds:
        tp = sum(1 for s, l in zip(scores, labels) if s >= thresh and l == 1)
        fp = sum(1 for s, l in zip(scores, labels) if s >= thresh and l == 0)

        tpr = tp / n_positive if n_positive > 0 else 0
        fpr = fp / n_negative if n_negative > 0 else 0

        tpr_list.append(tpr)
        fpr_list.append(fpr)

    # Calculate AUC using trapezoidal rule
    auc = 0.0
    for i in range(1, len(fpr_list)):
        auc += (fpr_list[i] - fpr_list[i-1]) * (tpr_list[i] + tpr_list[i-1]) / 2

    return {
        'fpr': fpr_list,
        'tpr': tpr_list,
        'thresholds': thresholds,
        'auc': abs(auc)
    }


def calculate_precision_recall_curve(
    labels: List[int],
    scores: List[float],
    n_thresholds: int = 100
) -> Dict[str, List[float]]:
    """
    Calculate Precision-Recall curve data points.

    Args:
        labels: Binary ground truth (1=positive, 0=negative)
        scores: Continuous confidence/probability scores
        n_thresholds: Number of threshold points

    Returns:
        Dict with 'precision', 'recall', 'thresholds', 'average_precision'
    """
    if not labels or not scores or len(labels) != len(scores):
        return {'precision': [], 'recall': [], 'thresholds': [], 'average_precision': 0.0}

    n_positive = sum(labels)
    if n_positive == 0:
        return {'precision': [1], 'recall': [0], 'thresholds': [1], 'average_precision': 0.0}

    # Generate thresholds
    min_score = min(scores)
    max_score = max(scores)
    thresholds = [max_score + 0.01]
    thresholds.extend([max_score - i * (max_score - min_score) / (n_thresholds - 1)
                       for i in range(n_thresholds)])
    thresholds.append(min_score - 0.01)

    precision_list = []
    recall_list = []

    for thresh in thresholds:
        tp = sum(1 for s, l in zip(scores, labels) if s >= thresh and l == 1)
        fp = sum(1 for s, l in zip(scores, labels) if s >= thresh and l == 0)
        fn = sum(1 for s, l in zip(scores, labels) if s < thresh and l == 1)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        precision_list.append(precision)
        recall_list.append(recall)

    # Calculate Average Precision (area under PR curve)
    ap = 0.0
    for i in range(1, len(recall_list)):
        ap += (recall_list[i] - recall_list[i-1]) * precision_list[i]

    return {
        'precision': precision_list,
        'recall': recall_list,
        'thresholds': thresholds,
        'average_precision': abs(ap)
    }


def calculate_calibration_curve(
    labels: List[int],
    scores: List[float],
    n_bins: int = 10
) -> Dict[str, List[float]]:
    """
    Calculate calibration curve (reliability diagram).

    Args:
        labels: Binary ground truth (1=positive, 0=negative)
        scores: Predicted probabilities
        n_bins: Number of bins for calibration

    Returns:
        Dict with 'mean_predicted', 'fraction_positive', 'bin_counts', 'ece'
    """
    if not labels or not scores:
        return {'mean_predicted': [], 'fraction_positive': [], 'bin_counts': [], 'ece': 0.0}

    bin_edges = [i / n_bins for i in range(n_bins + 1)]
    mean_predicted = []
    fraction_positive = []
    bin_counts = []

    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i + 1]

        # Find samples in this bin
        in_bin = [(s, l) for s, l in zip(scores, labels) if low <= s < high]

        if in_bin:
            bin_scores = [s for s, l in in_bin]
            bin_labels = [l for s, l in in_bin]

            mean_predicted.append(sum(bin_scores) / len(bin_scores))
            fraction_positive.append(sum(bin_labels) / len(bin_labels))
            bin_counts.append(len(in_bin))
        else:
            mean_predicted.append((low + high) / 2)
            fraction_positive.append(0.0)
            bin_counts.append(0)

    # Calculate Expected Calibration Error (ECE)
    n_total = len(labels)
    ece = sum(count * abs(mean - frac)
              for mean, frac, count in zip(mean_predicted, fraction_positive, bin_counts)) / n_total

    return {
        'mean_predicted': mean_predicted,
        'fraction_positive': fraction_positive,
        'bin_counts': bin_counts,
        'ece': ece
    }


def interpret_auc(auc: float) -> str:
    """Interpret AUC value."""
    if auc >= 0.9:
        return "Excellent"
    elif auc >= 0.8:
        return "Good"
    elif auc >= 0.7:
        return "Fair"
    elif auc >= 0.6:
        return "Poor"
    else:
        return "Fail"


# ============================================================
# CONFIDENCE CALIBRATION
# ============================================================

# Confidence Score Weights (explicit for reproducibility)
CONFIDENCE_WEIGHTS = {
    'W1_VALUE_EXTRACTED': 0.50,      # Base score for successful extraction
    'W2_CI_EXTRACTED': 0.30,         # Both CI bounds present
    'W3_CI_VALID': 0.10,             # CI_low < CI_high (valid ordering)
    'W4_TEXT_STRUCTURE': 0.10,       # Text contains expected keywords
}


def calculate_confidence_score(
    extraction_result: Dict,
    text: str
) -> float:
    """
    Calculate confidence score for an extraction based on multiple factors.

    Formula:
        Confidence = W1*value_extracted + W2*ci_extracted + W3*ci_valid + W4*structure_score

    Where:
        W1 = 0.50 (value successfully extracted)
        W2 = 0.30 (both CI bounds extracted)
        W3 = 0.10 (CI ordering valid: low < high)
        W4 = 0.10 (text structure indicators present)

    Factors considered:
    1. Value extraction success (W1=0.50)
       - Point estimate extracted from text
    2. CI extraction success (W2=0.30)
       - Both lower and upper CI bounds present
    3. CI validity (W3=0.10)
       - Logical ordering: ci_low < ci_high
    4. Text structure clarity (W4=0.10)
       - Presence of "95%", "CI", p-value, measure keywords

    Args:
        extraction_result: Dict with extracted values (hr/or/rr/rd/md, ci_low, ci_high)
        text: Original text string

    Returns:
        Confidence score between 0.0 and 1.0

    Example:
        >>> result = {'hr': 0.74, 'ci_low': 0.65, 'ci_high': 0.85}
        >>> text = "HR 0.74 (95% CI, 0.65 to 0.85; P<0.001)"
        >>> calculate_confidence_score(result, text)
        1.0  # All factors present
    """
    if not extraction_result:
        return 0.0

    score = 0.0

    # Factor 1: Value extracted (W1 = 0.50)
    value = (extraction_result.get('hr') or extraction_result.get('or') or
             extraction_result.get('rr') or extraction_result.get('rd') or
             extraction_result.get('md'))
    if value is not None:
        score += CONFIDENCE_WEIGHTS['W1_VALUE_EXTRACTED']

    # Factor 2: CI extracted (W2 = 0.30)
    ci_low = extraction_result.get('ci_low')
    ci_high = extraction_result.get('ci_high')
    if ci_low is not None and ci_high is not None:
        score += CONFIDENCE_WEIGHTS['W2_CI_EXTRACTED']

        # Factor 3: CI validity check (W3 = 0.10)
        if ci_low < ci_high:
            score += CONFIDENCE_WEIGHTS['W3_CI_VALID']

    # Factor 4: Text structure indicators (W4 = 0.10)
    structure_indicators = [
        '95%' in text or '95 %' in text,           # CI level specified
        'CI' in text.upper(),                       # CI keyword present
        'P<' in text or 'P =' in text or 'P=' in text or 'P <' in text,  # P-value
        any(w in text.lower() for w in ['hazard', 'odds', 'relative', 'difference', 'ratio'])
    ]
    structure_score = sum(structure_indicators) / len(structure_indicators)
    score += CONFIDENCE_WEIGHTS['W4_TEXT_STRUCTURE'] * structure_score

    # Cap at 1.0
    return min(1.0, score)


def run_confidence_analysis(
    cases: List[Dict],
    extract_func
) -> Dict:
    """
    Run full confidence calibration analysis.

    Args:
        cases: List of test cases with 'text', 'expected' fields
        extract_func: Function that extracts values from text

    Returns:
        Dict with ROC, PR, and calibration results
    """
    labels = []  # 1 = correct extraction, 0 = incorrect
    scores = []  # confidence scores

    for case in cases:
        text = case.get('text', '')
        expected = case.get('expected', {})
        measure_type = expected.get('measure_type', 'HR')

        # Extract
        result = extract_func(text, measure_type)

        # Determine if correct
        expected_value = expected.get(measure_type.lower()) or expected.get('hr') or expected.get('or')
        extracted_value = None
        if result:
            extracted_value = (result.get('hr') or result.get('or') or
                             result.get('rr') or result.get('rd') or result.get('md'))

        is_correct = _values_match(extracted_value, expected_value, 0.05) if expected_value else False
        labels.append(1 if is_correct else 0)

        # Calculate confidence
        confidence = calculate_confidence_score(result or {}, text)
        scores.append(confidence)

    # Calculate curves
    roc = calculate_roc_curve(labels, scores)
    pr = calculate_precision_recall_curve(labels, scores)
    calibration = calculate_calibration_curve(labels, scores)

    return {
        'roc': roc,
        'precision_recall': pr,
        'calibration': calibration,
        'n_samples': len(cases),
        'n_correct': sum(labels),
        'accuracy': sum(labels) / len(labels) if labels else 0.0
    }
