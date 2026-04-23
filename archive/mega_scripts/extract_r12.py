# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
import json
import sys
import io

# Set UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Read input
with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r12.json', 'r', encoding='utf-8') as f:
    batch = json.load(f)

# Create all 15 extraction results
results = [
    # Study 1
    {
        "study_id": "Sadeghnia 2014_2014",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "In Table 3, the frequency distribution of unsuccessful first attempts of intervention for i-gel and ET-tube placement are listed and compared",
        "reasoning": "Table 3 is mentioned as containing the data for unsuccessful first attempts, but the actual numerical values from the table are not provided in the results_text excerpt."
    },
    # Study 2
    {
        "study_id": "Ain 2021_2021",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "There were significant differences from pre- to post-intervention scores of FMA-UE and BBT (p < 0.001) in both groups",
        "reasoning": "The text mentions significant differences in FMA-UE scores (p < 0.001) but does not provide the actual post-intervention mean and SD values for XKTG vs ETG groups separately."
    },
    # Study 3
    {
        "study_id": "Choi 2014_2014",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "After 4 weeks, both groups showed significant improvement in the FMA-UL, MFT, BBT, K-MBI, K-MMSE, and correct detection of auditory CPT. However, grip strength was improved significantly only in the case group. There were no significant inter-group differences before and after the treatment.",
        "reasoning": "The text mentions improvements in FMA-UL and states no significant inter-group differences, but does not provide specific post-intervention mean and SD values for VR vs conventional OT groups."
    },
    # Study 4
    {
        "study_id": "Junior 2019_2019",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "An improvement in the mean scores was observed after treatment independent of the allocation group with significant intragroup changes: 14.5, 10.5, and 10.4 for PNF, VR, and PNF/VR, respectively.",
        "reasoning": "The values given (14.5, 10.5, 10.4) are mean CHANGE scores (improvement), not absolute post-intervention scores. The outcome requires absolute post-intervention mean and SD values for each group."
    },
    # Study 5
    {
        "study_id": "Levin 2012_2012",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "Improvements occurred in both groups, but more patients in the VR group improved upper limb clinical impairment (FMA, CSI) and activity scores (WMFT) and improvements occurred earlier.",
        "reasoning": "The text provides qualitative comparison stating VR group showed more improvement, but no specific post-intervention mean and SD values for FMA, CSI, or WMFT scores are provided."
    },
    # Study 6
    {
        "study_id": "Miclaus 2020_2020",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "The Wilcoxon Signed-Rank test showed significant differences in all four groups regarding MMT, FMUE, and FIM assessments pre- and post-therapy, while for AROM, only experimental groups registered significant differences.",
        "reasoning": "The text mentions statistically significant differences for FMUE (Fugl-Meyer Upper Extremity) but does not provide the actual post-intervention mean and SD values for NIVR vs standard physiotherapy groups."
    },
    # Study 7
    {
        "study_id": "Reinkensmeyer 2012_2012",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "Training helped both groups significantly reduce their motor impairment, as measured by the primary outcome measure, the Fugl-Meyer score, but the improvement was small (3.0 +/- 4.9 points for robot therapy, versus 0.9 +/- 1.7 for conventional therapy).",
        "reasoning": "The text provides CHANGE scores (improvement of 3.0+/-4.9 for robot, 0.9+/-1.7 for conventional) but not the absolute post-intervention mean and SD values. Without baseline values per group, cannot derive post-intervention scores."
    },
    # Study 8
    {
        "study_id": "Rodriguez-Hernandez 2023_2023",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "Fugl-Meyer Assessment scores were observed to increase in both groups, with a notably larger increase in the experimental group (total motor function: effect size = 0.300; mean: -35.5; 95% confidence interval: -38.9 to -32.0)",
        "reasoning": "The text provides effect size (0.300) and what appears to be mean difference statistics (mean: -35.5, CI: -38.9 to -32.0), but not the raw post-intervention mean and SD values for each group separately."
    },
    # Study 9
    {
        "study_id": "Schuster-Amft 2018_2018",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "Patients in the experimental and control group improved: Box and Block Test mean 21.5+/-SD 16 baseline to mean 24.1+/-SD 17 follow-up; Chedoke-McMaster Arm and Hand Activity Inventory mean 66.0+/-SD 21 baseline to mean 70.2+/-SD 19 follow-up. An intention-to-treat analysis found no between-group differences.",
        "reasoning": "The reported values (Box and Block Test baseline 21.5+/-16 to follow-up 24.1+/-17) appear to be pooled across both experimental and control groups combined, not separated by group. Group-specific post-intervention values are needed."
    },
    # Study 10
    {
        "study_id": "Shin 2022_2022",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "The experimental group had significantly better improvements in UFMA (T1-T0 mean [SD]; Experimental 13.50 [7.49]; Control 8.00 [4.44]; p = 0.014) and JTT (Experimental 21.10 [20.84]; Control 5.63 [5.06]; p = 0.012)",
        "reasoning": "The text provides CHANGE scores (T1-T0) for UFMA with mean and SD: Experimental 13.50 [7.49], Control 8.00 [4.44]. These are changes from baseline, not absolute post-intervention values. The outcome requires post-intervention absolute scores."
    },
    # Study 11
    {
        "study_id": "Thielbar 2014_2014",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "only the Keypad group displayed statistically significant improvement both for measures of impairment (FMH: p = 0.048) and measures of task performance (JTHFT: p = 0.021)",
        "reasoning": "The text reports p-values for statistical significance of improvements but does not provide the actual post-intervention mean and SD values for upper limb function scores in Keypad vs OT groups."
    },
    # Study 12
    {
        "study_id": "Song 2015_2015",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "Both the VRG and ETG subjects exhibited a significant difference in weight distribution ratio on the paralyzed side and balance ability.",
        "reasoning": "The outcome is gait speed post intervention, but the results_text excerpt discusses weight distribution and balance, and does not contain specific gait speed mean and SD values for VRG vs ETG groups post-intervention."
    },
    # Study 13
    {
        "study_id": "El-Kafy 2021_2021",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "No significant difference in HGS scores was detected between groups after completion of the treatment (P = 0.252)",
        "reasoning": "The outcome is hand grip strength (HGS) post intervention. The text reports no significant difference (p=0.252) between experimental and control groups but does not provide the actual mean and SD values for HGS in each group post-intervention."
    },
    # Study 14
    {
        "study_id": "Cikajlo 2020_2020",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "Results of the calculated COP area for each exergame per session are presented in Table 1",
        "reasoning": "The outcome is gait speed post intervention, but the results_text excerpt only discusses COP (center of pressure) area analysis and does not contain gait speed data with mean and SD values."
    },
    # Study 15
    {
        "study_id": "Linder 2015_2015",
        "found": False,
        "effect_type": "NONE",
        "point_estimate": None,
        "ci_lower": None,
        "ci_upper": None,
        "intervention_events": None,
        "intervention_n": None,
        "control_events": None,
        "control_n": None,
        "intervention_mean": None,
        "intervention_sd": None,
        "control_mean": None,
        "control_sd": None,
        "source_quote": "The excerpt shown contains only references, not results data",
        "reasoning": "The outcome is participation restriction and quality of life post intervention, but the results_text excerpt appears to be from the references section and does not contain actual outcome data with mean and SD values."
    }
]

# Write to output file
output_path = 'C:/Users/user/rct-extractor-v2/gold_data/mega/clean_results_r12.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Extraction complete!")
print(f"Processed {len(results)} studies")
print(f"Found data: {sum(1 for r in results if r['found'])}")
print(f"Not found: {sum(1 for r in results if not r['found'])}")
print(f"\nOutput written to: {output_path}")

# Print summary
print("\nSummary by study:")
for i, r in enumerate(results, 1):
    print(f"{i:2d}. {r['study_id']:35s} found={r['found']}")
