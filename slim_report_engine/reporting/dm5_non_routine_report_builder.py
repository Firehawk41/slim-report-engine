"""Orchestrates a NON-ROUTINE DM5 sample's report content — ported from
clsDM5NonRoutineReportBuilder.cls. This is the path where a DM5 sample
arrives via a normal testing request, same as every other Chemical/Water
sample (the routine schedule-grid path is explicitly out of scope, see
DOMAIN_BRIEF.md). For a given (chemical_name, location), this dispatches
to the right content builder(s) across all 3 DM5 shapes (element panel,
standalone Assay, composite element+anions+Assay) and computes the
standard sample-ID string and the cell address it belongs in.

SCOPE: all 21 DM5 chemicals across both locations dispatch correctly
(element panel: 13, standalone Assay: 5, composite: 3).

COMPOSITE'S ANION/ASSAY BLOCKS ARE CONDITIONAL, NOT FIXED — confirmed
real: unlike the routine schedule-grid path (out of scope, always renders
a fixed set of blocks), a non-routine sample only gets the composite
chemical's anion block and/or embedded Assay when those were actually
requested on THAT sample's TR form (same Anions/Titrations selections the
generic Chemical/Water path already reads) — see
requested_analysis_names below and _ANION_ANALYSIS_NAMES.

Per the Parse -> Transform -> Write pipeline (see project memory
feedback_pipeline_stages), this function is Transform-stage only: it
returns WHAT to write and WHERE (sections, sample string, target cell
address) as plain data. The actual worksheet write stays out of scope for
Python per this project's architecture (README.md) -- a future VBA/Excel
writer applies the result to a real sheet.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from slim_domain.domain.element.element_service import ElementService

from slim_report_engine.reporting import column_widths
from slim_report_engine.reporting.dm5 import chemical_rules, element_specs
from slim_report_engine.reporting.report_section import ReportSection
from slim_report_engine.reporting.sample_string_builder import build_sample_string
from slim_report_engine.reporting.section_builders import (
    dm5_assay_section_builder,
    dm5_element_panel_builder,
)

_ELEMENT_CHEMICALS = {"NH4OH", "H2O2", "IPA", "BHF", "49%HF", "HCl", "SurfEtch"}
_ASSAY_CHEMICALS = {"CSL9044C", "W2000", "W7808"}
_COMPOSITE_CHEMICALS = {"0.49%HF", "2.5%HF"}

# Confirmed real (2026-09-03): a Composite chemical's anion block and
# embedded Assay are NOT unconditional -- they only appear on the real
# report when the sample's TR form actually requested them, same as
# every other Chemical/Water sample's analysis selections. The routine
# DM5 schedule-grid path (out of scope) DOES always get a fixed set --
# non-routine, which this module builds, does not.
_ANION_ANALYSIS_NAMES = {"4 Anions", "5 Anions", "7 Anions", "Anions", "5 Anions + MS Authentication"}

_ELEMENT_SPECS_BY_LOCATION: dict[str, dict[str, Callable[[], dict[str, float]]]] = {
    "DM5N": {
        "NH4OH": element_specs.nh4oh_specs,
        "H2O2": element_specs.h2o2_specs,
        "IPA": element_specs.ipa_specs,
        "BHF": element_specs.bhf_specs,
        "49%HF": element_specs.hf49_specs,
        "HCl": element_specs.hcl_specs,
    },
    "DM5S": {
        "NH4OH": element_specs.nh4oh_specs_s,
        "H2O2": element_specs.h2o2_specs_s,
        "IPA": element_specs.ipa_specs_s,
        "BHF": element_specs.bhf_specs_s,
        "49%HF": element_specs.hf49_specs_s,
        "HCl": element_specs.hcl_specs_s,
        "SurfEtch": element_specs.surf_etch_specs,
    },
}

_QC_CODES = {
    ("DM5N", "NH4OH"): "DM5N-QS-OPPOD-NH4OH",
    ("DM5N", "H2O2"): "DM5N-QS-OPPOD-H2O2",
    ("DM5N", "IPA"): "DM5N-QS-OPPOD-IPA",
    ("DM5N", "BHF"): "DM5N-QS-OPPOD-BHF",
    ("DM5N", "49%HF"): "DM5N-QS-OPPOD-49HF",
    ("DM5N", "HCl"): "DM5N-QS-OPPOD-HCL",
    ("DM5S", "NH4OH"): "DM5S-QS-OPPOD-NH4OH",
    ("DM5S", "H2O2"): "DM5S-QS-OPPOD-H2O2",
    ("DM5S", "IPA"): "DM5S-QS-OPPOD-IPA",
    ("DM5S", "BHF"): "DM5S-QS-OPPOD-BHF",
    ("DM5S", "49%HF"): "DM5S-QS-OPPOD-49HF",
    ("DM5S", "HCl"): "DM5S-QS-OPPOD-HCL",
    ("DM5S", "SurfEtch"): "DM5S-QS-OPPOD-SURFETCH",
}


@dataclass(frozen=True)
class DM5NonRoutineResult:
    sections: tuple[ReportSection, ...]
    chemical_label: str
    name_cell_address: str
    sample_string: str
    column_widths: dict[int, float]


def is_supported_chemical(chemical_name: str) -> bool:
    """Lets a caller check before committing to this path -- e.g. falling
    back to legacy handling for a DM5 chemical this doesn't know about
    yet, rather than raising.
    """
    return _get_category(chemical_name) != ""


def build_non_routine_report(
    chemical_name: str,
    location: str,
    date_received: date,
    sample_id: str,
    element_service: ElementService,
    requested_analysis_names: frozenset[str] = frozenset(),
) -> DM5NonRoutineResult:
    """chemical_name: the raw selection value (e.g. "NH4OH", "W2000",
    "2.5%HF" -- one of the 21 known DM5 chemical names, raises if not).
    location: "DM5N" or "DM5S". sample_id: the TR-form's own sample
    identifier for this row (the same value every other Chemical/Water
    sample's sample string embeds).

    requested_analysis_names: the sample's OTHER resolved analysis
    selections (Anions/Titrations column), same names the generic
    Chemical/Water path resolves -- only consulted for the Composite
    category, to decide whether this sample's anion block / embedded
    Assay are actually present (see _ANION_ANALYSIS_NAMES above). Element
    and Assay category chemicals ignore this entirely; their shape never
    varies by what else was requested.
    """
    category = _get_category(chemical_name)
    chemical_label = _get_chemical_label(chemical_name, location)

    if category == "Element":
        specs = _get_element_specs(chemical_name, location)
        if specs is None:
            raise ValueError(f"not a known element-panel chemical for {location}: {chemical_name!r}")
        sections = [
            dm5_element_panel_builder.build_element_panel(
                chemical_name, chemical_label, _get_qc_code(chemical_name, location), specs, element_service
            )
        ]
        widths = column_widths.DM5_ELEMENT
    elif category == "Assay":
        spec_range, parameter_label, result_col_label, note_text = _get_assay_params(chemical_name, location)
        sections = [
            dm5_assay_section_builder.build_assay(
                chemical_name, chemical_label, spec_range, parameter_label, result_col_label, note_text
            )
        ]
        widths = column_widths.DM5_ASSAY
    elif category == "Composite":
        qc_code, spec_range, note_text, units_note_text, units_note_column = _get_composite_params(
            chemical_name, location
        )
        include_anions = bool(requested_analysis_names & _ANION_ANALYSIS_NAMES)
        include_assay = "Assay" in requested_analysis_names

        if include_anions:
            sections = [
                dm5_element_panel_builder.build_element_panel_with_anions(
                    chemical_name,
                    chemical_label,
                    qc_code,
                    element_specs.hf_composite_element_specs(),
                    element_specs.hf_composite_anion_specs(),
                    element_service,
                    units_note_text,
                    units_note_column,
                )
            ]
        else:
            sections = [
                dm5_element_panel_builder.build_element_panel(
                    chemical_name,
                    chemical_label,
                    qc_code,
                    element_specs.hf_composite_element_specs(),
                    element_service,
                    units_note_text,
                    units_note_column,
                )
            ]
        if include_assay:
            sections.append(
                dm5_assay_section_builder.build_embedded_assay(f"{chemical_name}_Assay", spec_range, note_text)
            )
        widths = column_widths.DM5_ELEMENT
    else:
        raise ValueError(f"unknown DM5 chemical for {location}: {chemical_name!r}")

    sample_string = build_sample_string(date_received, chemical_name, location, sample_id)
    # name_cell_address decides from the real LABEL, not the raw dispatch
    # key -- confirmed to resolve correctly for all 3 shapes (D5 for
    # element/composite, C4/C5 for the Assay shape's special cases) since
    # each shape's QC/Sample-# row was independently built to match the
    # real template's row position.
    cell_address = chemical_rules.name_cell_address(chemical_label)

    return DM5NonRoutineResult(
        sections=tuple(sections),
        chemical_label=chemical_label,
        name_cell_address=cell_address,
        sample_string=sample_string,
        column_widths=widths,
    )


# ---------------------------------------------------------------------------
# Private dispatch tables / helpers
# ---------------------------------------------------------------------------

def _get_category(chemical_name: str) -> str:
    if chemical_name in _ELEMENT_CHEMICALS:
        return "Element"
    if chemical_name in _ASSAY_CHEMICALS:
        return "Assay"
    if chemical_name in _COMPOSITE_CHEMICALS:
        return "Composite"
    return ""


def _get_element_specs(chemical_name: str, location: str) -> dict[str, float] | None:
    getter = _ELEMENT_SPECS_BY_LOCATION.get(location, {}).get(chemical_name)
    return getter() if getter else None


def _get_chemical_label(chemical_name: str, location: str) -> str:
    """chemical_label is what the section's title row and sheet-tab name
    actually show -- distinct from chemical_name (the dispatch key/raw
    selection value) wherever the real template's own A1 differs:
      - DM5-S's "SurfEtch" displays as "Surfetch" (lowercase t)
      - "W2000" displays as "2to1W2000" on DM5-N, plain "W2000" on DM5-S
      - "2.5%HF" displays as "2.5%HF" (matches chemical_name here, but the
        SHEET TAB is "2.5%HF-5%" -- handled by
        dm5/chemical_rules.translate_sheet_name, not this function)
    Every other chemical's label matches chemical_name unchanged.
    """
    if location == "DM5S" and chemical_name == "SurfEtch":
        return "Surfetch"
    if chemical_name == "W2000" and location == "DM5N":
        return "2to1W2000"
    return chemical_name


def _get_qc_code(chemical_name: str, location: str) -> str:
    key = (location, chemical_name)
    if key not in _QC_CODES:
        raise ValueError(f"no QC code mapping for {location}/{chemical_name}")
    return _QC_CODES[key]


def _get_assay_params(chemical_name: str, location: str) -> tuple[str, str, str, str]:
    """Returns (spec_range, parameter_label, result_col_label, note_text).
    CSL9044C (DM5-N only) and W7808 (both) share one exact shape (no note,
    "% H2O2" result column). W2000 differs: "Results" result column, the
    "Bold Red Font..." note, and its spec range differs by location
    (W7808's is identical on both sides).
    """
    if chemical_name == "CSL9044C":
        return "1.1 - 1.3", "Assay", "% H2O2", ""
    if chemical_name == "W7808":
        return "2.2715 - 2.5285", "Assay", "% H2O2", ""
    if chemical_name == "W2000":
        spec_range = "1.916 - 2.173   H2O2 % " if location == "DM5N" else "2.2715 - 2.5285   H2O2 % "
        return spec_range, "% H2O2", "Results", "Bold Red Font: Indicates data outside specification limits"
    raise ValueError(f"not a known Assay-shape chemical: {chemical_name!r}")


def _get_composite_params(chemical_name: str, location: str) -> tuple[str, str, str, str, int]:
    """Returns (qc_code, spec_range, note_text, units_note_text,
    units_note_column). Element/anion specs are shared across all 3 known
    composite sheets -- only QC code, Assay spec range, the Assay note
    (DM5-N's "0.49%HF" only), and the units-note text/column (both
    "0.49%HF" sheets use a longer caveat in column 3; "2.5%HF" uses the
    standard column-4 text) vary.
    """
    if chemical_name == "0.49%HF":
        units_note_text = "All data in ppb except where indicated below."
        units_note_column = 3
        if location == "DM5N":
            return (
                "DM5N-QS-OPPOD-PNT49HF",
                "0.495 % - 0.515 %",
                "TI not longer wants North assay.  This left for XML program use only.",
                units_note_text,
                units_note_column,
            )
        return "DM5S-QS-OPPOD-PNT49HF", "0.475 % - 0.505 %", "", units_note_text, units_note_column
    if chemical_name == "2.5%HF":
        return "DM5S-QS-OPPOD-2.5HF", "2.4 - 2.6 %", "", "All data in ppb", 4
    raise ValueError(f"not a known composite chemical: {chemical_name!r}")
