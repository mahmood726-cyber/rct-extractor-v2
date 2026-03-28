Mahmood Ahmad
Tahir Heart Institute
author@example.com

Deterministic Effect Estimate Extraction from RCT PDFs

Can a deterministic regex pipeline extract effect estimates from randomized controlled trial PDFs accurately enough for automated meta-analysis? We applied RCT Extractor v10.3 to 407 published trial PDFs spanning nine effect types including hazard ratios, odds ratios, risk ratios, mean differences, and standardized mean differences. The system chains 180 regex patterns, a finite-state-machine tokenizer, and team-of-rivals consensus voting through pdfplumber, PyMuPDF, table parsing, and OCR with provenance tracking attaching source text and content hash to every extraction. Against ClinicalTrials.gov registry data for 33 validated trials, the pipeline achieved 97.7 percent sensitivity (95% CI 92.0-99.7) for primary endpoint extraction, with 757 pattern-level tests passing across all types. Leave-one-type-out analysis confirmed stable performance across all nine effect measures and multiple publication formats. Deterministic extraction can serve as a scalable first-pass audit layer for systematic reviews requiring rapid effect-size verification from source documents. However, generalizability beyond English-language cardiology-heavy corpora remains a limitation requiring prospective validation on broader clinical domains.

Outside Notes

Type: methods
Primary estimand: Sensitivity
App: RCT Extractor v10.3
Data: 407 published RCT PDFs, 33 ClinicalTrials.gov validated trials
Code: https://github.com/mahmood726-cyber/rct-extractor-v2
Version: 10.3
Validation: DRAFT

References

1. Marshall IJ, Noel-Storr A, Kuber J, et al. Machine learning for identifying randomized controlled trials: an evaluation and practitioner's guide. Res Synth Methods. 2018;9(4):602-614.
2. Jonnalagadda SR, Goyal P, Huffman MD. Automating data extraction in systematic reviews: a systematic review. Syst Rev. 2015;4:78.
3. Borenstein M, Hedges LV, Higgins JPT, Rothstein HR. Introduction to Meta-Analysis. 2nd ed. Wiley; 2021.
