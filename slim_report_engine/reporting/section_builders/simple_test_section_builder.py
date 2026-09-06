"""Builds TOC, Alkalinity, and Bacteria — ported from
clsSimpleTestSectionBuilder.cls. Three single-parameter TR-form categories
with no combinable sub-options (unlike Misc Analysis's 4 blocks or
Electrical Testing's 3 combinations), so they're grouped in one module
rather than three near-empty ones.

KNOWN GAP (per the VBA source's own note, not re-investigated here): the
real template has no named range at all covering these rows — not even a
broken/stale external link like Cations had. The legacy VBA macro builds
range names dynamically from the TR form's own column headers and silently
skips copying when the range doesn't exist, so this looks like it should
produce a blank spot in generated reports for these test types. Confirmed
gap, reproduce the content verbatim rather than dig further.
"""

from __future__ import annotations

from slim_report_engine.reporting import row_builders, sop_codes
from slim_report_engine.reporting.report_section import ReportSection


def build_toc(id: str, date_of_analysis: str | None = None) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "TOC", "Results", "STDEV", "QL")
    row_builders.add_analyte_row(section, "TOC", "ppb")
    row_builders.add_footer_row(
        section, "Analysis by TOC Instrument", sop_codes=sop_codes.SIMPLE_SHAPE_SOP_CODES.get(id),
        date_of_analysis=date_of_analysis,
    )
    return section


def build_alkalinity(id: str, date_of_analysis: str | None = None) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Alkalinity", "Results", "STDEV")
    row_builders.add_analyte_row(section, "Alkalinity", "ppm")
    row_builders.add_footer_row(section, "Analysis by Auto-Titrator", date_of_analysis=date_of_analysis)
    return section


def build_bacteria(id: str, date_of_analysis: str | None = None) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Bacteria", "Results", "1/2 Delta")
    row_builders.add_analyte_row(section, "48 h incubation", "CFU/L")
    row_builders.add_footer_row(section, "Heterotrophic Plate Count", date_of_analysis=date_of_analysis)
    return section
