# Malaria Extractor — Independent LLM Adjudication

Independent judge re-derives each effect estimate from the source text and rules
on whether the extractor's (type, value, CI) is correct. This is cross-method
validation (regex extractor vs LLM reading) -- with `--provider openai`, also
cross-vendor.

## Round 1 — Claude (Opus) as independent judge, 2026-05-31
- Sample: **33** extractions, type-stratified (3 per effect type) across the
  2,257-PDF corpus (`adjudication_sample.jsonl`).
- **Adjudicated accuracy: 31/33 = 93.9%** (full match: type + value + CI).
- The 2 errors are **type mislabels** (value + CI were correct) and **both come
  from the core engine**, not the malaria layer:
  - `aRR, 0.99 [0.77-1.28]` typed `ARD` — aRR is an adjusted *risk ratio* (RR).
  - bare `61% (95% CI 52-70)` typed `MD` — a percentage/proportion, not a mean
    difference.
- Every malaria-specific extraction in the sample (efficacy %, RevMan rows,
  bracketed adjusted ratios, NNT, GMR, arm-level) was correct.
- Verdicts: `adjudication_verdicts.jsonl`.

## Round 2 — external GPT (run when an API key is available)
```
python scripts/malaria/build_adjudication_sample.py 50
set OPENAI_API_KEY=sk-...
python scripts/malaria/adjudicate_with_llm.py --provider openai --model gpt-4o
```
Writes `adjudication_llm_verdicts.jsonl` and prints the GPT-judged accuracy for a
cross-vendor second opinion. (`--provider anthropic` also supported.)

## Reading
- This is **machine adjudication**, stronger than self-consistency but still not
  a human-certified gold. For publication, confirm a sample with a domain expert.
- The two core type-mislabels are candidates for a future core-engine fix
  (aRR/aHR/aOR adjusted-ratio typing; guarding bare `%` against MD).
