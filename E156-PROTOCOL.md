# E156 Protocol — `rct-extractor-v2`

This repository is the source code and dashboard backing an E156 micro-paper on the [E156 Student Board](https://mahmood726-cyber.github.io/e156/students.html).

---

## `[143]` Deterministic Effect Estimate Extraction from RCT PDFs

**Type:** methods  |  ESTIMAND: Sensitivity  
**Data:** 407 published RCT PDFs, 33 ClinicalTrials.gov validated trials

### 156-word body

Can a deterministic regex pipeline extract effect estimates from randomized controlled trial PDFs accurately enough for automated meta-analysis? We applied RCT Extractor v10.3 to 407 published trial PDFs spanning nine effect types including hazard ratios, odds ratios, risk ratios, mean differences, and standardized mean differences. The system chains 180 regex patterns, a finite-state-machine tokenizer, and team-of-rivals consensus voting through pdfplumber, PyMuPDF, table parsing, and OCR with provenance tracking attaching source text and content hash to every extraction. Against ClinicalTrials.gov registry data for 33 validated trials, the pipeline achieved 97.7 percent sensitivity (95% CI 92.0-99.7) for primary endpoint extraction, with 757 pattern-level tests passing across all types. Leave-one-type-out analysis confirmed stable performance across all nine effect measures and multiple publication formats. Deterministic extraction can serve as a scalable first-pass audit layer for systematic reviews requiring rapid effect-size verification from source documents. However, generalizability beyond English-language cardiology-heavy corpora remains a limitation requiring prospective validation on broader clinical domains.

### Submission metadata

```
Corresponding author: Mahmood Ahmad <mahmood.ahmad2@nhs.net>
ORCID: 0000-0001-9107-3704
Affiliation: Tahir Heart Institute, Rabwah, Pakistan

Links:
  Code:      https://github.com/mahmood726-cyber/rct-extractor-v2
  Protocol:  https://github.com/mahmood726-cyber/rct-extractor-v2/blob/main/E156-PROTOCOL.md
  Dashboard: https://mahmood726-cyber.github.io/rct-extractor-v2/

References (topic pack: restricted mean survival time / survival meta-analysis):
  1. Royston P, Parmar MK. 2013. Restricted mean survival time: an alternative to the hazard ratio for the design and analysis of randomized trials with a time-to-event outcome. BMC Med Res Methodol. 13:152. doi:10.1186/1471-2288-13-152
  2. Tierney JF, Stewart LA, Ghersi D, Burdett S, Sydes MR. 2007. Practical methods for incorporating summary time-to-event data into meta-analysis. Trials. 8:16. doi:10.1186/1745-6215-8-16

Data availability: No patient-level data used. Analysis derived exclusively
  from publicly available aggregate records. All source identifiers are in
  the protocol document linked above.

Ethics: Not required. Study uses only publicly available aggregate data; no
  human participants; no patient-identifiable information; no individual-
  participant data. No institutional review board approval sought or required
  under standard research-ethics guidelines for secondary methodological
  research on published literature.

Funding: None.

Competing interests: MA serves on the editorial board of Synthēsis (the
  target journal); MA had no role in editorial decisions on this
  manuscript, which was handled by an independent editor of the journal.

Author contributions (CRediT):
  [STUDENT REWRITER, first author] — Writing – original draft, Writing –
    review & editing, Validation.
  [SUPERVISING FACULTY, last/senior author] — Supervision, Validation,
    Writing – review & editing.
  Mahmood Ahmad (middle author, NOT first or last) — Conceptualization,
    Methodology, Software, Data curation, Formal analysis, Resources.

AI disclosure: Computational tooling (including AI-assisted coding via
  Claude Code [Anthropic]) was used to develop analysis scripts and assist
  with data extraction. The final manuscript was human-written, reviewed,
  and approved by the author; the submitted text is not AI-generated. All
  quantitative claims were verified against source data; cross-validation
  was performed where applicable. The author retains full responsibility for
  the final content.

Preprint: Not preprinted.

Reporting checklist: PRISMA 2020 (methods-paper variant — reports on review corpus).

Target journal: ◆ Synthēsis (https://www.synthesis-medicine.org/index.php/journal)
  Section: Methods Note — submit the 156-word E156 body verbatim as the main text.
  The journal caps main text at ≤400 words; E156's 156-word, 7-sentence
  contract sits well inside that ceiling. Do NOT pad to 400 — the
  micro-paper length is the point of the format.

Manuscript license: CC-BY-4.0.
Code license: MIT.

SUBMITTED: [ ]
```


---

_Auto-generated from the workbook by `C:/E156/scripts/create_missing_protocols.py`. If something is wrong, edit `rewrite-workbook.txt` and re-run the script — it will overwrite this file via the GitHub API._