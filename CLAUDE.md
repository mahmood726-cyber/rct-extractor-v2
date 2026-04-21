# CLAUDE.md — RCT Extractor v5.0

## Project Overview
RCT effect estimate extraction from published PDFs. Extracts HR, OR, RR, MD, SMD, ARD, IRR, GMR and their confidence intervals using 180+ regex patterns, table parsing, and team-of-rivals consensus. Stripped to essentials in v5.0.

## Current Plan
See STRAIGHT_PATH_PLAN.md — Phase 0 (strip) complete. Next: Phase 1 (gold standard).

## Key Architecture
- **BaseExtractor + variants**: pattern-based extraction per effect type
- **Team of Rivals**: multiple extractors compete, consensus via tolerance-based clustering
- **Proof-Carrying Numbers (PCN)**: every extraction includes hash, provenance, validator outcomes
- **FSM tokenizer**: state machine for numeric token extraction
- **PDF pipeline**: `pdf_extraction_pipeline.py` orchestrates text + table extraction

## Testing
```bash
# Run all tests
python -m pytest tests/ --tb=short -q

# Critical test suites
python -m pytest tests/test_proof_carrying_numbers.py
python -m pytest tests/test_team_of_rivals.py
```

## Critical Warnings
- **ReDoS**: all `[\w\s]+?` patterns must be bounded: `[\w\s]{1,80}?`
- **FSM tokenizer**: `-?\d+` captures range dashes as negatives — use lookbehind `(?<![0-9)])-`
- **`all()` on empty list** is vacuously True — always check `len(evaluated) > 0`
- **`if value:`** drops 0.0 — use `is not None` for ANY numeric field (CI bounds, p-values, etc.)
- **`parseFloat(x) || fallback`** drops valid zero — use `isFinite()` check instead
- **European decimal regex** `(\d),(\d{1,2})` corrupts CI comma-pairs — add `(?<!\.\d)` lookbehind
- **U+037E** (Greek question mark) is visually identical to semicolon — common PDF artifact, normalize it
- **New EffectType** must be added to ALL auxiliary paths (plausibility checks, SE calculation, text normalization), not just pattern_map
- **Consensus**: use tolerance-based clustering, not `round(value, 3)` dict keys
- **Grade F**: majority-based (not any pairwise). Critic: only on disagreement
- **CI ordering**: consistent `<=` across all modules
- **PCN hash**: must include check results + always recompute (anti-forgery)
- **OCR**: Cl→CI only in statistical context (not chemistry "serum Cl")
- **Negative context**: meta-analysis/review patterns removed (valid pooled estimates)

## Do NOT
- Use `eval()` anywhere
- Fabricate NCT IDs, DOIs, or gold standard reference data
- Use unbounded regex quantifiers (`+?`, `*?`) on user-controlled text
- Compare floats with `===` or exact equality
- Use `round(value, N)` for clustering/grouping (use tolerance-based)

## Workflow Rules (from 1,600+ message usage analysis)

### Test-First Verification (CRITICAL)
- **Never say "done" without test verification.** After any round of fixes, run the full test suite and report pass/fail counts before declaring complete.
- **Test each feature immediately upon implementation** — do not batch test runs at the end.
- If fixes introduce new failures, fix those too before declaring done. Track fixes with IDs (e.g., P0-1, P1-3).

### Data Model Verification Before Implementation
- **Before implementing any feature**, grep the codebase for all data objects/structures related to that feature. Verify actual property names, types, and where they are set.
- **Never guess property names or element IDs.** Confirm properties exist in the actual data model before writing access paths.

### Context Persistence
- **Save review findings to files** (e.g., `review-findings.md`) so they persist across sessions.
- **Never report features as "missing" without evidence.** Search thoroughly with Grep before claiming a feature is absent.

### Data Integrity
Never fabricate or hallucinate identifiers (NCT IDs, DOIs, trial names, PMIDs). If you don't have the real identifier, say so and ask the user to provide it. Always verify identifiers against existing data files before using them in configs or gold standards.

### Multi-Persona Reviews
When running multi-persona reviews, run agents sequentially (not in parallel) to avoid rate limits and empty agent outputs. If an agent returns empty output, immediately retry it before moving on. Never launch more than 2 sub-agents simultaneously.

### Fix Completeness
When asked to "fix all issues", fix ALL identified issues in a single pass — do not stop partway. After applying fixes, re-run the relevant tests/validation before reporting completion. If fixes introduce new failures, fix those too before declaring done.

### Scope Discipline
Stay focused on the specific files and scope the user requests. Do not survey or analyze files outside the stated scope. When editing files, triple-check you are editing the correct file path — never edit a stale copy or wrong directory.

### Regression Prevention
Before applying optimization changes to extraction or analysis pipelines, save a snapshot of current accuracy metrics. After each change, compare against the snapshot. If any trial/metric regresses by more than 2%, immediately rollback and try a different approach. Never apply aggressive heuristics without isolated testing first.
