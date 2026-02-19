"""Regression tests for raw_data_extractor pattern coverage."""

from src.core.raw_data_extractor import extract_raw_data


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
