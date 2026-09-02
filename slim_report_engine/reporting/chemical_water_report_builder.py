"""Orchestrates ONE Chemical/Water sample's report content — dispatches
each of the sample's resolved analysis IDs (TRSample.analysis_ids, from
slim-domain's TR parsing stack) to the right section-builder function, in
the ORDER the analyses were requested, and returns the assembled sections.
Ported from clsChemicalWaterReportBuilder.cls.

Covers the analyses that map unambiguously onto an existing section
builder. Deliberately NOT supported yet (raises a clear, actionable error
rather than guessing):
  - Any "+ MS Confirmation"/"+ Organic Anions" anion variant — a separate
    "Anions MS-Authentication rendering" (extra analyte, elution-order
    sort) not built yet.
  - Organic-matrix / ICP-OES / microwave-digestion / "with reported
    replicates" element-panel variants, Assay/Moisture/GC-FID/GC-MS/
    Titrations, Mixed Acid Assay, UV-Vis, Acetate and Formate, Sn+2 Iodine
    Titration, Free Acid, TS-SLG, and all customer-specific edge cases —
    deliberately last priority, not attempted here.

PH DISPATCH — a deliberate improvement over the VBA source: standalone
"pH" (Conductivity NOT also requested) maps to
misc_analysis_section_builder.build_ph; "pH" + "Conductivity" together map
to electrical_section_builder.build_conductivity_and_ph. The VBA source
raises on standalone "pH" rather than resolving it, reasoning the resolved
analysis ID alone couldn't disambiguate two real, distinct template blocks.
Verified empirically against the real Chemical/Water intake forms' own
dropdown option lists that this ambiguity doesn't actually exist in
practice: Chemical's form never offers "Conductivity" as an option at all,
and Water's dropdown has a distinct "Conductivity + pH" value separate
from standalone "pH" — so `has_conductivity` alone is sufficient, no need
to carry original form text through the parsing stack.

SILICON GAP FIX — also a deliberate improvement: the VBA source's
BuildSections checks for an analysis literally named "Dissolved and Total
Si" (in its Total/DissolvedSi flags) but its CanBuildSections' allow-list
never includes that name — a real inconsistency between the two methods in
the same class. Included here in the supported set so the two functions
agree, rather than reproduced verbatim.
"""

from __future__ import annotations

from slim_domain.domain.analysis.analysis_service import AnalysisService
from slim_domain.domain.element.element_service import ElementService
from slim_domain.domain.tr.tr_sample import TRSample

from slim_report_engine.reporting.presets import analyte_presets, ion_presets
from slim_report_engine.reporting.report_section import ReportSection
from slim_report_engine.reporting.section_builders import (
    analyte_list_section_builder,
    electrical_section_builder,
    ion_list_section_builder,
    misc_analysis_section_builder,
    silicon_section_builder,
    simple_test_section_builder,
)

_UNCONDITIONALLY_SUPPORTED = {
    "36 Elements", "26 Elements", "10 Elements", "67 Elements", "USP Elements", "List #2 36 Elements",
    "4 Anions", "5 Anions", "7 Anions", "Anions",
    "6 Cations", "NH4", "Methylamines", "Cations", "GBP",
    "Total Silicon", "Dissolved Silicon", "Dissolved and Total Si",
    "TOC", "Alkalinity", "Bacteria Count",
    "Conductivity", "Density", "Liquid Particle Count", "APHA Color",
    "pH",
}


def can_build_sections(sample: TRSample, analysis_service: AnalysisService) -> bool:
    """Lets a caller check before committing to this path — e.g. falling
    back to legacy handling for a sample whose analyses this doesn't (yet)
    fully cover, rather than raising mid-build.
    """
    names = _resolved_names_in_order(sample, analysis_service)
    if not names:
        return False
    return all(name in _UNCONDITIONALLY_SUPPORTED for name in names)


def build_sections(
    sample: TRSample,
    analysis_service: AnalysisService,
    element_service: ElementService,
) -> list[ReportSection]:
    """Returns one (or more, for Silicon's calculated Colloidal Silica row)
    ReportSection per resolved analysis on the sample, in request order —
    except Conductivity+pH, which collapse into ONE combined section.
    """
    names = _resolved_names_in_order(sample, analysis_service)
    names_set = set(names)

    has_conductivity = "Conductivity" in names_set
    include_total_si = "Total Silicon" in names_set or "Dissolved and Total Si" in names_set
    include_dissolved_si = "Dissolved Silicon" in names_set or "Dissolved and Total Si" in names_set

    sections: list[ReportSection] = []
    silicon_added = False
    conductivity_and_ph_handled = False

    for name in names:
        if name in ("36 Elements", "26 Elements", "10 Elements"):
            # The 10/26/36-Elements selections render the SAME 36-element
            # list -- only the AVERAGE/TOTAL summary label differs.
            summary_label = name.replace("Elements", "Tr.Elts")
            sections.append(
                analyte_list_section_builder.build_metals_panel(
                    name, analyte_presets.trace_elements_36(), summary_label, element_service
                )
            )
        elif name == "67 Elements":
            sections.append(
                analyte_list_section_builder.build_metals_panel(
                    name, analyte_presets.trace_elements_67(), "67 Tr.Elts", element_service
                )
            )
        elif name == "USP Elements":
            sections.append(
                analyte_list_section_builder.build_metals_panel(
                    name, analyte_presets.trace_elements_usp(), "USP Tr.Elts", element_service
                )
            )
        elif name == "List #2 36 Elements":
            sections.append(
                analyte_list_section_builder.build_metals_panel(
                    name, analyte_presets.trace_elements_36_list2(), "36 Tr.Elts", element_service
                )
            )
        elif name == "4 Anions":
            sections.append(_ion_panel(name, "Anion", ion_presets.anions_4()))
        elif name == "5 Anions":
            sections.append(_ion_panel(name, "Anion", ion_presets.anions_5()))
        elif name == "7 Anions":
            sections.append(_ion_panel(name, "Anion", ion_presets.anions_7()))
        elif name == "Anions":
            sections.append(_ion_panel(name, "Anion", ion_presets.anions_master()))
        elif name == "6 Cations":
            sections.append(_ion_panel(name, "Cation", ion_presets.cations_6()))
        elif name == "NH4":
            sections.append(_ion_panel(name, "Cation", ion_presets.cations_nh4()))
        elif name == "Methylamines":
            sections.append(_ion_panel(name, "Cation", ion_presets.cations_methylamines()))
        elif name == "Cations":
            sections.append(_ion_panel(name, "Cation", ion_presets.cations_master()))
        elif name == "GBP":
            sections.append(_ion_panel(name, "Analyte", ion_presets.gbp_group()))
        elif name in ("Total Silicon", "Dissolved Silicon", "Dissolved and Total Si"):
            # Total/Dissolved Silicon share ONE build_silicon call (it
            # decides internally whether to add the Colloidal Silica row)
            # -- guard against calling it twice when a sample requests both.
            if not silicon_added:
                sections.append(
                    silicon_section_builder.build_silicon("Silicon", include_total_si, include_dissolved_si)
                )
                silicon_added = True
        elif name == "TOC":
            sections.append(simple_test_section_builder.build_toc(name))
        elif name == "Alkalinity":
            sections.append(simple_test_section_builder.build_alkalinity(name))
        elif name == "Bacteria Count":
            sections.append(simple_test_section_builder.build_bacteria(name))
        elif name == "Conductivity":
            if "pH" in names_set:
                if not conductivity_and_ph_handled:
                    sections.append(electrical_section_builder.build_conductivity_and_ph(name))
                    conductivity_and_ph_handled = True
                # else: already added when "pH" was processed (or will be) -- skip duplicate
            else:
                sections.append(electrical_section_builder.build_conductivity(name))
        elif name == "pH":
            if has_conductivity:
                if not conductivity_and_ph_handled:
                    sections.append(electrical_section_builder.build_conductivity_and_ph(name))
                    conductivity_and_ph_handled = True
            else:
                sections.append(misc_analysis_section_builder.build_ph(name))
        elif name == "Density":
            sections.append(misc_analysis_section_builder.build_density(name))
        elif name == "Liquid Particle Count":
            sections.append(misc_analysis_section_builder.build_lpc(name))
        elif name == "APHA Color":
            sections.append(misc_analysis_section_builder.build_apha(name))
        else:
            raise ValueError(
                f"analysis {name!r} is not yet supported by this architecture -- "
                "add a case for it once a matching section builder exists "
                "(see module docstring for the deferred list)."
            )

    return sections


def _ion_panel(name: str, category_label: str, analytes) -> ReportSection:
    return ion_list_section_builder.build_ion_panel(name, category_label, analytes, "Analysis by IC")


def _resolved_names_in_order(sample: TRSample, analysis_service: AnalysisService) -> list[str]:
    """Distinct analysis names, in first-requested order."""
    names: list[str] = []
    seen: set[str] = set()
    for analysis_id in sample.analysis_ids:
        analysis = analysis_service.load_analysis(analysis_id)
        if analysis is None:
            continue
        if analysis.name not in seen:
            seen.add(analysis.name)
            names.append(analysis.name)
    return names
