"""
Text Preprocessor - Build a Reliable Text Layer

Based on Al-Fātiḥah Principle 2: "Praise = build a reliable text layer before extraction"
Most rules fail because the PDF text layer is messy.
"""

import re
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class TextLine:
    """Single line of text with provenance."""
    text: str
    page_num: int
    line_num: int
    bbox: Optional[Tuple[float, float, float, float]] = None  # x0, y0, x1, y1
    is_header_footer: bool = False
    column: int = 0  # 0=single column, 1=left, 2=right


@dataclass
class TextBlock:
    """Block of related text (paragraph, table cell, etc.)."""
    lines: List[TextLine] = field(default_factory=list)
    block_type: str = "text"  # text, heading, table, figure_caption
    section: str = ""  # abstract, methods, results, discussion

    @property
    def text(self) -> str:
        return " ".join(line.text for line in self.lines)

    @property
    def page_num(self) -> int:
        return self.lines[0].page_num if self.lines else 0


@dataclass
class ProcessedDocument:
    """Complete processed document with multiple representations."""
    # Raw line grid with coordinates
    lines: List[TextLine] = field(default_factory=list)

    # Reading-order text (for narrative extraction)
    reading_order_text: str = ""

    # Section-aware blocks
    blocks: List[TextBlock] = field(default_factory=list)

    # Section boundaries
    sections: Dict[str, Tuple[int, int]] = field(default_factory=dict)  # section -> (start_char, end_char)

    # Metadata
    num_pages: int = 0
    is_two_column: bool = False
    has_tables: bool = False


class TextPreprocessor:
    """
    Preprocesses PDF text for reliable extraction.

    Key functions:
    1. Dehyphenate line breaks
    2. Normalize Unicode
    3. Remove headers/footers
    4. Detect and handle 2-column layouts
    5. Preserve line + page provenance
    """

    # Unicode normalizations
    UNICODE_MAP = {
        '\ufb01': 'fi',
        '\ufb02': 'fl',
        '\ufb03': 'ffi',
        '\ufb04': 'ffl',
        '\u2010': '-',  # Hyphen
        '\u2011': '-',  # Non-breaking hyphen
        '\u2012': '-',  # Figure dash
        '\u2013': '-',  # En dash
        '\u2014': '-',  # Em dash
        '\u2015': '-',  # Horizontal bar
        '\u2212': '-',  # Minus sign
        '\uff0d': '-',  # Fullwidth hyphen-minus
        '\u00a0': ' ',  # Non-breaking space
        '\u2002': ' ',  # En space
        '\u2003': ' ',  # Em space
        '\u2009': ' ',  # Thin space
        '\u200a': ' ',  # Hair space
        '\u200b': '',   # Zero-width space
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote
        '\u201c': '"',  # Left double quote
        '\u201d': '"',  # Right double quote
        '\u00b1': '±',  # Plus-minus (keep but standardize)
        '\u2264': '<=', # Less than or equal
        '\u2265': '>=', # Greater than or equal
        '\u00d7': 'x',  # Multiplication sign
    }

    # Common header/footer patterns
    HEADER_FOOTER_PATTERNS = [
        r'^Page\s+\d+',
        r'^\d+\s*$',  # Just page number
        r'^[A-Z][a-z]+\s+et\s+al\.?',  # Author et al.
        r'^\w+\s+\d{4};\d+:\d+',  # Journal citation
        r'^Downloaded\s+from',
        r'^Copyright\s+©',
        r'^All\s+rights\s+reserved',
    ]

    # Section detection patterns
    SECTION_PATTERNS = {
        'abstract': [r'\bAbstract\b', r'\bSummary\b', r'\bBackground\b'],
        'introduction': [r'\bIntroduction\b', r'\bBackground\b'],
        'methods': [r'\bMethods\b', r'\bMaterials?\s+and\s+Methods\b', r'\bStudy\s+Design\b', r'\bPatients?\s+and\s+Methods\b'],
        'results': [r'\bResults\b', r'\bFindings\b'],
        'discussion': [r'\bDiscussion\b', r'\bConclusions?\b'],
        'references': [r'\bReferences\b', r'\bBibliography\b'],
    }

    def __init__(self):
        self.unicode_pattern = re.compile(
            '|'.join(re.escape(k) for k in self.UNICODE_MAP.keys())
        )

    def process(self, lines: List[TextLine]) -> ProcessedDocument:
        """
        Process raw text lines into a clean document.

        Args:
            lines: Raw text lines with page/line numbers and bboxes

        Returns:
            ProcessedDocument with multiple representations
        """
        doc = ProcessedDocument()
        doc.num_pages = max((line.page_num for line in lines), default=0)

        # Step 1: Normalize Unicode
        lines = self._normalize_unicode(lines)

        # Step 2: Detect and remove headers/footers
        lines = self._remove_headers_footers(lines)

        # Step 3: Detect two-column layout
        doc.is_two_column = self._detect_two_column(lines)

        # Step 4: Reorder columns if needed
        if doc.is_two_column:
            lines = self._reorder_columns(lines)

        # Step 5: Dehyphenate
        lines = self._dehyphenate(lines)

        # Step 6: Detect sections
        doc.sections = self._detect_sections(lines)

        # Step 7: Build blocks
        doc.blocks = self._build_blocks(lines, doc.sections)

        # Store processed lines
        doc.lines = lines

        # Build reading-order text
        doc.reading_order_text = self._build_reading_order_text(lines)

        return doc

    def _normalize_unicode(self, lines: List[TextLine]) -> List[TextLine]:
        """Normalize Unicode characters."""
        for line in lines:
            # Apply character-level normalizations
            for old, new in self.UNICODE_MAP.items():
                line.text = line.text.replace(old, new)

            # Normalize whitespace
            line.text = re.sub(r'[ \t]+', ' ', line.text)
            line.text = line.text.strip()

        return lines

    def _remove_headers_footers(self, lines: List[TextLine]) -> List[TextLine]:
        """
        Detect and mark repeated lines as headers/footers.
        Uses frequency analysis across pages.
        """
        if not lines:
            return lines

        # Group lines by page
        pages = {}
        for line in lines:
            if line.page_num not in pages:
                pages[line.page_num] = []
            pages[line.page_num].append(line)

        # Find repeated patterns at top/bottom of pages
        top_lines = {}  # text -> count
        bottom_lines = {}

        for page_num, page_lines in pages.items():
            if page_lines:
                # Top 2 lines
                for line in page_lines[:2]:
                    text = line.text.strip()
                    if text:
                        top_lines[text] = top_lines.get(text, 0) + 1

                # Bottom 2 lines
                for line in page_lines[-2:]:
                    text = line.text.strip()
                    if text:
                        bottom_lines[text] = bottom_lines.get(text, 0) + 1

        # Threshold: appears on >50% of pages
        threshold = len(pages) * 0.5

        repeated_top = {t for t, c in top_lines.items() if c >= threshold}
        repeated_bottom = {t for t, c in bottom_lines.items() if c >= threshold}

        # Also check pattern-based headers/footers
        for line in lines:
            text = line.text.strip()

            # Mark as header/footer if repeated or matches pattern
            if text in repeated_top or text in repeated_bottom:
                line.is_header_footer = True
            else:
                for pattern in self.HEADER_FOOTER_PATTERNS:
                    if re.match(pattern, text, re.IGNORECASE):
                        line.is_header_footer = True
                        break

        # Filter out headers/footers
        return [line for line in lines if not line.is_header_footer]

    def _detect_two_column(self, lines: List[TextLine]) -> bool:
        """
        Detect if document uses two-column layout.
        Uses bbox analysis if available, otherwise heuristics.
        """
        if not lines:
            return False

        # If we have bboxes, use them
        lines_with_bbox = [l for l in lines if l.bbox]

        if len(lines_with_bbox) > 10:
            # Get page width from max x1
            max_x = max(l.bbox[2] for l in lines_with_bbox)

            # Check for gap in middle
            midpoint = max_x / 2
            margin = max_x * 0.1

            left_lines = [l for l in lines_with_bbox if l.bbox[2] < midpoint - margin]
            right_lines = [l for l in lines_with_bbox if l.bbox[0] > midpoint + margin]

            # Two-column if significant content on both sides
            if len(left_lines) > 10 and len(right_lines) > 10:
                return True

        # Heuristic: many short lines suggest columns
        short_lines = sum(1 for l in lines if 20 < len(l.text) < 60)
        if short_lines > len(lines) * 0.4:
            return True

        return False

    def _reorder_columns(self, lines: List[TextLine]) -> List[TextLine]:
        """
        Reorder two-column text to reading order (left column, then right).
        """
        if not lines:
            return lines

        # Group by page
        pages = {}
        for line in lines:
            if line.page_num not in pages:
                pages[line.page_num] = []
            pages[line.page_num].append(line)

        reordered = []

        for page_num in sorted(pages.keys()):
            page_lines = pages[page_num]

            # If we have bboxes, use them for column detection
            lines_with_bbox = [l for l in page_lines if l.bbox]

            if lines_with_bbox:
                max_x = max(l.bbox[2] for l in lines_with_bbox)
                midpoint = max_x / 2

                left_col = [l for l in page_lines if l.bbox and l.bbox[2] < midpoint * 1.1]
                right_col = [l for l in page_lines if l.bbox and l.bbox[0] > midpoint * 0.9]
                other = [l for l in page_lines if l not in left_col and l not in right_col]

                # Sort by y position within each column
                left_col.sort(key=lambda l: l.bbox[1] if l.bbox else 0)
                right_col.sort(key=lambda l: l.bbox[1] if l.bbox else 0)

                # Mark columns
                for l in left_col:
                    l.column = 1
                for l in right_col:
                    l.column = 2

                # Add in reading order: left column, then right column
                reordered.extend(left_col)
                reordered.extend(right_col)
                reordered.extend(other)
            else:
                # No bbox info, keep original order
                reordered.extend(page_lines)

        return reordered

    def _dehyphenate(self, lines: List[TextLine]) -> List[TextLine]:
        """
        Rejoin words split across line breaks.
        "hy-\\nphen" -> "hyphen"
        """
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]
            text = line.text

            # Check if line ends with hyphen followed by lowercase
            if text.endswith('-') and i + 1 < len(lines):
                next_line = lines[i + 1]
                # Check if next line starts with lowercase letter
                if next_line.text and next_line.text[0].islower():
                    # Dehyphenate: remove hyphen and join
                    text = text[:-1] + next_line.text
                    line.text = text
                    i += 1  # Skip next line

            result.append(line)
            i += 1

        return result

    def _detect_sections(self, lines: List[TextLine]) -> Dict[str, Tuple[int, int]]:
        """
        Detect document sections and their character boundaries.
        """
        sections = {}
        current_pos = 0

        for line in lines:
            text = line.text
            text_lower = text.lower()

            for section_name, patterns in self.SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        # Mark start of section
                        if section_name not in sections:
                            sections[section_name] = (current_pos, -1)
                        break

            current_pos += len(text) + 1  # +1 for newline

        # Fill in end positions
        section_starts = [(name, start) for name, (start, _) in sections.items()]
        section_starts.sort(key=lambda x: x[1])

        for i, (name, start) in enumerate(section_starts):
            if i + 1 < len(section_starts):
                end = section_starts[i + 1][1]
            else:
                end = current_pos
            sections[name] = (start, end)

        return sections

    def _build_blocks(self, lines: List[TextLine], sections: Dict[str, Tuple[int, int]]) -> List[TextBlock]:
        """
        Group lines into semantic blocks.
        """
        blocks = []
        current_block = TextBlock()
        current_section = ""

        # Precompute cumulative character positions for each line (O(n))
        line_positions = []
        cumulative = 0
        for line in lines:
            line_positions.append(cumulative)
            cumulative += len(line.text) + 1  # +1 for newline

        # Sort sections by start position for efficient lookup
        sorted_sections = sorted(sections.items(), key=lambda x: x[1][0])

        for i, line in enumerate(lines):
            line_pos = line_positions[i]

            # Find which section this line belongs to
            new_section = ""
            for section_name, (start, end) in sorted_sections:
                if start <= line_pos < end:
                    new_section = section_name
                    break

            if new_section:
                current_section = new_section

            # Start new block on empty line or section change
            if not line.text.strip() or (current_block.section and current_block.section != current_section):
                if current_block.lines:
                    blocks.append(current_block)
                current_block = TextBlock(section=current_section)

            current_block.lines.append(line)
            current_block.section = current_section

        # Add final block
        if current_block.lines:
            blocks.append(current_block)

        return blocks

    def _build_reading_order_text(self, lines: List[TextLine]) -> str:
        """Build continuous reading-order text."""
        # Join lines, handling hyphenation and spacing
        texts = []
        for i, line in enumerate(lines):
            text = line.text.strip()
            if not text:
                texts.append('\n\n')  # Paragraph break
            else:
                texts.append(text)
                if i + 1 < len(lines) and lines[i + 1].text.strip():
                    texts.append(' ')

        return ''.join(texts)


def preprocess_pdf_text(lines: List[TextLine]) -> ProcessedDocument:
    """Convenience function to preprocess PDF text."""
    preprocessor = TextPreprocessor()
    return preprocessor.process(lines)
