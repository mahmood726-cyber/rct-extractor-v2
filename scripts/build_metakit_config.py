"""
Build a meta-starter-kit config from trial records using the extractor.

Input JSON: {title, effect_measure (OR/HR/RR/MD/SMD/RD), endpoint?, intervention?,
comparator?, condition?, outcome?, authors?, records:[{name, text, nct?, pmid?,
year?}]}. Each record's `text` is the trial's abstract/results text; the
extractor (topic-routed: cardiology -> effects, malaria binary -> 2x2) pulls the
poolable datum, and the result is a config the kit's build.py consumes directly.

Usage:
  python scripts/build_metakit_config.py records.json --out config.json
  python build.py config.json     # (in the meta-starter-kit repo)
"""
import argparse
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.core.enhanced_extractor_v3 import EnhancedExtractor
from src.bridges.meta_starter_kit import build_config_from_records


def main():
    ap = argparse.ArgumentParser(description="Extractor -> meta-starter-kit config")
    ap.add_argument("records", help="input records JSON")
    ap.add_argument("--out", default="metakit_config.json")
    ap.add_argument("--topics", default=None,
                    help="comma list (e.g. malaria,cardiology): only engage for "
                         "these auto-detected topics")
    args = ap.parse_args()

    spec = json.loads(Path(args.records).read_text(encoding="utf-8"))
    records = spec.get("records", [])
    if len(records) < 2:
        print("need >=2 records"); sys.exit(1)

    extractor = EnhancedExtractor()
    meta = {k: spec[k] for k in ("intervention", "comparator", "condition",
                                 "outcome", "authors") if spec.get(k)}
    topics = [t.strip() for t in args.topics.split(",")] if args.topics else \
        (spec.get("topics") if isinstance(spec.get("topics"), list) else None)
    cfg = build_config_from_records(
        records, extractor,
        title=spec.get("title", "Meta-analysis"),
        effect_measure=spec.get("effect_measure", "RR"),
        endpoint=spec.get("endpoint"),
        topics=topics,
        **meta)
    Path(args.out).write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}: {len(cfg['trials'])}/{len(records)} records -> trials "
          f"({cfg['effect_measure']})")


if __name__ == "__main__":
    main()
