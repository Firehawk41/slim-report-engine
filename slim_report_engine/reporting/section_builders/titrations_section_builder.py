"""Builds the generic Titrations section shapes — ported from
clsTitrationsSectionBuilder.cls. Confirmed from the real template
("Full Analysis (8)" rows 295-332) to be 3 INDEPENDENT atomic blocks: Assay
(%), Karl Fischer Water (%), and GC-FID (Chemical 1/2, %/Vol) — the 4 real
Titrations_* named ranges are every observed union of these 3, not
independent content.

GC-FID's "Chemical 1"/"Chemical 2" row labels, and Assay's blank analyte
name, are real placeholders manually filled in by staff per sample after
generation — not resolved by any code path, so they're reproduced verbatim
here (same category as Wafer's own hand-filled notes).

DISPATCH STATUS: "Assay", "GC-FID", and "Moisture (Karl Fischer)" are all
wired into chemical_water_report_builder.py — confirmed against real
completed reports (Assay: 3 different real Chemical customers; GC-FID and
Moisture (Karl Fischer): one real Chemical customer's intake form uses
both verbatim as Titrations selections, on the same submission).

EXCLUDED (customer-specific edge cases, deferred, same bucket as other
customer-specific edge cases already out of scope): bespoke titration
blocks with hardcoded specification text tied to a specific customer/
chemical combination.
"""

from __future__ import annotations

from slim_report_engine.reporting import row_builders, sop_codes
from slim_report_engine.reporting.report_section import ReportSection


def build_assay(id: str, date_of_analysis: str | None = None) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Assay", "Result", "STDEV")
    row_builders.add_analyte_row(section, "", "%")
    row_builders.add_footer_row(
        section, "Analysis by Auto-Titrator", sop_codes=sop_codes.SIMPLE_SHAPE_SOP_CODES.get(id),
        date_of_analysis=date_of_analysis,
    )
    return section


def build_kf_water(id: str, date_of_analysis: str | None = None) -> ReportSection:
    """Confirmed real: the data row's unit is "ppm", not the "%" the real
    VBA reference source (clsTitrationsSectionBuilder.cls) has -- the
    template that source was ported from disagrees with a real completed
    report on this one detail, and the real report wins (see this
    project's general policy: verify against real source over the
    closest local approximation)."""
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Karl Fischer", "Result", "STDEV")
    row_builders.add_analyte_row(section, "Water", "ppm")
    row_builders.add_footer_row(section, "Analysis by KF-Titration", date_of_analysis=date_of_analysis)
    return section


def build_gc_fid(id: str, date_of_analysis: str | None = None) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "GC-FID", "Results", "STDEV")
    row_builders.add_analyte_row(section, "Chemical 1", "%/Vol")
    row_builders.add_analyte_row(section, "Chemical 2", "%/Vol")
    row_builders.add_footer_row(section, "Analysis by GC-FID (average of triplicates)", date_of_analysis=date_of_analysis)
    return section
