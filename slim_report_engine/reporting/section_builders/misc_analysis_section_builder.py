"""Builds the "Misc Analysis" section shapes — ported from
clsMiscAnalysisSectionBuilder.cls: pH, Density, Liquid Particle Count
(LPC), and APHA Color. Confirmed from the real template to be 4 INDEPENDENT
atomic blocks — the real named ranges are every observed union of these 4
blocks, not independent content. Callers just include whichever build_*
results they want in their own section list; there's no preset per
combination.

NOTE: this Misc Analysis "pH" block is a separate, slightly different block
from electrical_section_builder.build_ph — the real template has BOTH,
presumably because Electrical Testing and Misc Analysis are offered as
independent TR-form selections. Reproduced verbatim as two separate blocks
rather than silently deduplicated.
"""

from __future__ import annotations

from slim_report_engine.reporting import row_builders, sop_codes
from slim_report_engine.reporting.report_section import ReportSection


def build_ph(id: str, date_of_analysis: str | None = None) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "pH", "Result")
    row_builders.add_analyte_row(section, "pH", "")
    row_builders.add_note_row(section, "Dimensionless quantity")
    row_builders.add_footer_row(section, "Analysis by pH Electrode", date_of_analysis=date_of_analysis)
    return section


def build_density(id: str, date_of_analysis: str | None = None) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Density", "Result", "STDEV")
    row_builders.add_analyte_row(section, "Density of solution", "(g/mL)")
    row_builders.add_footer_row(section, "Analysis by Gay-Lussac Pycnometer", date_of_analysis=date_of_analysis)
    return section


def build_lpc(id: str, date_of_analysis: str | None = None) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Particles/mL", "Results", "STD Dev")
    for threshold in ("0.10", "0.15", "0.20", "0.30", "0.50", "1.00"):
        row_builders.add_analyte_row(section, _ge_threshold(threshold), "")
    row_builders.add_footer_row(
        section, "Analysis by Liquid Particle Counter.", sop_codes=sop_codes.SIMPLE_SHAPE_SOP_CODES.get(id),
        date_of_analysis=date_of_analysis,
    )
    return section


def build_apha(id: str, date_of_analysis: str | None = None) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Parameter", "Result")
    row_builders.add_analyte_row(section, "APHA number", "")
    row_builders.add_footer_row(section, "Analysis by UV-Vis (average of six replicates)", date_of_analysis=date_of_analysis)
    return section


def _ge_threshold(value_text: str) -> str:
    return f"≥ {value_text} µm"
