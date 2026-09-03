from slim_report_engine.reporting.section_builders import misc_analysis_section_builder as builder


def test_ph_block_is_distinct_from_electrical_ph():
    """This Misc Analysis pH block is a real, separate block from
    electrical_section_builder.build_ph -- different header category label
    and includes a dimensionless-quantity note row electrical's doesn't."""
    section = builder.build_ph("Misc pH")
    header = section.rows[1]
    assert header.get_value(2) == "pH"
    assert header.get_value(4) == "Result"
    note = section.rows[3]
    assert note.get_value(1) == "Dimensionless quantity"
    footer = section.rows[-2]
    assert footer.get_value(1) == "Analysis by pH Electrode"


def test_density():
    section = builder.build_density("Density")
    data = section.rows[2]
    assert data.get_value(2) == "Density of solution"
    assert data.get_value(3) == "(g/mL)"
    footer = section.rows[-2]
    assert footer.get_value(1) == "Analysis by Gay-Lussac Pycnometer"


def test_lpc_has_six_threshold_rows_in_ascending_order():
    section = builder.build_lpc("LPC")
    labels = [r.get_value(2) for r in section.rows if r.style_name == "DataLabel"]
    assert labels == [
        "≥ 0.10 µm",
        "≥ 0.15 µm",
        "≥ 0.20 µm",
        "≥ 0.30 µm",
        "≥ 0.50 µm",
        "≥ 1.00 µm",
    ]


def test_apha():
    section = builder.build_apha("APHA")
    data = section.rows[2]
    assert data.get_value(2) == "APHA number"
    footer = section.rows[-2]
    assert footer.get_value(1) == "Analysis by UV-Vis (average of six replicates)"
