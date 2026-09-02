from datetime import date

from slim_report_engine.reporting.sample_string_builder import build_sample_string


def test_standard_format():
    result = build_sample_string(date(2026, 3, 5), "NH4OH", "Acme Corp", "S-001")
    assert result == "030526-NH4OH-Acme Corp-S-001"


def test_ups_customer_override():
    result = build_sample_string(date(2026, 3, 5), "Test Acid", "UPS", "S-001")
    assert "FUJIFILM UPS" in result
    assert result == "030526-Test Acid-FUJIFILM UPS-S-001"


def test_dm5n_w2000_chemical_override():
    result = build_sample_string(date(2026, 3, 5), "W2000", "DM5N", "S-001")
    assert result == "030526-2to1W2000-DM5N-S-001"


def test_w2000_override_is_dm5n_specific_not_dm5s():
    """DM5-S's W2000 does NOT get the 2to1 prefix -- only DM5-N's does."""
    result = build_sample_string(date(2026, 3, 5), "W2000", "DM5S", "S-001")
    assert result == "030526-W2000-DM5S-S-001"


def test_ups_override_does_not_affect_other_customers():
    result = build_sample_string(date(2026, 3, 5), "Test Acid", "Acme Corp", "S-001")
    assert "FUJIFILM" not in result
