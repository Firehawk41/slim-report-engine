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

DISPATCH STATUS: only "Assay" is wired into chemical_water_report_builder.py
so far — confirmed against real completed reports from 3 different real
Chemical customers. build_kf_water/build_gc_fid are ported and ready
(their shape is directly from the real VBA source), but not yet
dispatched: no real submitted report in hand confirms the exact catalog
analysis-name string for either ("Karl Fischer"? "KF Water"? "GC-FID" is
plausible from the intake form's own example row, but that's instructional
text, not a confirmed real submission) — wire them once a real one shows
up rather than guessing the dispatch key.

EXCLUDED (customer-specific edge cases, deferred, same bucket as other
customer-specific edge cases already out of scope): bespoke titration
blocks with hardcoded specification text tied to a specific customer/
chemical combination.
"""

from __future__ import annotations

from slim_report_engine.reporting import row_builders
from slim_report_engine.reporting.report_section import ReportSection


def build_assay(id: str) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Assay", "Result", "STDEV")
    row_builders.add_analyte_row(section, "", "%")
    row_builders.add_footer_row(section, "Analysis by Auto-Titrator")
    return section


def build_kf_water(id: str) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Karl Fischer", "Result", "STDEV")
    row_builders.add_analyte_row(section, "Water", "%")
    row_builders.add_footer_row(section, "Analysis by KF-Titration")
    return section


def build_gc_fid(id: str) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "GC-FID", "Results", "STDEV")
    row_builders.add_analyte_row(section, "Chemical 1", "%/Vol")
    row_builders.add_analyte_row(section, "Chemical 2", "%/Vol")
    row_builders.add_footer_row(section, "Analysis by GC-FID (average of triplicates)")
    return section
