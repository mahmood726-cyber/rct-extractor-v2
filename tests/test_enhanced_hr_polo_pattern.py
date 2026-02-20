from src.core.enhanced_extractor_v3 import EnhancedExtractor, to_dict


def test_extracts_hr_with_for_context_and_confidence_interval_brackets() -> None:
    text = (
        "hazard ratio for disease progression or death, 0.53; "
        "95% confidence interval [CI], 0.35 to 0.82; P = 0.004"
    )

    extractor = EnhancedExtractor()
    normalized = extractor.normalize_text(text)
    extractions = [to_dict(item) for item in extractor.extract(normalized)]

    assert any(
        row.get("type") == "HR"
        and abs(float(row.get("effect_size")) - 0.53) < 1e-9
        and abs(float(row.get("ci_lower")) - 0.35) < 1e-9
        and abs(float(row.get("ci_upper")) - 0.82) < 1e-9
        for row in extractions
    )
