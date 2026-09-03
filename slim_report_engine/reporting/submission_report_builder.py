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

SAMPLE-ID STRING ECHO: row_builders.add_header_rows/add_simple_header_row
deliberately leave column 4 of each section's own "Sample Identification:"
row blank -- "filled in by the caller assembling the whole sheet, not
here... the sample-level identity string every section on a sheet
shares" (see row_builders.py). This module is that caller: for generic
Chemical/Water it computes the standard "mmddyy-Chemical-Customer-SampleID"
string (sample_string_builder.build_sample_string -- the SAME format DM5
non-routine and Wafer use, just with different inputs) and stamps it into
EVERY section's row 1 / column 4, matching the "every section shares it"
framing. Cell A1 also gets a title stamp on every path (matching the
legacy macro's `.Range("A1").Value = ...`) -- DM5's own first section
already carries this internally (its TitleRow is row 1 of the section,
landing on A1 naturally), so only generic Chemical/Water and Wafer need
an explicit extra stamp for it.
"""

from __future__ import annotations

from dataclasses import dataclass

from slim_domain.domain.analysis.analysis_service import AnalysisService
from slim_domain.domain.chemical.chemical_service import ChemicalService
from slim_domain.domain.customer.customer import Customer
from slim_domain.domain.element.element_service import ElementService
from slim_domain.domain.tr.enums import RequestType
from slim_domain.domain.tr.tr_submission import TRSubmission

from slim_report_engine.reporting import chemical_water_report_builder, column_widths, dm5_non_routine_report_builder
from slim_report_engine.reporting import wafer_submission_builder
from slim_report_engine.reporting.report_section import ReportSection
from slim_report_engine.reporting.sample_string_builder import build_sample_string

_DM5_CUSTOMER_NAMES = {"DM5N", "DM5S"}


@dataclass(frozen=True)
class OutputSheet:
    name: str
    sections: tuple[ReportSection, ...]
    header_title: str
    # Column index (1-based) -> width in points, matching whichever
    # report family produced this sheet's content -- see column_widths.py.
    column_widths: dict[int, float]
    # (cell_address, value) pairs to write AFTER the section content --
    # e.g. A1's title, DM5's sample-ID cell. Applied in order.
    extra_cell_stamps: tuple[tuple[str, str], ...] = ()


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
                    column_widths=result.column_widths,
                    extra_cell_stamps=((result.name_cell_address, result.sample_string),),
                )
            )
            continue

        sections = chemical_water_report_builder.build_sections(sample, analysis_service, element_service)
        chemical_name = sample.form_chemical_name if submission.request_type == RequestType.CHEMICAL else "Water"
        sample_string = build_sample_string(
            submission.date_received, chemical_name, customer.name, sample.sample_name
        )
        for section in sections:
            if section.rows:
                section.rows[0].set_value(4, sample_string)
        name = _dedupe_name(_sanitize_sheet_name(sample.sample_name), used_names)
        sheets.append(
            OutputSheet(
                name=name,
                sections=tuple(sections),
                header_title=chemical_name,
                column_widths=column_widths.STANDARD,
                extra_cell_stamps=(("A1", chemical_name),),
            )
        )

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
        sheets.append(
            OutputSheet(
                name=name,
                sections=(result.section,),
                header_title=result.sheet_title,
                column_widths=column_widths.WAFER,
                extra_cell_stamps=(("A1", result.sheet_title),),
            )
        )
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
