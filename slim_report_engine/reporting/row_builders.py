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


def build_header_preamble(title: str) -> ReportSection:
    """The sheet-wide preamble every generic Chemical/Water report starts
    with, before ANY section's own sample-ID echo row -- confirmed real
    (every real Chemical/Water report checked, both request types): title
    (its own row, column 1 only), one blank row, then 3 fixed lines --
    "Notes:", "All data in units of ppb unless otherwise noted", "Blue
    font indicates data at or below detection limits". Always exactly
    these 3 lines and this order for the generic path; NOT shared with
    DM5 (its own, different 4-row shape -- title/blank/blank/one combined
    notes row, no "Blue font" line) or Wafer (which already reproduces
    this same 5-row shape itself, with its own analysis-specific note
    text, in wafer_panel_builder.py).

    Returned as its OWN ReportSection, deliberately excluded from the
    "stamp column 4 of every section's row 0 with the sample-ID string"
    loop (submission_report_builder.py) -- the title row carries no
    sample-ID echo, only the real sample-ID-echo row (in the first REAL
    section) does.
    """
    section = ReportSection("Header")

    title_row = ReportRow(style_name="SectionTitle")
    title_row.set_value(1, title)
    section.add_row(title_row)

    section.add_row(blank_row())

    notes_row = ReportRow(style_name="NormalBold")
    notes_row.set_value(1, "Notes:")
    section.add_row(notes_row)

    units_row = ReportRow(style_name="NormalBold")
    units_row.set_value(1, "All data in units of ppb unless otherwise noted")
    section.add_row(units_row)

    blue_font_row = ReportRow(style_name="NormalBold")
    blue_font_row.set_value(1, "Blue font indicates data at or below detection limits")
    section.add_row(blue_font_row)

    return section


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


def add_analyte_row(section: ReportSection, name: str, symbol: str, max_columns: int | None = None) -> None:
    """max_columns: override the row's style-application width -- confirmed
    real (Wafers Report Template.xlsx): Wafer's own analyte rows border/fill
    all the way to column 19 (its MAX_SAMPLE_COLUMNS, matching its header
    rows), not the standard family's column 6 -- wafer_panel_builder.py
    passes it explicitly; every other caller leaves this at the default.
    """
    row = ReportRow(style_name="DataLabel", **({"max_columns": max_columns} if max_columns else {}))
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


def add_footer_row(section: ReportSection, text: str, sop_codes: list[str] | None = None) -> None:
    """Confirmed real (every shape checked -- metals/ion panels, Assay,
    LPC): exactly one blank row separates the last content row from
    "Analysis by ...", and exactly one blank row separates it from
    whatever comes next (the next section's own sample-ID echo row, or
    the end of the sheet). The leading blank is skipped when the section
    already ends in one (e.g. the metals panel's own AVERAGE/TOTAL
    summary already adds its own trailing spacer) so sections never end
    up with two blank rows in a row.

    sop_codes: real ISO17025 SOP codes covering this section (see
    sop_codes.py) -- when given, a "Test Methods: ..." row is added
    directly under the footer text row, BEFORE the trailing blank --
    confirmed real (every real "Test Methods:" line found sits
    immediately under its own section's "Analysis by ..." footer, not
    after the blank spacer). None (the default) means no confirmed real
    evidence yet for this exact combination -- omit the line entirely
    rather than guess.
    """
    if section.rows and section.rows[-1].values:
        section.add_row(blank_row())
    row = ReportRow(style_name="Normal")
    row.set_value(1, text)
    row.set_value(4, "Date of Analysis: ")
    section.add_row(row)
    if sop_codes:
        section.add_row(test_methods_row(sop_codes))
    section.add_row(blank_row())


def test_methods_row(codes: list[str], max_columns: int | None = None) -> ReportRow:
    """Confirmed real format: "Test Methods: " + codes joined with ", "
    between all but the last pair and " and " before the last, always
    ending in a period. Real reports are inconsistent about the trailing
    period on a SINGLE-code line (some real reports omit it, no
    discernible rule -- see sop_codes.py) -- always included here for
    consistency. max_columns: see add_analyte_row -- Wafer passes its own
    wide override here too.
    """
    row = ReportRow(style_name="Normal", **({"max_columns": max_columns} if max_columns else {}))
    if len(codes) == 1:
        text = f"Test Methods: {codes[0]}."
    else:
        text = f"Test Methods: {', '.join(codes[:-1])} and {codes[-1]}."
    row.set_value(1, text)
    return row


def blank_row() -> ReportRow:
    return ReportRow(style_name="Normal")
