"""Real ISO17025 SOP ("Test Methods:") code mappings — confirmed real
(per the user directly: a 2026-08 lab audit finding; recent reports list
which SOPs cover each section). Mined from every "Test Methods:" line
found across every real completed report in real_data/ (2026-09-04),
correlated against each line's own preceding "Analysis by ..." footer
and, where possible, the originating sample's real form selection. Cross-
checked against the lab's own real SOP "Test Methods" master list
(supplied directly 2026-09-04) — see per-table notes below for what that
list confirmed, corrected, or left still open.

DELIBERATELY INCOMPLETE — only combinations with solid, repeated real
evidence are mapped here. Anything not listed renders NO Test Methods
line at all — never guessed — until confirmed.

FORMAT, confirmed real: "Test Methods: " + codes joined
", " ... " and " + ".". Real reports are NOT fully consistent about the
trailing period on a single-code line (some have it, some don't, no
discernible rule — e.g. Dow's own report has "PR-IN04" and "PR-IN61"
with no period, while another real customer's report has "PR-IN04." and
"PR-IN02." WITH one) — this codebase always includes the period for
consistency; revisit if the completed list says the omission was
deliberate.
"""

from __future__ import annotations

# Metals-panel SOPs, keyed by (instrument, prep_text) -- confirmed real
# the codes depend on BOTH, not prep_text alone (ICPMS-Evaporation and
# ICP-OES-Evaporation are completely different code sets).
#
# Keyed on the STORED instrument identifier (Chemical.metals_instrument,
# "ICPMS"/"ICPOES", no hyphen) -- NOT the real report's own display text,
# which hyphenates it ("Analysis by ICP-OES (...)"). Mining this mapping
# surfaced that mismatch as a real, separate, pre-existing bug: the footer
# text was rendering "ICPOES" verbatim with no hyphen. Fixed alongside this
# feature in analyte_list_section_builder.py's _display_instrument.
#
# Cross-referenced against the lab's own SOP master list: the master list
# names its ICPMS methods by digestion temperature ("Cold Only"/"Hot
# Only"/"Hot & Cold") rather than by this codebase's prep_text strings --
# "ICPMS: Cold Only" (PR-IN14, PR-IN48) and "ICPMS: Hot & Cold" (PR-IN14,
# PR-IN48, PR-IN52) match "Dilute and Shoot" and "Evaporation" here
# EXACTLY, confirming those two prep_text values really do mean "cold
# digestion only" and "both", respectively. "ICPMS: Hot Only" (PR-IN14,
# PR-IN52, no PR-IN48) has no corresponding prep_text here -- no evidence
# yet that any real chemical's metals_prep should resolve to hot-only, so
# not mapped (would need a confirmed real example to know which prep_text
# value it corresponds to). The master list also confirms "ICPMS - TQs2"
# is the SAME real thing as "Organic Dilute and Shoot" (identical codes:
# PR-IN14, PR-IN58) -- TQs2 is just the instrument's own model name for
# the same method.
#
# "Standard Addition" is a real metals_prep value on file (unlike "Hot
# Only") but the master list splits it into Cold/Hot/Hot & Cold variants
# (PR-IN47 plus PR-IN48 and/or PR-IN52) the same way ICPMS is split --
# with no confirmed real report showing bare "Standard Addition" prep
# text next to a Test Methods line, there's no way to tell which variant
# applies, so it's deliberately left unmapped rather than guessed at.
METALS_PANEL_SOP_CODES: dict[tuple[str, str], list[str]] = {
    ("ICPMS", "Evaporation"): ["PR-IN14", "PR-IN48", "PR-IN52"],
    ("ICPOES", "Evaporation"): ["PR-IN02"],
    ("ICPMS", "Dilute and Shoot"): ["PR-IN14", "PR-IN48"],
    ("ICPMS", "Organic Dilute and Shoot"): ["PR-IN14", "PR-IN58"],
    # Same real method as "Organic Dilute and Shoot" above -- confirmed
    # real: at least one real chemical's metals_prep is stored with an
    # ampersand instead of "and" (a data-entry inconsistency, not a
    # different method), which would otherwise silently fall through to
    # no Test Methods line for that chemical alone.
    ("ICPMS", "Organic Dilute & Shoot"): ["PR-IN14", "PR-IN58"],
}

# PR-IN45 marks KED (collision-cell) mode. Confirmed real (lab's own SOP
# master list): every ICPMS "with KEDS" variant is exactly its non-KEDS
# counterpart's codes with PR-IN45 inserted right after the first code
# ("Cold with KEDS" = PR-IN14, PR-IN45, PR-IN48; "Hot & Cold with KEDS" =
# PR-IN14, PR-IN45, PR-IN48, PR-IN52) -- and Wafer's own bare "Wafers"
# entry (PR-IN27 alone, no PR-IN45) confirms Wafer's real element-panel
# SOP is the same base-plus-conditional-KEDS shape, not a fixed pair.
# Chemical.ked_element_ids (slim-domain) already tracks exactly which
# elements need KED mode per chemical -- confirmed real: 49 real chemicals
# have it populated, overwhelmingly on "Dilute and Shoot" prep. Use
# metals_panel_sop_codes()/wafer_element_panel_sop_codes() below rather
# than the raw dicts/list so this is applied consistently.
_KED_SOP_CODE = "PR-IN45"


def metals_panel_sop_codes(instrument: str, prep_text: str, has_ked_elements: bool = False) -> list[str] | None:
    """SOP codes for a metals-panel footer, or None if this (instrument,
    prep_text) combination has no confirmed real mapping at all. Adds
    PR-IN45 in the confirmed real position (right after the first code)
    when has_ked_elements is True -- see _KED_SOP_CODE above.
    """
    base = METALS_PANEL_SOP_CODES.get((instrument, prep_text))
    if base is None:
        return None
    if not has_ked_elements:
        return list(base)
    return [base[0], _KED_SOP_CODE, *base[1:]]


# Ion-panel SOPs, keyed by the exact resolved analysis name -- confirmed
# real: the second code (after what looks like a constant "IC" base code,
# PR-IN46, seen on every single ion-panel instance checked) varies by the
# EXACT panel selected, not just "Anions" vs "Cations". Confirmed by
# directly cross-referencing the intake form's own selection for that
# exact sample against its Test Methods line, AND by the lab's own SOP
# master list, which separately lists "PPB Anions - System 1"/"System 2"
# with these EXACT same two code pairs -- "System 1"/"System 2" appear to
# name which physical IC instrument runs a panel, not a different panel
# selection, so this doesn't add new resolved-analysis-name entries, just
# corroborates the two already confirmed here.
ION_PANEL_SOP_CODES: dict[str, list[str]] = {
    "4 Anions": ["PR-IN46", "PR-IN06"],
    "5 Anions + MS Confirmation": ["PR-IN46", "PR-IN59"],
}
# The lab's own SOP master list gives real codes for several more real ion
# panels/preps -- PPT Anions (PR-IN11 alone, no PR-IN46 base -- matches a
# previously-observed real Apex Water code with no confirmed panel),
# H2O2 Anions (PR-IN46, PR-IN16), Caustic (PR-IN46, PR-IN15), PPB Cation
# (PR-IN46, PR-IN21 -- matches a previously-observed real GlobalWafers
# code), PPT Cations (PR-IN12 alone) -- but none of "PPT"/"PPB"/"H2O2"/
# "Caustic" match any resolved analysis name in the real catalog (checked
# directly), and none of the 5/7 Anions/Anions master/6 Cations/NH4/
# Methylamines/Cations master/GBP panels currently in this codebase
# correspond to them either. These look like sample-prep/matrix variants
# (a separate axis from which elements are selected, the same way
# Chemical.ions_prep is separate from the panel choice) rather than a
# different panel choice -- needs the user to say which real ions_prep
# value or panel combination each one actually corresponds to before
# these can be wired in; deliberately left unmapped rather than guessed.

# Simple/misc shapes, keyed by the resolved analysis name -- each
# confirmed by at least one real instance; TOC and Assay by several.
# "Assay"/PR-IN04 additionally confirmed by the lab's own SOP master list
# (its "Titrator" entry -- the auto-titrator instrument Assay's own
# footer names, "Analysis by Auto-Titrator" -- lists the same code).
SIMPLE_SHAPE_SOP_CODES: dict[str, list[str]] = {
    "TOC": ["PR-IN38"],
    "Assay": ["PR-IN04"],
    "Liquid Particle Count": ["PR-IN61"],
}
# No real evidence found (yet) for: GC-FID, Moisture (Karl Fischer),
# Dissolved Silicon (Total Silicon has its own confirmed mapping, see
# SILICON_TOTAL_SOP_CODES below), Density, APHA Color, Bacteria Count,
# Alkalinity, Conductivity/pH (Electrical or Misc Analysis), GBP.

# Silicon's Total-Si footer ("Analysis by ICP-OES (Evaporation)") used to
# reuse METALS_PANEL_SOP_CODES[("ICPOES", "Evaporation")] (PR-IN02 alone)
# on the assumption it's the same method as the generic metals panel's
# own ICPOES/Evaporation combo. The lab's own SOP master list shows this
# was incomplete: a dedicated "ICP-OES - Water Evaporator + Silicon"
# entry gives PR-IN49 AND PR-IN02 together -- Silicon has its own
# additional method code (PR-IN49) on top of the shared ICP-OES base code
# (PR-IN02), the same "shared base + panel-specific extra" shape ion
# panels already have with PR-IN46.
SILICON_TOTAL_SOP_CODES: list[str] = ["PR-IN49", "PR-IN02"]

# Wafer, keyed by category ("Element" panel only -- the one real instance
# found; no real evidence yet for the Anion panel's own "Analysis by
# LP-IC." SOP code(s)). The lab's own SOP master list's bare "Wafers"
# entry (PR-IN27 alone) implies PR-IN45 should be conditional on KED
# elements here too, same as the generic metals panel above -- but unlike
# the generic path, nothing in the Wafer report-building chain currently
# looks up a Chemical record at all (Wafer submissions are dispatched
# without a chemical_service, see submission_report_builder.py), so there
# is no has_ked_elements to check yet and no confirmed real counter-example
# of a Wafer sample that should have omitted PR-IN45. Left unconditional
# until that's confirmed one way or the other -- see
# wafer_element_panel_sop_codes() below, which already has the
# has_ked_elements parameter ready for when that wiring exists.
WAFER_ELEMENT_PANEL_SOP_CODES: list[str] = ["PR-IN27"]


def wafer_element_panel_sop_codes(has_ked_elements: bool = True) -> list[str]:
    """SOP codes for Wafer's element-panel footer. Defaults
    has_ked_elements to True (unlike metals_panel_sop_codes' False)
    because every real Wafer instance found so far includes PR-IN45 and
    nothing yet threads a real has_ked_elements value in -- see the
    WAFER_ELEMENT_PANEL_SOP_CODES comment above.
    """
    if has_ked_elements:
        return [*WAFER_ELEMENT_PANEL_SOP_CODES, _KED_SOP_CODE]
    return list(WAFER_ELEMENT_PANEL_SOP_CODES)
