from dataclasses import dataclass

import pytest

from slim_report_engine.reporting.section_builders import analyte_list_section_builder as builder


@dataclass(frozen=True)
class _FakeElement:
    name: str
    symbol: str


class _FakeElementService:
    """Duck-types ElementService.get_by_symbol without a real DB session."""

    _CATALOG = {
        "Al": _FakeElement("Aluminum", "Al"),
        "Sb": _FakeElement("Antimony", "Sb"),
        "As": _FakeElement("Arsenic", "As"),
    }

    def get_by_symbol(self, symbol: str):
        return self._CATALOG.get(symbol)

    def get_by_name(self, name: str):
        return next((e for e in self._CATALOG.values() if e.name == name), None)


def test_build_metals_panel_header_and_footer():
    section = builder.build_metals_panel(
        "36 Elements", ["Al", "Sb"], "36 Tr.Elts", _FakeElementService()
    )
    top, header = section.rows[0], section.rows[1]
    assert top.get_value(1) == "Specification"
    assert header.get_value(2) == "Element"
    assert header.get_value(6) == "MDL"
    footer = section.rows[-1]
    assert footer.get_value(1) == "Analysis by ICPMS (Evaporation)"


def test_build_metals_panel_adds_one_row_per_symbol_in_order():
    section = builder.build_metals_panel(
        "36 Elements", ["Al", "Sb", "As"], "36 Tr.Elts", _FakeElementService()
    )
    # rows: top, header, Al, Sb, As, blank, AVERAGE, TOTAL, blank, footer
    data_rows = section.rows[2:5]
    assert [r.get_value(3) for r in data_rows] == ["Al", "Sb", "As"]
    assert [r.get_value(2) for r in data_rows] == ["Aluminum", "Antimony", "Arsenic"]


def test_build_metals_panel_unknown_symbol_raises():
    with pytest.raises(ValueError):
        builder.build_metals_panel("x", ["Xx"], "label", _FakeElementService())


def test_summary_rows_use_summary_label():
    section = builder.build_metals_panel(
        "10 Elements", ["Al"], "10 Tr.Elts", _FakeElementService()
    )
    avg_row = next(r for r in section.rows if r.style_name == "SummaryRow" and r.get_value(2) and "AVERAGE" in r.get_value(2))
    total_row = next(r for r in section.rows if r.style_name == "SummaryRow" and r.get_value(2) and "TOTAL" in r.get_value(2))
    assert avg_row.get_value(2) == "AVERAGE / 10 Tr.Elts"
    assert total_row.get_value(2) == "TOTAL / 10 Tr.Elts"


def test_summary_formulas_are_relative_r1c1_and_cover_the_data_rows():
    """With 3 analyte rows starting right after the 2 header rows, the
    AVERAGE row (logical row 6, 1-based: top=1,header=2,Al=3,Sb=4,As=5,
    blank=6? -- actually blank comes first) should reference back to the
    first/last data rows via relative offsets."""
    section = builder.build_metals_panel(
        "36 Elements", ["Al", "Sb", "As"], "36 Tr.Elts", _FakeElementService()
    )
    # logical rows: 1 top, 2 header, 3 Al, 4 Sb, 5 As, 6 blank, 7 AVERAGE, 8 TOTAL, 9 blank, 10 footer
    avg_row = section.rows[6]
    assert avg_row.get_formula(4) == "=AVERAGE(R[-4]C:R[-2]C)"
    total_row = section.rows[7]
    assert total_row.get_formula(4) == "=SUM(R[-5]C:R[-3]C)"


def test_build_metals_panel_default_prep_text_is_evaporation():
    section = builder.build_metals_panel("36 Elements", ["Al"], "36 Tr.Elts", _FakeElementService())
    footer = section.rows[-1]
    assert footer.get_value(1) == "Analysis by ICPMS (Evaporation)"


def test_build_metals_panel_custom_prep_text():
    section = builder.build_metals_panel(
        "36 Elements", ["Al"], "36 Tr.Elts", _FakeElementService(), prep_text="Dilute and Shoot"
    )
    footer = section.rows[-1]
    assert footer.get_value(1) == "Analysis by ICPMS (Dilute and Shoot)"


def test_build_metals_panel_with_additional_elements_appends_labeled_block():
    section = builder.build_metals_panel(
        "36 Elements", ["Al"], "36 Tr.Elts", _FakeElementService(),
        additional_element_names=["Antimony", "Arsenic"],
    )
    # rows: top, header, Al, blank, AVERAGE, TOTAL, blank, footer,
    #       blank, label, Sb, As, blank, footer
    label_row = section.rows[-5]
    assert label_row.get_value(4) == "Additional Elements"
    sb_row, as_row = section.rows[-4], section.rows[-3]
    assert (sb_row.get_value(2), sb_row.get_value(3)) == ("Antimony", "Sb")
    assert (as_row.get_value(2), as_row.get_value(3)) == ("Arsenic", "As")
    assert section.rows[-1].get_value(1) == "Analysis by ICPMS (Evaporation)"
    # the main panel's own footer is untouched, still present before the block
    main_footer = section.rows[-7]
    assert main_footer.get_value(1) == "Analysis by ICPMS (Evaporation)"


def test_build_metals_panel_without_additional_elements_has_no_extra_block():
    section = builder.build_metals_panel("36 Elements", ["Al"], "36 Tr.Elts", _FakeElementService())
    assert section.rows[-1].get_value(1) == "Analysis by ICPMS (Evaporation)"
    # top, header, Al, blank, AVERAGE, TOTAL, blank, footer == 8 rows
    assert len(section.rows) == 8


def test_add_additional_elements_block_unknown_name_raises():
    section = builder.build_metals_panel("36 Elements", ["Al"], "36 Tr.Elts", _FakeElementService())
    with pytest.raises(ValueError):
        builder.add_additional_elements_block(section, ["Not A Real Element"], _FakeElementService(), "Evaporation")


def test_build_additional_elements_only_panel_has_no_summary_or_label_row():
    section = builder.build_additional_elements_only_panel(
        "Additional Elements", ["Antimony", "Arsenic"], _FakeElementService(), "Dilute and Shoot"
    )
    # top, header, Sb, As, footer == 5 rows -- no blank/AVERAGE/TOTAL/label
    assert len(section.rows) == 5
    sb_row, as_row = section.rows[2], section.rows[3]
    assert (sb_row.get_value(2), sb_row.get_value(3)) == ("Antimony", "Sb")
    assert (as_row.get_value(2), as_row.get_value(3)) == ("Arsenic", "As")
    assert section.rows[-1].get_value(1) == "Analysis by ICPMS (Dilute and Shoot)"


def test_build_additional_elements_only_panel_unknown_name_raises():
    with pytest.raises(ValueError):
        builder.build_additional_elements_only_panel(
            "x", ["Not A Real Element"], _FakeElementService(), "Evaporation"
        )


def test_summary_rows_only_have_formulas_on_expected_columns():
    section = builder.build_metals_panel(
        "36 Elements", ["Al"], "36 Tr.Elts", _FakeElementService()
    )
    # rows: top, header, Al, blank, AVERAGE, TOTAL, blank, footer
    avg_row = section.rows[4]
    total_row = section.rows[5]
    assert set(avg_row.formula_columns) == {4, 5, 6}
    assert set(total_row.formula_columns) == {4, 6}
