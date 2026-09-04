"""Builds a ReportSection for the trace-element (metals) panel shape — a
list of analytes with Result/Recovery/MDL columns and an AVERAGE/TOTAL
summary — the shape shared by every trace-element panel (10/26/36/67/USP
Elements). Ported from clsAnalyteListSectionBuilder.cls.

Replaces ~15 near-duplicate named ranges that turned out to be the same
header/summary shape wrapped around a different analyte list and summary
label: the "10/26/36 Elements" selections are the SAME 36-element list —
only the AVERAGE/TOTAL label text differs — so the caller passes the
summary label explicitly rather than this inferring it from the list.

Ions (Anions/Cations/GBP) share the header/row/footer shape (see
row_builders) but have no DB-backed catalog and no AVERAGE/TOTAL summary —
they're built by ion_list_section_builder instead, so this doesn't take an
ElementService dependency ion callers would have no use for.

SUMMARY FORMULAS: AVERAGE/TOTAL rows use relative R1C1 formula text (see
ReportRow.set_formula) computed from the section's own row count as analyte
rows are added — correct for any analyte count without hardcoding row
numbers, unlike the template it replaces.
"""

from __future__ import annotations

from slim_domain.domain.element.element_service import ElementService

from slim_report_engine.reporting import row_builders, sop_codes
from slim_report_engine.reporting.report_row import ReportRow
from slim_report_engine.reporting.report_section import ReportSection


def build_metals_panel(
    id: str,
    symbols: list[str],
    summary_label: str,
    element_service: ElementService,
    prep_text: str = "Evaporation",
    additional_element_names: list[str] | None = None,
    instrument: str = "ICPMS",
    specs: dict[str, float] | None = None,
) -> ReportSection:
    """symbols: element symbols in display order. summary_label: the text
    that appears in "AVERAGE / <summary_label>" and "TOTAL / <summary_label>"
    — e.g. "36 Tr.Elts" for the 10/26/36-Elements selections (all three
    render the same 36 analytes; only this label differs), "67 Tr.Elts",
    "USP Tr.Elts".

    specs: element symbol -> spec threshold, from the resolved customer's
    real per-chemical specification (Specification domain, slim-domain) —
    a symbol absent from specs (or specs itself being None/empty, e.g. no
    real spec on file for this customer+chemical) simply gets no column-1
    value, same convention DM5's own element panel already uses
    (dm5_element_panel_builder.py). Unlike DM5 (a small fixed set of
    chemicals with specs hardcoded as static data), the generic path
    serves the full real customer/chemical catalog, which is exactly what
    the real Specifications_Database table exists for — looked up per
    sample by the caller (submission_report_builder.py), not here.

    prep_text: the parenthesized method text in the footer ("Analysis by
    <instrument> (<prep_text>)") — the catalog's real per-chemical/per-matrix
    prep method (e.g. Chemical.metals_prep, or "Dilute and Shoot" for Water,
    confirmed against real completed reports — see chemical_water_report_builder.py,
    which computes this). Defaults to "Evaporation" to match current
    practice for a chemical with no override on file.

    additional_element_names: the free-text "Additional Elements (specify)"
    request, if any — confirmed real (multiple real customers' reports):
    rendered as a SEPARATE labeled block appended after this panel's own
    footer, not merged into the panel's own analyte rows or its
    AVERAGE/TOTAL summary. Uses the SAME prep_text/instrument as the main
    panel here -- a customer-specific PREP override (one real customer's
    additional elements are actually run by a different method than its
    main panel) is handled by the caller instead, see
    chemical_water_report_builder.py's additional_elements_prep_text.

    instrument: the footer's instrument name — confirmed real: usually
    "ICPMS", but a very dirty/nasty matrix, or one that itself contains a
    metal (e.g. NaOH), is manually switched to "ICPOES" during the quote
    process (Chemical.metals_instrument, slim-domain) — a real,
    non-trivial human judgment call upstream of the TR form, not derived
    here. Unlike prep_text, this is the SAME for the main panel and any
    additional-elements block -- it's a property of the sample's physical
    matrix, not a per-block override.
    """
    section = ReportSection(id)
    row_builders.add_header_rows(section, "Element", "MDL")

    first_data_row = section.row_count + 1  # row right after the 2 header rows

    for symbol in symbols:
        element = element_service.get_by_symbol(symbol)
        if element is None:
            raise ValueError(f"unknown element symbol in panel definition: {symbol!r}")
        row_builders.add_analyte_row_with_spec(section, element.name, element.symbol, (specs or {}).get(symbol))

    _add_summary_rows(section, summary_label, first_data_row)
    row_builders.add_footer_row(
        section, f"Analysis by {_display_instrument(instrument)} ({prep_text})",
        sop_codes=sop_codes.METALS_PANEL_SOP_CODES.get((instrument, prep_text)),
    )

    if additional_element_names:
        add_additional_elements_block(
            section, additional_element_names, element_service, prep_text, instrument, specs
        )

    return section


def add_additional_elements_block(
    section: ReportSection,
    element_names: list[str],
    element_service: ElementService,
    prep_text: str,
    instrument: str = "ICPMS",
    specs: dict[str, float] | None = None,
) -> None:
    """Appends a labeled additional-elements block to an EXISTING metals
    panel section, in place -- confirmed real layout (two different real
    customers' reports, same shape both times): one blank row (already
    provided by the panel's own preceding add_footer_row call -- no
    explicit blank added here, to avoid a double gap), one label row
    ("Additional Elements" in column 4, no repeated column-header row),
    one analyte row per element (same specs dict as the main panel, since
    it's the SAME customer+chemical, just different elements; no
    AVERAGE/TOTAL), then its own complete footer -- same shape as the
    panel's own footer, just a second one (add_footer_row supplies its
    own leading/trailing blank rows).
    """
    label_row = ReportRow(style_name="Normal")
    label_row.set_value(4, "Additional Elements")
    section.add_row(label_row)

    for name in element_names:
        element = element_service.get_by_name(name.strip())
        if element is None:
            raise ValueError(f"unknown additional element name: {name!r}")
        row_builders.add_analyte_row_with_spec(section, element.name, element.symbol, (specs or {}).get(element.symbol))

    row_builders.add_footer_row(
        section, f"Analysis by {_display_instrument(instrument)} ({prep_text})",
        sop_codes=sop_codes.METALS_PANEL_SOP_CODES.get((instrument, prep_text)),
    )


def build_additional_elements_only_panel(
    id: str,
    element_names: list[str],
    element_service: ElementService,
    prep_text: str,
    instrument: str = "ICPMS",
    specs: dict[str, float] | None = None,
) -> ReportSection:
    """The shape when additional elements are the ONLY thing requested on a
    sample -- no catalog metals-panel selection at all -- confirmed real
    (a real Water customer's sample requesting only two free-text elements,
    no "# of Elements" selection at all). A full Sample-ID/column-header
    pair around
    the requested elements, but NO "Additional Elements" label (that label
    is specific to the two-block shape used when a catalog panel is ALSO
    present) and no AVERAGE/TOTAL summary (there's no real "panel" being
    summarized, just a short ad hoc list). specs: same convention as
    build_metals_panel -- always empty for Water (no Chemical record to
    look specs up against), populated for Chemical when the resolved
    customer+chemical has one on file.
    """
    section = ReportSection(id)
    row_builders.add_header_rows(section, "Element", "MDL")

    for name in element_names:
        element = element_service.get_by_name(name.strip())
        if element is None:
            raise ValueError(f"unknown additional element name: {name!r}")
        row_builders.add_analyte_row_with_spec(section, element.name, element.symbol, (specs or {}).get(element.symbol))

    row_builders.add_footer_row(
        section, f"Analysis by {_display_instrument(instrument)} ({prep_text})",
        sop_codes=sop_codes.METALS_PANEL_SOP_CODES.get((instrument, prep_text)),
    )
    return section


def _add_summary_rows(section: ReportSection, summary_label: str, first_data_row: int) -> None:
    """Adds: blank spacer, AVERAGE row, TOTAL row, blank spacer — matching
    the real template's layout (one blank row before AND after the
    AVERAGE/TOTAL pair). Formula row/column references are RELATIVE R1C1
    text, computed from logical row positions within this section so
    they're correct regardless of how many analytes were added or where
    this section ends up on the final sheet.
    """
    last_data_row = section.row_count  # last analyte row added so far

    section.add_row(row_builders.blank_row())  # spacer before summary

    avg_row_index = section.row_count + 1
    avg_row = ReportRow(style_name="SummaryRow")
    avg_row.set_value(2, f"AVERAGE / {summary_label}")
    for col in (4, 5, 6):
        _set_range_formula(avg_row, col, "AVERAGE", first_data_row, last_data_row, avg_row_index)
    section.add_row(avg_row)

    total_row_index = section.row_count + 1
    total_row = ReportRow(style_name="SummaryRow")
    total_row.set_value(2, f"TOTAL / {summary_label}")
    for col in (4, 6):
        _set_range_formula(total_row, col, "SUM", first_data_row, last_data_row, total_row_index)
    section.add_row(total_row)

    section.add_row(row_builders.blank_row())  # spacer after summary


def _display_instrument(instrument: str) -> str:
    """Chemical.metals_instrument stores "ICPOES" (no hyphen, matching
    ChemicalService.create_chemical's own param name), but the real report
    footer text hyphenates it -- "Analysis by ICP-OES (...)" -- confirmed
    against real data while mining sop_codes.py's mapping. "ICPMS" needs no
    such translation (real report text matches the stored value verbatim).
    """
    return "ICP-OES" if instrument == "ICPOES" else instrument


def _set_range_formula(
    target_row: ReportRow,
    col_index: int,
    func_name: str,
    first_row: int,
    last_row: int,
    formula_row: int,
) -> None:
    offset_first = first_row - formula_row
    offset_last = last_row - formula_row
    target_row.set_formula(col_index, f"={func_name}(R[{offset_first}]C:R[{offset_last}]C)")
