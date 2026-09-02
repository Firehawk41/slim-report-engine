"""Builds the Silicon section — ported from clsSiliconSectionBuilder.cls:
Total Si (element "Silicon"/Si), Dissolved Si ("Dissolved Silica"/SiO2),
and — only when BOTH are selected — a calculated "Colloidal Silica"/SiO2
row (defined as the difference between the two; Total_Si = Silicon row
alone, Dissolved_Si = Dissolved Silica row alone, Colloidal Silica only
appears when both are requested together).

Not DB-backed like the metals builder: "Dissolved Silica"/"Colloidal
Silica" are chemical species, not periodic elements, so they aren't
resolvable via an element service.

Shares the metals/ions analyte-panel header shape (Element/Result/Recovery/
MDL) via row_builders.add_header_rows, but the real template uses the
SINGULAR "Result" here rather than the plural metals/ions use — a genuine
inconsistency in the template, reproduced verbatim via the result_label
override rather than "corrected" to match metals.
"""

from __future__ import annotations

from slim_report_engine.reporting import row_builders
from slim_report_engine.reporting.report_section import ReportSection


def build_silicon(id: str, include_total: bool, include_dissolved: bool) -> ReportSection:
    if not include_total and not include_dissolved:
        raise ValueError("must include at least one of total/dissolved Si")

    section = ReportSection(id)
    row_builders.add_header_rows(section, "Element", "MDL", result_label="Result")

    if include_total:
        row_builders.add_analyte_row(section, "Silicon", "Si")
    if include_dissolved:
        row_builders.add_analyte_row(section, "Dissolved Silica", "SiO2")
    if include_total and include_dissolved:
        row_builders.add_analyte_row(section, "Colloidal Silica *", "SiO2")

    if include_total:
        row_builders.add_footer_row(section, "Analysis by ICP-OES (Evaporation)")
    if include_dissolved:
        row_builders.add_footer_row(section, "Dissolved Silica Analysis by UV-VIS (Evaporation)")
    if include_total and include_dissolved:
        row_builders.add_note_row(
            section,
            "* Colloidal silica is calculated as the difference between Total Silica and Dissolved Silica",
        )

    return section
