Mahmood Ahmad
Tahir Heart Institute
mahmood.ahmad2@nhs.net

Protocol: Deterministic Effect Estimate Extraction from RCT PDFs

This protocol describes the planned methods submission for RCT Extractor v10.3, a deterministic pipeline for extracting effect estimates from randomized trial PDFs. The audited corpus comprises 407 published RCT PDFs and a 33-trial ClinicalTrials.gov validated subset used as the primary external benchmark. The extraction stack combines regex libraries, finite-state tokenization, table parsing, OCR fallback, and team-of-rivals consensus voting with source-text provenance. Primary reporting will focus on sensitivity for primary endpoint extraction, with confidence intervals and pattern-level regression checks reported from the frozen validation set. Secondary analyses will summarize performance across nine effect types and leave-one-type-out stability rather than pooled clinical effect estimates. All code, benchmark artifacts, and the static E156 reader are archived repo-relatively for deterministic review. The protocol does not claim regulatory-grade extraction and is limited by English-language, cardiology-heavy validation data and remaining generalizability questions.

Outside Notes

Type: protocol
Primary estimand: Sensitivity
App: RCT Extractor v10.3
Code: https://github.com/mahmood726-cyber/rct-extractor-v2
Date: 2026-03-26
Validation: DRAFT

References

1. Royston P, Parmar MK. Restricted mean survival time: an alternative to the hazard ratio for the design and analysis of randomized trials with a time-to-event outcome. BMC Med Res Methodol. 2013;13:152. doi:10.1186/1471-2288-13-152.
2. Tierney JF, Stewart LA, Ghersi D, Burdett S, Sydes MR. Practical methods for incorporating summary time-to-event data into meta-analysis. Trials. 2007;8:16. doi:10.1186/1745-6215-8-16.
