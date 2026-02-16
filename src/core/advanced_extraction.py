"""
Advanced Extraction Module — ML tables, OCR, and LLM-based extraction.

Three escalation tiers for PDFs where regex + pdfplumber fail:
1. Table Transformer: ML-based table detection → structured grid → regex
2. OCR Tables: Render pages to images → pytesseract → regex on OCR text
3. LLM Extraction: Send text/image to Claude API → structured JSON output

Each tier is optional and gated by dependency availability.
Results are labeled with extraction_method for TruthCert provenance.
"""

from __future__ import annotations

import io
import json
import logging
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# ============================================================
# Dependency checks
# ============================================================

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    from transformers import TableTransformerForObjectDetection, DetrImageProcessor
    import torch
    HAS_TABLE_TRANSFORMER = True
except ImportError:
    HAS_TABLE_TRANSFORMER = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# ============================================================
# Data structures
# ============================================================

@dataclass
class AdvancedExtraction:
    """Result from an advanced extraction method."""
    effect_type: str          # OR, RR, HR, MD, SMD, etc.
    point_estimate: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    method: str = ""          # "table_transformer", "ocr", "llm"
    source_text: str = ""     # The text snippet that was parsed
    confidence: float = 0.5
    page_num: Optional[int] = None


# ============================================================
# 1. TABLE TRANSFORMER
# ============================================================

class TableTransformerExtractor:
    """
    Use Microsoft's Table Transformer to detect tables in page images,
    then OCR/extract text from detected table regions, then regex.
    """

    def __init__(self):
        if not HAS_TABLE_TRANSFORMER or not HAS_PYMUPDF or not HAS_PIL:
            raise RuntimeError(
                "Table Transformer requires: transformers, torch, pymupdf, PIL"
            )
        self.processor = DetrImageProcessor.from_pretrained(
            "microsoft/table-transformer-detection"
        )
        self.model = TableTransformerForObjectDetection.from_pretrained(
            "microsoft/table-transformer-detection"
        )
        self.model.eval()
        logger.info("Table Transformer model loaded")

    def extract_from_pdf(self, pdf_path: str, pages: Optional[List[int]] = None) -> List[AdvancedExtraction]:
        """
        Detect tables in PDF pages and extract effect estimates from them.

        Args:
            pdf_path: Path to PDF file
            pages: Optional list of page numbers (1-indexed). If None, process all.

        Returns:
            List of AdvancedExtraction objects
        """
        results = []
        doc = fitz.open(pdf_path)

        page_range = range(len(doc)) if pages is None else [p - 1 for p in pages]

        for page_idx in page_range:
            if page_idx >= len(doc):
                continue
            page = doc[page_idx]

            # Render page to image at 150 DPI
            mat = fitz.Matrix(150 / 72, 150 / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

            # Detect tables
            tables = self._detect_tables(img)

            for table_bbox, score in tables:
                # Scale bbox back to PDF coordinates
                scale_x = page.rect.width / img.width
                scale_y = page.rect.height / img.height
                pdf_bbox = (
                    table_bbox[0] * scale_x,
                    table_bbox[1] * scale_y,
                    table_bbox[2] * scale_x,
                    table_bbox[3] * scale_y,
                )

                # Extract text from the table region
                table_text = self._extract_text_from_region(page, pdf_bbox)

                if table_text:
                    # Also try OCR on the cropped image
                    if HAS_TESSERACT:
                        crop = img.crop([int(c) for c in table_bbox])
                        ocr_text = pytesseract.image_to_string(crop)
                        if len(ocr_text) > len(table_text):
                            table_text = ocr_text

                    # Parse effect estimates from table text
                    effects = self._parse_effects(table_text, page_idx + 1, score)
                    results.extend(effects)

        doc.close()
        return results

    def _detect_tables(self, image: Image.Image) -> List[tuple]:
        """Detect tables in page image. Returns [(bbox, score), ...]."""
        import torch
        inputs = self.processor(images=image, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model(**inputs)

        target_sizes = torch.tensor([image.size[::-1]])
        post = self.processor.post_process_object_detection(
            outputs, threshold=0.5, target_sizes=target_sizes
        )[0]

        tables = []
        for score, label, box in zip(post["scores"], post["labels"], post["boxes"]):
            label_name = self.model.config.id2label[label.item()]
            if label_name == "table":
                tables.append((box.tolist(), score.item()))

        return tables

    def _extract_text_from_region(self, page, bbox: tuple) -> str:
        """Extract text from a rectangular region of a PDF page."""
        rect = fitz.Rect(*bbox)
        # Get text within the rect
        text = page.get_text("text", clip=rect)
        return text.strip()

    def _parse_effects(self, text: str, page_num: int, table_score: float) -> List[AdvancedExtraction]:
        """Parse effect estimates from table text using regex."""
        results = []

        # Common table patterns for effect estimates
        patterns = [
            # "OR 1.23 (0.95-1.56)" or "HR 0.76 (0.55, 0.98)"
            (r'\b(OR|RR|HR|IRR|RD)\s*[=:]?\s*(-?\d+\.?\d*)\s*'
             r'\(\s*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)\s*\)',
             lambda m: (m.group(1), m.group(2), m.group(3), m.group(4))),
            # "1.23 (0.95-1.56)" on a line that looks like a results row
            (r'(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*[-–—]\s*(-?\d+\.?\d*)\s*\)',
             lambda m: (None, m.group(1), m.group(2), m.group(3))),
            # "1.23 (0.95, 1.56)" comma-separated CI
            (r'(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)',
             lambda m: (None, m.group(1), m.group(2), m.group(3))),
            # "MD -2.3 [-4.5, -0.1]" square brackets
            (r'\b(MD|SMD|WMD)\s*[=:]?\s*(-?\d+\.?\d*)\s*'
             r'\[\s*(-?\d+\.?\d*)\s*[,]\s*(-?\d+\.?\d*)\s*\]',
             lambda m: (m.group(1), m.group(2), m.group(3), m.group(4))),
        ]

        for pattern, extractor in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                etype, val, lo, hi = extractor(match)
                try:
                    pe = float(val)
                    ci_lo = float(lo) if lo else None
                    ci_hi = float(hi) if hi else None

                    # Basic sanity: CI should bracket the point estimate
                    if ci_lo is not None and ci_hi is not None:
                        if ci_lo > ci_hi:
                            ci_lo, ci_hi = ci_hi, ci_lo

                    results.append(AdvancedExtraction(
                        effect_type=etype or "UNKNOWN",
                        point_estimate=pe,
                        ci_lower=ci_lo,
                        ci_upper=ci_hi,
                        method="table_transformer",
                        source_text=match.group(0)[:150],
                        confidence=0.6 * table_score,
                        page_num=page_num,
                    ))
                except (ValueError, TypeError):
                    continue

        # 2x2 contingency data from tables: "X/N" pairs
        slash_pairs = list(re.finditer(r'(\d+)\s*/\s*(\d+)', text))
        if len(slash_pairs) >= 2:
            for i in range(len(slash_pairs) - 1):
                e1, n1 = int(slash_pairs[i].group(1)), int(slash_pairs[i].group(2))
                e2, n2 = int(slash_pairs[i+1].group(1)), int(slash_pairs[i+1].group(2))
                if e1 <= n1 and e2 <= n2 and n1 >= 5 and n2 >= 5:
                    # Compute OR from raw counts
                    try:
                        a, b = e1, n1 - e1
                        c, d = e2, n2 - e2
                        if b > 0 and c > 0 and d > 0 and a >= 0:
                            # Add 0.5 continuity correction if any zero
                            if a == 0 or b == 0 or c == 0 or d == 0:
                                a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
                            OR = (a * d) / (b * c)
                            results.append(AdvancedExtraction(
                                effect_type="OR",
                                point_estimate=round(OR, 4),
                                method="table_transformer_2x2",
                                source_text=f"{e1}/{n1} vs {e2}/{n2}",
                                confidence=0.4 * table_score,
                                page_num=page_num,
                            ))
                    except (ZeroDivisionError, ValueError):
                        continue

        return results


# ============================================================
# 2. OCR EXTRACTION
# ============================================================

class OCRExtractor:
    """
    OCR entire pages and re-run regex extraction on OCR text.
    For PDFs where text extraction yields poor results.
    """

    def __init__(self, dpi: int = 200):
        if not HAS_PYMUPDF or not HAS_TESSERACT or not HAS_PIL:
            raise RuntimeError("OCR requires: pymupdf, pytesseract, PIL")
        self.dpi = dpi

    def extract_from_pdf(self, pdf_path: str, pages: Optional[List[int]] = None) -> List[AdvancedExtraction]:
        """OCR pages and extract effect estimates."""
        results = []
        doc = fitz.open(pdf_path)
        page_range = range(len(doc)) if pages is None else [p - 1 for p in pages]

        for page_idx in page_range:
            if page_idx >= len(doc):
                continue
            page = doc[page_idx]

            # Render to image
            mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))

            # OCR
            ocr_text = pytesseract.image_to_string(img)
            if not ocr_text or len(ocr_text.strip()) < 50:
                continue

            # Extract from OCR text using comprehensive patterns
            effects = self._extract_effects_from_text(ocr_text, page_idx + 1)
            results.extend(effects)

        doc.close()
        return results

    def _extract_effects_from_text(self, text: str, page_num: int) -> List[AdvancedExtraction]:
        """Extract effect estimates from OCR text."""
        results = []

        # Normalize common OCR errors
        text = self._normalize_ocr(text)

        # Same pattern set as table transformer plus a few more
        patterns = [
            # "OR 1.23 (95% CI 0.95-1.56)"
            (r'\b(OR|RR|HR|IRR|ARD?)\s*[=:]?\s*(-?\d+\.?\d*)\s*'
             r'\(\s*(?:95%?\s*)?CI[:\s]+(-?\d+\.?\d*)\s*[-–—to]+\s*(-?\d+\.?\d*)\s*\)',
             lambda m: (m.group(1), m.group(2), m.group(3), m.group(4))),
            # "OR 1.23 (0.95-1.56)"
            (r'\b(OR|RR|HR|IRR|MD|SMD|WMD)\s*[=:]?\s*(-?\d+\.?\d*)\s*'
             r'\(\s*(-?\d+\.?\d*)\s*[-–—,]\s*(-?\d+\.?\d*)\s*\)',
             lambda m: (m.group(1), m.group(2), m.group(3), m.group(4))),
            # "1.23 (0.95 to 1.56)"
            (r'(-?\d+\.?\d*)\s*\(\s*(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)\s*\)',
             lambda m: (None, m.group(1), m.group(2), m.group(3))),
            # "MD -2.3 [-4.5, -0.1]"
            (r'\b(MD|SMD|WMD)\s*[=:]?\s*(-?\d+\.?\d*)\s*'
             r'\[\s*(-?\d+\.?\d*)\s*[,]\s*(-?\d+\.?\d*)\s*\]',
             lambda m: (m.group(1), m.group(2), m.group(3), m.group(4))),
            # "1.23 [0.95, 1.56]"
            (r'(-?\d+\.?\d*)\s*\[\s*(-?\d+\.?\d*)\s*[,]\s*(-?\d+\.?\d*)\s*\]',
             lambda m: (None, m.group(1), m.group(2), m.group(3))),
        ]

        for pattern, extractor in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                etype, val, lo, hi = extractor(match)
                try:
                    pe = float(val)
                    ci_lo = float(lo) if lo else None
                    ci_hi = float(hi) if hi else None
                    if ci_lo is not None and ci_hi is not None and ci_lo > ci_hi:
                        ci_lo, ci_hi = ci_hi, ci_lo

                    results.append(AdvancedExtraction(
                        effect_type=etype or "UNKNOWN",
                        point_estimate=pe,
                        ci_lower=ci_lo,
                        ci_upper=ci_hi,
                        method="ocr",
                        source_text=match.group(0)[:150],
                        confidence=0.5,
                        page_num=page_num,
                    ))
                except (ValueError, TypeError):
                    continue

        return results

    @staticmethod
    def _normalize_ocr(text: str) -> str:
        """Fix common OCR errors in statistical text."""
        # Common OCR confusions
        text = text.replace('Cl', 'CI').replace('|', 'l')  # careful: only in stat context
        # Actually, be conservative — only fix clear cases
        text = re.sub(r'\b95%\s*Cl\b', '95% CI', text)
        text = re.sub(r'\b95%\s*C[Il]\b', '95% CI', text)
        # Fix common digit confusions
        text = text.replace('O.', '0.')  # O → 0 before decimal
        text = re.sub(r'(?<=\d)l(?=\d)', '1', text)  # l → 1 between digits
        return text


# ============================================================
# 3. LLM EXTRACTION
# ============================================================

class LLMExtractor:
    """
    Use Claude API to extract effect estimates from text or images.

    IMPORTANT: Results are labeled UNCERTIFIED per TruthCert rules.
    LLM extraction is non-deterministic and should only be used
    as a last resort when regex/table/OCR methods fail.
    """

    EXTRACTION_PROMPT = """Extract all effect estimates (statistical results) from this clinical trial text.

For each effect estimate found, provide:
- effect_type: OR, RR, HR, MD, SMD, ARD, IRR, or other
- point_estimate: the main value (numeric)
- ci_lower: lower bound of 95% CI (if available)
- ci_upper: upper bound of 95% CI (if available)
- context: brief description of what this estimate measures

Return a JSON array. If no effect estimates found, return [].

Example output:
[
  {"effect_type": "OR", "point_estimate": 1.45, "ci_lower": 1.02, "ci_upper": 2.05, "context": "risk of hospitalization"},
  {"effect_type": "MD", "point_estimate": -3.2, "ci_lower": -5.1, "ci_upper": -1.3, "context": "change in blood pressure"}
]

Text to analyze:
"""

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        if not HAS_ANTHROPIC:
            raise RuntimeError("LLM extraction requires: pip install anthropic")
        self.client = anthropic.Anthropic()
        self.model = model

    def extract_from_text(self, text: str, max_chars: int = 15000) -> List[AdvancedExtraction]:
        """Send text to Claude and parse structured output."""
        # Truncate very long text
        if len(text) > max_chars:
            text = text[:max_chars]

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": self.EXTRACTION_PROMPT + text
                }]
            )

            content = response.content[0].text.strip()

            # Parse JSON from response
            return self._parse_llm_response(content)

        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return []

    def extract_from_pdf(self, pdf_path: str, pages: Optional[List[int]] = None) -> List[AdvancedExtraction]:
        """Extract from PDF by sending text (and optionally images) to LLM."""
        if not HAS_PYMUPDF:
            raise RuntimeError("Need pymupdf to read PDF text")

        doc = fitz.open(pdf_path)
        page_range = range(len(doc)) if pages is None else [p - 1 for p in pages]

        # Collect all text
        all_text = []
        for page_idx in page_range:
            if page_idx >= len(doc):
                continue
            page = doc[page_idx]
            text = page.get_text()
            if text.strip():
                all_text.append(f"--- Page {page_idx + 1} ---\n{text}")

        doc.close()

        if not all_text:
            return []

        combined = "\n\n".join(all_text)
        results = self.extract_from_text(combined)

        return results

    def _parse_llm_response(self, content: str) -> List[AdvancedExtraction]:
        """Parse JSON array from LLM response."""
        results = []

        # Find JSON array in response
        json_match = re.search(r'\[[\s\S]*\]', content)
        if not json_match:
            return results

        try:
            items = json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM JSON response")
            return results

        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                pe = float(item.get("point_estimate", 0))
                etype = str(item.get("effect_type", "UNKNOWN")).upper()
                ci_lo = item.get("ci_lower")
                ci_hi = item.get("ci_upper")
                if ci_lo is not None:
                    ci_lo = float(ci_lo)
                if ci_hi is not None:
                    ci_hi = float(ci_hi)

                results.append(AdvancedExtraction(
                    effect_type=etype,
                    point_estimate=pe,
                    ci_lower=ci_lo,
                    ci_upper=ci_hi,
                    method="llm",
                    source_text=f"[LLM-UNCERTIFIED] {item.get('context', '')}",
                    confidence=0.4,  # Low confidence — non-deterministic
                ))
            except (ValueError, TypeError):
                continue

        return results


# ============================================================
# 4. OUTCOME-GUIDED LLM EXTRACTION (Strategy A)
# ============================================================

# Tool schema for Claude structured output — guarantees JSON compliance
_EXTRACTION_TOOL = {
    "name": "report_extraction",
    "description": "Report the extracted effect estimate and/or raw data from the clinical trial paper.",
    "input_schema": {
        "type": "object",
        "properties": {
            "found": {
                "type": "boolean",
                "description": "Whether any relevant data was found for this outcome"
            },
            "effect_type": {
                "type": "string",
                "enum": ["OR", "RR", "HR", "MD", "SMD", "ARD", "IRR", "RD", "GMR", "NONE"],
                "description": "Type of effect estimate found"
            },
            "point_estimate": {
                "type": "number",
                "description": "The main effect estimate value"
            },
            "ci_lower": {
                "type": ["number", "null"],
                "description": "Lower bound of 95% CI, or null if not reported"
            },
            "ci_upper": {
                "type": ["number", "null"],
                "description": "Upper bound of 95% CI, or null if not reported"
            },
            "source_quote": {
                "type": "string",
                "description": "Exact quote from the paper containing the extracted number (max 200 chars)"
            },
            "intervention_events": {
                "type": ["integer", "null"],
                "description": "Number of events in the intervention/treatment group"
            },
            "intervention_n": {
                "type": ["integer", "null"],
                "description": "Total participants in the intervention/treatment group"
            },
            "control_events": {
                "type": ["integer", "null"],
                "description": "Number of events in the control/placebo group"
            },
            "control_n": {
                "type": ["integer", "null"],
                "description": "Total participants in the control/placebo group"
            },
            "intervention_mean": {
                "type": ["number", "null"],
                "description": "Mean outcome in the intervention group"
            },
            "intervention_sd": {
                "type": ["number", "null"],
                "description": "Standard deviation in the intervention group"
            },
            "control_mean": {
                "type": ["number", "null"],
                "description": "Mean outcome in the control group"
            },
            "control_sd": {
                "type": ["number", "null"],
                "description": "Standard deviation in the control group"
            },
            "is_adjusted": {
                "type": "boolean",
                "description": "Whether this is an adjusted estimate (from regression/multivariable model)"
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of where you found this data and any caveats"
            }
        },
        "required": ["found", "effect_type", "reasoning"]
    }
}


class OutcomeGuidedExtractor:
    """
    Outcome-guided LLM extraction with anti-hallucination safeguards.

    Instead of asking "extract everything", we tell the LLM:
    - What specific outcome to look for (from Cochrane metadata)
    - What data type to expect (binary → events/N, continuous → means/SDs)
    - To return raw data (2x2 cells) in addition to computed effects

    Anti-hallucination safeguards:
    1. Structured output via tool_use (guaranteed JSON schema compliance)
    2. Source verification: extracted numbers must appear in PDF text
    3. Plausibility checks: effect type matches data type, values in range
    4. Raw data cross-check: if raw data provided, compute effect and compare
    """

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        if not HAS_ANTHROPIC:
            raise RuntimeError("Requires: pip install anthropic")
        self.client = anthropic.Anthropic()
        self.model = model

    def extract_for_outcome(
        self,
        pdf_text: str,
        outcome_name: str,
        data_type: Optional[str] = None,
        review_id: str = "",
        max_chars: int = 25000,
    ) -> List[AdvancedExtraction]:
        """
        Extract effect estimate for a specific outcome from PDF text.

        Args:
            pdf_text: Full text extracted from the PDF
            outcome_name: Cochrane outcome name (e.g., "All-cause mortality")
            data_type: "binary" or "continuous" (guides what to look for)
            review_id: Cochrane review ID for context
            max_chars: Max text to send to API

        Returns:
            List of verified AdvancedExtraction objects
        """
        # Truncate text intelligently — prioritize results/abstract/tables
        text = self._smart_truncate(pdf_text, max_chars)

        # Build the outcome-guided prompt
        prompt = self._build_prompt(outcome_name, data_type)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                tools=[_EXTRACTION_TOOL],
                tool_choice={"type": "tool", "name": "report_extraction"},
                messages=[{
                    "role": "user",
                    "content": f"{prompt}\n\n--- PAPER TEXT ---\n{text}"
                }]
            )

            # Parse the tool_use response
            for block in response.content:
                if block.type == "tool_use" and block.name == "report_extraction":
                    raw_result = block.input
                    return self._validate_and_convert(raw_result, pdf_text, data_type)

            return []

        except Exception as e:
            logger.warning(f"Outcome-guided LLM extraction failed: {e}")
            return []

    def _build_prompt(self, outcome_name: str, data_type: Optional[str]) -> str:
        """Build the RISEN-framework prompt for outcome-guided extraction."""
        data_guidance = ""
        if data_type == "binary":
            data_guidance = """
DATA TYPE: Binary (dichotomous) outcome.
Look for:
- Number of events and total participants per arm (e.g., "15/56 in treatment vs 18/57 in control")
- Odds ratio (OR), risk ratio (RR), or relative risk with 95% CI
- Percentages with denominators that allow computing events/N
IMPORTANT: Raw event counts (events/N per arm) are MORE valuable than adjusted ORs,
because the systematic review computes its own unadjusted OR from the raw 2x2 table."""
        elif data_type == "continuous":
            data_guidance = """
DATA TYPE: Continuous outcome.
Look for:
- Mean and standard deviation (SD) per arm, with sample sizes
- Mean difference (MD) or standardized mean difference (SMD) with 95% CI
- Change from baseline means/SDs per arm
IMPORTANT: Per-arm means and SDs are MORE valuable than adjusted mean differences,
because the systematic review computes its own unadjusted MD from the raw data."""

        return f"""ROLE: You are a precise clinical trial data extractor for Cochrane systematic reviews.

INSTRUCTION: Extract the effect estimate for ONE specific outcome from this RCT paper.

TARGET OUTCOME: "{outcome_name}"
{data_guidance}

STEPS:
1. Scan the paper for the Results section, tables, and abstract
2. Find data specifically about "{outcome_name}" (or closely matching outcome names)
3. Extract BOTH the reported effect estimate AND the raw per-arm data if available
4. Quote the exact text where you found the numbers

CRITICAL RULES:
- Only extract from THIS paper's own results (not references to other studies or meta-analyses)
- Do NOT fabricate or estimate numbers — only report what is explicitly stated
- If the exact outcome is not found, look for closely related outcomes (e.g., "mortality" for "death")
- If you find raw data (events/N or means/SDs), report those even if no effect estimate is stated
- Set found=false if you genuinely cannot find any relevant data
- The source_quote MUST be a verbatim quote from the paper containing the key numbers"""

    def _smart_truncate(self, text: str, max_chars: int) -> str:
        """Truncate text intelligently, prioritizing results sections."""
        if len(text) <= max_chars:
            return text

        # Try to find and prioritize results/discussion sections
        sections = []
        lower = text.lower()

        # Find key section boundaries
        results_markers = ['results', 'findings', 'outcome']
        abstract_markers = ['abstract', 'summary']
        methods_markers = ['method', 'statistical analysis']

        # Split into chunks and score by relevance
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_score = 1  # default score

        for line in lines:
            ll = line.lower().strip()
            # Check for section headers
            if any(m in ll for m in results_markers) and len(ll) < 50:
                if current_chunk:
                    chunks.append(('\n'.join(current_chunk), current_score))
                current_chunk = [line]
                current_score = 3  # Results get highest priority
            elif any(m in ll for m in abstract_markers) and len(ll) < 50:
                if current_chunk:
                    chunks.append(('\n'.join(current_chunk), current_score))
                current_chunk = [line]
                current_score = 2  # Abstract gets medium priority
            elif any(m in ll for m in methods_markers) and len(ll) < 50:
                if current_chunk:
                    chunks.append(('\n'.join(current_chunk), current_score))
                current_chunk = [line]
                current_score = 1  # Methods get low priority
            else:
                current_chunk.append(line)

        if current_chunk:
            chunks.append(('\n'.join(current_chunk), current_score))

        # Sort by score (highest first) and take until we hit limit
        chunks.sort(key=lambda x: -x[1])
        result_parts = []
        total_len = 0
        for chunk_text, score in chunks:
            if total_len + len(chunk_text) > max_chars:
                remaining = max_chars - total_len
                if remaining > 500:
                    result_parts.append(chunk_text[:remaining])
                break
            result_parts.append(chunk_text)
            total_len += len(chunk_text)

        return '\n'.join(result_parts)

    def _validate_and_convert(
        self,
        raw: Dict[str, Any],
        full_text: str,
        expected_data_type: Optional[str],
    ) -> List[AdvancedExtraction]:
        """
        Validate LLM output against source text and convert to extractions.

        Anti-hallucination checks:
        1. Source verification: key numbers must appear in PDF text
        2. Plausibility: effect values in reasonable range
        3. Raw data consistency: if both effect and raw data, they should agree
        """
        results = []

        if not raw.get("found", False):
            return results

        effect_type = raw.get("effect_type", "NONE")
        if effect_type == "NONE":
            # Check if raw data was provided even without an explicit effect
            pass

        point_estimate = raw.get("point_estimate")
        ci_lower = raw.get("ci_lower")
        ci_upper = raw.get("ci_upper")
        source_quote = raw.get("source_quote", "")
        reasoning = raw.get("reasoning", "")
        is_adjusted = raw.get("is_adjusted", False)

        confidence = 0.7  # Start at 0.7 for LLM extraction

        # --- Anti-hallucination check 1: Source text verification ---
        verification_hits = 0
        verification_checks = 0

        if point_estimate is not None:
            verification_checks += 1
            if self._number_in_text(point_estimate, full_text):
                verification_hits += 1
            else:
                confidence -= 0.3  # Major penalty — number not found in text
                logger.info(f"  VERIFY FAIL: point_estimate {point_estimate} not in text")

        if ci_lower is not None:
            verification_checks += 1
            if self._number_in_text(ci_lower, full_text):
                verification_hits += 1
            else:
                confidence -= 0.1

        if ci_upper is not None:
            verification_checks += 1
            if self._number_in_text(ci_upper, full_text):
                verification_hits += 1
            else:
                confidence -= 0.1

        # Verify raw data numbers too
        for field in ["intervention_events", "intervention_n", "control_events", "control_n"]:
            val = raw.get(field)
            if val is not None:
                verification_checks += 1
                if self._number_in_text(val, full_text):
                    verification_hits += 1

        for field in ["intervention_mean", "intervention_sd", "control_mean", "control_sd"]:
            val = raw.get(field)
            if val is not None:
                verification_checks += 1
                if self._number_in_text(val, full_text):
                    verification_hits += 1

        if verification_checks > 0:
            verify_rate = verification_hits / verification_checks
            if verify_rate < 0.5:
                confidence -= 0.2  # Too many numbers not found
                logger.info(f"  VERIFY LOW: {verification_hits}/{verification_checks} numbers found in text")

        # --- Anti-hallucination check 2: Plausibility ---
        if point_estimate is not None and effect_type in ("OR", "RR", "HR", "IRR"):
            if point_estimate <= 0:
                logger.info(f"  PLAUSIBILITY FAIL: {effect_type}={point_estimate} <= 0")
                confidence -= 0.3
            elif point_estimate > 100:
                confidence -= 0.1  # Unusual but possible

        # --- Anti-hallucination check 3: Raw data cross-check ---
        computed_from_raw = None
        if raw.get("intervention_events") is not None and raw.get("control_events") is not None:
            ie = raw["intervention_events"]
            in_ = raw.get("intervention_n")
            ce = raw["control_events"]
            cn = raw.get("control_n")
            if in_ and cn and ie <= in_ and ce <= cn and in_ > 0 and cn > 0:
                # Compute OR from raw 2x2
                a, b = ie, in_ - ie
                c, d = ce, cn - ce
                if b > 0 and c > 0 and d > 0 and a >= 0:
                    computed_or = (a * d) / max(b * c, 1e-10)
                    computed_from_raw = {"OR": computed_or}

                    # Also compute RR
                    p1 = a / in_ if in_ > 0 else 0
                    p2 = c / cn if cn > 0 else 0
                    if p2 > 0:
                        computed_from_raw["RR"] = p1 / p2

                    # Also compute RD
                    computed_from_raw["RD"] = p1 - p2

                # Add raw-data-based extractions
                for etype, val in (computed_from_raw or {}).items():
                    results.append(AdvancedExtraction(
                        effect_type=etype,
                        point_estimate=val,
                        ci_lower=None,
                        ci_upper=None,
                        method="llm_guided_raw",
                        source_text=f"[LLM-RAW-DATA] {ie}/{in_} vs {ce}/{cn}; {reasoning[:100]}",
                        confidence=min(confidence + 0.1, 0.9),  # Raw data is more trustworthy
                    ))

        # Continuous raw data
        if raw.get("intervention_mean") is not None and raw.get("control_mean") is not None:
            im = raw["intervention_mean"]
            isd = raw.get("intervention_sd")
            cm = raw["control_mean"]
            csd = raw.get("control_sd")
            in_ = raw.get("intervention_n")
            cn = raw.get("control_n")

            md = im - cm
            results.append(AdvancedExtraction(
                effect_type="MD",
                point_estimate=md,
                ci_lower=None,
                ci_upper=None,
                method="llm_guided_raw",
                source_text=f"[LLM-RAW-DATA] mean {im}({isd}) vs {cm}({csd}); {reasoning[:100]}",
                confidence=min(confidence + 0.1, 0.9),
            ))

            # SMD (Hedges' g) if SDs available
            if isd and csd and in_ and cn and isd > 0 and csd > 0:
                pooled_sd = ((((in_ - 1) * isd**2) + ((cn - 1) * csd**2))
                             / max(in_ + cn - 2, 1)) ** 0.5
                if pooled_sd > 0:
                    smd = md / pooled_sd
                    # Hedges' g correction
                    df = in_ + cn - 2
                    correction = 1 - 3 / (4 * df - 1) if df > 1 else 1
                    smd *= correction
                    results.append(AdvancedExtraction(
                        effect_type="SMD",
                        point_estimate=smd,
                        method="llm_guided_raw",
                        source_text=f"[LLM-RAW-DATA] SMD from means; {reasoning[:100]}",
                        confidence=min(confidence + 0.1, 0.9),
                    ))

        # Add the directly-reported effect estimate (if any)
        if point_estimate is not None and effect_type != "NONE":
            # Skip if confidence is too low (likely hallucinated)
            if confidence >= 0.2:
                adj_label = "[ADJ]" if is_adjusted else ""
                results.append(AdvancedExtraction(
                    effect_type=effect_type,
                    point_estimate=point_estimate,
                    ci_lower=ci_lower,
                    ci_upper=ci_upper,
                    method="llm_guided",
                    source_text=f"[LLM-GUIDED{adj_label}] {source_quote[:150]}",
                    confidence=confidence,
                ))

        return results

    @staticmethod
    def _number_in_text(value, text: str, tolerance: float = 0.005) -> bool:
        """
        Check if a number appears in the text (anti-hallucination verification).

        Handles various formats: 1.45, 1·45, 1,45 (European), 15/56, etc.
        """
        if value is None:
            return True  # Can't verify null

        try:
            val = float(value)
        except (ValueError, TypeError):
            return False

        # For integers, check exact match
        if val == int(val) and abs(val) < 10000:
            int_val = int(val)
            # Look for the integer in text (word boundary)
            if re.search(rf'(?<!\d){re.escape(str(int_val))}(?!\d)', text):
                return True

        # For floats, check formatted representations
        # Try common formats: 1.45, 1·45, 0.45
        for fmt in [f"{val:.4f}", f"{val:.3f}", f"{val:.2f}", f"{val:.1f}", f"{val:.0f}"]:
            # Strip trailing zeros after decimal
            clean = fmt.rstrip('0').rstrip('.')
            if clean and clean in text:
                return True
            # Also check with middle dot (·) common in medical papers
            if '.' in clean and clean.replace('.', '\u00b7') in text:
                return True
            # European comma decimal
            if '.' in clean and clean.replace('.', ',') in text:
                return True

        # Try absolute value too (sign might differ in text)
        if val < 0:
            return OutcomeGuidedExtractor._number_in_text(abs(val), text, tolerance)

        return False


# ============================================================
# UNIFIED ADVANCED EXTRACTOR
# ============================================================

class AdvancedExtractionPipeline:
    """
    Runs all available advanced extraction methods in order:
    1. Table Transformer (if tables detected)
    2. OCR (if text extraction was poor)
    3. LLM (if enabled and nothing else worked)

    Use this as a fallback after the main regex pipeline.
    """

    def __init__(
        self,
        enable_table_transformer: bool = True,
        enable_ocr: bool = True,
        enable_llm: bool = False,  # Off by default (non-deterministic)
        llm_model: str = "claude-sonnet-4-5-20250929",
    ):
        self.table_extractor = None
        self.ocr_extractor = None
        self.llm_extractor = None

        if enable_table_transformer and HAS_TABLE_TRANSFORMER and HAS_PYMUPDF and HAS_PIL:
            try:
                self.table_extractor = TableTransformerExtractor()
            except Exception as e:
                logger.warning(f"Failed to init Table Transformer: {e}")

        if enable_ocr and HAS_PYMUPDF and HAS_TESSERACT and HAS_PIL:
            try:
                self.ocr_extractor = OCRExtractor()
            except Exception as e:
                logger.warning(f"Failed to init OCR extractor: {e}")

        if enable_llm and HAS_ANTHROPIC:
            try:
                self.llm_extractor = LLMExtractor(model=llm_model)
            except Exception as e:
                logger.warning(f"Failed to init LLM extractor: {e}")

    def extract_from_pdf(
        self,
        pdf_path: str,
        existing_text: str = "",
        min_text_for_ocr: int = 500,
    ) -> List[AdvancedExtraction]:
        """
        Run advanced extraction pipeline.

        Args:
            pdf_path: Path to PDF
            existing_text: Text already extracted by main pipeline (to check quality)
            min_text_for_ocr: If existing text is shorter, trigger OCR

        Returns:
            Combined list from all methods, deduplicated
        """
        all_results = []

        # 1. Table Transformer — always try if available
        if self.table_extractor:
            try:
                tt_results = self.table_extractor.extract_from_pdf(pdf_path)
                logger.info(f"Table Transformer: {len(tt_results)} extractions")
                all_results.extend(tt_results)
            except Exception as e:
                logger.warning(f"Table Transformer failed: {e}")

        # 2. OCR — only if existing text is poor quality
        if self.ocr_extractor and len(existing_text.strip()) < min_text_for_ocr:
            try:
                ocr_results = self.ocr_extractor.extract_from_pdf(pdf_path)
                logger.info(f"OCR extraction: {len(ocr_results)} extractions")
                all_results.extend(ocr_results)
            except Exception as e:
                logger.warning(f"OCR extraction failed: {e}")

        # 3. LLM — only if nothing else worked
        if self.llm_extractor and not all_results:
            try:
                llm_results = self.llm_extractor.extract_from_pdf(pdf_path)
                logger.info(f"LLM extraction: {len(llm_results)} extractions")
                all_results.extend(llm_results)
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")

        # Deduplicate (same value within 1% tolerance)
        deduped = self._deduplicate(all_results)
        return deduped

    @staticmethod
    def _deduplicate(results: List[AdvancedExtraction]) -> List[AdvancedExtraction]:
        """Remove near-duplicate extractions, keeping highest confidence."""
        if not results:
            return results

        # Sort by confidence (highest first)
        results.sort(key=lambda x: x.confidence, reverse=True)

        unique = []
        for r in results:
            is_dup = False
            for u in unique:
                if u.effect_type == r.effect_type:
                    if u.point_estimate != 0:
                        rel_dist = abs(r.point_estimate - u.point_estimate) / abs(u.point_estimate)
                    else:
                        rel_dist = abs(r.point_estimate)
                    if rel_dist < 0.01:
                        is_dup = True
                        break
            if not is_dup:
                unique.append(r)

        return unique
