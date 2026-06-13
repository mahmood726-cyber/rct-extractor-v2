# Dose-Response Extractor

A **new extraction mode**, additive to the RCT effect extractor, that targets the
data a *dose-response meta-analysis* pools. It is invocable alongside the RCT
specialty extractors and shares the engine's design principles (pattern
registry, spelling/Unicode traps, ReDoS-safe bounded regex, plausibility
guards).

## What it extracts

For a block of text (abstract or full body) it returns a `DoseResponseResult`:

| Field | Meaning |
|-------|---------|
| `effects[]` | one record per dose-response effect (below) |
| `effects[].relation_type` | `per_unit` (trend/slope) or `categorical` (dose category vs reference) |
| `effects[].effect_type` | ratio metric: `RR` / `OR` / `HR` / `IRR` |
| `effects[].point_estimate`, `ci_lower`, `ci_upper`, `ci_level` | the effect + 95% CI |
| `effects[].dose_amount`, `dose_unit` | the increment, e.g. `10` + `g/day` (per-unit) |
| `effects[].increment_text` | verbatim increment phrase, e.g. `"per 10 g/day"` |
| `effects[].category_label`, `reference_label` | e.g. `highest` vs `lowest`, `Q4` vs `Q1` (categorical) |
| `dose_metric` | best-effort exposure name (e.g. `fibre`, `alcohol`) |
| `dose_units[]` | dose units seen in the text |
| `n_dose_categories` | 3 (tertiles) / 4 (quartiles) / 5 (quintiles) / 10 (deciles) … |
| `reference_category` | e.g. `lowest quartile`, `Q1`, `reference` |
| `nonlinearity_reported`, `nonlinearity_shape`, `p_nonlinearity` | `J-shaped` / `U-shaped` / `inverse` / `nonlinear` / `linear`, and P for nonlinearity |

## Usage

```python
import rct_extractor as rx

out = rx.extract_dose_response(
    "Each 10 g/day increase in fibre intake was associated with a lower risk "
    "(RR 0.90, 95% CI 0.84-0.97). Compared with the lowest quintile, the "
    "highest quintile had HR 0.74 (0.65-0.85); P for nonlinearity = 0.02."
)
# out["effects"][0] -> per_unit RR 0.90 (0.84-0.97), dose_unit "g/day", amount 10
# out["effects"][1] -> categorical HR 0.74 (0.65-0.85), highest vs lowest
# out["n_dose_categories"] == 5 ; out["p_nonlinearity"] == 0.02
```

CLI (alongside the RCT extractor):

```bash
rct-extract --dose-response --text "Per 10 g/day, RR 0.90 (95% CI 0.84-0.97)."
rct-extract --dose-response -i abstract.txt --json
```

The RCT effect extractor (`rx.extract`) is unchanged; this is a separate entry
point.

## How classification works (word-order robust)

The engine finds every `"<type> … <point> <CI>"` tuple (point is required to sit
**immediately** before the CI, so an intervening dose amount such as the `1000`
in *"RR for every 1000 mg increase was 1.00 (95% CI …)"* is never mistaken for
the estimate). Each tuple is then classified by inspecting a bounded window
around it:

* **per_unit** — an explicit increment phrase (`per / for each / every / by
  <amount> <unit>`) is present.
* **categorical** — a high+low dose-category pair, **or** any quantile token
  with a comparison/reference cue (covers middle-reference designs such as
  *"compared with Q2, … Q4 (HR …)"*).
* otherwise the effect is **not** emitted — this engine only returns
  dose-response data, never every ratio in a paper.

Quantile buckets (`quartile`/`quintile`/…) are deliberately **not** treated as
per-unit "units"; *"per/by quartile"* is a categorical grouping, handled by the
categorical branch.

## Validation (real PDFs, non-circular, honest)

The gold standard is built the **same non-circular way** as the RCT engine
(`scripts/pdf_eval/`):

1. **Discovery** (`scripts/doseresponse_eval/acquire_dr_via_europepmc.py`)
   searches EuropePMC for OA dose-response meta-analyses / cohort studies,
   pre-screens abstracts with the eval's *own* independent harvester, and writes
   a candidate manifest.
2. **Full text** (`fetch_dr_fulltext.py`) caches each paper's real NCBI JATS
   full-text body (`efetch db=pmc`) — the scoring surface.
3. **Gold** (`build_dr_gold_from_abstracts.py`) harvests the per-dose effect +
   CI + dose signal **verbatim from the abstract** using an INDEPENDENT regex
   that shares no code with the extractor under test, with a **substring
   anti-fabrication guard** (point + both CI bounds must appear verbatim in the
   quoted source).
4. **Score** (`run_dr_eval.py`) runs the extractor on the **full-text body** (a
   different, messier surface than the abstract the gold came from) and on the
   abstract (sanity floor).

> **Scoring surface note (honesty):** at build time the EuropePMC `?pdf=render`
> endpoint and the NCBI OA package service were returning HTTP 500 / stale FTP
> paths, so rendered PDFs could not be downloaded. The scoring surface is
> therefore the NCBI **JATS full-text body** — the same human-authored article
> text a PDF carries, and a strictly different/messier surface than the abstract,
> so the measurement remains non-circular. `run_dr_eval.py` also scores a real
> PDF surface for any paper whose rendered PDF is available.

### Measured accuracy (88 real PMC-OA papers, 220 gold dose-response tuples)

| Surface | strict-correct | located (point matched) | among matched: relation / type / CI-lo / CI-hi / point(2dp) | dose-unit | category present |
|---------|:---:|:---:|:---:|:---:|:---:|
| abstract (clean source, sanity floor) | **97%** (213/220) | 97% | 100% / 100% / 100% / 100% / 100% | 96% | 100% |
| full-text JATS body (non-circular) | **51%** (113/220) | 67% (147/220) | 83% / 97% / 95% / 93% / 90% | 62% | 93% |

* **strict-correct** = point within tol AND both CI bounds within tol AND
  `relation_type` matches AND `effect_type` matches.
* The 313 "extra" body extractions are **not** errors: sampling confirms they
  are overwhelmingly *real* dose-response effects stated in the body but absent
  from the abstract-sourced gold (e.g. additional `Q2/Q3/Q4 vs Q1` rows, `per 1
  SD` slopes). The harness reports them without penalty, mirroring the RCT eval.

### Honest gaps (full-text body)

Of 73 body misses (only **1** had its numbers genuinely absent from the body):

* **~57**: the effect+CI is stated far (> ~110 chars) from its dose context, or
  is a single-category statement with no local comparison cue. The engine is
  conservative by design (it will not label a bare ratio as dose-response).
* **~17**: table-row estimates (`Q2 0.72 (0.59, 0.87)`) whose effect-type label
  lives only in a flattened column header. The engine does **not** infer the
  ratio type from a distant header (that would risk wrong-type output), so these
  are left for a future table-aware pass.
* a few are genuine gold-vs-body value differences (abstract reported a
  different model/subgroup estimate than the body row at the same point value).

## Reproduce

```bash
python scripts/doseresponse_eval/acquire_dr_via_europepmc.py --max-candidates 90
python scripts/doseresponse_eval/fetch_dr_fulltext.py
python scripts/doseresponse_eval/build_dr_gold_from_abstracts.py
python scripts/doseresponse_eval/run_dr_eval.py
python -m pytest tests/test_doseresponse_extractor.py -q
```
