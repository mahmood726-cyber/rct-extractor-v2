"""
Machine Learning Enhanced Extractor for RCT Extractor v2.15
============================================================

Implements ML-based extraction without LLMs:
1. Feature-based classifier for effect type detection
2. Confidence scoring from multiple signals
3. Ensemble approach combining regex + ML
4. Cross-validation checks

Dependencies:
- scikit-learn (required)
- numpy (required)
- Optional: scispacy, torch for advanced features
"""

import re
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any
from enum import Enum
import json

# Core ML - sklearn is lightweight and reliable
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import LabelEncoder
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    np = None


class EffectType(Enum):
    """Standard effect measure types"""
    HR = "HR"       # Hazard Ratio
    OR = "OR"       # Odds Ratio
    RR = "RR"       # Risk Ratio / Relative Risk
    IRR = "IRR"     # Incidence Rate Ratio
    MD = "MD"       # Mean Difference
    SMD = "SMD"     # Standardized Mean Difference
    RD = "RD"       # Risk Difference
    NNT = "NNT"     # Number Needed to Treat
    UNKNOWN = "UNKNOWN"


@dataclass
class ExtractionResult:
    """Result from ML-enhanced extraction"""
    effect_type: str
    value: float
    ci_lower: float
    ci_upper: float
    confidence: float  # 0.0 to 1.0
    source: str  # "regex", "ml", "ensemble"
    features: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# FEATURE EXTRACTION
# =============================================================================

class FeatureExtractor:
    """Extract features from clinical trial text for ML classification"""

    # Keywords associated with each effect type
    EFFECT_KEYWORDS = {
        "HR": ["hazard", "survival", "time-to-event", "cox", "kaplan", "meier",
               "death", "mortality", "event-free"],
        "OR": ["odds", "logistic", "case-control", "cross-sectional", "binary"],
        "RR": ["risk ratio", "relative risk", "cohort", "incidence", "prospective"],
        "IRR": ["incidence rate", "rate ratio", "person-years", "exposure"],
        "MD": ["mean difference", "continuous", "change from baseline", "delta"],
        "SMD": ["standardized", "hedges", "cohen", "effect size", "pooled"],
        "RD": ["risk difference", "absolute", "attributable", "ard", "arr"],
        "NNT": ["number needed", "nnt", "nnth", "nnh"],
    }

    # Context patterns for each type
    CONTEXT_PATTERNS = {
        "HR": [
            r"time.to.(?:first\s+)?event",
            r"(?:overall|progression.free|event.free)\s+survival",
            r"cox\s+(?:proportional|regression)",
            r"kaplan.meier",
            r"(?:median|mean)\s+follow.up",
        ],
        "OR": [
            r"(?:adjusted|crude|unadjusted)\s+odds",
            r"logistic\s+regression",
            r"case.control",
            r"cross.sectional",
        ],
        "RR": [
            r"relative\s+risk",
            r"risk\s+ratio",
            r"(?:prospective|retrospective)\s+cohort",
            r"incidence\s+(?:rate\s+)?ratio",
        ],
    }

    def extract_features(self, text: str) -> Dict[str, float]:
        """Extract numeric features from text for classification"""
        text_lower = text.lower()
        features = {}

        # 1. Keyword presence features
        for effect_type, keywords in self.EFFECT_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            features[f"kw_{effect_type.lower()}"] = count / len(keywords)

        # 2. Context pattern features
        for effect_type, patterns in self.CONTEXT_PATTERNS.items():
            count = sum(1 for p in patterns if re.search(p, text_lower))
            features[f"ctx_{effect_type.lower()}"] = count / max(len(patterns), 1)

        # 3. Numeric features
        numbers = re.findall(r'(\d+\.?\d*)', text)
        if numbers:
            numeric_values = [float(n) for n in numbers if float(n) < 100]
            if numeric_values:
                features["num_count"] = len(numeric_values)
                features["num_mean"] = sum(numeric_values) / len(numeric_values)
                features["num_max"] = max(numeric_values)
                features["num_min"] = min(numeric_values)
                features["num_range"] = features["num_max"] - features["num_min"]

                # Typical ranges for different effect types
                # HR/OR/RR typically 0.1-10, MD can be any range
                typical_ratio = sum(1 for v in numeric_values if 0.1 < v < 10)
                features["typical_ratio_range"] = typical_ratio / len(numeric_values)
        else:
            features["num_count"] = 0
            features["num_mean"] = 0
            features["num_max"] = 0
            features["num_min"] = 0
            features["num_range"] = 0
            features["typical_ratio_range"] = 0

        # 4. CI pattern features
        features["has_ci"] = 1 if re.search(r'(?:95%?\s*)?ci', text_lower) else 0
        features["has_pvalue"] = 1 if re.search(r'p\s*[<>=]', text_lower) else 0
        features["has_percent"] = 1 if '%' in text else 0

        # 5. Structural features
        features["has_parentheses"] = 1 if '(' in text and ')' in text else 0
        features["text_length"] = min(len(text) / 500, 1.0)  # Normalized
        features["word_count"] = len(text.split()) / 100  # Normalized

        # 6. Effect measure abbreviation presence
        features["has_hr_abbrev"] = 1 if re.search(r'\bHR\b', text) else 0
        features["has_or_abbrev"] = 1 if re.search(r'\bOR\b', text) else 0
        features["has_rr_abbrev"] = 1 if re.search(r'\bRR\b', text) else 0
        features["has_irr_abbrev"] = 1 if re.search(r'\bIRR\b', text) else 0
        features["has_md_abbrev"] = 1 if re.search(r'\bMD\b', text) else 0
        features["has_smd_abbrev"] = 1 if re.search(r'\bSMD\b', text) else 0

        return features

    def extract_feature_vector(self, text: str) -> List[float]:
        """Extract features as a vector for sklearn"""
        features = self.extract_features(text)
        # Ensure consistent ordering
        keys = sorted(features.keys())
        return [features[k] for k in keys]

    def get_feature_names(self) -> List[str]:
        """Get ordered feature names"""
        # Create a dummy extraction to get keys
        dummy_features = self.extract_features("sample text")
        return sorted(dummy_features.keys())


# =============================================================================
# ML CLASSIFIER
# =============================================================================

class EffectTypeClassifier:
    """
    ML classifier for effect measure type detection.

    Uses ensemble of multiple classifiers for robustness.
    """

    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.label_encoder = LabelEncoder() if SKLEARN_AVAILABLE else None
        self.models = {}
        self.is_trained = False

        if SKLEARN_AVAILABLE:
            # Ensemble of classifiers
            self.models = {
                "rf": RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42),
                "lr": LogisticRegression(max_iter=1000, random_state=42),
                "gb": GradientBoostingClassifier(n_estimators=50, max_depth=5, random_state=42),
            }

    def train(self, texts: List[str], labels: List[str]):
        """Train the classifier on labeled examples"""
        if not SKLEARN_AVAILABLE:
            print("Warning: sklearn not available, using rule-based fallback")
            return

        # Extract features
        X = np.array([self.feature_extractor.extract_feature_vector(t) for t in texts])

        # Encode labels
        y = self.label_encoder.fit_transform(labels)

        # Train all models
        for name, model in self.models.items():
            model.fit(X, y)

        self.is_trained = True

    def predict(self, text: str) -> Tuple[str, float]:
        """
        Predict effect type with confidence.

        Returns: (effect_type, confidence)
        """
        if not SKLEARN_AVAILABLE or not self.is_trained:
            # Fall back to rule-based
            return self._rule_based_predict(text)

        # Extract features
        X = np.array([self.feature_extractor.extract_feature_vector(text)])

        # Get predictions from all models
        predictions = {}
        probabilities = {}

        for name, model in self.models.items():
            pred = model.predict(X)[0]
            prob = model.predict_proba(X)[0]
            predictions[name] = pred
            probabilities[name] = max(prob)

        # Ensemble: majority vote with weighted confidence
        pred_counts = {}
        for pred in predictions.values():
            pred_counts[pred] = pred_counts.get(pred, 0) + 1

        majority_pred = max(pred_counts, key=pred_counts.get)
        agreement_ratio = pred_counts[majority_pred] / len(predictions)

        # Average probability of agreeing models
        agreeing_probs = [probabilities[name] for name, pred in predictions.items()
                         if pred == majority_pred]
        avg_prob = sum(agreeing_probs) / len(agreeing_probs)

        # Final confidence combines agreement and probability
        confidence = agreement_ratio * avg_prob

        effect_type = self.label_encoder.inverse_transform([majority_pred])[0]

        return effect_type, confidence

    def _rule_based_predict(self, text: str) -> Tuple[str, float]:
        """Rule-based prediction when ML is not available"""
        text_lower = text.lower()

        # Simple keyword matching with confidence
        # IMPORTANT: More specific patterns must come before less specific ones
        # e.g., SMD before MD, since "standardized mean difference" contains "mean difference"
        rules = [
            (r'\bstandardized\s+mean\s+difference\b|\bSMD\b', "SMD", 0.95),  # Before MD!
            (r'\bhazard\s+ratio\b|\bHR\b', "HR", 0.95),
            (r'\bodds\s+ratio\b|\bOR\b', "OR", 0.95),
            (r'\brisk\s+ratio\b|\brelative\s+risk\b|\bRR\b', "RR", 0.95),
            (r'\bincidence\s+rate\s+ratio\b|\bIRR\b', "IRR", 0.95),
            (r'\brisk\s+difference\b|\bRD\b', "RD", 0.90),  # Before MD (risk vs mean)
            (r'\bmean\s+difference\b|\bMD\b', "MD", 0.90),
        ]

        for pattern, effect_type, confidence in rules:
            if re.search(pattern, text, re.IGNORECASE):
                return effect_type, confidence

        return "UNKNOWN", 0.3

    def save_model(self, filepath: str):
        """Save trained model to file"""
        if not SKLEARN_AVAILABLE or not self.is_trained:
            return

        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump({
                'models': self.models,
                'label_encoder': self.label_encoder,
                'feature_names': self.feature_extractor.get_feature_names()
            }, f)

    def load_model(self, filepath: str):
        """Load trained model from file"""
        if not SKLEARN_AVAILABLE:
            return

        import pickle
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.models = data['models']
            self.label_encoder = data['label_encoder']
            self.is_trained = True


# =============================================================================
# CONFIDENCE SCORER
# =============================================================================

class ConfidenceScorer:
    """
    Score extraction confidence based on multiple signals.

    Combines:
    1. Pattern match quality
    2. Statistical plausibility
    3. Context relevance
    4. Value consistency
    """

    def __init__(self):
        self.feature_extractor = FeatureExtractor()

    def score(self, text: str, extraction: Dict) -> float:
        """
        Calculate confidence score for an extraction.

        Returns: confidence (0.0 to 1.0)
        """
        scores = []

        # 1. Pattern match quality (0.0 to 1.0)
        pattern_score = self._score_pattern_match(text, extraction)
        scores.append(("pattern", pattern_score, 0.3))

        # 2. Statistical plausibility (0.0 to 1.0)
        plausibility_score = self._score_plausibility(extraction)
        scores.append(("plausibility", plausibility_score, 0.25))

        # 3. Context relevance (0.0 to 1.0)
        context_score = self._score_context(text, extraction)
        scores.append(("context", context_score, 0.25))

        # 4. CI consistency (0.0 to 1.0)
        ci_score = self._score_ci_consistency(extraction)
        scores.append(("ci", ci_score, 0.2))

        # Weighted average
        total_weight = sum(w for _, _, w in scores)
        weighted_score = sum(s * w for _, s, w in scores) / total_weight

        return round(weighted_score, 3)

    def _score_pattern_match(self, text: str, extraction: Dict) -> float:
        """Score based on how well the extraction matches expected patterns"""
        effect_type = extraction.get('type', '')

        # Check for explicit mention of effect type
        patterns = {
            'HR': r'\b(?:hazard\s+ratio|HR)\b',
            'OR': r'\b(?:odds\s+ratio|OR)\b',
            'RR': r'\b(?:risk\s+ratio|relative\s+risk|RR)\b',
            'IRR': r'\b(?:incidence\s+rate\s+ratio|IRR)\b',
            'MD': r'\b(?:mean\s+difference|MD)\b',
            'SMD': r'\b(?:standardized\s+mean\s+difference|SMD)\b',
        }

        pattern = patterns.get(effect_type)
        if pattern and re.search(pattern, text, re.IGNORECASE):
            return 1.0
        elif effect_type in text:
            return 0.8
        else:
            return 0.5

    def _score_plausibility(self, extraction: Dict) -> float:
        """Score based on statistical plausibility of values"""
        effect_type = extraction.get('type', '')
        value = extraction.get('effect_size', 0)
        ci_lower = extraction.get('ci_lower', extraction.get('ci_low', 0))
        ci_upper = extraction.get('ci_upper', extraction.get('ci_high', 0))

        # Define plausible ranges by effect type
        # Typical clinical trial values - ranges are tighter than theoretical
        ranges = {
            'HR': (0.05, 10),    # Typical HR 0.3-3.0, extreme 0.05-10
            'OR': (0.05, 50),    # Typical OR 0.1-10, extreme 0.05-50
            'RR': (0.05, 20),    # Typical RR 0.2-5.0, extreme 0.05-20
            'IRR': (0.05, 50),   # Similar to OR
            'MD': (-500, 500),   # Depends on outcome scale
            'SMD': (-3, 3),      # Typical |SMD| < 2
            'RD': (-50, 50),     # Percentage points
        }

        min_val, max_val = ranges.get(effect_type, (0, 100))

        # Check if value is in plausible range
        if min_val <= value <= max_val:
            value_score = 1.0
        else:
            # Steeper penalty for extreme values
            if value < min_val:
                distance = abs(value - min_val)
                value_score = max(0, 1 - (distance / abs(min_val)) ** 0.5)
            else:
                distance = abs(value - max_val)
                # For very extreme values (10x outside range), score is 0
                value_score = max(0, 1 - (distance / max_val))

        return value_score

    def _score_context(self, text: str, extraction: Dict) -> float:
        """Score based on context keywords"""
        effect_type = extraction.get('type', '')
        features = self.feature_extractor.extract_features(text)

        # Get keyword score for the detected type
        keyword_key = f"kw_{effect_type.lower()}"
        context_key = f"ctx_{effect_type.lower()}"

        keyword_score = features.get(keyword_key, 0)
        context_score = features.get(context_key, 0)

        return (keyword_score + context_score) / 2 + 0.5  # Base of 0.5

    def _score_ci_consistency(self, extraction: Dict) -> float:
        """Score based on CI consistency"""
        value = extraction.get('effect_size', 0)
        ci_lower = extraction.get('ci_lower', extraction.get('ci_low', 0))
        ci_upper = extraction.get('ci_upper', extraction.get('ci_high', 0))

        # Check CI contains point estimate (CRITICAL - should be weighted heavily)
        if ci_lower < value < ci_upper:
            containment_score = 1.0
        elif ci_lower <= value <= ci_upper:
            containment_score = 0.8  # Edge case - on boundary
        else:
            containment_score = 0.0  # Major issue

        # Check CI order
        if ci_lower < ci_upper:
            order_score = 1.0
        else:
            order_score = 0.0

        # Check CI width is reasonable
        if ci_upper > 0 and ci_lower > 0:
            ci_ratio = ci_upper / ci_lower
            if 1.05 < ci_ratio < 20:
                width_score = 1.0
            elif 1.01 < ci_ratio < 50:
                width_score = 0.7
            else:
                width_score = 0.3
        else:
            width_score = 0.6

        # Weighted average - containment is most important
        # If estimate not in CI, max score is 0.45
        return containment_score * 0.6 + order_score * 0.25 + width_score * 0.15


# =============================================================================
# ENSEMBLE EXTRACTOR
# =============================================================================

class EnsembleExtractor:
    """
    Ensemble extractor combining regex and ML approaches.

    Strategy:
    1. Run regex extraction first (fast, high precision)
    2. Apply ML classifier for type validation
    3. Calculate confidence scores
    4. Flag low-confidence extractions for review
    """

    def __init__(self):
        self.classifier = EffectTypeClassifier()
        self.confidence_scorer = ConfidenceScorer()
        self.feature_extractor = FeatureExtractor()

    def extract(self, text: str, regex_results: List[Dict]) -> List[ExtractionResult]:
        """
        Enhance regex results with ML confidence scoring.

        Args:
            text: Original text
            regex_results: Results from regex extractor

        Returns:
            List of ExtractionResult with confidence scores
        """
        enhanced_results = []

        for result in regex_results:
            # Calculate confidence
            confidence = self.confidence_scorer.score(text, result)

            # If classifier is trained, validate type
            if self.classifier.is_trained:
                ml_type, ml_confidence = self.classifier.predict(text)

                # If ML disagrees with regex, lower confidence
                if ml_type != result.get('type') and ml_confidence > 0.8:
                    confidence *= 0.7
                    result['ml_suggested_type'] = ml_type

            # Extract features for debugging
            features = self.feature_extractor.extract_features(text)

            enhanced_results.append(ExtractionResult(
                effect_type=result.get('type', 'UNKNOWN'),
                value=result.get('effect_size', 0),
                ci_lower=result.get('ci_lower', result.get('ci_low', 0)),
                ci_upper=result.get('ci_upper', result.get('ci_high', 0)),
                confidence=confidence,
                source="ensemble",
                features=features
            ))

        return enhanced_results

    def train_classifier(self, training_data: List[Tuple[str, str]]):
        """
        Train the ML classifier on labeled data.

        Args:
            training_data: List of (text, effect_type) tuples
        """
        texts, labels = zip(*training_data)
        self.classifier.train(list(texts), list(labels))


# =============================================================================
# CROSS-PAPER VALIDATOR
# =============================================================================

@dataclass
class TrialExtraction:
    """Extraction from a single trial/paper"""
    trial_id: str  # NCT number or name
    source: str    # Paper DOI or file path
    extractions: List[ExtractionResult]


class CrossPaperValidator:
    """
    Validate extractions across multiple papers reporting the same trial.

    Detects:
    1. Duplicate extractions
    2. Conflicting values for same endpoint
    3. Inconsistent reporting
    """

    def __init__(self):
        self.extractions_by_trial: Dict[str, List[TrialExtraction]] = {}

    def add_extraction(self, trial_id: str, source: str, extractions: List[ExtractionResult]):
        """Add extraction from a paper"""
        if trial_id not in self.extractions_by_trial:
            self.extractions_by_trial[trial_id] = []

        self.extractions_by_trial[trial_id].append(TrialExtraction(
            trial_id=trial_id,
            source=source,
            extractions=extractions
        ))

    def validate(self) -> Dict[str, List[Dict]]:
        """
        Validate all extractions for consistency.

        Returns dict of trial_id -> list of issues
        """
        issues = {}

        for trial_id, extractions_list in self.extractions_by_trial.items():
            trial_issues = []

            if len(extractions_list) < 2:
                continue

            # Compare all pairs of extractions
            for i, ext1 in enumerate(extractions_list):
                for ext2 in extractions_list[i+1:]:
                    pair_issues = self._compare_extractions(ext1, ext2)
                    trial_issues.extend(pair_issues)

            if trial_issues:
                issues[trial_id] = trial_issues

        return issues

    def _compare_extractions(self, ext1: TrialExtraction,
                            ext2: TrialExtraction) -> List[Dict]:
        """Compare two extractions from different sources"""
        issues = []

        # Group by effect type
        for e1 in ext1.extractions:
            for e2 in ext2.extractions:
                if e1.effect_type == e2.effect_type:
                    # Check if values match (within tolerance)
                    value_diff = abs(e1.value - e2.value)
                    relative_diff = value_diff / max(e1.value, e2.value, 0.01)

                    if relative_diff > 0.05:  # More than 5% difference
                        issues.append({
                            'type': 'VALUE_MISMATCH',
                            'effect_type': e1.effect_type,
                            'source1': ext1.source,
                            'value1': e1.value,
                            'source2': ext2.source,
                            'value2': e2.value,
                            'difference': f"{relative_diff*100:.1f}%"
                        })

                    # Check CI overlap
                    ci_overlap = self._ci_overlap(
                        (e1.ci_lower, e1.ci_upper),
                        (e2.ci_lower, e2.ci_upper)
                    )

                    if not ci_overlap:
                        issues.append({
                            'type': 'CI_NO_OVERLAP',
                            'effect_type': e1.effect_type,
                            'source1': ext1.source,
                            'ci1': f"({e1.ci_lower}-{e1.ci_upper})",
                            'source2': ext2.source,
                            'ci2': f"({e2.ci_lower}-{e2.ci_upper})"
                        })

        return issues

    def _ci_overlap(self, ci1: Tuple[float, float], ci2: Tuple[float, float]) -> bool:
        """Check if two confidence intervals overlap"""
        return not (ci1[1] < ci2[0] or ci2[1] < ci1[0])


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_training_data_from_gold_standard():
    """Create training data from gold standard trials plus synthetic balanced examples"""
    training_data = []

    # First, try to load gold standard
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'data'))
        from pdf_gold_standard import ALL_GOLD_STANDARD_TRIALS

        for trial in ALL_GOLD_STANDARD_TRIALS:
            for effect in trial.expected_effects:
                # Create sample text
                text = f"{effect.effect_type} {effect.value} (95% CI {effect.ci_lower}-{effect.ci_upper})"
                training_data.append((text, effect.effect_type))
    except ImportError:
        pass

    # Add synthetic balanced training data for each effect type
    # This ensures the classifier sees diverse examples of each type
    synthetic_data = [
        # HR examples
        ("HR 0.75 (95% CI 0.63-0.89)", "HR"),
        ("hazard ratio 0.82 (0.71-0.95)", "HR"),
        ("The hazard ratio for death was 0.65 (95% CI 0.52-0.81)", "HR"),
        ("Cox regression HR 1.25 (1.08-1.45), p=0.003", "HR"),
        ("survival analysis showed HR 0.58 (0.44-0.76)", "HR"),
        ("time-to-event HR 0.91 (0.84-0.99)", "HR"),
        ("overall survival hazard ratio 0.72 (0.60-0.86)", "HR"),
        ("progression-free survival HR 0.56 (0.45-0.70)", "HR"),

        # OR examples
        ("OR 2.3 (95% CI 1.5-3.4)", "OR"),
        ("odds ratio 1.85 (1.42-2.41)", "OR"),
        ("The adjusted odds ratio was 0.65 (95% CI 0.48-0.88)", "OR"),
        ("logistic regression OR 3.12 (2.15-4.52)", "OR"),
        ("case-control study OR 2.8 (1.9-4.1)", "OR"),
        ("cross-sectional odds ratio 1.45 (1.12-1.88)", "OR"),
        ("multivariate OR 0.72 (0.58-0.89)", "OR"),
        ("binary outcome OR 1.95 (1.35-2.82)", "OR"),

        # RR examples
        ("RR 1.45 (95% CI 1.12-1.88)", "RR"),
        ("relative risk 0.65 (0.52-0.81)", "RR"),
        ("The risk ratio was 1.28 (95% CI 1.05-1.56)", "RR"),
        ("cohort study RR 0.78 (0.65-0.94)", "RR"),
        ("incidence ratio RR 1.52 (1.18-1.96)", "RR"),
        ("prospective relative risk 0.85 (0.72-1.00)", "RR"),
        ("risk ratio for events RR 1.15 (0.98-1.35)", "RR"),
        ("adjusted RR 0.92 (0.84-1.01)", "RR"),

        # IRR examples
        ("IRR 1.8 (95% CI 1.4-2.3)", "IRR"),
        ("incidence rate ratio 0.72 (0.58-0.89)", "IRR"),
        ("The IRR was 1.45 (95% CI 1.12-1.88)", "IRR"),
        ("per 1000 person-years IRR 0.65 (0.48-0.88)", "IRR"),
        ("rate ratio IRR 2.1 (1.6-2.8)", "IRR"),
        ("exposure IRR 1.35 (1.08-1.69)", "IRR"),

        # MD examples
        ("MD -3.5 (95% CI -5.2 to -1.8)", "MD"),
        ("mean difference 2.4 (0.8-4.0)", "MD"),
        ("The MD was -5.2 mmHg (95% CI -7.1 to -3.3)", "MD"),
        ("change from baseline MD 1.8 (0.5-3.1)", "MD"),
        ("continuous outcome mean difference -2.1 (-3.8 to -0.4)", "MD"),
        ("delta MD 4.5 (2.1-6.9)", "MD"),
        ("weighted mean difference MD -1.2 (-2.5 to 0.1)", "MD"),
        ("pooled MD 3.2 (1.5-4.9)", "MD"),

        # SMD examples
        ("SMD 0.35 (95% CI 0.12-0.58)", "SMD"),
        ("standardized mean difference -0.42 (-0.68 to -0.16)", "SMD"),
        ("The SMD was 0.28 (95% CI 0.05-0.51)", "SMD"),
        ("Hedges g SMD 0.55 (0.28-0.82)", "SMD"),
        ("Cohen d effect size SMD -0.32 (-0.58 to -0.06)", "SMD"),
        ("pooled SMD 0.18 (-0.05 to 0.41)", "SMD"),
        ("standardized effect SMD 0.65 (0.38-0.92)", "SMD"),
        ("effect size SMD -0.25 (-0.48 to -0.02)", "SMD"),

        # RD examples
        ("RD -5.2% (95% CI -8.1 to -2.3)", "RD"),
        ("risk difference 3.8% (1.2-6.4)", "RD"),
        ("absolute risk difference RD -2.5% (-4.8 to -0.2)", "RD"),
        ("ARD -4.1% (95% CI -6.5 to -1.7)", "RD"),
        ("attributable risk RD 5.2% (2.1-8.3)", "RD"),
    ]

    training_data.extend(synthetic_data)

    return training_data


def train_default_classifier() -> EffectTypeClassifier:
    """Train classifier on gold standard data"""
    classifier = EffectTypeClassifier()
    training_data = create_training_data_from_gold_standard()

    if training_data:
        texts, labels = zip(*training_data)
        classifier.train(list(texts), list(labels))

    return classifier
