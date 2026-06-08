"""
rct-extract -- unified command-line interface for the RCT extractor.

Run any of the 17 disease-specialty extractors on an abstract or a corpus of
abstracts, or let it auto-detect the specialty.

Examples
--------
    # list everything you can extract
    rct-extract --list-specialties

    # extract from a single abstract file, forcing the diabetes profile
    rct-extract --specialty diabetes --input abstract.txt

    # auto-detect the specialty
    rct-extract --auto --input abstract.txt

    # pass text directly, machine-readable JSON to stdout
    rct-extract --text "HbA1c fell (HR 0.62, 95% CI 0.45-0.85)..." --json

    # batch: every *.txt in a folder, one JSON object per line, to a file
    rct-extract --auto --input ./corpus --json -o results.jsonl

    # just tell me the specialty
    rct-extract --detect --input abstract.txt

The original PDF-table pipeline remains available as ``rct-extract-pdf``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from .api import SPECIALTIES, detect_specialty, extract


def _read_inputs(args) -> List[Dict[str, str]]:
    """Return [{name, text}] from --text / --input file / --input dir / stdin."""
    if args.text is not None:
        return [{"name": "<text>", "text": args.text}]
    if args.input:
        p = Path(args.input)
        if not p.exists():
            raise FileNotFoundError(f"input not found: {p}")
        if p.is_dir():
            files = sorted(p.glob("*.txt"))
            if not files:
                raise FileNotFoundError(f"no *.txt files in {p}")
            return [{"name": f.stem, "text": f.read_text(encoding="utf-8")} for f in files]
        return [{"name": p.stem, "text": p.read_text(encoding="utf-8")}]
    # stdin
    data = sys.stdin.read()
    if not data.strip():
        raise ValueError("no input: use --text, --input, or pipe text via stdin")
    return [{"name": "<stdin>", "text": data}]


def _format_summary(name: str, res: Dict[str, Any]) -> str:
    """Build the human-readable summary for one record (returned, not printed,
    so the same text can go to stdout AND to --output)."""
    out = [f"\n{'=' * 60}", f"{name}", f"{'=' * 60}"]
    conf = res.get("confidence")
    conf_s = f"{conf:.2f}" if isinstance(conf, (int, float)) else str(conf)
    out.append(f"specialty   : {res['specialty']}")
    out.append(f"subspecialty: {res.get('subspecialty')}  (confidence {conf_s})")
    effects = res.get("effects") or []
    out.append(f"effects     : {len(effects)}")
    for e in effects[:10]:
        et = e.get("type", "?")
        es = e.get("effect_size")
        lo, hi = e.get("ci_lower"), e.get("ci_upper")
        ep = e.get("endpoint", "")
        ci = f" [{lo}-{hi}]" if lo is not None and hi is not None else ""
        es_s = f"{es}" if es is not None else "?"
        out.append(f"  - {et}={es_s}{ci}  {ep}".rstrip())
    arm = res.get("arm_level")
    if arm:
        p2 = arm.get("poolable_2x2") or []
        cont = arm.get("continuous") or []
        out.append(f"arm-level   : {len(p2)} poolable 2x2, {len(cont)} continuous")
        for t in p2[:5]:
            a1, a2 = t.get("arm1", {}), t.get("arm2", {})
            out.append(
                f"  - {t.get('endpoint','?')}: "
                f"{a1.get('label','?')} {a1.get('events','?')}/{a1.get('total','?')} vs "
                f"{a2.get('label','?')} {a2.get('events','?')}/{a2.get('total','?')}"
            )
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="rct-extract",
        description="Extract RCT effects/arm-level data from abstracts across 17 disease specialties.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    try:
        from src import __version__
    except Exception:
        __version__ = "?"
    parser.add_argument("--version", action="version", version=str(__version__))

    parser.add_argument("--list-specialties", action="store_true",
                        help="print the 17 supported specialties and exit")
    parser.add_argument("--detect", action="store_true",
                        help="only detect specialty/subspecialty, do not extract")

    src_group = parser.add_argument_group("specialty selection")
    src_group.add_argument("-s", "--specialty", default=None,
                           help=f"force a specialty ({', '.join(SPECIALTIES)})")
    src_group.add_argument("--auto", action="store_true",
                           help="auto-detect the specialty (default if -s omitted)")

    in_group = parser.add_argument_group("input")
    in_group.add_argument("-i", "--input",
                          help="abstract file, or a directory of *.txt files")
    in_group.add_argument("--text", help="abstract text passed directly")

    out_group = parser.add_argument_group("output")
    out_group.add_argument("-o", "--output", help="write results here (default: stdout)")
    out_group.add_argument("--json", action="store_true",
                           help="emit JSON (one object per line for batches)")
    out_group.add_argument("--no-arm-level", action="store_true",
                           help="skip arm-level (2x2/continuous) extraction")
    out_group.add_argument("--no-effects", action="store_true",
                           help="skip precomputed effect-estimate extraction")

    args = parser.parse_args(argv)

    if args.list_specialties:
        print("Supported specialties (17):")
        for s in SPECIALTIES:
            print(f"  - {s}")
        return 0

    specialty = args.specialty or "auto"
    if specialty != "auto" and specialty.lower() not in SPECIALTIES:
        parser.error(
            f"unknown specialty {specialty!r}; choose from {', '.join(SPECIALTIES)} or use --auto"
        )

    try:
        inputs = _read_inputs(args)
    except (FileNotFoundError, ValueError) as e:
        parser.error(str(e))

    lines: List[str] = []
    for rec in inputs:
        name, text = rec["name"], rec["text"]
        if args.detect:
            spec, sub, conf = detect_specialty(text)
            res = {"name": name, "specialty": spec, "subspecialty": sub, "confidence": conf}
            if args.json:
                lines.append(json.dumps(res, default=str))
            else:
                print(f"{name}: {spec} / {sub} (confidence {conf})")
            continue

        res = extract(
            text,
            specialty=specialty,
            with_effects=not args.no_effects,
            with_arm_level=not args.no_arm_level,
        )
        if args.json:
            out = {"name": name, **res}
            lines.append(json.dumps(out, default=str))
        else:
            summary = _format_summary(name, res)
            print(summary)
            lines.append(summary)

    if args.json:
        payload = "\n".join(lines) + ("\n" if lines else "")
        if args.output:
            Path(args.output).write_text(payload, encoding="utf-8")
            print(f"wrote {len(lines)} result(s) to {args.output}")
        else:
            sys.stdout.write(payload)
    elif args.output and not args.detect:
        # human format + --output: also persist the printed summaries (lines is
        # now populated above, so this no longer writes an empty file).
        Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
