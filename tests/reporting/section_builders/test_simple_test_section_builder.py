from slim_report_engine.reporting.section_builders import simple_test_section_builder as builder


def test_build_toc():
    section = builder.build_toc("TOC")
    header = section.rows[1]
    assert header.get_value(5) == "STDEV"
    assert header.get_value(6) == "QL"
    data = section.rows[2]
    assert data.get_value(2) == "TOC"
    assert data.get_value(3) == "ppb"
    footer = section.rows[-2]
    assert footer.get_value(1) == "Analysis by TOC Instrument"


def test_build_alkalinity_has_no_third_column():
    section = builder.build_alkalinity("Alkalinity")
    header = section.rows[1]
    assert header.get_value(5) == "STDEV"
    assert header.get_value(6) is None


def test_build_bacteria():
    section = builder.build_bacteria("Bacteria")
    header = section.rows[1]
    assert header.get_value(5) == "1/2 Delta"
    data = section.rows[2]
    assert data.get_value(2) == "48 h incubation"
    assert data.get_value(3) == "CFU/L"
    footer = section.rows[-2]
    assert footer.get_value(1) == "Heterotrophic Plate Count"
