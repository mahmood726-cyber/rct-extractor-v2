"""
Negative Controls Dataset for RCT Extractor
=============================================

Contains text samples that should NOT produce effect extractions.
Used to measure false positive rate (precision denominator).

Categories:
1. Protocol papers (no results)
2. Secondary/post-hoc analyses (derived effects)
3. Observational studies (non-RCT)
4. Review articles (aggregated effects)
5. Editorials/commentaries
6. Methods descriptions (example effects, not real)
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class NegativeControlType(Enum):
    """Type of negative control"""
    PROTOCOL = "protocol"
    SECONDARY_ANALYSIS = "secondary_analysis"
    OBSERVATIONAL = "observational"
    REVIEW = "review"
    EDITORIAL = "editorial"
    METHODS_EXAMPLE = "methods_example"
    NON_MEDICAL = "non_medical"


@dataclass
class NegativeControl:
    """A text sample that should NOT produce extractions"""
    id: str
    control_type: NegativeControlType
    description: str
    source_text: str
    expected_extractions: int = 0  # Should always be 0
    notes: str = ""


NEGATIVE_CONTROLS = [
    # ==========================================================================
    # PROTOCOL PAPERS - describe planned trials, no results
    # ==========================================================================
    NegativeControl(
        id="NC001",
        control_type=NegativeControlType.PROTOCOL,
        description="DAPA-CKD Protocol - describes planned primary endpoint, no results",
        source_text="""DAPA-CKD Protocol: Study Design and Rationale

The primary endpoint is a composite of sustained decline in eGFR of at least 50%,
end-stage kidney disease, or death from renal or cardiovascular causes. We hypothesize
that the hazard ratio for the primary composite will be 0.75 (dapagliflozin vs placebo),
powered at 90% with two-sided alpha of 0.05.

Sample size calculation: Assuming a hazard ratio of 0.75 and 15% annual event rate
in the placebo group, we estimate 4000 patients will be needed for adequate power.
The trial is designed to detect a clinically meaningful reduction with 95% confidence
intervals that exclude 1.0.

This protocol describes the methodology; results will be reported separately.""",
        notes="Contains hypothesized HR but no actual results"
    ),

    NegativeControl(
        id="NC002",
        control_type=NegativeControlType.PROTOCOL,
        description="EMPEROR-Preserved Protocol - sample size assumptions only",
        source_text="""EMPEROR-Preserved: Study Protocol

Design: Randomized, double-blind, placebo-controlled trial of empagliflozin in
patients with heart failure with preserved ejection fraction (HFpEF).

Statistical Considerations: The sample size was calculated assuming an event rate
of 12% per year and hazard ratio of 0.80 for the primary endpoint. With 5988 patients
and approximately 841 events, the study has 90% power.

Expected timeline: Patient enrollment from 2017-2019, primary analysis in 2021.

Primary endpoint definition: Time to first event of cardiovascular death or
hospitalization for heart failure. Secondary endpoints include total HF hospitalizations
and change in Kansas City Cardiomyopathy Questionnaire.""",
        notes="Protocol only, HR is assumed not observed"
    ),

    # ==========================================================================
    # SECONDARY/POST-HOC ANALYSES - should flag as derived, not primary
    # ==========================================================================
    NegativeControl(
        id="NC003",
        control_type=NegativeControlType.SECONDARY_ANALYSIS,
        description="Post-hoc subgroup analysis with recalculated effects",
        source_text="""Secondary Analysis: Effect of Baseline Renal Function on Treatment Response

In this post-hoc exploratory analysis of the PARADIGM-HF trial, we examined
treatment effects across baseline eGFR categories. The original trial reported
HR 0.80 (0.73-0.87) for the primary endpoint.

In our subgroup analysis:
- eGFR ≥90: HR 0.76 (0.59-0.97) [n=1,234]
- eGFR 60-89: HR 0.82 (0.71-0.95) [n=2,456]
- eGFR 30-59: HR 0.79 (0.67-0.93) [n=1,890]

These exploratory findings should be interpreted with caution given
multiple comparisons and post-hoc nature. Interaction p=0.67 suggests
no significant heterogeneity by renal function.""",
        notes="Subgroup HRs are exploratory/derived, not primary RCT results"
    ),

    NegativeControl(
        id="NC004",
        control_type=NegativeControlType.SECONDARY_ANALYSIS,
        description="Pooled analysis combining multiple trials",
        source_text="""Pooled Analysis of SGLT2 Inhibitor Trials in Heart Failure

We pooled individual patient data from DAPA-HF (n=4,744) and EMPEROR-Reduced
(n=3,730) to assess class effects of SGLT2 inhibitors.

Pooled hazard ratio for CV death or HF hospitalization: 0.74 (95% CI, 0.68-0.82)
Pooled HR for CV death: 0.86 (0.76-0.98)
Pooled HR for HF hospitalization: 0.69 (0.62-0.78)

Heterogeneity: I² = 0% for primary endpoint.

Note: These pooled estimates should not replace individual trial findings
for regulatory or clinical decision making.""",
        notes="Pooled estimates are meta-analytic, not original RCT"
    ),

    # ==========================================================================
    # OBSERVATIONAL STUDIES - non-randomized
    # ==========================================================================
    NegativeControl(
        id="NC005",
        control_type=NegativeControlType.OBSERVATIONAL,
        description="Cohort study with propensity matching",
        source_text="""Real-World Evidence: SGLT2 Inhibitors in Clinical Practice

Methods: Retrospective cohort study using Medicare claims data 2017-2022.
Propensity score matching was used to balance baseline characteristics.

Results: Among 45,678 matched pairs:
- Hazard ratio for HF hospitalization: 0.68 (95% CI, 0.62-0.74)
- Hazard ratio for all-cause mortality: 0.79 (0.71-0.88)

Limitations: As an observational study, residual confounding cannot be excluded.
These findings complement but do not replace evidence from randomized trials.""",
        notes="Observational cohort, not RCT"
    ),

    NegativeControl(
        id="NC006",
        control_type=NegativeControlType.OBSERVATIONAL,
        description="Case-control study with odds ratios",
        source_text="""Case-Control Study: Statin Use and Dementia Risk

We conducted a nested case-control study within a primary care database.
Cases (n=5,234) were matched to controls (n=20,936) on age, sex, and practice.

Odds ratio for dementia with any statin use: 0.82 (95% CI, 0.76-0.89)
Odds ratio for high-intensity statin use: 0.71 (0.62-0.81)

Duration-response analysis:
- <2 years use: OR 0.91 (0.82-1.01)
- 2-5 years use: OR 0.78 (0.69-0.88)
- >5 years use: OR 0.69 (0.58-0.82)

This observational evidence suggests potential neuroprotective effects.""",
        notes="Case-control observational study"
    ),

    # ==========================================================================
    # REVIEW ARTICLES - citing effects from other studies
    # ==========================================================================
    NegativeControl(
        id="NC007",
        control_type=NegativeControlType.REVIEW,
        description="Narrative review citing multiple trial results",
        source_text="""Review: SGLT2 Inhibitors in Cardiovascular Medicine

The SGLT2 inhibitor class has demonstrated remarkable cardiovascular benefits
across multiple randomized controlled trials.

In EMPA-REG OUTCOME, empagliflozin reduced the primary composite endpoint
(HR 0.86, 95% CI 0.74-0.99) and showed striking reductions in heart failure
hospitalization (HR 0.65, 0.50-0.85).

DECLARE-TIMI 58 showed canagliflozin reduced heart failure hospitalization
(HR 0.73, 0.61-0.88) though the primary MACE endpoint was not significant
(HR 0.93, 0.84-1.03).

The DAPA-HF trial extended benefits to patients with established heart failure
regardless of diabetes status (HR 0.74, 0.65-0.85 for primary endpoint).

Current guidelines recommend SGLT2 inhibitors as first-line therapy...""",
        notes="Review article citing HRs from other trials"
    ),

    NegativeControl(
        id="NC008",
        control_type=NegativeControlType.REVIEW,
        description="Systematic review methodology section",
        source_text="""Systematic Review: Methods for Synthesizing Hazard Ratios

When pooling hazard ratios from randomized controlled trials, several methods
are available. The generic inverse variance method weights studies by the
inverse of their variance, typically derived from confidence intervals.

For a study reporting HR 0.75 (95% CI 0.65-0.87), the standard error
can be estimated as: SE(ln HR) = (ln(0.87) - ln(0.65)) / (2 × 1.96) = 0.074

Example calculation: If Study A reports HR 0.80 (0.70-0.92) and Study B
reports HR 0.70 (0.55-0.89), the pooled estimate using fixed effects
would be approximately HR 0.76.

These methodological considerations apply to all meta-analyses of time-to-event
outcomes from clinical trials.""",
        notes="Methods/tutorial showing example calculations"
    ),

    # ==========================================================================
    # EDITORIALS/COMMENTARIES
    # ==========================================================================
    NegativeControl(
        id="NC009",
        control_type=NegativeControlType.EDITORIAL,
        description="Editorial commentary on trial results",
        source_text="""Editorial: A New Era in Heart Failure Treatment

The publication of DAPA-HF marks a watershed moment in heart failure therapy.
The hazard ratio of 0.74 for the primary endpoint represents a 26% relative
risk reduction - a magnitude of benefit rarely seen in modern trials.

What makes this finding particularly compelling is the consistency across
subgroups. Whether patients had diabetes or not, the benefit was similar.
The number needed to treat of approximately 21 to prevent one primary
endpoint event over 18 months is highly favorable.

However, questions remain. Will these benefits translate to real-world
populations? Can we afford widespread SGLT2 inhibitor use? These considerations
will shape implementation strategies going forward.

The era of quadruple therapy for HFrEF has arrived.""",
        notes="Editorial discussing trial results, not reporting them"
    ),

    # ==========================================================================
    # METHODS/EXAMPLE EFFECTS
    # ==========================================================================
    NegativeControl(
        id="NC010",
        control_type=NegativeControlType.METHODS_EXAMPLE,
        description="Statistical textbook example",
        source_text="""Chapter 12: Sample Size Calculation for Survival Studies

Example 12.3: Suppose we are planning a trial where we expect the control
group to have a 2-year survival of 60%, and we wish to detect a hazard ratio
of 0.75 with 90% power and two-sided alpha of 0.05.

Using the formula: n = 4(Z_α/2 + Z_β)² / (ln(HR))² × (1/d)

Where d is the event fraction. For our example with HR = 0.75:
n = 4(1.96 + 1.28)² / (ln(0.75))² × (1/0.4) = 776 events required

This corresponds to approximately 1,940 patients if 40% experience events.

Practice Problem: Calculate the sample size needed to detect HR 0.80 with
95% CI that excludes 1.0, assuming 25% event rate and 80% power.

Answer: Approximately 1,200 patients with 300 events.""",
        notes="Textbook example, no actual trial"
    ),

    NegativeControl(
        id="NC011",
        control_type=NegativeControlType.METHODS_EXAMPLE,
        description="Forest plot interpretation guide",
        source_text="""How to Read a Forest Plot

A forest plot displays effect estimates from multiple studies with their
confidence intervals. Consider this hypothetical example:

Study 1: HR 0.82 (0.65-1.03) ----[====■====]----
Study 2: HR 0.71 (0.52-0.97)   --[===■===]--
Study 3: HR 0.89 (0.72-1.10)     ---[====■====]---
Pooled:  HR 0.80 (0.69-0.93)      --[==◆==]--

The diamond at the bottom represents the pooled estimate. A hazard ratio
below 1.0 indicates benefit for the intervention. If the confidence interval
excludes 1.0 (doesn't cross the vertical line), the result is statistically
significant at p<0.05.

In this example, the pooled HR of 0.80 (0.69-0.93) suggests a 20%
relative risk reduction with statistical significance.""",
        notes="Educational example, hypothetical data"
    ),

    # ==========================================================================
    # NON-MEDICAL CONTENT WITH SIMILAR PATTERNS
    # ==========================================================================
    NegativeControl(
        id="NC012",
        control_type=NegativeControlType.NON_MEDICAL,
        description="Economic analysis with ratios that look like HRs",
        source_text="""Economic Analysis: Housing Market Trends

The ratio of median home prices to median income reached 0.74 (range 0.65-0.85)
in metropolitan areas, compared to 0.58 in rural regions.

Risk-adjusted returns showed:
- Urban portfolio: return ratio 1.32 (95% band: 1.12-1.55)
- Suburban portfolio: return ratio 0.89 (0.76-1.04)

The difference in means between high-density and low-density developments
was -4.2 percentage points (CI: -7.1 to -1.3).

Hazard model for foreclosure showed regional variation:
- Northeast: 0.75x baseline
- Southeast: 1.12x baseline
- Midwest: 0.92x baseline""",
        notes="Economic data with ratio patterns similar to medical"
    ),

    NegativeControl(
        id="NC013",
        control_type=NegativeControlType.NON_MEDICAL,
        description="Sports statistics with odds/ratios",
        source_text="""Advanced Analytics in Baseball

Win probability analysis for the 2023 season showed interesting patterns.
Teams with above-average bullpen ERA had odds ratio 0.72 (95% CI: 0.58-0.89)
for playoff advancement.

The hazard rate for player injury showed:
- Starting pitchers: HR 1.35 (1.12-1.62) vs. position players
- Catchers: HR 0.89 (0.71-1.11) vs. other positions

Mean difference in runs scored per game for high-contact teams was
0.45 (95% CI: 0.22 to 0.68) compared to power-focused approaches.

Relative risk of winning for home teams: RR 1.08 (1.02-1.14).""",
        notes="Sports analytics mimicking medical statistics terminology"
    ),

    # ==========================================================================
    # ANIMAL/PRECLINICAL STUDIES
    # ==========================================================================
    NegativeControl(
        id="NC014",
        control_type=NegativeControlType.OBSERVATIONAL,
        description="Mouse model preclinical study",
        source_text="""Preclinical Study: SGLT2 Inhibition in Murine Heart Failure Model

Methods: Male C57BL/6 mice (n=60) were randomized to vehicle or dapagliflozin
(1 mg/kg/day) following TAC-induced heart failure.

Results: At 8 weeks post-TAC:
- Survival: HR 0.45 (95% CI: 0.28-0.72, p=0.001) favoring dapagliflozin
- Ejection fraction: mean difference +12.3% (95% CI: 8.1-16.5%)
- Cardiac fibrosis: OR 0.31 (0.15-0.64) for extensive fibrosis

Conclusions: SGLT2 inhibition improves survival and cardiac function in
this preclinical model. These findings support investigation in human trials.""",
        notes="Animal study, not human RCT"
    ),

    # ==========================================================================
    # IN-VITRO / LABORATORY STUDIES
    # ==========================================================================
    NegativeControl(
        id="NC015",
        control_type=NegativeControlType.OBSERVATIONAL,
        description="In-vitro cell culture study",
        source_text="""In-Vitro Effects of SGLT2 Inhibitors on Cardiomyocytes

Human iPSC-derived cardiomyocytes were exposed to empagliflozin (1μM) or
vehicle control for 48 hours under hypoxic conditions.

Cell viability assay:
- Odds ratio for cell death: 0.52 (95% CI: 0.38-0.71, p<0.001)
- Mean difference in ATP production: +23.5 nmol/mg (95% CI: 15.2-31.8)

Gene expression changes:
- SIRT1 expression ratio: 1.85 (1.42-2.41)
- Inflammatory cytokine ratio: 0.62 (0.48-0.80)

These mechanistic findings suggest direct cardioprotective effects
independent of glucose lowering.""",
        notes="In-vitro laboratory study"
    ),

    # ==========================================================================
    # META-ANALYSES AND SYSTEMATIC REVIEWS (aggregated effects)
    # ==========================================================================
    NegativeControl(
        id="NC016",
        control_type=NegativeControlType.REVIEW,
        description="Cochrane review abstract with pooled estimates",
        source_text="""Cochrane Database of Systematic Reviews

SGLT2 inhibitors for heart failure: a systematic review and meta-analysis

Background: We synthesized evidence from randomized controlled trials of SGLT2
inhibitors in patients with heart failure.

Methods: We searched MEDLINE, Embase, and CENTRAL through March 2024. Two
reviewers independently extracted data using Cochrane methods.

Results: We included 12 RCTs (n=15,234 participants). Meta-analysis showed:

Primary outcome (CV death or HF hospitalization):
- Pooled HR 0.74 (95% CI 0.70-0.78), I²=0%, high certainty evidence

Secondary outcomes:
- All-cause mortality: pooled HR 0.87 (0.82-0.93), I²=12%
- HF hospitalization: pooled HR 0.69 (0.64-0.75), I²=8%
- Renal composite: pooled HR 0.71 (0.64-0.79), I²=22%

Conclusions: High-certainty evidence supports SGLT2 inhibitors for HFrEF.""",
        notes="Meta-analysis pooled estimates, not individual RCT"
    ),

    NegativeControl(
        id="NC017",
        control_type=NegativeControlType.REVIEW,
        description="Network meta-analysis with indirect comparisons",
        source_text="""Network Meta-Analysis: Comparative Effectiveness of DOAC Regimens

We performed a Bayesian network meta-analysis comparing DOACs for stroke
prevention in atrial fibrillation using data from 8 randomized trials.

Direct and indirect comparisons:

Apixaban vs Warfarin: HR 0.79 (0.66-0.95) - direct evidence
Rivaroxaban vs Warfarin: HR 0.88 (0.75-1.03) - direct evidence
Apixaban vs Rivaroxaban: HR 0.90 (0.72-1.12) - indirect estimate
Dabigatran 150mg vs Apixaban: HR 1.05 (0.82-1.34) - mixed evidence

Surface under cumulative ranking (SUCRA):
- Apixaban: 0.89
- Dabigatran 150mg: 0.71
- Edoxaban: 0.52

These comparative effectiveness estimates enable treatment selection.""",
        notes="NMA indirect estimates, not original RCT data"
    ),

    NegativeControl(
        id="NC018",
        control_type=NegativeControlType.REVIEW,
        description="Umbrella review summarizing meta-analyses",
        source_text="""Umbrella Review: Cardiovascular Effects of Diabetes Medications

We conducted an umbrella review of meta-analyses examining cardiovascular
outcomes with glucose-lowering drugs.

Summary of meta-analytic estimates:

GLP-1 receptor agonists (12 meta-analyses):
- MACE: pooled RR range 0.86-0.91 across reviews
- Mortality: pooled RR range 0.85-0.92

SGLT2 inhibitors (15 meta-analyses):
- MACE: pooled HR range 0.86-0.93
- Heart failure: pooled HR range 0.65-0.73

DPP-4 inhibitors (8 meta-analyses):
- MACE: pooled RR range 0.98-1.02 (neutral)
- Heart failure: pooled RR range 1.00-1.14

Evidence quality was high for SGLT2i in HF, moderate for GLP-1 RA.""",
        notes="Umbrella review of meta-analyses"
    ),

    NegativeControl(
        id="NC019",
        control_type=NegativeControlType.SECONDARY_ANALYSIS,
        description="Individual patient data meta-analysis",
        source_text="""IPD Meta-Analysis: SGLT2 Inhibitors Across HF Phenotypes

Using individual patient data from DAPA-HF, EMPEROR-Reduced, and DELIVER,
we examined treatment effects across ejection fraction categories.

Patient-level analysis (n=15,988):

HFrEF (EF <40%): HR 0.72 (95% CI 0.66-0.79)
HFmrEF (EF 40-49%): HR 0.78 (95% CI 0.68-0.90)
HFpEF (EF ≥50%): HR 0.83 (95% CI 0.74-0.93)

P for interaction = 0.08 (no significant heterogeneity)

These pooled IPD estimates supersede individual trial reports for
cross-phenotype comparisons.""",
        notes="IPD meta-analysis pooled estimates"
    ),

    # ==========================================================================
    # GUIDELINE RECOMMENDATIONS (citing evidence)
    # ==========================================================================
    NegativeControl(
        id="NC020",
        control_type=NegativeControlType.REVIEW,
        description="Clinical practice guideline citing trial evidence",
        source_text="""ESC Guidelines for Heart Failure Management (2023 Update)

Recommendation 4.2: SGLT2 Inhibitors

SGLT2 inhibitors are recommended for all patients with HFrEF to reduce
the risk of HF hospitalization and death (Class I, Level A).

Evidence base:
- DAPA-HF showed HR 0.74 (0.65-0.85) for the primary composite
- EMPEROR-Reduced demonstrated HR 0.75 (0.65-0.86)
- Pooled analysis confirms consistent benefit across subgroups

Practical considerations:
- Initiate regardless of diabetes status
- Monitor renal function and ketoacidosis risk
- Can be combined with other quadruple therapy components

This recommendation supersedes 2021 guidance based on new evidence.""",
        notes="Guideline citing RCT evidence"
    ),
]


def get_negative_controls_by_type(control_type: NegativeControlType) -> List[NegativeControl]:
    """Filter negative controls by type"""
    return [nc for nc in NEGATIVE_CONTROLS if nc.control_type == control_type]


def get_all_negative_control_texts() -> List[str]:
    """Get all negative control source texts for batch testing"""
    return [nc.source_text for nc in NEGATIVE_CONTROLS]


# Summary stats
NEGATIVE_CONTROL_SUMMARY = {
    "total": len(NEGATIVE_CONTROLS),
    "by_type": {
        ct.value: len([nc for nc in NEGATIVE_CONTROLS if nc.control_type == ct])
        for ct in NegativeControlType
    }
}


if __name__ == "__main__":
    print("Negative Controls Dataset Summary")
    print("=" * 50)
    print(f"Total controls: {NEGATIVE_CONTROL_SUMMARY['total']}")
    print("\nBy type:")
    for ctype, count in NEGATIVE_CONTROL_SUMMARY['by_type'].items():
        print(f"  {ctype}: {count}")
