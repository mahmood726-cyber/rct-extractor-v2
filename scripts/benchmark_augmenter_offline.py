"""
OFFLINE, reproducible augmenter benchmark (no network).

Replays the published-MA silver-standard validation (reviewer_data + recover,
the SAME logic the live scripts/<sp>/validate_*_ma.py use) against the cached
abstract corpora in data/field_portability/<sp>/<sp>_matched.jsonl.

Two outputs:
  1. RECOVERY: per specialty, of every reviewer-reported `value (95% CI lo-hi)`
     that carries an effect label, how many our extractor recovers (point+CI
     agree, 5% tol). This is the silver-standard effect_agreement. (Capped by
     --limit because it runs the full core+augmenter pipeline; the % is stable.)
  2. ADDITIVITY: the full set of (type, value, ci_lower, ci_upper) the augmenter
     emits per abstract -- snapshotted over the ENTIRE corpus so a before/after
     diff PROVES the change only ADDED extractions (strict superset), never
     dropped one. Augmenter-only, so it is fast over all ~7.4k abstracts.

Usage:
  python scripts/benchmark_augmenter_offline.py --snapshot OLD.json   # write baseline
  python scripts/benchmark_augmenter_offline.py --compare OLD.json    # diff vs baseline
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor
from rct_extractor._engine.specialties.malaria_effects import augment_malaria_effects, extract_malaria_effects
from scripts.malaria.validate_against_ma import reviewer_data, recover

CORPORA = {
    "hiv":     "data/field_portability/hiv/hiv_matched.jsonl",
    "malaria": "data/field_portability/malaria/malaria_matched.jsonl",
    "typhoid": "data/field_portability/typhoid/typhoid_matched.jsonl",
}
RECOVERY_LIMIT = 500   # abstracts/specialty for the (slow) full-pipeline recovery


def abstracts(path):
    for line in (ROOT / path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        ab = d.get("abstract")
        if ab and len(ab) > 40:
            yield (str(d.get("pmid") or d.get("study_id")), ab)


def aug_key(e):
    def r(x):
        return round(x, 4) if isinstance(x, (int, float)) else x
    return (e.get("type"), r(e.get("effect_size")), r(e.get("ci_lower")), r(e.get("ci_upper")))


def run(recovery_limit=RECOVERY_LIMIT):
    ext = EnhancedExtractor()
    recov, snap = {}, {}
    for sp, path in CORPORA.items():
        et = em = at = am = 0
        snap[sp] = {}
        for i, (pmid, ab) in enumerate(abstracts(path)):
            snap[sp][pmid] = sorted(set(map(aug_key, augment_malaria_effects(ab))))
            if i < recovery_limit:
                rev = reviewer_data(ab)
                if rev:
                    extracted = extract_malaria_effects(ext, ab)
                    eff = [r for r in rev if r["is_effect"]]
                    am += recover(rev, extracted)[0]
                    em += recover(eff, extracted)[0]
                    at += len(rev); et += len(eff)
        recov[sp] = (et, em, at, am)
    return recov, snap


def fmt_recov(recov):
    lines = ["specialty   eff_total eff_match  eff%    all_total all_match all%"]
    for sp, (et, em, at, am) in recov.items():
        lines.append(f"{sp:10s}  {et:8d} {em:8d}  {(em/et*100 if et else 0):5.1f}%  "
                     f"{at:8d} {am:8d} {(am/at*100 if at else 0):5.1f}%")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot")
    ap.add_argument("--compare")
    ap.add_argument("--limit", type=int, default=RECOVERY_LIMIT)
    args = ap.parse_args()
    recov, snap = run(args.limit)
    print(fmt_recov(recov))
    if args.snapshot:
        Path(args.snapshot).write_text(json.dumps({"recov": recov, "snap": snap}), encoding="utf-8")
        print(f"\nwrote snapshot {args.snapshot}")
    if args.compare:
        old = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        osnap = old["snap"]
        dropped = added = ndoc = 0
        for sp in snap:
            for pmid, keys in snap[sp].items():
                ndoc += 1
                oldkeys = set(map(tuple, osnap.get(sp, {}).get(pmid, [])))
                newkeys = set(map(tuple, keys))
                miss = oldkeys - newkeys
                if miss:
                    dropped += len(miss)
                    print(f"REGRESSION {sp} {pmid}: dropped {miss}")
                added += len(newkeys - oldkeys)
        print(f"\nADDITIVITY over {ndoc} abstracts: dropped={dropped}  added={added}")
        print("STRICT SUPERSET OK" if dropped == 0 else "!!! SUPERSET VIOLATED !!!")
        for sp in recov:
            oet, oem, oat, oam = old["recov"][sp]
            net, nem, nat, nam = recov[sp]
            print(f"{sp}: eff {oem}/{oet} ({oem/oet*100 if oet else 0:.1f}%) -> "
                  f"{nem}/{net} ({nem/net*100 if net else 0:.1f}%)  (+{nem-oem})  | "
                  f"all {oam}/{oat} -> {nam}/{nat} (+{nam-oam})")
