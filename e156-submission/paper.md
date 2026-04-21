Mahmood Ahmad
Tahir Heart Institute
mahmood.ahmad2@nhs.net

Deterministic Effect Estimate Extraction from RCT PDFs

Will a deterministic regex pipeline extract effect estimates from randomized controlled trial PDFs accurately enough for automated meta-analysis? We applied the RCT Extractor v10.3 to 407 published trial PDFs spanning nine effect types including hazard ratios, odds ratios, risk ratios, mean differences, and standardized mean differences. The system brings together 180 regex patterns, a finite-state-machine tokenizer, and team-of-rivals consensus voting through pdfplumber, PyMuPDF, table parsing, and OCR with provenance tracking attaching source text and content hash to every extraction. We used ClinicalTrials.gov registry data for 33 validated trials, the pipeline achieved 97.7 percent sensitivity (95% CI 92.0-99.7) for primary endpoint extraction (with 757 pattern-level tests passing across all types). Leave-one-type-out analysis confirmed stable performance across all nine effect measures in multiple publication formats. Deterministic extraction can serve as a scalable first-pass audit layer for systematic reviews requiring rapid effect-size verification. However, generalizability beyond English-language cardiology-heavy corpora is a limitation requiring prospective validation.

Outside Notes

Type: methods
Primary estimand: Sensitivity
App: RCT Extractor v10.3
Data: 407 published RCT PDFs, 33 ClinicalTrials.gov validated trials
Code: https://github.com/mahmood726-cyber/rct-extractor-v2
Version: 10.3
Validation: DRAFT

References

1. Royston P, Parmar MK. Restricted mean survival time: an alternative to the hazard ratio for the design and analysis of randomized trials with a time-to-event outcome. BMC Med Res Methodol. 2013;13:152. doi:10.1186/1471-2288-13-152.
2. Tierney JF, Stewart LA, Ghersi D, Burdett S, Sydes MR. Practical methods for incorporating summary time-to-event data into meta-analysis. Trials. 2007;8:16. doi:10.1186/1745-6215-8-16.
