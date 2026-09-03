import openpyxl
import pytest

from slim_report_engine.reporting import report_writer
from slim_report_engine.reporting.report_row import ReportRow
from slim_report_engine.reporting.report_section import ReportSection


@pytest.fixture
def ws():
    wb = openpyxl.Workbook()
    return wb.active


# ---------------------------------------------------------------------------
# apply_style
# ---------------------------------------------------------------------------

def test_normal_style_leaves_default_formatting(ws):
    report_writer.apply_style(ws, row_index=1, min_col=1, max_col=3, style_name="Normal")
    cell = ws.cell(row=1, column=1)
    assert cell.font.bold is not True
    assert cell.border.left.style is None


def test_header_bold_style(ws):
    report_writer.apply_style(ws, row_index=1, min_col=2, max_col=4, style_name="HeaderBold")
    for col in (2, 3, 4):
        cell = ws.cell(row=1, column=col)
        assert cell.font.bold is True
        assert cell.border.left.style == "thin"
        assert cell.alignment.horizontal == "center"
    # Untouched outside the given column range.
    assert ws.cell(row=1, column=1).font.bold is not True


def test_data_label_style(ws):
    report_writer.apply_style(ws, row_index=2, min_col=1, max_col=1, style_name="DataLabel")
    cell = ws.cell(row=2, column=1)
    assert cell.border.left.style == "thin"
    assert cell.alignment.horizontal == "left"
    assert cell.font.bold is not True


def test_data_value_style(ws):
    report_writer.apply_style(ws, row_index=2, min_col=1, max_col=1, style_name="DataValue")
    cell = ws.cell(row=2, column=1)
    assert cell.border.left.style == "thin"
    assert cell.alignment.horizontal == "right"


def test_section_title_style_bold_centered_wrapped_no_fill_assumed(ws):
    report_writer.apply_style(ws, row_index=1, min_col=1, max_col=5, style_name="SectionTitle")
    cell = ws.cell(row=1, column=1)
    assert cell.font.bold is True
    assert cell.alignment.horizontal == "center"
    assert cell.alignment.vertical == "center"
    assert cell.alignment.wrap_text is True


def test_unknown_style_raises(ws):
    with pytest.raises(ValueError, match="unknown style name"):
        report_writer.apply_style(ws, row_index=1, min_col=1, max_col=1, style_name="Nonexistent")


# ---------------------------------------------------------------------------
# write_row
# ---------------------------------------------------------------------------

def test_write_row_writes_values(ws):
    row = ReportRow(style_name="Normal")
    row.set_value(2, "Aluminum")
    row.set_value(3, "Al")
    report_writer.write_row(ws, row, row_index=5)
    assert ws.cell(row=5, column=2).value == "Aluminum"
    assert ws.cell(row=5, column=3).value == "Al"


def test_write_row_translates_formula_to_real_a1_range(ws):
    row = ReportRow(style_name="DataLabel")
    row.set_formula(4, "=AVERAGE(R[-4]C:R[-2]C)")
    report_writer.write_row(ws, row, row_index=40)
    assert ws.cell(row=40, column=4).value == "=AVERAGE(D36:D38)"


def test_write_row_applies_style(ws):
    row = ReportRow(style_name="HeaderBold")
    row.set_value(2, "Element")
    report_writer.write_row(ws, row, row_index=1)
    assert ws.cell(row=1, column=2).font.bold is True


def test_write_row_unsupported_formula_shape_raises(ws):
    row = ReportRow(style_name="Normal")
    row.set_formula(1, "=SUM(R1C1:R5C5)")  # a cross-column shape, never used, not supported
    with pytest.raises(ValueError, match="doesn't match the only supported"):
        report_writer.write_row(ws, row, row_index=1)


# ---------------------------------------------------------------------------
# write_section / write_sections
# ---------------------------------------------------------------------------

def _two_row_section(id: str) -> ReportSection:
    section = ReportSection(id)
    r1 = ReportRow(style_name="Normal")
    r1.set_value(1, f"{id}-row1")
    section.add_row(r1)
    r2 = ReportRow(style_name="Normal")
    r2.set_value(1, f"{id}-row2")
    section.add_row(r2)
    return section


def test_write_section_returns_next_row(ws):
    next_row = report_writer.write_section(ws, _two_row_section("A"), start_row=1)
    assert next_row == 3
    assert ws.cell(row=1, column=1).value == "A-row1"
    assert ws.cell(row=2, column=1).value == "A-row2"


def test_write_sections_chains_back_to_back(ws):
    sections = [_two_row_section("A"), _two_row_section("B")]
    next_row = report_writer.write_sections(ws, sections, start_row=1)
    assert next_row == 5
    assert ws.cell(row=1, column=1).value == "A-row1"
    assert ws.cell(row=2, column=1).value == "A-row2"
    assert ws.cell(row=3, column=1).value == "B-row1"
    assert ws.cell(row=4, column=1).value == "B-row2"


# ---------------------------------------------------------------------------
# apply_header_footer
# ---------------------------------------------------------------------------

def test_apply_header_footer_sets_expected_fields(ws):
    report_writer.apply_header_footer(
        ws,
        center_header="36 Elements",
        customer_name="Acme Corp",
        customer_address_line1="123 Main St",
        customer_address_line2="Springfield, IL",
        lab_header_lines=("Some Lab", "100 Industrial Pkwy", "Phone: 555-0100"),
    )
    assert ws.oddHeader.left.text == "Some Lab\n100 Industrial Pkwy\nPhone: 555-0100"
    assert ws.oddHeader.center.text == "36 Elements"
    assert "Acme Corp" in ws.oddHeader.right.text
    assert ws.oddFooter.center.text == "&F"
    assert ws.oddFooter.right.text == "Page &P"
    assert ws.page_margins.top == 0.99


def test_apply_header_footer_survives_a_real_save_and_reload(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    report_writer.apply_header_footer(
        ws,
        center_header="36 Elements",
        customer_name="Acme Corp",
        customer_address_line1="123 Main St",
        customer_address_line2="Springfield, IL",
    )
    path = tmp_path / "test.xlsx"
    wb.save(path)

    reloaded = openpyxl.load_workbook(path)
    reloaded_ws = reloaded.active
    assert reloaded_ws.oddHeader.center.text == "36 Elements"
    assert reloaded_ws.oddFooter.center.text == "&F"
    assert reloaded_ws.page_margins.top == 0.99


def test_apply_header_footer_no_lab_lines_leaves_left_header_unset(ws):
    """Deliberately left unset (not assigned an empty string) -- see the
    comment in apply_header_footer for the real openpyxl serialization bug
    this avoids."""
    report_writer.apply_header_footer(
        ws,
        center_header="TOC",
        customer_name="Acme Corp",
        customer_address_line1="",
        customer_address_line2="",
    )
    assert ws.oddHeader.left.text is None


def test_apply_header_footer_no_lab_lines_survives_save_and_reload(tmp_path):
    """Regression test for the empty-string-corrupts-neighboring-parts bug:
    confirms center/right still come back correctly when left is never set."""
    wb = openpyxl.Workbook()
    ws = wb.active
    report_writer.apply_header_footer(
        ws,
        center_header="TOC",
        customer_name="Acme Corp",
        customer_address_line1="",
        customer_address_line2="",
    )
    path = tmp_path / "test.xlsx"
    wb.save(path)

    reloaded = openpyxl.load_workbook(path)
    reloaded_ws = reloaded.active
    assert reloaded_ws.oddHeader.center.text == "TOC"
    assert reloaded_ws.oddHeader.right.text is not None
    assert "Acme Corp" in reloaded_ws.oddHeader.right.text
