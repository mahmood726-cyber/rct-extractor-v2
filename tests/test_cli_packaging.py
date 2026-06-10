"""Tests for the unified rct-extract CLI (rct_extractor.cli)."""
import json

import pytest

from rct_extractor.cli import main

DIABETES_ABSTRACT = (
    "Empagliflozin versus placebo in type 2 diabetes: cardiovascular death "
    "occurred in 30/200 (15.0%) in the empagliflozin group and 50/200 (25.0%) "
    "in the placebo group (hazard ratio 0.62, 95% CI 0.45-0.85)."
)


def test_list_specialties(capsys):
    rc = main(["--list-specialties"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Supported specialties (" in out
    for spec in ("diabetes", "tuberculosis", "hiv", "malaria", "cirrhosis"):
        assert spec in out


def test_detect_text_human(capsys):
    rc = main(["--detect", "--text", DIABETES_ABSTRACT])
    out = capsys.readouterr().out
    assert rc == 0
    assert "diabetes" in out


def test_extract_text_json(capsys):
    rc = main(["--specialty", "diabetes", "--text", DIABETES_ABSTRACT, "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    obj = json.loads(out.strip().splitlines()[0])
    assert obj["specialty"] == "diabetes"
    assert any(e.get("type") == "HR" for e in obj["effects"])
    assert "arm_level" in obj


def test_extract_auto_text_human(capsys):
    rc = main(["--auto", "--text", DIABETES_ABSTRACT])
    out = capsys.readouterr().out
    assert rc == 0
    assert "specialty   : diabetes" in out


def test_unknown_specialty_errors():
    with pytest.raises(SystemExit):
        main(["--specialty", "nonsense", "--text", "x"])


def test_input_file(tmp_path, capsys):
    p = tmp_path / "abstract.txt"
    p.write_text(DIABETES_ABSTRACT, encoding="utf-8")
    rc = main(["--specialty", "diabetes", "--input", str(p), "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    obj = json.loads(out.strip().splitlines()[0])
    assert obj["name"] == "abstract"
    assert obj["specialty"] == "diabetes"


def test_input_directory_batch(tmp_path, capsys):
    (tmp_path / "a.txt").write_text(DIABETES_ABSTRACT, encoding="utf-8")
    (tmp_path / "b.txt").write_text(
        "SVR12 achieved in 95/100 (95.0%) in the sofosbuvir group and "
        "80/100 (80.0%) in the placebo group.",
        encoding="utf-8",
    )
    out_file = tmp_path / "results.jsonl"
    rc = main(["--auto", "--input", str(tmp_path), "--json", "-o", str(out_file)])
    assert rc == 0
    lines = out_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    specialties = {json.loads(line)["specialty"] for line in lines}
    assert "diabetes" in specialties


def test_human_output_to_file_is_not_empty(tmp_path, capsys):
    # Regression: `rct-extract -i FILE -o OUT` (human format, no --json) used to
    # write a 0-byte file while printing to stdout. Fixed 2026-06-08.
    src = tmp_path / "abstract.txt"
    src.write_text(DIABETES_ABSTRACT, encoding="utf-8")
    out = tmp_path / "out.txt"
    rc = main(["--specialty", "diabetes", "-i", str(src), "-o", str(out)])
    capsys.readouterr()
    assert rc == 0
    written = out.read_text(encoding="utf-8")
    assert written.strip(), "human-format --output wrote an empty file"
    assert "specialty   : diabetes" in written
