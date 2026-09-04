from dataclasses import dataclass

import pytest

from slim_report_engine.reporting.analyte import Analyte
from slim_report_engine.reporting.section_builders import wafer_panel_builder as builder


@dataclass(frozen=True)
class _FakeElement:
    name: str
    symbol: str


class _FakeElementService:
    def get_by_symbol(self, symbol: str):
        return _FakeElement(name=symbol, symbol=symbol)

    def get_by_name(self, name: str):
        return _FakeElement(name=name, symbol=name[:2])


def test_header_footer_and_analyte_rows_all_use_max_sample_columns_width():
    """Confirmed real (Wafers Report Template.xlsx): analyte-row
    border/fill extends all the way to column 19, same as the header
    rows -- not the standard family's column 6. wafer_panel_builder.py
    passes max_columns explicitly to row_builders.add_analyte_row for
    this reason (every OTHER caller of add_analyte_row leaves it at the
    shared default -- this module is the one confirmed exception)."""
    section = builder.build_element_panel(
        "36 Elements", "note", "PB-ID", ["S1"], ["Al"], _FakeElementService()
    )
    for row in section.rows:
        assert row.max_columns == builder.MAX_SAMPLE_COLUMNS


def test_process_blank_and_slot_ids_placed_at_correct_columns():
    section = builder.build_element_panel(
        "36 Elements", "note", "PB-ID", ["S1", "S2"], ["Al"], _FakeElementService()
    )
    sample_id_row = section.rows[5]  # 2 blank, notes label, mdl note, units, THEN sample-id row
    assert sample_id_row.get_value(4) == "PB-ID"
    assert sample_id_row.get_value(5) == "S1"
    assert sample_id_row.get_value(6) == "S2"


def test_column_header_results_span_and_mdl_position_for_2_slots():
    """2 slot samples -> sample_count=2 -> Results spans columns 4..6
    (Process Blank + 2 slots), bare MDL header at column 6+2=8."""
    section = builder.build_element_panel(
        "36 Elements", "note", "PB-ID", ["S1", "S2"], ["Al"], _FakeElementService()
    )
    header_row = section.rows[6]
    assert header_row.get_value(2) == "Element"
    for col in (4, 5, 6):
        assert header_row.get_value(col) == "Results"
    assert header_row.get_value(8) == "MDL"


def test_anion_panel_uses_ql_and_no_date_of_analysis():
    anions = [Analyte("Chloride", "Cl")]
    section = builder.build_anion_panel("4 Anions", "ions note", "PB-ID", ["S1"], anions)
    header_row = section.rows[6]
    assert header_row.get_value(2) == "Anion"
    footer_analysis_row = next(r for r in section.rows if r.get_value(1) and "Analysis by" in str(r.get_value(1)))
    assert footer_analysis_row.get_value(1) == "Analysis by LP-IC."
    assert footer_analysis_row.get_value(4) is None  # no Date of Analysis placeholder


def test_element_panel_footer_has_date_of_analysis():
    section = builder.build_element_panel(
        "36 Elements", "note", "PB-ID", ["S1"], ["Al"], _FakeElementService()
    )
    footer_analysis_row = next(r for r in section.rows if r.get_value(1) and "Analysis by" in str(r.get_value(1)))
    assert footer_analysis_row.get_value(1) == "Analysis by LP-ICPMS."
    assert footer_analysis_row.get_value(4) == "Date of Analysis: "


def test_element_panel_test_methods_row_uses_max_sample_columns_width():
    """Confirmed real (one real Wafer report): the element panel's own
    Test Methods row exists and has the same wide border/fill extent as
    every other row on the sheet."""
    section = builder.build_element_panel(
        "36 Elements", "note", "PB-ID", ["S1"], ["Al"], _FakeElementService()
    )
    test_methods_row = next(r for r in section.rows if r.get_value(1) and "Test Methods" in str(r.get_value(1)))
    assert test_methods_row.get_value(1) == "Test Methods: PR-IN27 and PR-IN45."
    assert test_methods_row.max_columns == builder.MAX_SAMPLE_COLUMNS


def test_anion_panel_has_no_test_methods_row():
    """No confirmed real SOP evidence for the anion panel's own
    "Analysis by LP-IC." footer -- see sop_codes.py."""
    anions = [Analyte("Chloride", "Cl")]
    section = builder.build_anion_panel("4 Anions", "ions note", "PB-ID", ["S1"], anions)
    assert not any("Test Methods" in str(r.get_value(1)) for r in section.rows)


def test_additional_elements_appended_after_fixed_panel():
    section = builder.build_element_panel(
        "36 Elements", "note", "PB-ID", ["S1"], ["Al"], _FakeElementService(),
        additional_element_names=["Extra Element"],
    )
    data_rows = [r for r in section.rows if r.style_name == "DataLabel"]
    assert data_rows[-1].get_value(2) == "Extra Element"


def test_unknown_element_symbol_raises():
    class _EmptyElementService:
        def get_by_symbol(self, symbol):
            return None

    with pytest.raises(ValueError):
        builder.build_element_panel("x", "note", "PB", [], ["Xx"], _EmptyElementService())


def test_unknown_additional_element_name_raises():
    class _NoNameElementService:
        def get_by_symbol(self, symbol):
            return _FakeElement(name=symbol, symbol=symbol)

        def get_by_name(self, name):
            return None

    with pytest.raises(ValueError):
        builder.build_element_panel(
            "x", "note", "PB", [], [], _NoNameElementService(), additional_element_names=["Ghost"]
        )
