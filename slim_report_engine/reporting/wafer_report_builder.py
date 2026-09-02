"""Orchestrates ONE wafer report sheet — the group of intake-form rows
sharing one (Reporting Units, Wafer Size, Number of Elements, Processing
Time) combination, which the real template puts on a single sheet with
one sample column per physical wafer. Ported from clsWaferReportBuilder.cls.
Picks the right preset list + category (Element/Anion) from the intake
form's "Number of Elements" selection and builds the panel via
wafer_panel_builder.

REPLACES the legacy macro's copy-the-template-then-delete-unused-columns
mechanism, which depended on a counting function with a confirmed live bug
(comparing a variable to itself, always True) that silently over-counted
matching rows whenever two different element-count groups shared the same
Reporting Units/Wafer Size/Processing Time, leaving stray unused sample
columns in the real output. This builder never has that failure mode: it
writes exactly len(slot_sample_labels) sample columns because that's the
actual list it was given, with no separate count-then-delete step to get
wrong.

Per the Parse -> Transform -> Write pipeline (see project memory
feedback_pipeline_stages), this returns WHAT to write and WHERE as plain
data (WaferReportResult) — the actual worksheet write, including the
atoms/cm^2 superscript rich-text formatting (which needs real
Excel Range/Characters/Font access this content model has no way to
represent), stays out of scope for Python per this project's architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from slim_domain.domain.element.element_service import ElementService

from slim_report_engine.reporting.presets import analyte_presets, wafer_anion_presets
from slim_report_engine.reporting.report_section import ReportSection
from slim_report_engine.reporting.section_builders import wafer_panel_builder

_ATOMS_NOTE = "Results in units of 1010 atoms/cm2"
_IONS_NOTE = "Results in units of 1010 ions/cm2"


@dataclass(frozen=True)
class WaferReportResult:
    section: ReportSection
    sheet_title: str  # goes in A1, e.g. "150mm Wafers"
    # Real template quirk, preserved exactly: the "10^10" exponent in the
    # units note is written as literal "1010 " in plain text, which is
    # only made to look right when the intake form's own Reporting Units
    # field is literally "atoms/cm^2" -- the real macro gates this on that
    # field, not on which sheet/category was picked, so a genuinely
    # different Reporting Units selection leaves the "1010 " text
    # untouched exactly as before. When True, a future writer should drop
    # the "1010 " run from the notes row and superscript the trailing "2"
    # of "cm2" instead -- a real asymmetry in the source, not something to
    # "fix" here. This class only signals the decision; it can't perform
    # the actual rich-text formatting (no Excel access at this layer).
    apply_atoms_superscript_quirk: bool


def build_wafer_sheet(
    wafer_size: str,
    reporting_units: str,
    number_of_elements_label: str,
    customer: str,
    date_received: date,
    slot_sample_labels: list[str],
    additional_elements_text: str,
    element_service: ElementService,
) -> WaferReportResult:
    """number_of_elements_label: the ALREADY-NORMALIZED selection ("10/26
    Elements" folded into "36 Elements" -- same normalization the legacy
    grouping used, done by the caller since it's a grouping concern, not a
    content one). slot_sample_labels: one raw Sample-ID-column text per
    physical wafer sharing this sheet, in TR-row order -- becomes the
    "...-<label>" suffix of each sample column's header (column D's
    "Process Blank" suffix is fixed, not one of these). additional_elements_text:
    the raw comma-separated "Additional Elements" free-text column value,
    or "" -- only meaningful for an Element-category sheet (silently
    ignored for Anion, matching the real behavior: it only ever applies
    before the "Analysis by LP-ICPMS." footer, which doesn't exist on an
    anion sheet).
    """
    process_blank_id = _wafer_sample_string(date_received, wafer_size, customer, "Process Blank")
    slot_ids = [_wafer_sample_string(date_received, wafer_size, customer, label) for label in slot_sample_labels]
    additional_names = _additional_element_names(additional_elements_text)

    if number_of_elements_label == "36 Elements":
        section = wafer_panel_builder.build_element_panel(
            number_of_elements_label, _ATOMS_NOTE, process_blank_id, slot_ids,
            analyte_presets.trace_elements_36(), element_service, additional_names,
        )
    elif number_of_elements_label == "67 Elements":
        section = wafer_panel_builder.build_element_panel(
            number_of_elements_label, _ATOMS_NOTE, process_blank_id, slot_ids,
            analyte_presets.trace_elements_67(), element_service, additional_names,
        )
    elif number_of_elements_label == "List #2 36 Elements":
        section = wafer_panel_builder.build_element_panel(
            number_of_elements_label, _ATOMS_NOTE, process_blank_id, slot_ids,
            analyte_presets.trace_elements_36_list2(), element_service, additional_names,
        )
    elif number_of_elements_label == "4 Anions":
        section = wafer_panel_builder.build_anion_panel(
            number_of_elements_label, _IONS_NOTE, process_blank_id, slot_ids, wafer_anion_presets.wafer_anions_4()
        )
    elif number_of_elements_label == "5 Anions":
        section = wafer_panel_builder.build_anion_panel(
            number_of_elements_label, _IONS_NOTE, process_blank_id, slot_ids, wafer_anion_presets.wafer_anions_5()
        )
    elif number_of_elements_label == "7 Anions":
        section = wafer_panel_builder.build_anion_panel(
            number_of_elements_label, _IONS_NOTE, process_blank_id, slot_ids, wafer_anion_presets.wafer_anions_7()
        )
    else:
        raise ValueError(f"unknown wafer 'Number of Elements' selection: {number_of_elements_label!r}")

    return WaferReportResult(
        section=section,
        sheet_title=f"{wafer_size} Wafers",
        apply_atoms_superscript_quirk=(reporting_units == "atoms/cm^2"),
    )


def _wafer_sample_string(date_received: date, wafer_size: str, customer: str, suffix: str) -> str:
    return f"{date_received.strftime('%m%d%y')}-{wafer_size} Wafers-{customer}-{suffix}"


def _additional_element_names(raw_text: str) -> list[str]:
    if not raw_text.strip():
        return []
    return [part.strip() for part in raw_text.split(",")]
