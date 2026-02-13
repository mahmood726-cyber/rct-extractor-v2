"""
Update gold_50.jsonl with AI-assisted analysis results.

For WRONG_PDF entries: mark as excluded with reason
For COUNTS_ONLY entries: fill gold.notes with the raw data found
For entries with labeled effects already filled: keep as-is
"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")
GOLD_FILE = PROJECT_DIR / "gold_data" / "gold_50.jsonl"

# AI analysis results — manually compiled from 3 agent batches
AI_RESULTS = {
    # Batch 1
    "Anderson_2010": {
        "category": "WRONG_PDF",
        "notes": "File PMC9994449 is Miles et al. 2024 (sexual assault review), not Anderson 2010 RCT"
    },
    "Bomyea_2015": {
        "category": "COUNTS_ONLY",
        "notes": "CAPS PTSD scores: HIC post=45.32(19.92) n=22, LIC post=58.50(18.61) n=20. Within-group d reported, no between-group SMD/CI. Cochrane computes SMD from group means/SDs.",
        "raw_data": {"intervention_mean": 45.32, "intervention_sd": 19.92, "intervention_n": 22,
                     "control_mean": 58.50, "control_sd": 18.61, "control_n": 20}
    },
    "Hilliard_2012": {
        "category": "WRONG_PDF",
        "notes": "File PMC11456965 is Kapur et al. 2024 (asthma HiFlo), not Hilliard 2012. Other file PMC4467546 is also wrong (diabetes management)."
    },
    "Marigold_2005": {
        "category": "COUNTS_ONLY",
        "notes": "Berg Balance: Agility post=49.1(5.0) n=22, Stretching post=48.1(5.7) n=26. Cochrane MD=49.1-48.1=1.0 exactly.",
        "raw_data": {"intervention_mean": 49.1, "intervention_sd": 5.0, "intervention_n": 22,
                     "control_mean": 48.1, "control_sd": 5.7, "control_n": 26}
    },
    "Jandaghi_2021": {
        "category": "COUNTS_ONLY",
        "notes": "TUG/4SS/FTSS times reported, not 'gait velocity'. VD-SBT TUG post=10.0(1.2) n=15, Control post=15.4(3.0) n=15. Paper measures different outcomes than Cochrane specifies.",
        "raw_data": {"intervention_mean": 10.0, "intervention_sd": 1.2, "intervention_n": 15,
                     "control_mean": 15.4, "control_sd": 3.0, "control_n": 15}
    },
    "Ahamed_2019": {
        "category": "WRONG_PDF",
        "notes": "File PMC11744339 is Bagger-Jorgensen et al. 2024 (VDR & IBD), not Ahamed 2019 vitamin D RCT"
    },

    # Batch 2
    "Irmak_2012": {
        "category": "WRONG_PDF",
        "notes": "File PMC12390399 is Lu et al. 2025 (radar posture detection), not Irmak 2012 exercise RCT"
    },
    "Fagerlin_2011": {
        "category": "COUNTS_ONLY",
        "notes": "Decision aid RCT. 'Values-choice congruence' not measured. Raw proportions: 5.7% vs 3.2% chemoprevention intent, 54.7% vs 70.0% undecided. No OR computed.",
    },
    "Hirono_2019": {
        "category": "COUNTS_ONLY",
        "notes": "Grade B/C POPF: mattress 11/107 (10.3%) vs interrupted 7/103 (6.8%), P=0.367. Cochrane OR~1.57 matches 2x2 table.",
        "raw_data": {"intervention_events": 11, "intervention_n": 107,
                     "control_events": 7, "control_n": 103}
    },
    "Hutchins_2019": {
        "category": "COUNTS_ONLY",
        "notes": "Pain medians(range): 0-24h experimental 3.0(0,10) vs control 5.0(2,10) P=0.018. Opioid MME 0-24h: 7.5 vs 22.5. Reports medians not means. Cochrane MD=-17.6 may be MME or rescaled VAS.",
    },
    "Jiang_2020": {
        "category": "COUNTS_ONLY",
        "notes": "NRS rest 24h: TK 1.43(0.94) n=51 vs C 2.13(1.10) n=49. Diff=-0.70, not -1.8. May be wrong comparison or file.",
        "raw_data": {"intervention_mean": 1.43, "intervention_sd": 0.94, "intervention_n": 51,
                     "control_mean": 2.13, "control_sd": 1.10, "control_n": 49}
    },
    "Rajanbabu_2019": {
        "category": "COUNTS_ONLY",
        "notes": "Pain in figure only, no tabulated means/SDs. Pilot data: Block 0.20(0.632) vs Control 3.60(2.797) at 24h n=20/20. Cochrane MD=-33 likely rescaled to 0-100mm VAS.",
    },
    "Delroy_2013": {
        "category": "COUNTS_ONLY",
        "notes": "Anatomical failure: mesh 7/40 vs AC 17/39. Bothersome symptoms: mesh 2/40 vs AC 10/39. No OR computed. Cochrane OR=0.59 doesn't match these simple ratios; may use different subitem.",
        "raw_data": {"intervention_events": 7, "intervention_n": 40,
                     "control_events": 17, "control_n": 39}
    },

    # Batch 3
    "Zou_2022": {
        "category": "WRONG_PDF",
        "notes": "File PMC12454206 is Cadwell et al. 2025 (skin-to-skin Uganda qualitative), not Zou 2022 episiotomy pain RCT"
    },
    "Beiranvand_2014": {
        "category": "COUNTS_ONLY",
        "notes": "IBAT total: SSC 8.76(3.63) n=46 vs routine 7.25(3.50) n=44, P=0.048. Raw diff=1.51, doesn't match Cochrane MD=0.42 (may use subscale).",
        "raw_data": {"intervention_mean": 8.76, "intervention_sd": 3.63, "intervention_n": 46,
                     "control_mean": 7.25, "control_sd": 3.50, "control_n": 44}
    },
    "Hanson_2016": {
        "category": "WRONG_PDF",  # Actually wrong but labeled NOT_FOUND
        "notes": "File PMC4898300 is cervicogenic headache protocol, PMC12281261 is 2025 POCUS review. Neither is Hanson 2016 LP positioning RCT."
    },
    "Habib_2017": {
        "category": "COUNTS_ONLY",
        "notes": "Fully immunised: arm B 32%(CI 29-35) n~26110 vs arm A 25%(CI 22-28) n~23334. Cochrane RR=32/25=1.28 exact. Reports proportions only, no RR.",
        "raw_data": {"intervention_pct": 32, "intervention_n": 26110,
                     "control_pct": 25, "control_n": 23334}
    },
    "Feltner_2009": {
        "category": "COUNTS_ONLY",
        "notes": "Completed: paroxetine 41/56 (73.2%) vs placebo 39/57 (68.4%). Dropout: 15/56 vs 18/57. Cochrane OR=0.85 for acceptability (dropout).",
        "raw_data": {"intervention_events": 15, "intervention_n": 56,
                     "control_events": 18, "control_n": 57}
    },
    "Moschonis_2019": {
        "category": "COUNTS_ONLY",
        "notes": "BMI change: IG -0.4(SEM 0.7) n=35 vs CG +0.2(SEM 0.9) n=30. Between-group diff=-0.6, doesn't match Cochrane MD=-1.4.",
        "raw_data": {"intervention_change": -0.4, "intervention_sem": 0.7, "intervention_n": 35,
                     "control_change": 0.2, "control_sem": 0.9, "control_n": 30}
    },
}


def main():
    entries = []
    with open(GOLD_FILE) as f:
        for line in f:
            entries.append(json.loads(line))

    stats = {"wrong_pdf": 0, "counts_only": 0, "already_filled": 0, "unchanged": 0}

    for entry in entries:
        sid = entry["study_id"]
        gold = entry.get("gold", {})

        # Skip already-filled entries
        if gold.get("point_estimate") is not None:
            stats["already_filled"] += 1
            continue

        if sid not in AI_RESULTS:
            stats["unchanged"] += 1
            continue

        ai = AI_RESULTS[sid]
        category = ai["category"]

        if category == "WRONG_PDF":
            gold["notes"] = f"WRONG_PDF: {ai['notes']}"
            gold["effect_type"] = None
            entry["excluded"] = True
            entry["exclude_reason"] = "wrong_pdf"
            stats["wrong_pdf"] += 1
            print(f"  EXCLUDED: {sid} — wrong PDF")

        elif category == "COUNTS_ONLY":
            gold["notes"] = f"COUNTS_ONLY: {ai['notes']}"
            if "raw_data" in ai:
                gold["raw_data"] = ai["raw_data"]
            gold["effect_type"] = None  # No labeled effect to extract
            entry["category"] = "COUNTS_ONLY"
            stats["counts_only"] += 1
            print(f"  COUNTS: {sid}")

    # Save
    with open(GOLD_FILE, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    print(f"\n{'='*60}")
    print(f"UPDATE SUMMARY")
    print(f"{'='*60}")
    print(f"Already filled:  {stats['already_filled']}")
    print(f"Wrong PDF:       {stats['wrong_pdf']} (excluded)")
    print(f"Counts only:     {stats['counts_only']} (noted)")
    print(f"Unchanged:       {stats['unchanged']}")
    total = len(entries)
    usable = total - stats["wrong_pdf"]
    filled = stats["already_filled"]
    print(f"\nUsable entries:  {usable}/{total}")
    print(f"Filled (auto):   {filled}/{usable} ({filled/usable*100:.0f}%)")
    print(f"Counts only:     {stats['counts_only']}/{usable}")


if __name__ == "__main__":
    main()
