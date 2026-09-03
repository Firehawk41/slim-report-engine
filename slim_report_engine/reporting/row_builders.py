"""Row-assembly primitives shared by every analyte-list section builder
(metals, ions, ...) — ported from modReportRowBuilders.bas. Pulled out to a
plain module so ion_list_section_builder can reuse this header/row/footer
shape without any element-service dependency it has no use for.

COLUMNS (1-based), matching the real template's layout:
  1=Specification  2=Label  3=Symbol  4=Result  5=Recovery  6=<third column label>
"""

from __future__ import annotations

from typing import Any

from slim_report_engine.reporting.report_row import ReportRow
from slim_report_engine.reporting.report_section import ReportSection

_DEFAULT_RESULT_LABEL = "Results"


def add_header_rows(
    section: ReportSection,
    category_label: str,
    third_column_label: str,
    result_label: str = _DEFAULT_RESULT_LABEL,
) -> None:
    """result_label defaults to the plural form used by metals/ions. Silicon's
    real header uses the SINGULAR "Result" instead — a genuine inconsistency
    in the template itself, not an error here — so it passes result_label
    explicitly rather than this default being "corrected" to match it.
    """
    top_row = ReportRow(style_name="SampleIdEchoWide", row_height=60.0)
    top_row.set_value(1, "Specification")
    top_row.set_value(2, "Sample Identification:")
    # Column 4 (sample-string echo) is filled in by the caller assembling
    # the whole sheet, not here -- a section builder only knows about ONE
    # section's own content, not the sample-level identity string that
    # every section on a sheet shares.
    # Real template merges D:F into the one echo-value cell (confirmed:
    # "Full Analysis (8)" template's D6:F6) -- declared here since it's a
    # structural property of the row's shape, independent of the value.
    top_row.add_merge(4, 6)
    section.add_row(top_row)

    header_row = ReportRow(style_name="ColumnHeader", row_height=25.5)
    header_row.set_value(2, category_label)
    header_row.set_value(4, result_label)
    header_row.set_value(5, "Recovery")
    header_row.set_value(6, third_column_label)
    section.add_row(header_row)


def add_analyte_row(section: ReportSection, name: str, symbol: str) -> None:
    row = ReportRow(style_name="DataLabel")
    row.set_value(2, name)
    row.set_value(3, symbol)
    section.add_row(row)


def add_analyte_row_with_spec(
    section: ReportSection, name: str, symbol: str, spec_value: Any = None
) -> None:
    """Same shape as add_analyte_row, plus an optional column-1 spec
    threshold (DM5 element panels carry a per-element spec value there —
    omit spec_value entirely for an element with no spec for that chemical,
    matching the real template rather than writing a 0/blank placeholder).
    """
    row = ReportRow(style_name="DataLabel")
    if spec_value is not None:
        row.set_value(1, spec_value)
    row.set_value(2, name)
    row.set_value(3, symbol)
    section.add_row(row)


def add_simple_header_row(
    section: ReportSection,
    category_label: str,
    result_label: str,
    second_col_label: str = "",
    third_col_label: str = "",
) -> None:
    """Header shape for the single/multi-parameter blocks (Electrical
    Testing, Titrations, Misc Analysis's pH/Density/LPC/APHA) — differs from
    the metals/ions analyte-panel header: no "Specification" text in column
    1, second results column is labeled "STDEV" (or blank) rather than
    always "Recovery", and there is never a third results column
    (no MDL/QL).
    """
    top_row = ReportRow(style_name="SampleIdEchoSimple", row_height=60.0)
    top_row.set_value(2, "Sample Identification:")
    # Real template's merge span on this echo cell varies slightly by
    # exact block (D:E for some, D:F for others) -- reproducing the
    # dominant D:F span uniformly rather than chasing each block's own
    # variant, consistent with this project's general "don't chase every
    # incidental template inconsistency" policy.
    top_row.add_merge(4, 6)
    section.add_row(top_row)

    header_row = ReportRow(style_name="ColumnHeader", row_height=25.5)
    header_row.set_value(2, category_label)
    header_row.set_value(4, result_label)
    if second_col_label:
        header_row.set_value(5, second_col_label)
    if third_col_label:
        header_row.set_value(6, third_col_label)
    section.add_row(header_row)


def add_note_row(section: ReportSection, text: str) -> None:
    """A single-column note/footnote row (e.g. "Dimensionless quantity", the
    Colloidal Silica calculation footnote) — like add_footer_row but without
    the "Date of Analysis: " echo, since these aren't the section's closing
    row.
    """
    row = ReportRow(style_name="Normal")
    row.set_value(1, text)
    section.add_row(row)


def add_footer_row(section: ReportSection, text: str) -> None:
    row = ReportRow(style_name="Normal")
    row.set_value(1, text)
    row.set_value(4, "Date of Analysis: ")
    section.add_row(row)


def blank_row() -> ReportRow:
    return ReportRow(style_name="Normal")
