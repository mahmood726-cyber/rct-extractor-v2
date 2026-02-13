"""
JavaScript Extractor Bridge
Calls RCTExtractor_v4_8_AI.js from Python via Node.js subprocess.

This preserves the battle-tested JavaScript extraction patterns while
integrating into the Python ensemble pipeline.
"""

from __future__ import annotations
import subprocess
import json
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Path to the JS extractor — override via environment variable
DEFAULT_JS_EXTRACTOR = os.environ.get(
    "JS_EXTRACTOR_PATH",
    str(Path(__file__).parent.parent.parent / "js" / "RCTExtractor_v4_8_AI.js")
)


class JSExtractorBridge:
    """
    Bridge to call RCTExtractor_v4_8_AI.js from Python.

    Uses Node.js subprocess to execute JavaScript extraction,
    then converts results to Python format for ensemble merging.
    """

    def __init__(self, js_extractor_path: str = None, node_path: str = "node"):
        self.js_extractor_path = js_extractor_path or DEFAULT_JS_EXTRACTOR
        self.node_path = node_path
        self._wrapper_script = None

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract effect measures from text using JS extractor.

        Args:
            text: Text to extract from

        Returns:
            Dict with extracted measures in Python format
        """
        # Create wrapper script for extraction
        wrapper = self._create_wrapper_script(text)

        try:
            # Run Node.js
            result = subprocess.run(
                [self.node_path, "-e", wrapper],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path(self.js_extractor_path).parent
            )

            if result.returncode != 0:
                logger.error(f"JS extraction failed: {result.stderr}")
                return {"error": result.stderr, "measures": {}}

            # Parse JSON output
            output = result.stdout.strip()
            if output:
                return json.loads(output)
            return {"measures": {}}

        except subprocess.TimeoutExpired:
            logger.error("JS extraction timed out")
            return {"error": "timeout", "measures": {}}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JS output: {e}")
            return {"error": str(e), "measures": {}}
        except FileNotFoundError:
            logger.error(f"Node.js not found at: {self.node_path}")
            return {"error": "node_not_found", "measures": {}}

    def _create_wrapper_script(self, text: str) -> str:
        """Create Node.js wrapper script for extraction"""
        # Escape text for JavaScript
        escaped_text = json.dumps(text)

        return f'''
const fs = require('fs');
const path = require('path');

// Load the extractor via require() only (no eval for security)
let AIStrategies;
try {{
    const extractor = require('{self.js_extractor_path.replace(chr(92), "/")}');
    AIStrategies = extractor.AIStrategies || extractor;
}} catch (e) {{
    console.error(JSON.stringify({{error: 'Failed to load JS extractor: ' + e.message, measures: {{}}}}));
    process.exit(1);
}}

const text = {escaped_text};

// Extract all effect measures
const result = {{
    hazardRatios: [],
    oddsRatios: [],
    relativeRisks: [],
    riskDifferences: [],
    meanDifferences: [],
    continuousOutcomes: [],
    subgroups: []
}};

if (typeof AIStrategies !== 'undefined' && AIStrategies.extractEffectMeasures) {{
    const measures = AIStrategies.extractEffectMeasures(text);
    result.hazardRatios = measures.hazardRatios || [];
    result.oddsRatios = measures.oddsRatios || [];
    result.relativeRisks = measures.relativeRisks || [];
    result.riskDifferences = measures.riskDifferences || [];
    result.meanDifferences = measures.meanDifferences || [];
}}

if (typeof AIStrategies !== 'undefined' && AIStrategies.extractContinuousOutcomes) {{
    result.continuousOutcomes = AIStrategies.extractContinuousOutcomes(text) || [];
}}

if (typeof AIStrategies !== 'undefined' && AIStrategies.extractSubgroupAnalyses) {{
    const sg = AIStrategies.extractSubgroupAnalyses(text);
    result.subgroups = sg.subgroups || [];
}}

console.log(JSON.stringify(result));
'''

    def extract_to_ensemble_format(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract and convert to ensemble ExtractorResult format.

        Returns:
            List of dicts compatible with ExtractorResult
        """
        from ..core.ensemble import ExtractorResult

        raw_results = self.extract(text)
        ensemble_results = []

        # Convert hazard ratios
        for hr in raw_results.get('hazardRatios', []):
            ensemble_results.append({
                'extractor_id': 'E2',
                'endpoint': self._infer_endpoint(hr.get('context', ''), 'HR'),
                'value': hr.get('value'),
                'ci_low': hr.get('ciLo'),
                'ci_high': hr.get('ciHi'),
                'measure_type': 'HR',
                'has_provenance': bool(hr.get('context')),
                'provenance_text': hr.get('context'),
                'confidence_score': 0.9 if hr.get('isPrimary') else 0.7,
                'raw_match': hr.get('raw'),
                # Meta-analysis fields from v4.8
                'se': hr.get('se'),
                'log_value': hr.get('logValue'),
                'variance': hr.get('variance'),
                'is_primary': hr.get('isPrimary', False),
                'is_secondary': hr.get('isSecondary', False),
                'direction': hr.get('direction'),
                'statistically_significant': hr.get('statisticallySignificant', False)
            })

        # Convert odds ratios
        for or_val in raw_results.get('oddsRatios', []):
            ensemble_results.append({
                'extractor_id': 'E2',
                'endpoint': self._infer_endpoint(or_val.get('context', ''), 'OR'),
                'value': or_val.get('value'),
                'ci_low': or_val.get('ciLo'),
                'ci_high': or_val.get('ciHi'),
                'measure_type': 'OR',
                'has_provenance': bool(or_val.get('context')),
                'provenance_text': or_val.get('context'),
                'confidence_score': 0.8,
                'raw_match': or_val.get('raw')
            })

        # Convert relative risks
        for rr in raw_results.get('relativeRisks', []):
            ensemble_results.append({
                'extractor_id': 'E2',
                'endpoint': self._infer_endpoint(rr.get('context', ''), 'RR'),
                'value': rr.get('value'),
                'ci_low': rr.get('ciLo'),
                'ci_high': rr.get('ciHi'),
                'measure_type': 'RR',
                'has_provenance': bool(rr.get('context')),
                'provenance_text': rr.get('context'),
                'confidence_score': 0.8,
                'raw_match': rr.get('raw')
            })

        # Convert risk differences
        for rd in raw_results.get('riskDifferences', []):
            ensemble_results.append({
                'extractor_id': 'E2',
                'endpoint': self._infer_endpoint(rd.get('context', ''), 'RD'),
                'value': rd.get('value'),
                'ci_low': rd.get('ciLo'),
                'ci_high': rd.get('ciHi'),
                'measure_type': 'RD',
                'has_provenance': bool(rd.get('context')),
                'provenance_text': rd.get('context'),
                'confidence_score': 0.8,
                'raw_match': rd.get('raw')
            })

        return ensemble_results

    def _infer_endpoint(self, context: str, measure_type: str) -> str:
        """Infer endpoint name from context"""
        context_lower = context.lower() if context else ''

        # Common endpoint patterns
        endpoint_patterns = {
            'death': 'ALL_CAUSE_DEATH',
            'mortality': 'ALL_CAUSE_DEATH',
            'cardiovascular death': 'CV_DEATH',
            'cv death': 'CV_DEATH',
            'heart failure': 'HF_HOSPITALIZATION',
            'hospitalization': 'HF_HOSPITALIZATION',
            'myocardial infarction': 'MI',
            'mi': 'MI',
            'stroke': 'STROKE',
            'mace': 'MACE_3PT',
            'composite': 'COMPOSITE',
            'primary': 'PRIMARY_OUTCOME'
        }

        for pattern, endpoint in endpoint_patterns.items():
            if pattern in context_lower:
                return endpoint

        return f"UNKNOWN_{measure_type}"


# ============================================================
# STANDALONE EXTRACTION (for testing)
# ============================================================

def extract_with_js(text: str, js_path: str = None) -> Dict[str, Any]:
    """
    Convenience function to extract with JS extractor.

    Args:
        text: Text to extract from
        js_path: Path to JS extractor (optional)

    Returns:
        Extracted measures
    """
    bridge = JSExtractorBridge(js_path)
    return bridge.extract(text)


if __name__ == "__main__":
    # Test the bridge
    test_text = """
    The hazard ratio for cardiovascular death or hospitalization for heart failure
    was 0.80 (95% confidence interval [CI], 0.73 to 0.87; P<0.001).
    For all-cause death, the hazard ratio was 0.68 (95% CI, 0.57 to 0.82).
    """

    bridge = JSExtractorBridge()
    results = bridge.extract(test_text)
    print(json.dumps(results, indent=2))
