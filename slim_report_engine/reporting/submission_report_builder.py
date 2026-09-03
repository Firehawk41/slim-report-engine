"""Dispatches a whole TRSubmission's samples to the right Transform-stage
builder (generic Chemical/Water, DM5 non-routine, or Wafer grouping) and
returns one OutputSheet per output sheet, ready for report_writer to
write. This is the piece that turns "the three paths work individually"
(chemical_water_report_builder, dm5_non_routine_report_builder,
wafer_submission_builder) into "a whole submission produces a whole
workbook" — the CLI entry point (cli.py) calls this once per parsed
submission.

DM5 ROUTING: matches the real macro's own check (`Customer Like "DM5?"`)
— any resolved customer named "DM5N" or "DM5S" routes through
dm5_non_routine_report_builder instead of the generic orchestrator, one
sheet per sample. A DM5 customer with a chemical that builder doesn't
recognize raises a clear error rather than silently falling back to a
generic path that has no DM5-specific content to offer.

SHEET NAMING: a first-cut scheme (sample_name for Chemical/Water/DM5,
the Wafer group's sheet title for Wafer), sanitized for Excel's sheet-
name rules and deduplicated with a numeric suffix on collision. The real
VBA source's SetChemicalSheetName/SetWaterSheetName have additional
fidelity (illegal-character scrubbing matching a specific rule set,
28-char truncation, per-duplicate-matrix incrementing) not yet ported
here — a known, deliberate simplification, not assumed equivalent.
"""

from __future__ import annotations

from dataclasses import dataclass

from slim_domain.domain.analysis.analysis_service import AnalysisService
from slim_domain.domain.chemical.chemical_service import ChemicalService
from slim_domain.domain.customer.customer import Customer
from slim_domain.domain.element.element_service import ElementService
from slim_domain.domain.tr.enums import RequestType
from slim_domain.domain.tr.tr_submission import TRSubmission

from slim_report_engine.reporting import chemical_water_report_builder, dm5_non_routine_report_builder
from slim_report_engine.reporting import wafer_submission_builder
from slim_report_engine.reporting.report_section import ReportSection

_DM5_CUSTOMER_NAMES = {"DM5N", "DM5S"}


@dataclass(frozen=True)
class OutputSheet:
    name: str
    sections: tuple[ReportSection, ...]
    header_title: str
    # (cell_address, value) -- only DM5 shapes need a sample-ID stamped
    # into a specific cell after the section content is written; None
    # for every other shape.
    sample_id_stamp: tuple[str, str] | None = None


def build_submission_sheets(
    submission: TRSubmission,
    customer: Customer,
    chemical_service: ChemicalService,
    analysis_service: AnalysisService,
    element_service: ElementService,
) -> list[OutputSheet]:
    if submission.request_type == RequestType.WAFER:
        return _build_wafer_sheets(submission, customer, analysis_service, element_service)

    is_dm5 = customer.name in _DM5_CUSTOMER_NAMES
    used_names: set[str] = set()
    sheets: list[OutputSheet] = []

    for sample in submission.samples:
        if is_dm5:
            chemical = chemical_service.load_chemical(sample.chemical_id)
            chemical_name = chemical.name if chemical is not None else sample.form_chemical_name
            if not dm5_non_routine_report_builder.is_supported_chemical(chemical_name):
                raise ValueError(
                    f"sample {sample.sample_name!r}: DM5 chemical {chemical_name!r} is not one of the "
                    "21 chemicals dm5_non_routine_report_builder supports -- not silently falling back "
                    "to the generic path, which has no DM5-specific content to offer."
                )
            result = dm5_non_routine_report_builder.build_non_routine_report(
                chemical_name, customer.name, submission.date_received, sample.sample_name, element_service
            )
            name = _dedupe_name(_sanitize_sheet_name(chemical_name), used_names)
            sheets.append(
                OutputSheet(
                    name=name,
                    sections=result.sections,
                    header_title=result.chemical_label,
                    sample_id_stamp=(result.name_cell_address, result.sample_string),
                )
            )
            continue

        sections = chemical_water_report_builder.build_sections(sample, analysis_service, element_service)
        title = sample.form_chemical_name if submission.request_type == RequestType.CHEMICAL else "Water"
        name = _dedupe_name(_sanitize_sheet_name(sample.sample_name), used_names)
        sheets.append(OutputSheet(name=name, sections=tuple(sections), header_title=title))

    return sheets


def _build_wafer_sheets(
    submission: TRSubmission,
    customer: Customer,
    analysis_service: AnalysisService,
    element_service: ElementService,
) -> list[OutputSheet]:
    results = wafer_submission_builder.build_wafer_sheets(submission, customer, analysis_service, element_service)
    used_names: set[str] = set()
    sheets: list[OutputSheet] = []
    for result in results:
        name = _dedupe_name(_sanitize_sheet_name(result.sheet_title), used_names)
        sheets.append(OutputSheet(name=name, sections=(result.section,), header_title=result.sheet_title))
    return sheets


def _sanitize_sheet_name(name: str) -> str:
    for ch in "[]:*?/\\":
        name = name.replace(ch, "_")
    return (name.strip() or "Sheet")[:31]


def _dedupe_name(name: str, used: set[str]) -> str:
    base, n = name, 2
    while name in used:
        suffix = f" ({n})"
        name = base[: 31 - len(suffix)] + suffix
        n += 1
    used.add(name)
    return name
