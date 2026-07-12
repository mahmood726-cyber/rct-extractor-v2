"""
Arbor-style recall-optimization pilot for the malaria effect extractor.

Truth-first design (see AGENTS.md "Held-out evaluation"):
  - Objective: maximise EFFECT RECALL of the core+augmenter extractor on
    malaria abstracts, against the reviewer_data reference parser.
  - Precision GUARD: a candidate may not win by over-extracting. Precision
    (extracted items that match a reviewer-reported effect) must not fall
    below the frozen baseline minus PRECISION_SLACK.
  - Split discipline: a single seeded split is frozen up front. E_dev is used
    for all tuning/model-selection; E_test is read ONCE for the final number.
    The E_test number is the headline; E_dev numbers are diagnostics only.

Gold note (honest caveat): the "gold" here is reviewer_data(), a permissive
"<effect label> value (95% CI lo-hi)" parser run over the SAME abstract. It is
a broader, independent reference than the extractor's pattern library, so
recall-against-reference is meaningful, but it is a silver standard, not human
adjudication. Both recall and precision use the same reference, so the guard is
internally consistent.

Usage:
  python pilot/recall_pilot.py build              # build + freeze the split
  python pilot/recall_pilot.py score --split dev  # diagnostic (tune here)
  python pilot/recall_pilot.py score --split test # FINAL gate (read once)
  python pilot/recall_pilot.py baseline           # dev+test baseline anchor
"""
import argparse, hashlib, io, json, random, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor
from rct_extractor._engine.specialties.malaria_effects import extract_malaria_effects
from scripts.malaria.validate_against_ma import reviewer_data, close

CORPUS = ROOT / "data/field_portability/malaria/malaria_matched.jsonl"
SPLIT_DIR = Path(__file__).resolve().parent / "splits"
MANIFEST = SPLIT_DIR / "manifest.json"
SEED = 20260619          # frozen; recorded in the manifest
DEV_FRAC = 0.70
PRECISION_SLACK = 0.02   # candidates may not drop precision below baseline - this


def _sha256(path):
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def load_corpus():
    """pmid -> abstract, for abstracts long enough to carry an effect sentence."""
    out = {}
    for line in CORPUS.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        ab = d.get("abstract")
        pmid = str(d.get("pmid") or d.get("study_id") or "")
        if ab and pmid and len(ab) > 40:
            out[pmid] = ab
    return out


def build_universe(corpus):
    """Eligible eval set = abstracts with >=1 effect-labelled reviewer datum."""
    universe = {}
    for pmid in sorted(corpus):           # sorted -> deterministic pre-shuffle order
        eff = [r for r in reviewer_data(corpus[pmid]) if r["is_effect"]]
        if eff:
            universe[pmid] = eff
    return universe


def make_split():
    corpus = load_corpus()
    universe = build_universe(corpus)
    pmids = sorted(universe)
    rng = random.Random(SEED)
    rng.shuffle(pmids)
    cut = int(len(pmids) * DEV_FRAC)
    dev, test = sorted(pmids[:cut]), sorted(pmids[cut:])
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    (SPLIT_DIR / "dev.txt").write_text("\n".join(dev) + "\n", encoding="utf-8")
    (SPLIT_DIR / "test.txt").write_text("\n".join(test) + "\n", encoding="utf-8")
    manifest = {
        "created_utc_note": "stamp after run; Date.now unavailable in-harness",
        "seed": SEED,
        "dev_frac": DEV_FRAC,
        "corpus": str(CORPUS.relative_to(ROOT)),
        "corpus_sha256": _sha256(CORPUS),
        "corpus_lines": len(corpus),
        "universe_size": len(universe),
        "n_dev": len(dev),
        "n_test": len(test),
        "gold_effects_dev": sum(len(universe[p]) for p in dev),
        "gold_effects_test": sum(len(universe[p]) for p in test),
        "metric": "effect recall vs reviewer_data; precision guard vs same reference",
        "match_tol": "close(): 5% relative on point + each CI bound",
        "precision_slack": PRECISION_SLACK,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return manifest


def _score_abstract(ext, ab, gold_eff):
    """Return (n_gold, n_recovered, n_extracted, n_extracted_matching_gold)."""
    extracted = extract_malaria_effects(ext, ab)
    recovered = 0
    for r in gold_eff:
        if any(close(e.get("effect_size"), r["value"])
               and close(e.get("ci_lower"), r["ci_lower"])
               and close(e.get("ci_upper"), r["ci_upper"]) for e in extracted):
            recovered += 1
    matched_ext = 0
    for e in extracted:
        if any(close(e.get("effect_size"), r["value"])
               and close(e.get("ci_lower"), r["ci_lower"])
               and close(e.get("ci_upper"), r["ci_upper"]) for r in gold_eff):
            matched_ext += 1
    return len(gold_eff), recovered, len(extracted), matched_ext


def score(split):
    pmids = [p for p in (SPLIT_DIR / f"{split}.txt").read_text(
        encoding="utf-8").splitlines() if p.strip()]
    corpus = load_corpus()
    universe = build_universe(corpus)
    ext = EnhancedExtractor()
    g = rec = ext_n = ext_match = 0
    t0 = time.time()
    for pmid in pmids:
        if pmid not in universe:
            continue
        a, b, c, d = _score_abstract(ext, corpus[pmid], universe[pmid])
        g += a; rec += b; ext_n += c; ext_match += d
    recall = rec / g if g else 0.0
    precision = ext_match / ext_n if ext_n else 0.0
    out = {"split": split, "n_abstracts": len(pmids), "gold_effects": g,
           "recovered": rec, "recall": round(recall, 4),
           "extracted": ext_n, "extracted_matching": ext_match,
           "precision": round(precision, 4),
           "elapsed_s": round(time.time() - t0, 1)}
    print(json.dumps(out))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "score", "baseline"])
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    args = ap.parse_args()
    if args.cmd == "build":
        make_split()
    elif args.cmd == "score":
        score(args.split)
    else:
        print("=== BASELINE (current hand-tuned extractor) ===")
        score("dev")
        score("test")
