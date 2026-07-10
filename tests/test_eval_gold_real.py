#!/usr/bin/env python3
"""Unit coverage for the real-selection eval's offline logic (JATS text parsing).
The efetch/download network paths are integration-only and not unit-tested here.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pytest

import eval_gold_real as ev


JATS = """<article>
  <front><article-meta>
    <abstract><p>The primary outcome was mortality.</p></abstract>
  </article-meta></front>
  <body>
    <sec><title>Results</title>
      <p>The hazard ratio was 0.70 (95% CI 0.55-0.89).</p>
    </sec>
  </body>
</article>"""


class TestJatsText:
    def test_extracts_abstract_and_body(self):
        text = ev._text_from_jats(JATS)
        assert "primary outcome was mortality" in text
        assert "hazard ratio was 0.70" in text

    def test_malformed_xml_falls_back_to_tag_strip(self):
        text = ev._text_from_jats("<body><p>MD -2.1 (95% CI -3.4 to -0.8)</p></bod")  # broken
        assert "MD -2.1" in text

    def test_empty(self):
        assert ev._text_from_jats("") == "" or ev._text_from_jats("").strip() == ""
