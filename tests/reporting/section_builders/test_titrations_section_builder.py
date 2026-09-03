from slim_report_engine.reporting.section_builders import titrations_section_builder as builder


def test_build_assay_shape():
    section = builder.build_assay("Assay")
    header, data = section.rows[1], section.rows[2]
    assert header.get_value(2) == "Assay"
    assert header.get_value(4) == "Result"
    assert header.get_value(5) == "STDEV"
    assert data.get_value(2) == ""
    assert data.get_value(3) == "%"
    footer = section.rows[-2]
    assert footer.get_value(1) == "Analysis by Auto-Titrator"


def test_build_kf_water_shape():
    section = builder.build_kf_water("Karl Fischer")
    header, data = section.rows[1], section.rows[2]
    assert header.get_value(2) == "Karl Fischer"
    assert data.get_value(2) == "Water"
    assert data.get_value(3) == "ppm"
    assert section.rows[-2].get_value(1) == "Analysis by KF-Titration"


def test_build_gc_fid_shape():
    section = builder.build_gc_fid("GC-FID")
    header = section.rows[1]
    assert header.get_value(2) == "GC-FID"
    assert header.get_value(4) == "Results"
    chem1, chem2 = section.rows[2], section.rows[3]
    assert chem1.get_value(2) == "Chemical 1"
    assert chem1.get_value(3) == "%/Vol"
    assert chem2.get_value(2) == "Chemical 2"
    assert chem2.get_value(3) == "%/Vol"
    assert section.rows[-2].get_value(1) == "Analysis by GC-FID (average of triplicates)"
