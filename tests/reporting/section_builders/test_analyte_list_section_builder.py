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


def test_summary_rows_only_have_formulas_on_expected_columns():
    section = builder.build_metals_panel(
        "36 Elements", ["Al"], "36 Tr.Elts", _FakeElementService()
    )
    # rows: top, header, Al, blank, AVERAGE, TOTAL, blank, footer
    avg_row = section.rows[4]
    total_row = section.rows[5]
    assert set(avg_row.formula_columns) == {4, 5, 6}
    assert set(total_row.formula_columns) == {4, 6}
