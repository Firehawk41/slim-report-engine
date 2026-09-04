from slim_report_engine.reporting import report_row, row_builders
from slim_report_engine.reporting.report_section import ReportSection


def test_add_header_rows_default_result_label():
    section = ReportSection("test")
    row_builders.add_header_rows(section, "Element", "MDL")
    assert section.row_count == 2
    top, header = section.rows
    assert top.get_value(1) == "Specification"
    assert top.get_value(2) == "Sample Identification:"
    assert header.get_value(2) == "Element"
    assert header.get_value(4) == "Results"
    assert header.get_value(5) == "Recovery"
    assert header.get_value(6) == "MDL"


def test_add_header_rows_custom_result_label():
    section = ReportSection("test")
    row_builders.add_header_rows(section, "Element", "MDL", result_label="Result")
    _, header = section.rows
    assert header.get_value(4) == "Result"


def test_add_analyte_row():
    section = ReportSection("test")
    row_builders.add_analyte_row(section, "Aluminum", "Al")
    row = section.rows[0]
    assert row.style_name == "DataLabel"
    assert row.get_value(2) == "Aluminum"
    assert row.get_value(3) == "Al"
    assert row.get_value(1) is None


def test_add_analyte_row_default_max_columns():
    section = ReportSection("test")
    row_builders.add_analyte_row(section, "Aluminum", "Al")
    assert section.rows[0].max_columns == report_row.DEFAULT_MAX_COLUMNS


def test_add_analyte_row_custom_max_columns():
    """Confirmed real (Wafers Report Template.xlsx): Wafer's analyte-row
    border/fill extends to column 19, not the standard family's 6 --
    wafer_panel_builder.py passes this explicitly."""
    section = ReportSection("test")
    row_builders.add_analyte_row(section, "Aluminum", "Al", max_columns=19)
    assert section.rows[0].max_columns == 19


def test_add_analyte_row_with_spec_omitted():
    section = ReportSection("test")
    row_builders.add_analyte_row_with_spec(section, "Aluminum", "Al")
    row = section.rows[0]
    assert row.get_value(1) is None


def test_add_analyte_row_with_spec_present():
    section = ReportSection("test")
    row_builders.add_analyte_row_with_spec(section, "Aluminum", "Al", spec_value=5.0)
    row = section.rows[0]
    assert row.get_value(1) == 5.0


def test_add_simple_header_row_optional_columns_omitted_when_blank():
    section = ReportSection("test")
    row_builders.add_simple_header_row(section, "pH", "Result")
    _, header = section.rows
    assert header.get_value(5) is None
    assert header.get_value(6) is None


def test_add_simple_header_row_optional_columns_set_when_given():
    section = ReportSection("test")
    row_builders.add_simple_header_row(section, "TOC", "Results", "STDEV", "QL")
    _, header = section.rows
    assert header.get_value(5) == "STDEV"
    assert header.get_value(6) == "QL"


def test_add_note_row():
    section = ReportSection("test")
    row_builders.add_note_row(section, "Dimensionless quantity")
    row = section.rows[0]
    assert row.get_value(1) == "Dimensionless quantity"
    assert row.get_value(4) is None


def test_add_footer_row_echoes_date_of_analysis():
    section = ReportSection("test")
    row_builders.add_footer_row(section, "Analysis by pH Electrode")
    row = section.rows[0]
    assert row.get_value(1) == "Analysis by pH Electrode"
    assert row.get_value(4) == "Date of Analysis: "


def test_add_footer_row_without_sop_codes_has_no_test_methods_row():
    section = ReportSection("test")
    row_builders.add_footer_row(section, "Analysis by pH Electrode")
    assert section.row_count == 2  # footer, trailing blank -- no Test Methods line
    assert not any("Test Methods" in str(r.get_value(1)) for r in section.rows)


def test_add_footer_row_with_sop_codes_inserts_test_methods_row_before_trailing_blank():
    section = ReportSection("test")
    row_builders.add_footer_row(section, "Analysis by ICPMS (Evaporation)", sop_codes=["PR-IN14", "PR-IN48"])
    footer, test_methods, trailing_blank = section.rows
    assert footer.get_value(1) == "Analysis by ICPMS (Evaporation)"
    assert test_methods.get_value(1) == "Test Methods: PR-IN14 and PR-IN48."
    assert trailing_blank.values == {}


def test_test_methods_row_single_code_has_trailing_period():
    row = row_builders.test_methods_row(["PR-IN04"])
    assert row.get_value(1) == "Test Methods: PR-IN04."


def test_test_methods_row_two_codes_joined_with_and():
    row = row_builders.test_methods_row(["PR-IN46", "PR-IN06"])
    assert row.get_value(1) == "Test Methods: PR-IN46 and PR-IN06."


def test_test_methods_row_three_codes_use_comma_then_and():
    row = row_builders.test_methods_row(["PR-IN14", "PR-IN48", "PR-IN52"])
    assert row.get_value(1) == "Test Methods: PR-IN14, PR-IN48 and PR-IN52."


def test_test_methods_row_default_max_columns():
    row = row_builders.test_methods_row(["PR-IN04"])
    assert row.max_columns == report_row.DEFAULT_MAX_COLUMNS


def test_test_methods_row_custom_max_columns():
    row = row_builders.test_methods_row(["PR-IN27", "PR-IN45"], max_columns=19)
    assert row.max_columns == 19


def test_blank_row_has_no_values():
    row = row_builders.blank_row()
    assert row.style_name == "Normal"
    assert row.get_value(1) is None
