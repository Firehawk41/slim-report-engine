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

SHEET NAMING: for generic Chemical/Water, ported from the real macro's
SetChemicalSheetName/SetWaterSheetName (modReportCreator.bas) — the
CHEMICAL MATRIX text (or literal "Water"), not the Sample ID, which is
what the real system actually shows and what the earlier Sample-ID-based
scheme got wrong (real Sample IDs are often unreadable delivery-lot/PO
strings). See _generic_tab_names. DM5 uses chemical_label, Wafer uses the
group's own sheet title -- both sanitized/deduplicated with the older,
simpler `_sanitize_sheet_name`/`_dedupe_name` fallback, since neither has
the same real-per-matrix-duplicate-numbering behavior confirmed for the
generic path.

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
from slim_domain.domain.tr.tr_sample import TRSample
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
    # Precomputed up front, not per-sample -- confirmed real (see
    # _generic_tab_names): whether a sample's tab gets a numeric suffix
    # depends on how many OTHER samples in the whole submission share its
    # chemical matrix, which isn't knowable one sample at a time.
    generic_tab_names = None if is_dm5 else _generic_tab_names(submission)

    for i, sample in enumerate(submission.samples):
        if is_dm5:
            chemical = chemical_service.load_chemical(sample.chemical_id)
            chemical_name = chemical.name if chemical is not None else sample.form_chemical_name
            if not dm5_non_routine_report_builder.is_supported_chemical(chemical_name):
                raise ValueError(
                    f"sample {sample.sample_name!r}: DM5 chemical {chemical_name!r} is not one of the "
                    "21 chemicals dm5_non_routine_report_builder supports -- not silently falling back "
                    "to the generic path, which has no DM5-specific content to offer."
                )
            requested_analysis_names = _resolved_analysis_names(sample, analysis_service)
            result = dm5_non_routine_report_builder.build_non_routine_report(
                chemical_name, customer.name, submission.date_received, sample.sample_name, element_service,
                requested_analysis_names,
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

        metals_prep_text = _metals_prep_text(submission, sample, chemical_service)
        additional_elements_prep_text = customer.additional_elements_prep or None
        sections = chemical_water_report_builder.build_sections(
            sample, analysis_service, element_service, metals_prep_text, additional_elements_prep_text
        )
        chemical_name = sample.form_chemical_name if submission.request_type == RequestType.CHEMICAL else "Water"
        sample_string = build_sample_string(
            submission.date_received, chemical_name, customer.name, sample.sample_name
        )
        for section in sections:
            if section.rows:
                section.rows[0].set_value(4, sample_string)
        name = _dedupe_name(generic_tab_names[i], used_names)
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


def _resolved_analysis_names(sample: TRSample, analysis_service: AnalysisService) -> frozenset[str]:
    """Distinct resolved analysis names for a sample -- used by the DM5
    branch to tell dm5_non_routine_report_builder what else was requested
    (see its COMPOSITE'S ANION/ASSAY BLOCKS ARE CONDITIONAL note). Same
    resolution chemical_water_report_builder.py does for the generic
    path, duplicated here rather than imported since it's three lines and
    that module has no reason to know about DM5 at all.
    """
    names: set[str] = set()
    for analysis_id in sample.analysis_ids:
        analysis = analysis_service.load_analysis(analysis_id)
        if analysis is not None:
            names.add(analysis.name)
    return frozenset(names)


_DEFAULT_METALS_PREP = "Evaporation"
_WATER_METALS_PREP = "Dilute and Shoot"


def _metals_prep_text(submission: TRSubmission, sample: TRSample, chemical_service: ChemicalService) -> str:
    """Confirmed real (see chemical_water_report_builder.py's PREP TEXT
    docstring section): Chemical samples read the resolved Chemical's own
    catalog prep, defaulting to "Evaporation" (current lab practice) when
    that field is blank; Water samples have no Chemical record to read
    from at all and use "Dilute and Shoot" -- confirmed across every real
    Water sample checked, not just additional-elements-only ones.
    """
    if submission.request_type != RequestType.CHEMICAL:
        return _WATER_METALS_PREP
    chemical = chemical_service.load_chemical(sample.chemical_id)
    if chemical is not None and chemical.metals_prep:
        return chemical.metals_prep
    return _DEFAULT_METALS_PREP


_SHEET_NAME_ILLEGAL_CHARS = ":/\\?*[]<>|"


def _generic_tab_names(submission: TRSubmission) -> list[str]:
    """One tab name per sample in submission.samples order — ported from
    the real macro's SetChemicalSheetName/SetWaterSheetName
    (modReportCreator.bas), ground truth for the real naming scheme this
    replaces (the old scheme used the raw Sample ID, which produces
    unreadable tabs on real ID-like sample IDs -- e.g. a real delivery-lot
    string instead of the real system's actual "PMAC").
    """
    if submission.request_type == RequestType.WATER:
        return _water_tab_names(len(submission.samples))
    return _chemical_matrix_tab_names([s.form_chemical_name for s in submission.samples])


def _water_tab_names(count: int) -> list[str]:
    """Confirmed real (SetWaterSheetName): "Water" alone when there's
    exactly one Water sample in the whole submission; "Water 1".."Water N"
    (by row/form order) when there's more than one -- Water samples have
    no chemical-matrix content to group by, so every sample counts as its
    own occurrence once there's more than one at all.
    """
    if count <= 1:
        return ["Water"] * count
    return [f"Water {i}" for i in range(1, count + 1)]


def _chemical_matrix_tab_names(chemical_matrices: list[str]) -> list[str]:
    """Confirmed real (SetChemicalSheetName): scrub illegal sheet-name
    characters (removed entirely, not replaced -- confirmed real:
    RemoveIllegalCharacters' Case Else branch), truncate to 28 characters
    (not 31 -- reserves room for a " N" suffix so a real 2-digit
    duplicate count still fits Excel's 31-character sheet-name limit),
    then group samples by that truncated value. A chemical matrix that's
    unique in the submission keeps its plain (truncated) name; one that
    repeats gets " N" appended to EVERY occurrence, N counted in the
    samples' own row/form order (1-based) -- not just the 2nd-onward,
    confirmed real (e.g. real duplicate tabs are "X 1"/"X 2", never a bare
    "X" alongside "X 2").
    """
    truncated = [_scrub_chemical_matrix_for_sheet_name(m)[:28] for m in chemical_matrices]
    counts: dict[str, int] = {}
    for t in truncated:
        counts[t] = counts.get(t, 0) + 1

    running: dict[str, int] = {}
    names = []
    for t in truncated:
        if counts[t] > 1:
            running[t] = running.get(t, 0) + 1
            names.append(f"{t} {running[t]}")
        else:
            names.append(t)
    return names


def _scrub_chemical_matrix_for_sheet_name(text: str) -> str:
    for ch in _SHEET_NAME_ILLEGAL_CHARS:
        text = text.replace(ch, "")
    return text


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
