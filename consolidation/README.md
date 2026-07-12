# Extraction consolidation — the primary-outcome selector + the precision ladder

**Date:** 2026-07-12 · measured, held-out. Full write-up: `C:\Projects\EXTRACTION-CONSOLIDATION-2026-07-12.md`.

## What this is
The consolidated fix for the **mis-grabbed-HR bug class** (CANVAS renal 0.60 vs MACE 0.86;
SAVOR on-treatment 1.03 vs ITT 1.00) plus the **verification-leg precision ladder**.

Root cause (verified in `F:\ubcma\regpub_pilot\src\extract.py`): both the registry path
(`primaries[0]` / `analyses[0]`) and the abstract path (`EFFECT_RE.search` = first prose
match) did **positional first-match selection** with no ranking by outcome primacy, analysis
population, or scope. The number was parsed correctly; the wrong ROW was chosen.

## The fix
`rct_extractor/_engine/selection/select_primary_effect.py` — a pure ranker that scores
candidate effect rows by outcome_type (PRIMARY), population (ITT/FAS up; per-protocol /
on-treatment-analysis / completers / evaluable / safety-set down — but an ITT marker
overrides, and mITT is a valid primary set), scope (subgroup / single-dose down; a
**stratified** primary analysis is NOT a subgroup), and effect completeness (has-CI). Ties
among structurally-equal rows keep SOURCE ORDER and raise an `ambiguous` flag so a genuine
co-primary contest is routed to verification instead of silently guessed.

## Reproduce
```
cd consolidation
python pull_heldout.py     # regenerate held-out sample from AACT (excludes the tuning NCTs)
python eval_ladder.py      # Part A (20 hand-audited) + Part B (2090-trial injection)
cd ../rct_extractor/_engine/selection && python test_select_primary_effect.py   # 8/8
```
Needs the AACT DuckDB (`AACT_DUCKDB`) and `C:\Projects\atmosphere-plausibility` for the
external-plausibility leg.

## Measured results (held-out)
**Part A — selection accuracy vs hand gold, 20 held-out multi-candidate trials:**

| method | clean | ambiguous | overall |
|---|---|---|---|
| naive first-row (AACT is primary-first) | 8/8 | 10/10 | **1.00** |
| "grab the striking number" (prose model) | 2/8 | 0/10 | **0.11** |
| **selector** | 8/8 | 10/10 | **1.00** (+ flags 11/12 ambiguous) |

On structured registry data (primary-first) the naive path is already right — the selector is
non-inferior. The selector's lever is the **prose/abstract/PDF regime** (no primary-first
order): there it takes multi-candidate selection from **0.11 → 1.00**.

**Part B — verification-leg recall + false-alarm (2090-trial injection):**

| leg | FAR (clean) | recall: row-swap→secondary | recall: scale ×10 |
|---|---|---|---|
| internal-triangulation (provenance gate) | **0.05** | **1.00** | 0.05 |
| external-plausibility (atmosphere) | 0.02 | 0.02 (blind) | 0.37 |
| cross-vendor consensus | — | NOT RUN headless | — |

Internal triangulation catches 100% of the dominant wrong-row/wrong-population error at 5%
false-alarm; external plausibility is blind to it (as its own pre-registration states) and
earns its keep only on decimal/scale errors. The two are complementary, not redundant.
