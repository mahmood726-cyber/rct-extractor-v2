# Recall-optimization pilot — Codex handoff (heavy iteration)

Arbor-style autonomous optimization of the malaria effect extractor, under a
**frozen held-out split** (AGENTS.md "Held-out evaluation"). Design + truth-gate
were set by Claude; **Codex runs the heavy proposal/scoring loop** (separate quota).

## The task
Maximise **effect recall** of the core+augmenter extractor on malaria abstracts,
**without dropping precision** (no winning by over-extracting).

## Files
- Harness/scorer: `pilot/recall_pilot.py` (deterministic, offline, no network).
- Frozen split: `pilot/splits/{dev,test}.txt` + `manifest.json` (seed 20260619). **Do not regenerate.**
- Baseline anchor: `pilot/BASELINE.json`.

## Baseline (current HEAD, do not beat by cheating)
- dev:  recall 0.9617, precision 0.8482
- test: recall 0.9685, precision 0.8376  ← headline reference, read ONCE

## What you may edit
- **Additive only, preferred:** `rct_extractor/_engine/specialties/malaria_effects.py`
  (add/relax regex patterns the core misses). Additive edits are guarded by the
  existing strict-superset benchmark — keep it green:
  `python scripts/benchmark_augmenter_offline.py --snapshot /tmp/base.json` then
  `--compare /tmp/base.json` must print `STRICT SUPERSET OK`.
- Core pattern tweaks are allowed but higher-risk; if you touch core, run `pytest -q` too.

## The loop (each round)
1. Propose 1–3 concrete pattern refinements (a hypothesis + the regex change).
2. Apply to a worktree/branch; run `python pilot/recall_pilot.py score --split dev`.
3. **ACCEPT a candidate iff** `recall_dev > 0.9617` **AND** `precision_dev >= 0.8282`
   (baseline precision − 0.02). Otherwise prune it and record WHY it failed
   (negative constraint) so you don't re-propose the same dead end.
4. Keep the running best; iterate.

## Tuning discipline (non-negotiable)
- **Tune on dev ONLY.** Do **not** run `score --split test` during iteration.
- Read `--split test` exactly **once**, on your single best dev candidate, at the end.

## Budget cap (bounded)
- Stop after **15 proposal rounds** or **~1.5M output tokens**, whichever first.
- Also stop early if 3 consecutive rounds produce no dev-accepted candidate.

## Final gate + KILL CRITERION
Run once on the best candidate:
`python pilot/recall_pilot.py score --split test`
- **WIN** iff `recall_test > 0.9685` AND `precision_test >= 0.8176`.
- **Otherwise → report the honest null.** A change that doesn't beat baseline on
  the frozen test split within budget is a non-result. Do NOT re-tune against test
  to manufacture a pass — that re-leaks the split and rebuilds an in-sample artifact
  (the exact `conformal-ma` failure this discipline exists to prevent).

## Expectation (truth-first)
Recall headroom is only ~3% and precision is already modest, so a null is a
likely and fully acceptable outcome. Report either the confirmed test-split gain
(with the patterns added) or the honest null with the negative constraints learned.
