"""Regression tests for PDF pipeline confidence aggregation."""

from types import SimpleNamespace

from src.core.enhanced_extractor_v3 import ConfidenceInterval, EffectType, Extraction
from src.core.pdf_extraction_pipeline import PDFExtractionPipeline


def test_confidence_uses_final_merged_effects(monkeypatch, tmp_path):
    """Confidence should be computed from final merged effects, not text-only effects."""
    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\\n%test")

    pipeline = PDFExtractionPipeline(extract_diagnostics=False, extract_tables=False)

    page = SimpleNamespace(
        full_text="No labeled effect in text.",
        page_num=1,
        is_ocr=False,
        ocr_confidence=None,
    )
    parsed = SimpleNamespace(
        num_pages=1,
        extraction_method="pdfplumber",
        is_born_digital=True,
        pages=[page],
    )

    monkeypatch.setattr(pipeline.pdf_parser, "parse", lambda _: parsed)
    monkeypatch.setattr(pipeline, "_extract_from_text", lambda *_args, **_kwargs: ([], [], page.full_text, []))

    computed = Extraction(
        effect_type=EffectType.OR,
        point_estimate=2.0,
        ci=ConfidenceInterval(lower=1.5, upper=2.5, level=0.95),
        source_text="[COMPUTED from raw data] synthetic",
        calibrated_confidence=0.9,
        has_complete_ci=True,
    )
    monkeypatch.setattr(pipeline, "_extract_computed_effects", lambda *_args, **_kwargs: [computed])
    monkeypatch.setattr(pipeline, "_merge_text_and_table_effects", lambda text_fx, table_fx: text_fx + table_fx)

    result = pipeline.extract_from_pdf(str(dummy_pdf))

    assert len(result.effect_estimates) == 1
    assert result.extraction_confidence == 0.9


def test_raw_data_fallback_merges_processed_and_full_text(monkeypatch, tmp_path):
    """Raw-data fallback should merge processed-text and full-text computed effects."""
    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\n%test")

    pipeline = PDFExtractionPipeline(extract_diagnostics=False, extract_tables=False)

    page = SimpleNamespace(
        full_text="FULL_TEXT_SIGNAL",
        page_num=1,
        is_ocr=False,
        ocr_confidence=None,
    )
    parsed = SimpleNamespace(
        num_pages=1,
        extraction_method="pdfplumber",
        is_born_digital=True,
        pages=[page],
    )

    monkeypatch.setattr(pipeline.pdf_parser, "parse", lambda _: parsed)
    monkeypatch.setattr(
        pipeline,
        "_extract_from_text",
        lambda *_args, **_kwargs: ([], [], "PROCESSED_TEXT_SIGNAL", []),
    )

    processed_only = Extraction(
        effect_type=EffectType.OR,
        point_estimate=1.2,
        ci=ConfidenceInterval(lower=0.9, upper=1.6, level=0.95),
        source_text="[COMPUTED from raw data] processed",
        calibrated_confidence=0.2,
        has_complete_ci=True,
    )
    full_text_only = Extraction(
        effect_type=EffectType.MD,
        point_estimate=5.0,
        ci=ConfidenceInterval(lower=1.0, upper=9.0, level=0.95),
        source_text="[COMPUTED from raw data] full",
        calibrated_confidence=0.3,
        has_complete_ci=True,
    )

    def _fake_extract_computed(text):
        if text == "PROCESSED_TEXT_SIGNAL":
            return [processed_only]
        if text == "FULL_TEXT_SIGNAL":
            return [full_text_only]
        return []

    monkeypatch.setattr(pipeline, "_extract_computed_effects", _fake_extract_computed)

    result = pipeline.extract_from_pdf(str(dummy_pdf))
    effect_types = {e.effect_type for e in result.effect_estimates}

    assert EffectType.OR in effect_types
    assert EffectType.MD in effect_types


def test_partial_raw_data_fallback_recovers_md_without_sample_sizes() -> None:
    pipeline = PDFExtractionPipeline(
        extract_diagnostics=False,
        extract_tables=False,
        run_rct_classification=False,
        score_primary_outcomes=False,
        include_page_audit=False,
    )

    text = (
        "When compared with standard care group (mean6.94(cid:3)1.44), "
        "participants in PDA group (mean8.05(cid:3)1.29) improved."
    )
    computed = pipeline._extract_computed_effects(text)

    assert computed
    assert any(e.effect_type == EffectType.MD for e in computed)
    assert any(abs(e.point_estimate - 1.11) < 0.01 or abs(e.point_estimate + 1.11) < 0.01 for e in computed)
    assert any(e.se_method == "computed_partial" for e in computed)


def test_computed_family_expansion_binary_includes_or_rr_ard() -> None:
    pipeline = PDFExtractionPipeline(
        extract_diagnostics=False,
        extract_tables=False,
        run_rct_classification=False,
        score_primary_outcomes=False,
        include_page_audit=False,
    )

    text = "Treatment 15/56 (26.8%) vs Placebo 18/57 (31.6%)"
    computed = pipeline._extract_computed_effects(text)
    types = {e.effect_type for e in computed}

    assert EffectType.OR in types
    assert EffectType.RR in types
    assert EffectType.ARD in types


def test_computed_family_expansion_continuous_includes_md_smd() -> None:
    pipeline = PDFExtractionPipeline(
        extract_diagnostics=False,
        extract_tables=False,
        run_rct_classification=False,
        score_primary_outcomes=False,
        include_page_audit=False,
    )

    text = "Group A 49.1 (5.0) n=22 vs Group B 48.1 (5.7) n=26"
    computed = pipeline._extract_computed_effects(text)
    types = {e.effect_type for e in computed}

    assert EffectType.MD in types
    assert EffectType.SMD in types
