from slim_report_engine.reporting.section_builders import electrical_section_builder as builder


def test_conductivity_alone_footer():
    section = builder.build_conductivity("Electrical")
    footer = section.rows[-2]
    assert footer.get_value(1) == "Analysis by Conductivity Electrode"
    labels = [r.get_value(2) for r in section.rows if r.style_name == "DataLabel"]
    assert labels == ["Conductivity"]


def test_ph_alone_footer():
    section = builder.build_ph("Electrical")
    footer = section.rows[-2]
    assert footer.get_value(1) == "Analysis by pH Electrode"
    labels = [r.get_value(2) for r in section.rows if r.style_name == "DataLabel"]
    assert labels == ["pH (dimensionless quantity)"]


def test_conductivity_and_ph_has_its_own_distinct_footer():
    """The 3 real footer variants are genuinely distinct text, not derived
    from combining the two individual footers."""
    section = builder.build_conductivity_and_ph("Electrical")
    footer = section.rows[-2]
    assert footer.get_value(1) == "Analysis by pH/Conductivity Electrode"
    labels = [r.get_value(2) for r in section.rows if r.style_name == "DataLabel"]
    assert labels == ["Conductivity", "pH (dimensionless quantity)"]


def test_all_three_variants_share_the_same_header_shape():
    for section in (
        builder.build_conductivity("x"),
        builder.build_ph("x"),
        builder.build_conductivity_and_ph("x"),
    ):
        header = section.rows[1]
        assert header.get_value(2) == "Electrical Testing"
        assert header.get_value(4) == "Results"
        assert header.get_value(5) == "STDEV"
