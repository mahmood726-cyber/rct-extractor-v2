#!/usr/bin/env python3
"""Check actual MD format in PDFs."""

import pdfplumber
import re
import sys

# Set encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Check PMC12719702 for MD patterns
pdf_path = 'test_pdfs/real_pdfs/diabetes/PMC12719702.pdf'
with pdfplumber.open(pdf_path) as pdf:
    text = ''
    for page in pdf.pages[:10]:
        text += (page.extract_text() or '')

print("=" * 60)
print("MD Pattern Analysis for PMC12719702.pdf")
print("=" * 60)

# Find all MD/mean difference mentions with context
matches = re.findall(r'.{0,30}mean\s+difference.{0,80}', text, re.IGNORECASE)
print(f"\nFound {len(matches)} 'mean difference' mentions:")
for i, m in enumerate(matches[:5]):
    print(f"\n{i+1}. Raw repr:")
    # Show hex for special chars
    for c in m[:100]:
        if ord(c) > 127:
            print(f"  [{hex(ord(c))}={c}]", end='')
        elif c == '\n':
            print(" ", end='')
    print()
    print(f"   Text: {m[:100]}")

# Check for the specific patterns we expect
print("\n" + "=" * 60)
print("Testing specific patterns:")
print("=" * 60)

test_patterns = [
    (r'mean\s+difference\s+([+-−]?\d+[.,]?\d*)%?\s*\[', "MD X% ["),
    (r'mean\s+difference\s+([+-−]?\d+[.,]?\d*)%?\s*\(\s*(?:95%?\s*)?CI', "MD X% (95% CI"),
    (r'\[95%?\s*CI\s+([+-−]?\d+[.,]?\d*)\s+to\s+([+-−]?\d+[.,]?\d*)', "[95% CI X to Y"),
    (r'−', "Unicode minus (U+2212)"),
]

for pattern, name in test_patterns:
    matches = re.findall(pattern, text, re.IGNORECASE)
    print(f"  {name}: {len(matches)} matches")
    if matches and len(matches) < 5:
        for m in matches[:3]:
            print(f"    -> {m}")

# Check one of the zero-extraction PDFs
print("\n" + "=" * 60)
print("Checking PMC10011807.pdf (0 extractions but has OR/CI)")
print("=" * 60)

pdf_path2 = 'test_pdfs/real_pdfs/infectious/PMC10011807.pdf'
with pdfplumber.open(pdf_path2) as pdf:
    text2 = ''
    for page in pdf.pages[:15]:
        text2 += (page.extract_text() or '')

# Find OR patterns with context
or_matches = re.findall(r'.{0,30}\bOR\b.{0,80}', text2)
print(f"\nFound {len(or_matches)} 'OR' mentions. First 5:")
for m in or_matches[:5]:
    print(f"  -> {m[:100].replace(chr(10), ' ')}")

# Check for actual odds ratio patterns
print("\nLooking for 'odds ratio' or 'OR =' patterns:")
or_patterns = [
    r'odds\s+ratio',
    r'\bOR\b\s*[=:]\s*\d',
    r'\bOR\b\s+\d+\.\d+',
    r'\bOR\b\s*,?\s*\d+\.\d+',
]
for p in or_patterns:
    m = re.findall(p, text2, re.IGNORECASE)
    print(f"  {p[:30]}: {len(m)} matches")
