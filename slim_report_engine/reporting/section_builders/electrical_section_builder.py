"""Builds the "Electrical Testing" (Conductivity/pH) section shapes —
ported from clsElectricalSectionBuilder.cls. Confirmed from the real
template: the two parameters (Conductivity, pH) are independent atomic
rows sharing one header, but the FOOTER TEXT depends on which combination
was requested — there are 3 distinct footer rows in the template (one for
Conductivity alone, one for pH alone, one for both together), not one
shared footer. Each build_* function below reproduces the exact real
combination rather than deriving footer text generically.
"""

from __future__ import annotations

from slim_report_engine.reporting import row_builders
from slim_report_engine.reporting.report_section import ReportSection


def build_conductivity(id: str) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Electrical Testing", "Results", "STDEV")
    row_builders.add_analyte_row(section, "Conductivity", "uS/cm")
    row_builders.add_footer_row(section, "Analysis by Conductivity Electrode")
    return section


def build_ph(id: str) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Electrical Testing", "Results", "STDEV")
    row_builders.add_analyte_row(section, "pH (dimensionless quantity)", "")
    row_builders.add_footer_row(section, "Analysis by pH Electrode")
    return section


def build_conductivity_and_ph(id: str) -> ReportSection:
    section = ReportSection(id)
    row_builders.add_simple_header_row(section, "Electrical Testing", "Results", "STDEV")
    row_builders.add_analyte_row(section, "Conductivity", "uS/cm")
    row_builders.add_analyte_row(section, "pH (dimensionless quantity)", "")
    row_builders.add_footer_row(section, "Analysis by pH/Conductivity Electrode")
    return section
