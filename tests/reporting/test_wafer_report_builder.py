from dataclasses import dataclass
from datetime import date

import pytest

from slim_domain.domain.tr.enums import ProcessingTime

from slim_report_engine.reporting import wafer_report_builder as orchestrator


@dataclass(frozen=True)
class _FakeElement:
    name: str
    symbol: str


class _FakeElementService:
    def get_by_symbol(self, symbol: str):
        return _FakeElement(name=symbol, symbol=symbol)

    def get_by_name(self, name: str):
        return _FakeElement(name=name, symbol=name[:2])


def test_sheet_title():
    result = orchestrator.build_wafer_sheet(
        "150mm", "atoms/cm^2", "36 Elements", "Acme Corp", date(2026, 3, 5), ["W-1"], [], _FakeElementService(), ProcessingTime.NEXT_DAY
    )
    assert result.sheet_title == "150mm Wafers"


def test_apply_superscript_quirk_only_for_atoms_reporting_units():
    result_atoms = orchestrator.build_wafer_sheet(
        "150mm", "atoms/cm^2", "36 Elements", "Acme Corp", date(2026, 3, 5), ["W-1"], [], _FakeElementService(), ProcessingTime.NEXT_DAY
    )
    result_other = orchestrator.build_wafer_sheet(
        "150mm", "ions/cm^2", "4 Anions", "Acme Corp", date(2026, 3, 5), ["W-1"], [], _FakeElementService(), ProcessingTime.NEXT_DAY
    )
    assert result_atoms.apply_atoms_superscript_quirk is True
    assert result_other.apply_atoms_superscript_quirk is False


def test_process_blank_and_slot_sample_id_format():
    result = orchestrator.build_wafer_sheet(
        "150mm", "atoms/cm^2", "36 Elements", "Acme Corp", date(2026, 3, 5), ["Slot-1", "Slot-2"], [], _FakeElementService(), ProcessingTime.NEXT_DAY
    )
    sample_id_row = result.section.rows[5]
    assert sample_id_row.get_value(4) == "030526-150mm Wafers-Acme Corp-Process Blank"
    assert sample_id_row.get_value(5) == "030526-150mm Wafers-Acme Corp-Slot-1"
    assert sample_id_row.get_value(6) == "030526-150mm Wafers-Acme Corp-Slot-2"


def test_element_selections_use_atoms_note():
    for label in ("36 Elements", "67 Elements", "List #2 36 Elements"):
        result = orchestrator.build_wafer_sheet(
            "150mm", "atoms/cm^2", label, "Acme Corp", date(2026, 3, 5), ["W-1"], [], _FakeElementService(), ProcessingTime.NEXT_DAY
        )
        units_row = result.section.rows[4]
        assert units_row.get_value(1) == "Results in units of 1010 atoms/cm2"


def test_anion_selections_use_ions_note():
    for label in ("4 Anions", "5 Anions", "7 Anions"):
        result = orchestrator.build_wafer_sheet(
            "150mm", "ions/cm^2", label, "Acme Corp", date(2026, 3, 5), ["W-1"], [], _FakeElementService(), ProcessingTime.NEXT_DAY
        )
        units_row = result.section.rows[4]
        assert units_row.get_value(1) == "Results in units of 1010 ions/cm2"


def test_67_elements_has_67_data_rows():
    result = orchestrator.build_wafer_sheet(
        "150mm", "atoms/cm^2", "67 Elements", "Acme Corp", date(2026, 3, 5), ["W-1"], [], _FakeElementService(), ProcessingTime.NEXT_DAY
    )
    data_rows = [r for r in result.section.rows if r.style_name == "DataLabel"]
    assert len(data_rows) == 67


def test_additional_element_names_appended_for_element_sheets():
    result = orchestrator.build_wafer_sheet(
        "150mm", "atoms/cm^2", "36 Elements", "Acme Corp", date(2026, 3, 5), ["W-1"], ["Gold", "Silver"],
        _FakeElementService(), ProcessingTime.NEXT_DAY,
    )
    data_rows = [r for r in result.section.rows if r.style_name == "DataLabel"]
    assert data_rows[-2].get_value(2) == "Gold"
    assert data_rows[-1].get_value(2) == "Silver"


def test_result_carries_processing_time():
    result = orchestrator.build_wafer_sheet(
        "150mm", "atoms/cm^2", "36 Elements", "Acme Corp", date(2026, 3, 5), ["W-1"], [],
        _FakeElementService(), ProcessingTime.SAME_DAY_RUSH,
    )
    assert result.processing_time == ProcessingTime.SAME_DAY_RUSH


def test_unknown_selection_raises():
    with pytest.raises(ValueError):
        orchestrator.build_wafer_sheet(
            "150mm", "atoms/cm^2", "Not A Real Selection", "Acme Corp", date(2026, 3, 5), ["W-1"], [],
            _FakeElementService(), ProcessingTime.NEXT_DAY,
        )
