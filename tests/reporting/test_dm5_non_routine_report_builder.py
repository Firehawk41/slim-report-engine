from dataclasses import dataclass
from datetime import date

import pytest

from slim_report_engine.reporting import column_widths, dm5_non_routine_report_builder as orchestrator


@dataclass(frozen=True)
class _FakeElement:
    name: str
    symbol: str


class _FakeElementService:
    def get_by_symbol(self, symbol: str):
        return _FakeElement(name=symbol, symbol=symbol)


# ---------------------------------------------------------------------------
# is_supported_chemical
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "chemical_name",
    ["NH4OH", "H2O2", "IPA", "BHF", "49%HF", "HCl", "SurfEtch",  # Element (7)
     "CSL9044C", "W2000", "W7808",  # Assay (3)
     "0.49%HF", "2.5%HF"],  # Composite (2)
)
def test_all_known_chemicals_are_supported(chemical_name):
    assert orchestrator.is_supported_chemical(chemical_name) is True


def test_unknown_chemical_not_supported():
    assert orchestrator.is_supported_chemical("Not A Real Chemical") is False


# ---------------------------------------------------------------------------
# Element-panel category
# ---------------------------------------------------------------------------

def test_nh4oh_dm5n_builds_one_element_panel_section():
    result = orchestrator.build_non_routine_report(
        "NH4OH", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService()
    )
    assert len(result.sections) == 1
    assert result.chemical_label == "NH4OH"
    assert result.name_cell_address == "D5"
    assert "NH4OH" in result.sample_string


def test_surfetch_is_dm5s_only_and_displays_lowercase():
    result = orchestrator.build_non_routine_report(
        "SurfEtch", "DM5S", date(2026, 3, 5), "S-001", _FakeElementService()
    )
    assert result.chemical_label == "Surfetch"
    with pytest.raises(ValueError):
        orchestrator.build_non_routine_report(
            "SurfEtch", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService()
        )


# ---------------------------------------------------------------------------
# Assay category
# ---------------------------------------------------------------------------

def test_csl9044c_only_on_dm5n():
    result = orchestrator.build_non_routine_report(
        "CSL9044C", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService()
    )
    assert result.name_cell_address == "C4"


def test_w7808_works_on_both_locations():
    for location in ("DM5N", "DM5S"):
        result = orchestrator.build_non_routine_report(
            "W7808", location, date(2026, 3, 5), "S-001", _FakeElementService()
        )
        assert result.name_cell_address == "C4"


def test_w2000_chemical_label_override_dm5n_only():
    n = orchestrator.build_non_routine_report("W2000", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService())
    s = orchestrator.build_non_routine_report("W2000", "DM5S", date(2026, 3, 5), "S-001", _FakeElementService())
    assert n.chemical_label == "2to1W2000"
    assert s.chemical_label == "W2000"
    # both use the C5 cell (matches "*W2000" via the label, not the raw name)
    assert n.name_cell_address == "C5"
    assert s.name_cell_address == "C5"


def test_w2000_spec_range_differs_by_location():
    n = orchestrator.build_non_routine_report("W2000", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService())
    s = orchestrator.build_non_routine_report("W2000", "DM5S", date(2026, 3, 5), "S-001", _FakeElementService())
    n_data = n.sections[0].rows[-1]
    s_data = s.sections[0].rows[-1]
    assert n_data.get_value(1) == "1.916 - 2.173   H2O2 % "
    assert s_data.get_value(1) == "2.2715 - 2.5285   H2O2 % "


# ---------------------------------------------------------------------------
# Composite category
# ---------------------------------------------------------------------------

def test_composite_produces_two_sections_element_panel_plus_embedded_assay():
    result = orchestrator.build_non_routine_report(
        "0.49%HF", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService()
    )
    assert len(result.sections) == 2
    assert result.sections[1].id == "0.49%HF_Assay"


def test_composite_049hf_dm5n_only_carries_the_deprecation_note():
    n = orchestrator.build_non_routine_report("0.49%HF", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService())
    s = orchestrator.build_non_routine_report("0.49%HF", "DM5S", date(2026, 3, 5), "S-001", _FakeElementService())
    n_assay_data = n.sections[1].rows[-1]
    s_assay_data = s.sections[1].rows[-1]
    assert n_assay_data.get_value(5) is not None
    assert s_assay_data.get_value(5) is None


def test_25hf_is_dm5s_only():
    result = orchestrator.build_non_routine_report(
        "2.5%HF", "DM5S", date(2026, 3, 5), "S-001", _FakeElementService()
    )
    assert result.sections[1].rows[-1].get_value(1) == "2.4 - 2.6 %"


def test_composite_element_and_anion_specs_are_shared_across_all_three_sheets():
    results = [
        orchestrator.build_non_routine_report("0.49%HF", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService()),
        orchestrator.build_non_routine_report("0.49%HF", "DM5S", date(2026, 3, 5), "S-001", _FakeElementService()),
        orchestrator.build_non_routine_report("2.5%HF", "DM5S", date(2026, 3, 5), "S-001", _FakeElementService()),
    ]
    al_values = []
    for r in results:
        panel = r.sections[0]
        al_row = next(row for row in panel.rows if row.get_value(3) == "Al")
        al_values.append(al_row.get_value(1))
    assert al_values == [0.08, 0.08, 0.08]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

def test_unknown_chemical_raises():
    with pytest.raises(ValueError):
        orchestrator.build_non_routine_report(
            "Not A Real Chemical", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService()
        )


# ---------------------------------------------------------------------------
# column_widths
# ---------------------------------------------------------------------------

def test_element_category_uses_dm5_element_widths():
    result = orchestrator.build_non_routine_report(
        "NH4OH", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService()
    )
    assert result.column_widths == column_widths.DM5_ELEMENT


def test_assay_category_uses_dm5_assay_widths():
    result = orchestrator.build_non_routine_report(
        "CSL9044C", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService()
    )
    assert result.column_widths == column_widths.DM5_ASSAY


def test_composite_category_uses_dm5_element_widths():
    result = orchestrator.build_non_routine_report(
        "0.49%HF", "DM5N", date(2026, 3, 5), "S-001", _FakeElementService()
    )
    assert result.column_widths == column_widths.DM5_ELEMENT
