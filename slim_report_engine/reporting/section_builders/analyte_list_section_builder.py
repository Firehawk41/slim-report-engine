"""Builds a ReportSection for the trace-element (metals) panel shape — a
list of analytes with Result/Recovery/MDL columns and an AVERAGE/TOTAL
summary — the shape shared by every trace-element panel (10/26/36/67/USP
Elements). Ported from clsAnalyteListSectionBuilder.cls.

Replaces ~15 near-duplicate named ranges that turned out to be the same
header/summary shape wrapped around a different analyte list and summary
label: the "10/26/36 Elements" selections are the SAME 36-element list —
only the AVERAGE/TOTAL label text differs — so the caller passes the
summary label explicitly rather than this inferring it from the list.

Ions (Anions/Cations/GBP) share the header/row/footer shape (see
row_builders) but have no DB-backed catalog and no AVERAGE/TOTAL summary —
they're built by ion_list_section_builder instead, so this doesn't take an
ElementService dependency ion callers would have no use for.

SUMMARY FORMULAS: AVERAGE/TOTAL rows use relative R1C1 formula text (see
ReportRow.set_formula) computed from the section's own row count as analyte
rows are added — correct for any analyte count without hardcoding row
numbers, unlike the template it replaces.
"""

from __future__ import annotations

from slim_domain.domain.element.element_service import ElementService

from slim_report_engine.reporting import row_builders
from slim_report_engine.reporting.report_row import ReportRow
from slim_report_engine.reporting.report_section import ReportSection


def build_metals_panel(
    id: str,
    symbols: list[str],
    summary_label: str,
    element_service: ElementService,
) -> ReportSection:
    """symbols: element symbols in display order. summary_label: the text
    that appears in "AVERAGE / <summary_label>" and "TOTAL / <summary_label>"
    — e.g. "36 Tr.Elts" for the 10/26/36-Elements selections (all three
    render the same 36 analytes; only this label differs), "67 Tr.Elts",
    "USP Tr.Elts".
    """
    section = ReportSection(id)
    row_builders.add_header_rows(section, "Element", "MDL")

    first_data_row = section.row_count + 1  # row right after the 2 header rows

    for symbol in symbols:
        element = element_service.get_by_symbol(symbol)
        if element is None:
            raise ValueError(f"unknown element symbol in panel definition: {symbol!r}")
        row_builders.add_analyte_row(section, element.name, element.symbol)

    _add_summary_rows(section, summary_label, first_data_row)
    row_builders.add_footer_row(section, "Analysis by ICPMS (Evaporation)")

    return section


def _add_summary_rows(section: ReportSection, summary_label: str, first_data_row: int) -> None:
    """Adds: blank spacer, AVERAGE row, TOTAL row, blank spacer — matching
    the real template's layout (one blank row before AND after the
    AVERAGE/TOTAL pair). Formula row/column references are RELATIVE R1C1
    text, computed from logical row positions within this section so
    they're correct regardless of how many analytes were added or where
    this section ends up on the final sheet.
    """
    last_data_row = section.row_count  # last analyte row added so far

    section.add_row(row_builders.blank_row())  # spacer before summary

    avg_row_index = section.row_count + 1
    avg_row = ReportRow(style_name="DataLabel")
    avg_row.set_value(2, f"AVERAGE / {summary_label}")
    for col in (4, 5, 6):
        _set_range_formula(avg_row, col, "AVERAGE", first_data_row, last_data_row, avg_row_index)
    section.add_row(avg_row)

    total_row_index = section.row_count + 1
    total_row = ReportRow(style_name="DataLabel")
    total_row.set_value(2, f"TOTAL / {summary_label}")
    for col in (4, 6):
        _set_range_formula(total_row, col, "SUM", first_data_row, last_data_row, total_row_index)
    section.add_row(total_row)

    section.add_row(row_builders.blank_row())  # spacer after summary


def _set_range_formula(
    target_row: ReportRow,
    col_index: int,
    func_name: str,
    first_row: int,
    last_row: int,
    formula_row: int,
) -> None:
    offset_first = first_row - formula_row
    offset_last = last_row - formula_row
    target_row.set_formula(col_index, f"={func_name}(R[{offset_first}]C:R[{offset_last}]C)")
