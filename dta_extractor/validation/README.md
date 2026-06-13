# DTA extractor — validation

Two complementary, independently-honest validations of the DTA (diagnostic test
accuracy) extraction mode. They measure different things and are reported
separately; neither is allowed to borrow the other's number.

## 1. DTA70 derivation check (the maths) — 6,348 real 2×2 tables

`dta70_to_gold.py` converts the **DTA70** R package
(`mahmood789/DTA70` — 76 real DTA datasets, 6,348 study rows, each with a
complete TP/FP/FN/TN table) into `gold/dta70_2x2.json` via `pyreadr` (no R
needed).

`tests/test_dta70_derivation.py` then asserts, **for every one of the 6,348
rows**, that the engine's `TwoByTwo` derivation reproduces sensitivity,
specificity and the diagnostic odds ratio computed independently from the raw
counts, to 1e-9 / 1e-6. This validates the exact arithmetic the extractor relies
on against real-world count distributions.

It also round-trips a deterministic 1-in-53 sample of the rows through a
synthesised 2×2 sentence and confirms the count extractor recovers the exact
cells. That is a **regression** check (the text is synthesised here), **not** an
external-text accuracy claim — DTA70 carries no abstract/PDF text.

Rebuild the gold file:

```bash
python -m dta_extractor.validation.dta70_to_gold \
    --src "F:/Projects/mahmood789/DTA70/data"
```

## 2. Real-PDF accuracy (non-circular) — measured

`dta_pdf_eval.py` reproduces the RCT engine's non-circular harness
(`scripts/pdf_eval/`) for DTA:

1. **Gold is never produced by the extractor under test.** A deliberately
   minimal, independent regex (`harvest_dta_gold`, which does not import
   `dta_extractor`) reads each article's **abstract** and records sensitivity /
   specificity, keeping a value only if it appears **verbatim** as a substring of
   the quoted sentence (anti-fabrication guard).
2. The DTA extractor is then scored on the **full PDF body** — a different,
   messier surface than the abstract — so the measurement is not circular.
3. Recall = abstract-stated gold values recovered by the full-body extractor
   within an absolute tolerance of 0.02 (on the 0–1 scale).

### Measured result (offline, real PMC-OA PDFs)

Run against the real PMC-OA PDFs already on disk under
`data/field_portability/*/rct_trial_pdfs/` whose cached abstracts state both
sensitivity and specificity (i.e. genuine diagnostic-accuracy papers that landed
in the RCT corpora):

| metric | value |
|---|---|
| papers scored | 22 |
| gold Se/Sp values | 69 |
| recovered on full PDF body | 64 |
| **overall recall** | **0.928** |
| sensitivity recall | 34/35 = 0.971 |
| specificity recall | 30/34 = 0.882 |

(`tol = 0.02`; full per-paper detail in `dta_pdf_eval_report.json`.)

```bash
python -m dta_extractor.validation.dta_pdf_eval --offline
```

### Honest gaps / caveats

- **Sample size is small (22 papers / 69 values).** These are the DTA papers that
  happened to be present in the RCT corpora on disk; it is a real but modest
  gold set, not a large purpose-built DTA corpus.
- **The online acquisition path is built but could not run here.** On this host,
  EuropePMC's full-text retrieval service was returning HTTP 500 for the PDF
  render endpoint and 404 for `fullTextXML` (their own documented example article
  404'd too), and NCBI's OA file mirror was unreachable (anonymous FTP blocked,
  HTTPS mirror 404). The abstract/search API worked fine. When the full-text
  service recovers, `python -m dta_extractor.validation.dta_pdf_eval
  --max-download 60` runs the identical method over a freshly-downloaded corpus.
- **The 0.928 figure is a recall measure** — does the full-body extractor recover
  the Se/Sp the abstract states. It is not a precision/2×2-cell accuracy claim;
  raw 2×2 cells are rarely stated in abstracts, so 2×2-cell extraction is
  exercised by the DTA70 round-trip and unit tests rather than this corpus.
- The largest single fix found during evaluation was typographic-ligature
  normalisation (PDF "speci‑<fi-ligature>‑city"); NFKC normalisation now happens
  inside `dta_extractor.extract`, which moved recall from 0.841 → 0.928.
