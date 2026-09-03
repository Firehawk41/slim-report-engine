"""Writes ReportSection/ReportRow content into a real Excel worksheet
using openpyxl — ported from clsReportWriter.cls + modReportStyles.bas.

This project originally planned to keep the actual Excel write VBA-side
(see README.md's earlier "Architecture direction" section) on the
assumption that the real template's styling logic was substantial,
already-solved, hard-to-re-derive work worth reusing as-is. Reading the
actual VBA source showed the opposite: modReportStyles.bas is a five-case
named-style vocabulary (~30 lines), and clsReportWriter.WriteRow is just
a bulk value write, a handful of sparse formula overrides, and one style
application call — all straightforwardly portable, and doing so collapses
the open "bridge mechanism" question (a live VBA<->Python COM
server/subprocess bridge) down to nothing: Python can own the whole
read-workbook -> parse -> transform -> write-workbook pipeline directly.

LAYER: Writer — the only module in this package allowed to import
openpyxl's Worksheet type or touch cell formatting. Everything upstream
(entities, presets, section builders, orchestrators) stays pure
computation, independently testable without ever opening a workbook.
"""

from __future__ import annotations

import re

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from slim_report_engine.reporting.report_row import ReportRow
from slim_report_engine.reporting.report_section import ReportSection

_THIN_BOX_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)
_BOLD = Font(bold=True)
_ALIGN_CENTER = Alignment(horizontal="center")
_ALIGN_LEFT = Alignment(horizontal="left")
_ALIGN_RIGHT = Alignment(horizontal="right")
_ALIGN_CENTER_MIDDLE_WRAP = Alignment(horizontal="center", vertical="center", wrap_text=True)

# R1C1-relative formula shape actually used anywhere in this codebase --
# same-column ranges only (the metals panel's AVERAGE/TOTAL summary rows).
# Excel itself always stores formulas as A1 references internally
# regardless of whether they were entered via .Formula or .FormulaR1C1 in
# VBA, so this translation produces an equivalent, not an approximation.
_R1C1_SAME_COLUMN_RANGE = re.compile(r"^=([A-Z]+)\(R\[(-?\d+)\]C:R\[(-?\d+)\]C\)$")


def apply_style(ws: Worksheet, row_index: int, min_col: int, max_col: int, style_name: str) -> None:
    """Ported from modReportStyles.ApplyStyle. Add a case here only when a
    genuinely new visual treatment is needed -- don't format ad hoc at a
    call site.
    """
    if style_name == "Normal":
        return  # no borders, no bold -- default cell appearance

    if style_name == "HeaderBold":
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row_index, column=col)
            cell.font = _BOLD
            cell.border = _THIN_BOX_BORDER
            cell.alignment = _ALIGN_CENTER
        return

    if style_name == "DataLabel":
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row_index, column=col)
            cell.border = _THIN_BOX_BORDER
            cell.alignment = _ALIGN_LEFT
        return

    if style_name == "DataValue":
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row_index, column=col)
            cell.border = _THIN_BOX_BORDER
            cell.alignment = _ALIGN_RIGHT
        return

    if style_name == "SectionTitle":
        # The real VBA source sets Interior.Pattern = xlSolid without ever
        # setting Interior.Color -- an unresolved real quirk (the visual
        # result depends on whatever the cell's inherited/default color
        # already was), not something to silently invent a color for.
        # Not currently used by any ported section builder. Bold/centered/
        # wrapped is applied; the fill is deliberately left unset.
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row_index, column=col)
            cell.font = _BOLD
            cell.alignment = _ALIGN_CENTER_MIDDLE_WRAP
        return

    raise ValueError(
        f"unknown style name: {style_name!r} -- add a case for it in apply_style, "
        "don't format ad hoc at the call site."
    )


def write_row(ws: Worksheet, row: ReportRow, row_index: int) -> None:
    for col_index, value in row.values.items():
        ws.cell(row=row_index, column=col_index).value = value

    # Sparse formula overrides: translated from R1C1-relative text to a
    # real A1 range using the row this row actually landed on, so the
    # offsets resolve correctly regardless of where the section ended up
    # on the sheet.
    for col_index in row.formula_columns:
        formula = row.get_formula(col_index)
        match = _R1C1_SAME_COLUMN_RANGE.match(formula)
        if match is None:
            raise ValueError(
                f"formula {formula!r} doesn't match the only supported R1C1 shape "
                "(=FUNC(R[a]C:R[b]C)) -- extend the translator in report_writer.py "
                "before using a new formula shape."
            )
        func, offset_first, offset_last = match.group(1), int(match.group(2)), int(match.group(3))
        col_letter = get_column_letter(col_index)
        first_row, last_row = row_index + offset_first, row_index + offset_last
        ws.cell(row=row_index, column=col_index).value = f"={func}({col_letter}{first_row}:{col_letter}{last_row})"

    apply_style(ws, row_index, min_col=1, max_col=row.max_columns, style_name=row.style_name)


def write_section(ws: Worksheet, section: ReportSection, start_row: int = 1) -> int:
    """Writes one section starting at start_row; returns the row
    immediately after the last row written, so callers can chain sections
    back to back."""
    row_index = start_row
    for row in section.rows:
        write_row(ws, row, row_index)
        row_index += 1
    return row_index


def write_sections(ws: Worksheet, sections: list[ReportSection], start_row: int = 1) -> int:
    current_row = start_row
    for section in sections:
        current_row = write_section(ws, section, current_row)
    return current_row


def apply_header_footer(
    ws: Worksheet,
    center_header: str,
    customer_name: str,
    customer_address_line1: str,
    customer_address_line2: str,
    lab_header_lines: tuple[str, ...] = (),
) -> None:
    """Ported from modReportCreator.bas's AddHeaderAndFooter. lab_header_lines:
    the lab's own name/address/phone block for the left header -- deliberately
    a caller-supplied parameter, not hardcoded, since that's real company
    identity this public repo doesn't carry (see DOMAIN_BRIEF.md's
    de-branding note); the internal/private fork supplies the real values.
    """
    # Confirmed real openpyxl quirk: assigning an explicit empty string to
    # a header/footer part corrupts the OTHER parts on save/reload (the
    # empty part's "&L"/"&C"/"&R" control code leaks into a neighboring
    # part's text instead of being omitted) -- only assign when there's
    # actual content, leave the attribute unset (its default) otherwise.
    if lab_header_lines:
        ws.oddHeader.left.text = "\n".join(lab_header_lines)
    ws.oddHeader.center.text = center_header
    ws.oddHeader.right.text = f"{customer_name}\n{customer_address_line1}\n{customer_address_line2}\n"
    ws.oddFooter.center.text = "&F"
    ws.oddFooter.right.text = "Page &P"
    ws.page_margins.top = 0.99
