"""Writes ReportSection/ReportRow content into a real Excel worksheet
using openpyxl — ported from clsReportWriter.cls + modReportStyles.bas,
then corrected against the REAL templates' actual cell formatting
(Report Creator Template.xlsx, DM5-N/S Report Template.xlsx, Wafers
Report Template.xlsx), since modReportStyles.bas's 5-case vocabulary
turned out to be a simplification, not a precise match — e.g. it marks
column-header text bold, but the real templates never bold it; it has
no fill at all, but the real templates use a consistent 3-color palette
that this module now reproduces.

FIDELITY POLICY (per explicit direction, 2026-09-03): borders are
critical and applied unconditionally per row-type, matching the real
template's border presence/absence exactly. Font/color/fill are applied
precisely for every cell that carries real template text (labels,
headers, titles); cells that are blank in every real template (waiting
for a technician to fill in results by hand) are left at default
formatting even where the real template has an incidental/leftover
font or fill on them (e.g. a blank formula cell's leftover bold
AvantGarde font) — that's exactly the kind of "probably not important"
formatting explicitly called out as not worth chasing.

REAL COLOR PALETTE (confirmed identical across all three templates via
openpyxl, resolving indexed colors against the legacy palette):
  white   (idx 9,  00FFFFFF) -- "Specification"/category-label cells
  pale cyan (idx 41, 00CCFFFF) -- the "Sample Identification:"/"Sample #:" row
  light blue (idx 44, 0099CCFF) -- Results/Recovery/MDL/STDEV/QL column headers

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
# Confirmed real (Report Creator Template.xlsx, every "Sample Identification:"
# row checked, Wide AND Simple shapes both): NO border between the label
# cell (column 2) and the cell immediately to its right (column 3) -- top/
# bottom/outer-left (or outer-right) stay thin, only the shared edge is
# omitted, on BOTH sides of it.
_THIN_BOX_BORDER_NO_RIGHT = Border(
    left=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"),
)
_THIN_BOX_BORDER_NO_LEFT = Border(
    right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"),
)

# Real palette, confirmed via openpyxl against all three real templates
# (see module docstring). Written as opaque ARGB for PatternFill.
_FILL_WHITE = PatternFill(fill_type="solid", fgColor="FFFFFFFF")
_FILL_PALE_CYAN = PatternFill(fill_type="solid", fgColor="FFCCFFFF")
_FILL_LIGHT_BLUE = PatternFill(fill_type="solid", fgColor="FF99CCFF")

# Real fonts, confirmed via openpyxl. The real templates use Arial
# throughout content cells (a leftover Calibri/AvantGarde shows up only
# on cells that are blank in every real template -- not reproduced, see
# FIDELITY POLICY above).
_FONT_SPEC_LABEL = Font(name="Arial", size=8, bold=True)  # "Specification" / DM5 QC code / spec values
_FONT_SAMPLE_ECHO_LABEL = Font(name="Arial", size=9)  # "Sample Identification:" / "Sample #:"
_FONT_SAMPLE_ID_VALUE = Font(name="Arial", size=12, bold=True)  # the sample-ID string cell -- confirmed real size 12
_FONT_COLUMN_HEADER = Font(name="Arial", size=10)  # category label + Results/Recovery/MDL -- NOT bold, confirmed real
_FONT_HEADER_SPEC_LABEL = Font(name="AvantGarde", size=8, bold=True)  # DM5's header-row "Specification" text specifically
_FONT_DATA = Font(name="Arial", size=10)  # analyte name/symbol
_FONT_TITLE = Font(name="Arial", size=12, bold=True)  # DM5 title row
# Confirmed real (Report Creator Template.xlsx row 5 -- legacy indexed
# color 12, resolves to opaque blue; Wafers Report Template.xlsx row 4 --
# already stored as this exact ARGB): the "Blue font indicates..." line
# itself is rendered in blue in every real template.
_BLUE = "FF0000FF"
_FONT_NORMAL_BOLD_BLUE = Font(name="Arial", size=10, bold=True, color=_BLUE)  # generic preamble's own line
_FONT_NORMAL_BLUE = Font(name="Arial", size=10, color=_BLUE)  # Wafer's equivalent line -- NOT bold

_ALIGN_CENTER = Alignment(horizontal="center")
_ALIGN_CENTER_VCENTER = Alignment(horizontal="center", vertical="center")  # ColumnHeader row specifically -- confirmed real
_ALIGN_CENTER_WRAP = Alignment(horizontal="center", wrap_text=True, vertical="center")  # the sample-ID echo VALUE cell specifically -- confirmed real (D6 in the real template)
_ALIGN_LEFT = Alignment(horizontal="left")
_ALIGN_LEFT_VCENTER = Alignment(horizontal="left", vertical="center")  # the "Sample Identification:"/"Sample #:" label cell specifically -- confirmed real
_ALIGN_RIGHT = Alignment(horizontal="right")
_ALIGN_JUSTIFY = Alignment(horizontal="justify", vertical="center")  # the "Specification" label cell -- confirmed real

# R1C1-relative formula shape actually used anywhere in this codebase --
# same-column ranges only (the metals panel's AVERAGE/TOTAL summary rows).
# Excel itself always stores formulas as A1 references internally
# regardless of whether they were entered via .Formula or .FormulaR1C1 in
# VBA, so this translation produces an equivalent, not an approximation.
_R1C1_SAME_COLUMN_RANGE = re.compile(r"^=([A-Z]+)\(R\[(-?\d+)\]C:R\[(-?\d+)\]C\)$")


def apply_style(ws: Worksheet, row_index: int, min_col: int, max_col: int, style_name: str) -> None:
    """Ported from modReportStyles.ApplyStyle, then corrected against the
    real templates' actual formatting (see module docstring). Add a case
    here only when a genuinely new visual treatment is needed -- don't
    format ad hoc at a call site.
    """
    if style_name == "Normal":
        return  # no borders, no fill, no bold -- default cell appearance

    if style_name == "SectionTitle":
        # DM5's chemical-label title row (e.g. "NH4OH", "CSL9044C").
        for col in range(min_col, max_col + 1):
            ws.cell(row=row_index, column=col).font = _FONT_TITLE
        return

    if style_name == "NormalBold":
        # No border, no fill (matches "Normal"), but bold text -- Wafer's
        # "Notes:" and units-note rows specifically.
        for col in range(min_col, max_col + 1):
            ws.cell(row=row_index, column=col).font = Font(name="Arial", size=10, bold=True)
        return

    if style_name == "NormalBoldBlue":
        # Same as "NormalBold", but blue -- confirmed real (Report Creator
        # Template.xlsx row 5): the generic preamble's own "Blue font
        # indicates..." line is itself rendered in blue, bold text.
        for col in range(min_col, max_col + 1):
            ws.cell(row=row_index, column=col).font = _FONT_NORMAL_BOLD_BLUE
        return

    if style_name == "NormalBlue":
        # Same as "Normal", but blue, NOT bold -- confirmed real (Wafers
        # Report Template.xlsx row 4): Wafer's own "Blue font indicates
        # data at or below the MDL" line is blue but NOT bold, unlike the
        # generic preamble's equivalent line.
        for col in range(min_col, max_col + 1):
            ws.cell(row=row_index, column=col).font = _FONT_NORMAL_BLUE
        return

    if style_name == "SampleIdEchoWide":
        # The "Sample Identification:"/QC-code row for shapes that HAVE a
        # column-1 label (metals/silicon/ion panels via add_header_rows,
        # DM5's QC-code row, Wafer's sample-ID row). Confirmed real: NO
        # border between columns 2 and 3 (the label sits in column 2;
        # column 3 is a separate, borderless-on-that-side spacer cell).
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row_index, column=col)
            if col == 2:
                cell.border = _THIN_BOX_BORDER_NO_RIGHT
            elif col == 3:
                cell.border = _THIN_BOX_BORDER_NO_LEFT
            else:
                cell.border = _THIN_BOX_BORDER
            if col == 1:
                cell.font = _FONT_SPEC_LABEL
                cell.fill = _FILL_WHITE
                cell.alignment = _ALIGN_JUSTIFY
            elif col in (2, 3):
                cell.font = _FONT_SAMPLE_ECHO_LABEL
                cell.fill = _FILL_PALE_CYAN
                cell.alignment = _ALIGN_LEFT_VCENTER
            else:
                cell.font = _FONT_SAMPLE_ID_VALUE
                cell.fill = _FILL_PALE_CYAN
                cell.alignment = _ALIGN_CENTER_WRAP
        return

    if style_name == "SampleIdEchoSimple":
        # Same row, for shapes with NO column-1 label (TOC/Alkalinity/
        # Bacteria/Electrical/Misc Analysis via add_simple_header_row) --
        # confirmed real: column 1 has no border or fill at all here,
        # unlike the "Wide" variant; same no-border-between-2-and-3 rule.
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row_index, column=col)
            if col == 1:
                continue
            if col == 2:
                cell.border = _THIN_BOX_BORDER_NO_RIGHT
            elif col == 3:
                cell.border = _THIN_BOX_BORDER_NO_LEFT
            else:
                cell.border = _THIN_BOX_BORDER
            if col in (2, 3):
                cell.font = _FONT_SAMPLE_ECHO_LABEL
                cell.fill = _FILL_PALE_CYAN
                cell.alignment = _ALIGN_LEFT_VCENTER
            else:
                cell.font = _FONT_SAMPLE_ID_VALUE
                cell.fill = _FILL_PALE_CYAN
                cell.alignment = _ALIGN_CENTER_WRAP
        return

    if style_name == "SampleIdEchoAssay":
        # DM5's Assay-shape "Sample #" row (CSL9044C/W-2000/W-7808) --
        # confirmed real: shifted one column left of the Wide variant
        # (label in column 2, the stamp target in column 3, nothing in
        # column 1 or beyond column 3).
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row_index, column=col)
            if col not in (2, 3):
                continue
            cell.border = _THIN_BOX_BORDER
            cell.fill = _FILL_PALE_CYAN
            cell.font = _FONT_SAMPLE_ECHO_LABEL
        return

    if style_name == "ColumnHeader":
        # The category-label + Results/Recovery/MDL (or STDEV/QL) row.
        # Confirmed real: NOT bold, despite the name inherited from
        # modReportStyles.bas's "HeaderBold". Column 1 is blank in generic
        # Chemical/Water/Wafer panels (font is applied but invisible) but
        # carries real "Specification" text in DM5 element panels -- same
        # AvantGarde/no-fill treatment either way, since it's correct when
        # populated and harmless when not. Confirmed real: every label on
        # this row is vertically centered.
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row_index, column=col)
            cell.border = _THIN_BOX_BORDER
            cell.alignment = _ALIGN_CENTER_VCENTER
            if col == 1:
                cell.font = _FONT_HEADER_SPEC_LABEL
                continue
            cell.font = _FONT_COLUMN_HEADER
            cell.fill = _FILL_WHITE if col in (2, 3) else _FILL_LIGHT_BLUE
        return

    if style_name == "ColumnHeaderAssay":
        # DM5's Assay-shape header row ("Current Specifications"/
        # "Parameter"/result-label/"STDV") -- confirmed real: results
        # start one column earlier than the Wide shapes (column 3, not
        # 4), column 1/2 have NO fill at all (not white), and the
        # results columns ARE bold here (unlike the general ColumnHeader
        # case) -- a genuinely different treatment, not reusable.
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row_index, column=col)
            cell.border = _THIN_BOX_BORDER
            cell.alignment = _ALIGN_CENTER
            if col == 1:
                cell.font = Font(name="Arial", size=9, bold=True)
            elif col == 2:
                cell.font = _FONT_COLUMN_HEADER
            else:
                cell.font = Font(name="Arial", size=10, bold=True)
                cell.fill = _FILL_LIGHT_BLUE
        return

    if style_name == "DataLabel":
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row_index, column=col)
            cell.border = _THIN_BOX_BORDER
            if col == 1:
                # Only DM5 element panels populate this (a per-element
                # spec threshold) -- styled whether or not this
                # particular row has one, so a populated spec value
                # elsewhere in the same column looks consistent.
                cell.font = _FONT_SPEC_LABEL
                cell.alignment = _ALIGN_CENTER
            else:
                cell.font = _FONT_DATA
                cell.alignment = _ALIGN_LEFT
        return

    if style_name == "DataValue":
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row_index, column=col)
            cell.border = _THIN_BOX_BORDER
            cell.font = _FONT_DATA
            cell.alignment = _ALIGN_RIGHT
        return

    if style_name == "SummaryRow":
        # The metals panel's AVERAGE/TOTAL rows -- confirmed real: same
        # pale-cyan fill as the Sample-ID row, starting at column 2 (no
        # real template populates column 1 here).
        for col in range(min_col, max_col + 1):
            if col == 1:
                continue
            cell = ws.cell(row=row_index, column=col)
            cell.border = _THIN_BOX_BORDER
            cell.font = _FONT_DATA
            cell.fill = _FILL_PALE_CYAN
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

    if row.row_height is not None:
        ws.row_dimensions[row_index].height = row.row_height

    for start_col, end_col in row.merges:
        ws.merge_cells(
            start_row=row_index, start_column=start_col, end_row=row_index, end_column=end_col
        )


def apply_zoom(ws: Worksheet, zoom: int) -> None:
    """Confirmed real (openpyxl against every real template): the generic
    Chemical/Water and DM5 templates are all zoomed to 90%; Wafer is the
    one exception, at 95% -- see OutputSheet.zoom (submission_report_builder.py).
    """
    ws.sheet_view.zoomScale = zoom


_PROCESSING_TIME_STAMP_COLORS = {"red": "FFFF0000", "blue": _BLUE}


def apply_processing_time_stamp(ws: Worksheet, cell_address: str, text: str, color: str, size: int) -> None:
    """Confirmed real (every completed report checked with a rush/time-
    limited sample -- generic Chemical/Water, DM5, and Wafer all showed
    it): a single-cell stamp on row 1, alongside the title (which already
    carries a different, row-wide style) -- bold, RED for the RUSH
    variants ("Same Day RUSH", "Call-in RUSH", Wafer's own "Next Day
    RUSH"), BLUE for "Next Day Time Limited". A plain "Next Day"/"Two
    Days"/"Three Days" sample has no stamp at all -- see
    submission_report_builder.py's _processing_time_stamp, which decides
    whether to call this at all.

    size: 10 for generic Chemical/Water and DM5, 12 for Wafer (matches its
    bigger title-row font throughout).
    """
    cell = ws[cell_address]
    cell.value = text
    cell.font = Font(name="Arial", size=size, bold=True, color=_PROCESSING_TIME_STAMP_COLORS[color])


def apply_column_widths(ws: Worksheet, widths: dict[int, float]) -> None:
    """widths: column index (1-based) -> width in points, e.g.
    column_widths.STANDARD. Applied once per sheet by the caller that knows
    which report family produced it (see submission_report_builder.py).
    """
    for col_index, width in widths.items():
        ws.column_dimensions[get_column_letter(col_index)].width = width


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
