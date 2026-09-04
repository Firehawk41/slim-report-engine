"""Real ISO17025 SOP ("Test Methods:") code mappings — confirmed real
(per the user directly: a 2026-08 lab audit finding; recent reports list
which SOPs cover each section). Mined from every "Test Methods:" line
found across every real completed report in real_data/ (2026-09-04),
correlated against each line's own preceding "Analysis by ..." footer
and, where possible, the originating sample's real form selection.

DELIBERATELY INCOMPLETE — per direction ("infer as much as you can, I'll
confirm and complete the list tomorrow"): only combinations with solid,
repeated real evidence are mapped here. Anything not listed renders NO
Test Methods line at all — never guessed — until confirmed. See the
per-table notes below for exactly what's confirmed vs. still open.

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
# ICP-OES-Evaporation are completely different code sets). Each entry
# below has 2+ independent real confirmations except
# "Organic Dilute and Shoot" (Monument's confirmed customer-specific
# prep override -- one real confirmation, but it's the exact real value
# the override mechanism already produces, so mapped here too).
#
# Keyed on the STORED instrument identifier (Chemical.metals_instrument,
# "ICPMS"/"ICPOES", no hyphen) -- NOT the real report's own display text,
# which hyphenates it ("Analysis by ICP-OES (...)"). Mining this mapping
# surfaced that mismatch as a real, separate, pre-existing bug: the footer
# text was rendering "ICPOES" verbatim with no hyphen. Fixed alongside this
# feature in analyte_list_section_builder.py's _display_instrument.
METALS_PANEL_SOP_CODES: dict[tuple[str, str], list[str]] = {
    ("ICPMS", "Evaporation"): ["PR-IN14", "PR-IN48", "PR-IN52"],
    ("ICPOES", "Evaporation"): ["PR-IN02"],
    ("ICPMS", "Dilute and Shoot"): ["PR-IN14", "PR-IN48"],
    ("ICPMS", "Organic Dilute and Shoot"): ["PR-IN14", "PR-IN58"],
}

# Ion-panel SOPs, keyed by the exact resolved analysis name -- confirmed
# real: the second code (after what looks like a constant "IC" base code,
# PR-IN46, seen on every single ion-panel instance checked) varies by the
# EXACT panel selected, not just "Anions" vs "Cations" -- e.g. a real
# GlobalWafers sheet has TWO different second-codes (PR-IN16, PR-IN21) on
# what's presumably two different ion panels sharing one sheet, and real
# Apex Water data shows a THIRD (PR-IN11) not cross-referenced to a
# specific panel selection. Only the 2 panels below were confirmed by
# directly cross-referencing the intake form's own selection for that
# exact sample against its Test Methods line -- every other real panel
# type (5/7 Anions, Anions master, 6 Cations, NH4, Methylamines, Cations
# master, GBP) renders no Test Methods line until confirmed.
ION_PANEL_SOP_CODES: dict[str, list[str]] = {
    "4 Anions": ["PR-IN46", "PR-IN06"],
    "5 Anions + MS Authentication": ["PR-IN46", "PR-IN59"],
}
# Observed real codes NOT YET attributed to a specific panel selection --
# for the user to cross-reference tomorrow: PR-IN11 (a real Apex Water
# sample's second "Analysis by IC" block), PR-IN16 and PR-IN21 (both seen
# on the same real GlobalWafers "IPA" sheet's two separate ion panels).

# Simple/misc shapes, keyed by the resolved analysis name -- each
# confirmed by at least one real instance; TOC and Assay by several.
SIMPLE_SHAPE_SOP_CODES: dict[str, list[str]] = {
    "TOC": ["PR-IN38"],
    "Assay": ["PR-IN04"],
    "Liquid Particle Count": ["PR-IN61"],
}
# No real evidence found (yet) for: GC-FID, Moisture (Karl Fischer),
# Silicon (Total/Dissolved), Density, APHA Color, Bacteria Count,
# Alkalinity, Conductivity/pH (Electrical or Misc Analysis), GBP.

# Wafer, keyed by category ("Element" panel only -- the one real
# instance found; no real evidence yet for the Anion panel's own
# "Analysis by LP-IC." SOP code(s)).
WAFER_ELEMENT_PANEL_SOP_CODES: list[str] = ["PR-IN27", "PR-IN45"]
