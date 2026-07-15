"""Regression tests for raw_data_extractor pattern coverage."""

from rct_extractor._engine.core.raw_data_extractor import extract_raw_data


def test_extracts_mean_pm_sd_with_cid_separator() -> None:
    text = (
        "When compared with standard care group (mean6.94(cid:3)1.44), "
        "participants in PDA group (mean8.05(cid:3)1.29) improved."
    )
    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous"]
    assert continuous
    assert any(
        abs((r.arm1.mean or 0.0) - 6.94) < 1e-6 and abs((r.arm2.mean or 0.0) - 8.05) < 1e-6
        for r in continuous
    ) or any(
        abs((r.arm1.mean or 0.0) - 8.05) < 1e-6 and abs((r.arm2.mean or 0.0) - 6.94) < 1e-6
        for r in continuous
    )


def test_extracts_split_column_mean_sd_rows() -> None:
    text = "ANB,u 5.65*** 1.28 5.25*** 0.99 .363"
    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous"]
    assert continuous
    assert any(
        abs((r.arm1.mean or 0.0) - 5.65) < 1e-6 and abs((r.arm1.sd or 0.0) - 1.28) < 1e-6
        and abs((r.arm2.mean or 0.0) - 5.25) < 1e-6 and abs((r.arm2.sd or 0.0) - 0.99) < 1e-6
        for r in continuous
    )


def test_extracts_events_with_percent_without_percent_symbol() -> None:
    text = "Periods perceived as very heavy 112(61) 115(64)"
    results = extract_raw_data(text)
    binary = [r for r in results if r.data_type == "binary"]
    assert binary
    assert any(
        (r.arm1.events, r.arm1.n, r.arm2.events, r.arm2.n) == (112, 184, 115, 180)
        for r in binary
    )


def test_extracts_continuous_with_colon_sample_sizes() -> None:
    text = "Treatment: 45.3 (19.9), n:22; Control: 58.5 (18.6), n:20"
    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous"]
    assert continuous
    assert any(
        ((r.arm1.n, r.arm2.n) == (22, 20) or (r.arm1.n, r.arm2.n) == (20, 22))
        and r.arm1.mean is not None
        and r.arm2.mean is not None
        for r in continuous
    )


def test_extracts_mean_pm_sd_with_control_char_separator() -> None:
    text = "Intervention mean6.94\x031.44 Control mean8.05\x031.29"
    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous"]
    assert continuous
    assert any(
        abs((r.arm1.mean or 0.0) - 6.94) < 1e-6 and abs((r.arm2.mean or 0.0) - 8.05) < 1e-6
        for r in continuous
    ) or any(
        abs((r.arm1.mean or 0.0) - 8.05) < 1e-6 and abs((r.arm2.mean or 0.0) - 6.94) < 1e-6
        for r in continuous
    )


def test_extracts_binary_of_n_pairs() -> None:
    text = "83 of 308 patients in the intervention group and 87 of 290 patients in control."
    results = extract_raw_data(text)
    binary = [r for r in results if r.data_type == "binary"]
    assert binary
    assert any((r.arm1.events, r.arm1.n, r.arm2.events, r.arm2.n) == (83, 308, 87, 290) for r in binary)


def test_extracts_percentages_with_ocr_dropped_decimal() -> None:
    text = "Remission table 12 (1000) 11 (846) N=12 N=13"
    results = extract_raw_data(text)
    binary = [r for r in results if r.data_type == "binary"]
    assert binary
    assert any(
        (r.arm1.events, r.arm1.n, r.arm2.events, r.arm2.n) == (12, 12, 11, 13)
        or (r.arm1.events, r.arm1.n, r.arm2.events, r.arm2.n) == (11, 13, 12, 12)
        for r in binary
    )


def test_extracts_binary_from_proportion_row_with_group_ns() -> None:
    text = (
        "Study Group Video Pamphlet Control\n"
        "(N=308) (N=295) (N=290)\n"
        "PSA within 2 weeks 0.27 0.29 0.28 0.28 0.30 0.29"
    )
    results = extract_raw_data(text)
    binary = [r for r in results if r.data_type == "binary"]
    assert binary
    assert any(
        (r.arm1.events, r.arm1.n, r.arm2.events, r.arm2.n) == (83, 308, 87, 290)
        for r in binary
    )


def test_extracts_continuous_from_mean_sd_n_table_row() -> None:
    text = "Knowledge score 81.85 11.95 78 66.90 13.69 66"
    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous"]
    assert continuous
    assert any(
        (
            abs((r.arm1.mean or 0.0) - 81.85) < 1e-6
            and abs((r.arm1.sd or 0.0) - 11.95) < 1e-6
            and (r.arm1.n == 78)
            and abs((r.arm2.mean or 0.0) - 66.9) < 1e-6
            and abs((r.arm2.sd or 0.0) - 13.69) < 1e-6
            and (r.arm2.n == 66)
        )
        or (
            abs((r.arm2.mean or 0.0) - 81.85) < 1e-6
            and abs((r.arm2.sd or 0.0) - 11.95) < 1e-6
            and (r.arm2.n == 78)
            and abs((r.arm1.mean or 0.0) - 66.9) < 1e-6
            and abs((r.arm1.sd or 0.0) - 13.69) < 1e-6
            and (r.arm1.n == 66)
        )
        for r in continuous
    )


def test_extracts_continuous_from_n_mean_sd_table_row() -> None:
    text = "Outcome row 86 75.00 32.04 94 62.00 32.04"
    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous"]
    assert continuous
    assert any(
        (
            (r.arm1.n, r.arm2.n) == (86, 94)
            and abs((r.arm1.mean or 0.0) - 75.0) < 1e-6
            and abs((r.arm1.sd or 0.0) - 32.04) < 1e-6
            and abs((r.arm2.mean or 0.0) - 62.0) < 1e-6
            and abs((r.arm2.sd or 0.0) - 32.04) < 1e-6
        )
        or (
            (r.arm1.n, r.arm2.n) == (94, 86)
            and abs((r.arm1.mean or 0.0) - 62.0) < 1e-6
            and abs((r.arm1.sd or 0.0) - 32.04) < 1e-6
            and abs((r.arm2.mean or 0.0) - 75.0) < 1e-6
            and abs((r.arm2.sd or 0.0) - 32.04) < 1e-6
        )
        for r in continuous
    )


def test_extracts_binary_from_percentage_vs_percentage_with_sample_sizes() -> None:
    text = "Adverse events 45% vs 30%, n=100 n=100"
    results = extract_raw_data(text)
    binary = [r for r in results if r.data_type == "binary"]
    assert binary
    assert any(
        (r.arm1.events, r.arm1.n, r.arm2.events, r.arm2.n) == (45, 100, 30, 100)
        or (r.arm1.events, r.arm1.n, r.arm2.events, r.arm2.n) == (30, 100, 45, 100)
        for r in binary
    )


def test_extracts_binary_from_table_percentage_row_with_group_ns() -> None:
    text = (
        "Intervention Control\n"
        "(N=120) (N=118)\n"
        "Adverse events 12.5% 18.6%"
    )
    results = extract_raw_data(text)
    binary = [r for r in results if r.data_type == "binary"]
    assert binary
    assert any(
        (r.arm1.events, r.arm1.n, r.arm2.events, r.arm2.n) == (15, 120, 22, 118)
        or (r.arm1.events, r.arm1.n, r.arm2.events, r.arm2.n) == (22, 118, 15, 120)
        for r in binary
    )


def test_control_first_percentage_table_header_swaps_binary_orientation() -> None:
    text = (
        "Control Treatment\n"
        "(N=118) (N=120)\n"
        "Adverse events 18.6% 12.5%"
    )
    results = extract_raw_data(text)
    binary = [r for r in results if r.data_type == "binary"]
    assert binary
    assert any(
        (r.arm1.events, r.arm1.n, r.arm2.events, r.arm2.n) == (15, 120, 22, 118)
        for r in binary
    )


def test_control_first_mean_sd_table_header_swaps_continuous_orientation() -> None:
    text = (
        "Control Treatment\n"
        "(N=20) (N=22)\n"
        "Pain score 58.5 (18.6) 45.3 (19.9)"
    )
    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous"]
    assert continuous
    assert any(
        (r.arm1.n, r.arm2.n) == (22, 20)
        and abs((r.arm1.mean or 0.0) - 45.3) < 1e-6
        and abs((r.arm2.mean or 0.0) - 58.5) < 1e-6
        for r in continuous
    )


def test_long_front_matter_is_not_treated_as_continuous_table_row() -> None:
    text = (
        "Donghee Han, MD; Kranthi K. Kolli, PhD; Subhi J. Al'Aref, MD; "
        "Lohendran Baskaran, MD; Alexander R. van Rosendael, MD; Heidi Gransar, MSc; "
        "Background--Rapid coronary plaque progression was studied in 1083 patients. "
        "Correspondence to: Hyuk-Jae Chang, MD, PhD, Yonsei University Health System, "
        "50 Yonsei-ro, Seoul 03722, South Korea. Received July 18, 2019; accepted "
        "December 20, 2019. DOI: 10.1161/JAHA.119.013958."
    )

    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous" and r.to_raw_data_dict()]

    assert continuous == []


def test_author_superscripts_are_not_treated_as_continuous_table_rows() -> None:
    text = (
        "Erica Maffei22, Hugo Marques23, Ivana Dacic24, Luca Rossi25 "
        "3711.88 2.0 5.0 7.0"
    )

    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous" and r.to_raw_data_dict()]

    assert continuous == []


def test_citation_count_prose_is_not_treated_as_continuous_table_row() -> None:
    text = (
        "listed diagnosis and from 787,750 to 2,283,673 for any AF diagnosis "
        "[20]. Other studies"
    )

    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous" and r.to_raw_data_dict()]

    assert continuous == []


def test_gene_locus_citation_chain_is_not_treated_as_continuous_table_row() -> None:
    text = (
        "4q25, 1q21 and 16q22.14.15.28 Interestingly, these loci not only "
        "represent risk factors for the"
    )

    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous" and r.to_raw_data_dict()]

    assert continuous == []


def test_baseline_characteristics_are_not_computed_as_continuous_effects() -> None:
    text = (
        "Table 1. Baseline Characteristics Control group Treatment group "
        "Age, mean (SD), years 60.0 (9.4) 60.0 (8.5) 0.977 "
        "Male sex, no. (%) 443 (58) 181 (56) 0.705"
    )

    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous" and r.to_raw_data_dict()]

    assert continuous == []


def test_percentage_count_rows_are_not_computed_as_continuous_effects() -> None:
    text = "Procedure success was observed in 87.5% (35/40) and 81.7% (152/186) in Wave I and Wave II."

    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous" and r.to_raw_data_dict()]

    assert continuous == []


def test_event_percentage_cells_are_not_computed_as_mean_sd() -> None:
    text = (
        "Wave I Wave II\n"
        "(N=40) (N=186)\n"
        "General anesthesia 34 (85.0) 132 (71.0)\n"
        "Conscious sedation 6 (15.0) 54 (29.0)"
    )

    results = extract_raw_data(text)
    continuous = [r for r in results if r.data_type == "continuous" and r.to_raw_data_dict()]

    assert continuous == []


def test_baseline_characteristics_are_not_computed_as_binary_effects() -> None:
    text = (
        "Author Manuscript Table 1. Baseline Characteristics Control group (N=16) "
        "Exercise group (N=30) Male sex 9 (56) 15 (50) Hypertension 11 (69) 21 (70)"
    )

    results = extract_raw_data(text)
    binary = [r for r in results if r.data_type == "binary" and r.to_raw_data_dict()]

    assert binary == []


def test_front_matter_affiliations_are_not_computed_as_binary_effects() -> None:
    text = (
        "Michinari Hieda, MD, PhD1.2.3, Satyam Sarma, MD1.2, "
        "Christopher Hearon Jr., PhD1.2, University Hospital 30 patients were screened."
    )

    results = extract_raw_data(text)
    binary = [r for r in results if r.data_type == "binary" and r.to_raw_data_dict()]

    assert binary == []


def test_reference_list_numeric_citations_are_not_binary_effects() -> None:
    text = (
        "References. George H. John, Pat Langley: Estimating Continuous Distributions "
        "in Bayesian Classifiers. In: Eleventh Conference on Uncertainty in Artificial "
        "Intelligence, 24/1200 and 13/433."
    )

    results = extract_raw_data(text)
    binary = [r for r in results if r.data_type == "binary" and r.to_raw_data_dict()]

    assert binary == []


def test_protocol_footer_numeric_pairs_are_not_binary_effects() -> None:
    text = (
        "CABANA Confidential 22 November, 2013 Page 61 of 78 Catheter Ablation "
        "Versus Antiarrhythmic Drug Therapy protocol 9/61 and 22/78"
    )

    results = extract_raw_data(text)
    binary = [r for r in results if r.data_type == "binary" and r.to_raw_data_dict()]

    assert binary == []
