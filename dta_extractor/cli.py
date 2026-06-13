"""
dta-extract -- command-line interface for the DTA extraction mode.

Sits alongside ``rct-extract``: where that pulls treatment effects from RCT
text, this pulls diagnostic-test-accuracy data (2x2 tables, sensitivity /
specificity / PPV / NPV / LR / DOR / AUC, plus the index test, reference
standard and target condition).

Examples
--------
    # list the DTA domains
    dta-extract --list-domains

    # extract from a single abstract/text file
    dta-extract --input abstract.txt

    # pass text directly, machine-readable JSON to stdout
    dta-extract --text "Sensitivity 92% (88-96), specificity 85%. RT-PCR was the reference standard." --json

    # batch: every *.txt in a folder, one JSON object per line
    dta-extract --input ./corpus --json -o results.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from . import DOMAINS, extract


def _read_inputs(args) -> List[Dict[str, str]]:
    if args.text is not None:
        return [{"id": "<text>", "text": args.text}]
    if not args.input:
        return []
    p = Path(args.input)
    if p.is_dir():
        return [{"id": f.name, "text": f.read_text(encoding="utf-8", errors="replace")}
                for f in sorted(p.glob("*.txt"))]
    return [{"id": p.name, "text": p.read_text(encoding="utf-8", errors="replace")}]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dta-extract", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", help="extract from this literal string")
    ap.add_argument("--input", help="a .txt file or a directory of .txt files")
    ap.add_argument("--domain", default="auto", help="force a DTA domain (default: auto)")
    ap.add_argument("--json", action="store_true", help="emit JSON (one object per input)")
    ap.add_argument("-o", "--output", help="write to this file instead of stdout")
    ap.add_argument("--list-domains", action="store_true", help="list DTA domains and exit")
    args = ap.parse_args(argv)

    if args.list_domains:
        print("\n".join(DOMAINS))
        return 0

    inputs = _read_inputs(args)
    if not inputs:
        ap.error("provide --text, --input, or --list-domains")

    out_lines = []
    for item in inputs:
        result = extract(item["text"], domain=args.domain)
        if args.json:
            out_lines.append(json.dumps({"id": item["id"], **result}, ensure_ascii=False))
        else:
            ents = result["entities"]
            out_lines.append(
                f"[{item['id']}] domain={result['domain']} poolable={result['poolable']}\n"
                f"  index_test={ents['index_test']!r}\n"
                f"  reference_standard={ents['reference_standard']!r}\n"
                f"  target_condition={ents['target_condition']!r}\n"
                f"  measures={[(m['measure'], m['value']) for m in result['measures']]}\n"
                f"  2x2={[(t['tp'], t['fp'], t['fn'], t['tn']) for t in result['two_by_two']]}"
            )

    text = "\n".join(out_lines) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
