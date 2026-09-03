"""Orchestrates ONE Chemical/Water sample's report content — dispatches
each of the sample's resolved analysis IDs (TRSample.analysis_ids, from
slim-domain's TR parsing stack) to the right section-builder function, in
the ORDER the analyses were requested, and returns the assembled sections.
Ported from clsChemicalWaterReportBuilder.cls.

Covers the analyses that map unambiguously onto an existing section
builder. Deliberately NOT supported yet (raises a clear, actionable error
rather than guessing):
  - Organic-matrix / ICP-OES / microwave-digestion / "with reported
    replicates" element-panel variants, Moisture/GC-MS, Mixed Acid Assay,
    UV-Vis, Acetate and Formate, Sn+2 Iodine Titration, Free Acid, TS-SLG,
    and all customer-specific edge cases — deliberately last priority, not
    attempted here.

"5 ANIONS + MS AUTHENTICATION" — confirmed real (one real Chemical
customer's report): renders the EXACT SAME 5-anion panel as plain
"5 Anions" (same analytes, same order, same footer). The "MS
Authentication" appendix visible on the real report (a "Conductivity"
label, ~35 blank rows, then an "MS data with..." label and 3 hand-typed
notes) is confirmed genuinely blank in every real file checked — no
embedded image, no cell data — i.e. staff paste/type it in separately
after generation; not reproduced here, same category as GC-FID's
manually-filled chemical-name placeholders. This matches the legacy
macro's own treatment (modReportCreator.bas only substitutes the TAB NAME
text for this variant, "MS confirmation" -> "MS Authentication", implying
the underlying content was already understood to be identical).

PREP TEXT — the metals panel's footer ("Analysis by ICPMS (<prep>)") is
NOT a fixed string. Confirmed real: Chemical samples use the resolved
Chemical's own catalog prep method (Chemical.metals_prep -- one real
Chemical sample's report used "Evaporation"), defaulting to "Evaporation"
when that field is blank (current lab practice, per direct confirmation:
default to Evaporation, then hand-correct when something else applies).
Water samples use "Dilute and Shoot" instead — confirmed across every real
Water sample checked, including ones with a full catalog panel, not just
additional-elements-only ones — there's no Chemical record for Water to
read a prep from at all, and physically it's a different method
(concentrates get evaporated down; water samples are already dilute). The
caller (submission_report_builder.py) computes this and passes it in as
metals_prep_text; this module has no DB dependency of its own.

ADDITIONAL ELEMENTS — confirmed real (several real Chemical and Water
customers' reports): the free-text "Additional Elements (specify)"
request was previously silently dropped entirely by this module. Now
rendered two ways, confirmed against real completed reports: appended as
a second labeled block after an existing metals panel's footer when one
was also requested (see
analyte_list_section_builder.add_additional_elements_block), or as its own
minimal panel-shaped section when additional elements are the ONLY thing
requested on a sample (confirmed real: several real Water samples were
exactly like this — see
analyte_list_section_builder.build_additional_elements_only_panel). Both
default to the SAME prep_text as the sample's main metals panel, unless
additional_elements_prep_text overrides it — confirmed real: at least one
customer's additional elements are run by a different method than their
main panel, per an agreement with that customer. The override is
deliberately customer-agnostic here: this module has no idea WHICH
customer, just whatever text the caller resolved from
Customer.additional_elements_prep (slim-domain) — the real customer-
specific value belongs only in a real database record, never in this
public repo.

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
    titrations_section_builder,
)

_UNCONDITIONALLY_SUPPORTED = {
    "36 Elements", "26 Elements", "10 Elements", "67 Elements", "USP Elements", "List #2 36 Elements",
    "4 Anions", "5 Anions", "7 Anions", "Anions", "5 Anions + MS Authentication",
    "6 Cations", "NH4", "Methylamines", "Cations", "GBP",
    "Total Silicon", "Dissolved Silicon", "Dissolved and Total Si",
    "TOC", "Alkalinity", "Bacteria Count",
    "Conductivity", "Density", "Liquid Particle Count", "APHA Color",
    "pH", "Assay", "GC-FID", "Moisture (Karl Fischer)",
}


def can_build_sections(sample: TRSample, analysis_service: AnalysisService) -> bool:
    """Lets a caller check before committing to this path — e.g. falling
    back to legacy handling for a sample whose analyses this doesn't (yet)
    fully cover, rather than raising mid-build.
    """
    names = _resolved_names_in_order(sample, analysis_service)
    if not names:
        # No named analysis at all is still buildable when the sample's
        # only request is the free-text "Additional Elements" field --
        # confirmed real (a real Water customer's report) -- see build_sections.
        return bool(sample.additional_element_ids)
    return all(name in _UNCONDITIONALLY_SUPPORTED for name in names)


def build_sections(
    sample: TRSample,
    analysis_service: AnalysisService,
    element_service: ElementService,
    metals_prep_text: str = "Evaporation",
    additional_elements_prep_text: str | None = None,
    metals_instrument: str = "ICPMS",
) -> list[ReportSection]:
    """Returns one (or more, for Silicon's calculated Colloidal Silica row,
    or the additional-elements block) ReportSection per resolved analysis
    on the sample, in request order — except Conductivity+pH, which
    collapse into ONE combined section.

    metals_prep_text: the metals panel's footer method text -- see module
    docstring's PREP TEXT section. The caller (submission_report_builder.py)
    computes this from the resolved Chemical's catalog prep (Chemical/Water
    request-type dependent); this module has no DB dependency of its own.

    additional_elements_prep_text: a separate prep-text override for the
    additional-elements block specifically -- None (the default) means
    "no override, reuse metals_prep_text" (current behavior). Confirmed
    real: at least one customer's additional elements are run by a
    different method than their main panel; see Customer.additional_elements_prep
    (slim-domain) -- deliberately customer-agnostic here too, this
    function has no idea which customer it's building for, just whatever
    text the caller resolved.

    metals_instrument: the footer's instrument name ("Analysis by
    <this> (<prep>)") -- see Chemical.metals_instrument (slim-domain) and
    analyte_list_section_builder.build_metals_panel's own docstring.
    Applied identically to the main panel AND any additional-elements
    block -- unlike prep_text, it's a property of the sample's physical
    matrix, not something that varies per block.
    """
    names = _resolved_names_in_order(sample, analysis_service)
    names_set = set(names)

    has_conductivity = "Conductivity" in names_set
    include_total_si = "Total Silicon" in names_set or "Dissolved and Total Si" in names_set
    include_dissolved_si = "Dissolved Silicon" in names_set or "Dissolved and Total Si" in names_set

    sections: list[ReportSection] = []
    silicon_added = False
    conductivity_and_ph_handled = False
    # Tracks the one metals-panel section a sample can have (36/26/10/67/
    # USP/List#2 36 -- mutually exclusive real form selections), so a
    # trailing additional-elements block can be attached to it below,
    # after the dispatch loop -- see module docstring's ADDITIONAL
    # ELEMENTS section.
    metals_panel_section: ReportSection | None = None

    for name in names:
        if name in ("36 Elements", "26 Elements", "10 Elements"):
            # The 10/26/36-Elements selections render the SAME 36-element
            # list -- only the AVERAGE/TOTAL summary label differs.
            summary_label = name.replace("Elements", "Tr.Elts")
            metals_panel_section = analyte_list_section_builder.build_metals_panel(
                name, analyte_presets.trace_elements_36(), summary_label, element_service, metals_prep_text,
                instrument=metals_instrument,
            )
            sections.append(metals_panel_section)
        elif name == "67 Elements":
            metals_panel_section = analyte_list_section_builder.build_metals_panel(
                name, analyte_presets.trace_elements_67(), "67 Tr.Elts", element_service, metals_prep_text,
                instrument=metals_instrument,
            )
            sections.append(metals_panel_section)
        elif name == "USP Elements":
            metals_panel_section = analyte_list_section_builder.build_metals_panel(
                name, analyte_presets.trace_elements_usp(), "USP Tr.Elts", element_service, metals_prep_text,
                instrument=metals_instrument,
            )
            sections.append(metals_panel_section)
        elif name == "List #2 36 Elements":
            metals_panel_section = analyte_list_section_builder.build_metals_panel(
                name, analyte_presets.trace_elements_36_list2(), "36 Tr.Elts", element_service, metals_prep_text,
                instrument=metals_instrument,
            )
            sections.append(metals_panel_section)
        elif name == "4 Anions":
            sections.append(_ion_panel(name, "Anion", ion_presets.anions_4(), metals_prep_text))
        elif name == "5 Anions":
            sections.append(_ion_panel(name, "Anion", ion_presets.anions_5(), metals_prep_text))
        elif name == "5 Anions + MS Authentication":
            # Confirmed real: identical panel content to plain "5 Anions"
            # -- see module docstring's "5 ANIONS + MS AUTHENTICATION"
            # section for why the appendix isn't reproduced here.
            sections.append(_ion_panel(name, "Anion", ion_presets.anions_5(), metals_prep_text))
        elif name == "7 Anions":
            sections.append(_ion_panel(name, "Anion", ion_presets.anions_7(), metals_prep_text))
        elif name == "Anions":
            sections.append(_ion_panel(name, "Anion", ion_presets.anions_master(), metals_prep_text))
        elif name == "6 Cations":
            sections.append(_ion_panel(name, "Cation", ion_presets.cations_6(), metals_prep_text))
        elif name == "NH4":
            sections.append(_ion_panel(name, "Cation", ion_presets.cations_nh4(), metals_prep_text))
        elif name == "Methylamines":
            sections.append(_ion_panel(name, "Cation", ion_presets.cations_methylamines(), metals_prep_text))
        elif name == "Cations":
            sections.append(_ion_panel(name, "Cation", ion_presets.cations_master(), metals_prep_text))
        elif name == "GBP":
            sections.append(_ion_panel(name, "Analyte", ion_presets.gbp_group(), metals_prep_text))
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
        elif name == "Assay":
            sections.append(titrations_section_builder.build_assay(name))
        elif name == "GC-FID":
            # Confirmed real (a real Chemical customer's intake form uses
            # "GC-FID" verbatim as a Titrations selection) -- see
            # titrations_section_builder.py's DISPATCH STATUS note, now
            # updated: this is no longer a guess.
            sections.append(titrations_section_builder.build_gc_fid(name))
        elif name == "Moisture (Karl Fischer)":
            # Confirmed real (same real Chemical customer's intake form,
            # verbatim Titrations selection alongside "GC-FID" above).
            sections.append(titrations_section_builder.build_kf_water(name))
        else:
            raise ValueError(
                f"analysis {name!r} is not yet supported by this architecture -- "
                "add a case for it once a matching section builder exists "
                "(see module docstring for the deferred list)."
            )

    additional_element_names = _resolve_additional_element_names(sample, element_service)
    if additional_element_names:
        prep_text = additional_elements_prep_text if additional_elements_prep_text is not None else metals_prep_text
        if metals_panel_section is not None:
            analyte_list_section_builder.add_additional_elements_block(
                metals_panel_section, additional_element_names, element_service, prep_text, metals_instrument
            )
        else:
            sections.append(
                analyte_list_section_builder.build_additional_elements_only_panel(
                    "Additional Elements", additional_element_names, element_service, prep_text, metals_instrument
                )
            )

    return sections


def _ion_panel(name: str, category_label: str, analytes, prep_text: str) -> ReportSection:
    # Confirmed real (a real Chemical customer's 4-Anions report):
    # "Analysis by IC (<prep>)", not a bare "Analysis by IC" -- the same
    # prep text the sample's metals panel would use.
    return ion_list_section_builder.build_ion_panel(name, category_label, analytes, f"Analysis by IC ({prep_text})")


def _resolve_additional_element_names(sample: TRSample, element_service: ElementService) -> list[str]:
    names: list[str] = []
    for element_id in sample.additional_element_ids:
        element = element_service.load_element(element_id)
        if element is not None:
            names.append(element.name)
    return names


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
