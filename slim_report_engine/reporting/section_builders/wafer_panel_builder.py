"""Builds ONE wafer report sheet's analyte panel — either an element panel
(36/67/List#2 36) or an anion panel (4/5/7 Anions). Ported from
clsWaferPanelBuilder.cls.

Structurally NEW versus every other report shape: a variable number of
physical wafer SAMPLES share one sheet side by side in columns (column D
is always "Process Blank", column E onward are numbered "Slot #" samples),
so this builder writes N sample-ID cells across successive columns instead
of one fixed result column — ReportRow.set_value already accepts arbitrary
column indices, so no new Row/Section type was needed, only wider rows
(see MAX_SAMPLE_COLUMNS).

Confirmed real differences between the two categories:
  - column 2 header: "Element" vs "Anion"
  - column-1 note text: "...atoms/cm2" vs "...ions/cm2"
  - the bare per-analyte-count summary header at column (6 + sample_count):
    "MDL" vs "QL"
  - footer analysis text: "Analysis by LP-ICPMS." vs "Analysis by LP-IC."
  - ONLY element panels carry a "Date of Analysis: " placeholder on the
    same footer row (anion panels have no such placeholder anywhere on
    the sheet — confirmed absent, not a template oversight)
Otherwise identical shape.

The (6 + sample_count) MDL/QL column position is derived from the real
template's own unmodified worst case: 13 slot columns (E..Q) with the bare
MDL/QL header fixed at column S (19) — i.e. one blank spacer column after
the last slot column, then the header. Confirmed self-consistent: 6 + 13
= 19.

The sheet title ("<WaferSize> Wafers") and the atoms/cm^2 superscript
formatting on the notes row are deliberately NOT set here — both need
direct Worksheet/Range access this builder doesn't have; see
wafer_report_builder.py (the orchestrator) for both, exactly the same
division of responsibility used by dm5_non_routine_report_builder.py for
the sample-ID stamp.
"""

from __future__ import annotations

from slim_domain.domain.element.element_service import ElementService

from slim_report_engine.reporting import row_builders
from slim_report_engine.reporting.analyte import Analyte
from slim_report_engine.reporting.report_row import ReportRow
from slim_report_engine.reporting.report_section import ReportSection

MAX_SAMPLE_COLUMNS = 19  # matches the real template's own column span (D..Q + a bare S header)


def build_element_panel(
    id: str,
    units_note_text: str,
    process_blank_sample_id: str,
    slot_sample_ids: list[str],
    element_symbols: list[str],
    element_service: ElementService,
    additional_element_names: list[str] | None = None,
) -> ReportSection:
    """process_blank_sample_id/slot_sample_ids: fully-formatted sample-ID
    strings (see wafer_report_builder.py for the format) — this builder
    only places them, it doesn't compute the format. additional_element_names:
    optional element NAME strings (not symbols) requested via the intake
    form's free-text "Additional Elements" field — looked up by name,
    appended after the fixed panel, matching the real insertion point
    (just before the "Analysis by..." footer row).
    """
    section = ReportSection(id)
    _add_common_header_rows(section, "Element", units_note_text, process_blank_sample_id, slot_sample_ids, "MDL")

    for symbol in element_symbols:
        element = element_service.get_by_symbol(symbol)
        if element is None:
            raise ValueError(f"unknown element symbol: {symbol!r}")
        row_builders.add_analyte_row(section, element.name, element.symbol)

    for name in additional_element_names or []:
        element = element_service.get_by_name(name.strip())
        if element is None:
            raise ValueError(f"unknown additional element name: {name!r}")
        row_builders.add_analyte_row(section, element.name, element.symbol)

    _add_footer_rows(section, "Analysis by LP-ICPMS.", include_date_of_analysis=True)
    return section


def build_anion_panel(
    id: str,
    units_note_text: str,
    process_blank_sample_id: str,
    slot_sample_ids: list[str],
    anions: list[Analyte],
) -> ReportSection:
    """anions: see presets/wafer_anion_presets.py — wafer anion order is
    alphabetical, a third convention distinct from both presets/ion_presets'
    elution order and DM5's own anion order.
    """
    section = ReportSection(id)
    _add_common_header_rows(section, "Anion", units_note_text, process_blank_sample_id, slot_sample_ids, "QL")

    for anion in anions:
        row_builders.add_analyte_row(section, anion.name, anion.symbol)

    _add_footer_rows(section, "Analysis by LP-IC.", include_date_of_analysis=False)
    return section


def _add_common_header_rows(
    section: ReportSection,
    category_label: str,
    units_note_text: str,
    process_blank_sample_id: str,
    slot_sample_ids: list[str],
    third_column_header: str,
) -> None:
    section.add_row(_blank_row_wide())
    section.add_row(_blank_row_wide())

    notes_label_row = ReportRow(style_name="Normal", max_columns=MAX_SAMPLE_COLUMNS)
    notes_label_row.set_value(1, "Notes:")
    section.add_row(notes_label_row)

    mdl_note_row = ReportRow(style_name="Normal", max_columns=MAX_SAMPLE_COLUMNS)
    mdl_note_row.set_value(1, "Blue font indicates data at or below the MDL")
    section.add_row(mdl_note_row)

    units_row = ReportRow(style_name="Normal", max_columns=MAX_SAMPLE_COLUMNS)
    units_row.set_value(1, units_note_text)
    section.add_row(units_row)

    sample_id_row = ReportRow(style_name="Normal", max_columns=MAX_SAMPLE_COLUMNS)
    sample_id_row.set_value(1, "Specification")
    sample_id_row.set_value(2, "Sample #:")
    sample_id_row.set_value(4, process_blank_sample_id)
    col_index = 5
    for slot_id in slot_sample_ids:
        sample_id_row.set_value(col_index, slot_id)
        col_index += 1
    section.add_row(sample_id_row)

    sample_count = len(slot_sample_ids)

    header_row = ReportRow(style_name="HeaderBold", max_columns=MAX_SAMPLE_COLUMNS)
    header_row.set_value(2, category_label)
    for c in range(4, 4 + sample_count + 1):
        header_row.set_value(c, "Results")
    header_row.set_value(6 + sample_count, third_column_header)
    section.add_row(header_row)


def _add_footer_rows(section: ReportSection, analysis_text: str, include_date_of_analysis: bool) -> None:
    section.add_row(_blank_row_wide())

    analysis_row = ReportRow(style_name="Normal", max_columns=MAX_SAMPLE_COLUMNS)
    analysis_row.set_value(1, analysis_text)
    if include_date_of_analysis:
        analysis_row.set_value(4, "Date of Analysis: ")
    section.add_row(analysis_row)

    wafer_number_row = ReportRow(style_name="Normal", max_columns=MAX_SAMPLE_COLUMNS)
    wafer_number_row.set_value(4, "Wafer # ")
    wafer_number_row.set_value(5, "Etching comments below:")
    section.add_row(wafer_number_row)


def _blank_row_wide() -> ReportRow:
    return ReportRow(style_name="Normal", max_columns=MAX_SAMPLE_COLUMNS)
