# Real-PDF Accuracy — Parkinson's disease (`parkinsons`)

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold tuples are
> harvested by an extractor-INDEPENDENT regex (`scripts/pdf_eval/build_gold_from_abstracts.py`,
> `harvest_effects`) over each article's own **abstract**, with a verbatim-substring
> anti-fabrication guard; the shipped extractor is then scored on the **full PDF
> body** (a different, messier surface). No gold value is produced by the extractor
> under test, and nothing is hard-coded per paper.

## Provenance note (honest)

The canonical harness sources abstracts/PDFs from NCBI E-utilities. On this build
host the `eutils.ncbi.nlm.nih.gov` subdomain is DNS-blocked (`getaddrinfo` fails)
while EuropePMC is reachable. The gold was therefore acquired with
`scripts/pdf_eval/acquire_epmc_gold.py`, which swaps **only the data source** to
EuropePMC: it imports the identical `harvest_effects`/`harvest_arm_ns` (verbatim
guard intact), downloads the real PMC PDF with the same `download_pmc_pdf` helper
(EuropePMC rendered PDF + PMC-OA tgz fallback, `%PDF`-verified), and scores on the
full PDF body via the unchanged `run_pdf_eval.py`. Each gold record stores
`source="europepmc"` and the verbatim quote, so every tuple is independently
checkable.

## Dataset

- **22 real PMC Open-Access Parkinson's-disease RCT articles**, **51 gold effect
  tuples** (each an explicit ratio + 95% CI stated in the abstract).
- Gold: `data/pdf_eval/gold_parkinsons.jsonl` (one JSON object per paper, with the
  abstract and every verbatim quote). PDFs are gitignored (large/transient).

## Results (match tol: point ±0.02/2%, CI ±0.03/3%)

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 51 | 47 (92%) | 0 | 4 (8%) |
| pdf_raw  | 51 | **50 (98%)** | 0 | 1 (2%) |
| pdf_pp   | 51 | 50 (98%) | 0 | 1 (2%) |

Among matched pairs on pdf_raw (n=50): effect **type 100%**, CI-low 100%,
CI-high 100%, point(exact 2dp) 98%.

**Real-PDF accuracy = 98% (50/51) ≥ 95% target.** (pdf_raw is the surface a user
actually gets; it scores higher than the abstract surface because the PDF body
restates several effects in cleaner forms than the abstract glue.)

## Honest remaining gap (1 tuple)

- `PMC13042752` missed: gold `HR 0.27, 95% CI 0.14–0.52`, quote
  `"subtype (HR [time to death]: 0.27, 95% CI: 0.14, 0.52)"`. A bracketed outcome
  descriptor `[time to death]` sits between the `HR` keyword and its value, which
  breaks the core's ratio→point glue. This is a single occurrence (n=1); it was
  not patched in the shared core because a one-sample change there is not a
  demonstrably generalizable fix and risks corpus-wide regressions. Reported as a
  residual rather than special-cased.

The effect-tuple extraction is performed by the shared core
(`enhanced_extractor_v3.py`), so this number reflects the same disease-agnostic
CI/effect logic measured across the existing 17 specialties; the `parkinsons`
module adds endpoint vocabulary (MDS-UPDRS, ON/OFF time, dyskinesia, LEDD, PDQ-39,
SAPS-PD, …), subspecialty routing, and arm-level labels.
