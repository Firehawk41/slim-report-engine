import pytest

from slim_report_engine.reporting.section_builders import silicon_section_builder as builder


def test_neither_included_raises():
    with pytest.raises(ValueError):
        builder.build_silicon("Silicon", False, False)


def test_total_only():
    section = builder.build_silicon("Silicon", True, False)
    labels = [r.get_value(2) for r in section.rows if r.style_name == "DataLabel"]
    assert "Silicon" in labels
    assert "Dissolved Silica" not in labels
    assert "Colloidal Silica *" not in labels


def test_dissolved_only():
    section = builder.build_silicon("Silicon", False, True)
    labels = [r.get_value(2) for r in section.rows if r.style_name == "DataLabel"]
    assert "Dissolved Silica" in labels
    assert "Silicon" not in labels
    assert "Colloidal Silica *" not in labels


def test_both_adds_colloidal_silica_row():
    section = builder.build_silicon("Silicon", True, True)
    labels = [r.get_value(2) for r in section.rows if r.style_name == "DataLabel"]
    assert labels == ["Silicon", "Dissolved Silica", "Colloidal Silica *"]


def test_both_adds_the_calculation_footnote():
    section = builder.build_silicon("Silicon", True, True)
    notes = [r.get_value(1) for r in section.rows if r.get_value(1) and "difference" in str(r.get_value(1))]
    assert len(notes) == 1


def test_header_uses_singular_result_not_plural():
    section = builder.build_silicon("Silicon", True, False)
    header = section.rows[1]
    assert header.get_value(4) == "Result"


def test_total_only_footer_is_icp_oes():
    section = builder.build_silicon("Silicon", True, False)
    footers = [r.get_value(1) for r in section.rows if r.get_value(1) and "Analysis by" in str(r.get_value(1))]
    assert footers == ["Analysis by ICP-OES (Evaporation)"]


def test_both_footers_present_in_order():
    section = builder.build_silicon("Silicon", True, True)
    footers = [r.get_value(1) for r in section.rows if r.get_value(1) and "Analysis by" in str(r.get_value(1))]
    assert footers == [
        "Analysis by ICP-OES (Evaporation)",
        "Dissolved Silica Analysis by UV-VIS (Evaporation)",
    ]
