from slim_report_engine.reporting.analyte import Analyte
from slim_report_engine.reporting.section_builders import ion_list_section_builder as builder


def test_build_ion_panel_uses_ql_not_mdl():
    section = builder.build_ion_panel("Anions", "Anion", [], "Analysis by IC")
    header = section.rows[1]
    assert header.get_value(6) == "QL"


def test_build_ion_panel_has_no_average_total_summary():
    analytes = [Analyte("Chloride", "Cl", 2), Analyte("Sulfate", "SO4", 5)]
    section = builder.build_ion_panel("Anions", "Anion", analytes, "Analysis by IC")
    for row in section.rows:
        value = row.get_value(2)
        if value:
            assert "AVERAGE" not in value
            assert "TOTAL" not in value


def test_build_ion_panel_ends_directly_at_footer():
    analytes = [Analyte("Chloride", "Cl", 2)]
    section = builder.build_ion_panel("Anions", "Anion", analytes, "Analysis by IC")
    # top, header, Chloride, footer -- no blank spacer rows
    assert section.row_count == 4
    footer = section.rows[-1]
    assert footer.get_value(1) == "Analysis by IC"


def test_build_ion_panel_rows_preserve_analyte_order():
    analytes = [Analyte("Fluoride", "F", 1), Analyte("Chloride", "Cl", 2)]
    section = builder.build_ion_panel("Anions", "Anion", analytes, "Analysis by IC")
    data_rows = section.rows[2:4]
    assert [r.get_value(3) for r in data_rows] == ["F", "Cl"]
