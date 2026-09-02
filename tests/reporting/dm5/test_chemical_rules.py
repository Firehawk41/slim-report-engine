from slim_report_engine.reporting.dm5 import chemical_rules


def test_name_cell_address_plain_w2000():
    assert chemical_rules.name_cell_address("W2000") == "C5"


def test_name_cell_address_2to1_w2000_override_also_matches():
    assert chemical_rules.name_cell_address("2to1W2000") == "C5"


def test_name_cell_address_csl9044c_and_w7808():
    assert chemical_rules.name_cell_address("CSL9044C") == "C4"
    assert chemical_rules.name_cell_address("W7808") == "C4"


def test_name_cell_address_default():
    assert chemical_rules.name_cell_address("NH4OH") == "D5"


def test_translate_sheet_name_known_overrides():
    assert chemical_rules.translate_sheet_name("2.5%HF") == "2.5%HF-5%"
    assert chemical_rules.translate_sheet_name("W2000") == "W-2000"
    assert chemical_rules.translate_sheet_name("W7808") == "W-7808"


def test_translate_sheet_name_passthrough_for_everything_else():
    assert chemical_rules.translate_sheet_name("NH4OH") == "NH4OH"
