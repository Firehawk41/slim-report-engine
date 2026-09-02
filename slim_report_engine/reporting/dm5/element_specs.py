"""Per-chemical trace-element specification thresholds for DM5
element-panel sheets — ported from modDM5ElementSpecs.bas. Data, not code,
same spirit as presets/analyte_presets.py. Each chemical uses the SAME
36-element list/order as the generic metals panel
(presets.analyte_presets.trace_elements_36), but with its OWN per-element
spec value (or none) in column A — that's the actual process-control
content DM5 reports exist for.

Only elements WITH a spec get an entry; an element with no spec for a
given chemical is simply absent from that chemical's dict (reproduced
verbatim from the real template — e.g. NH4OH has no spec for Beryllium,
Bismuth, Gallium, ...).

DM5-N and DM5-S variants are kept as fully independent functions rather
than shared, since a future edit to one side has no logical reason to also
apply to the other — confirmed some values already differ (e.g. 49%HF's
Calcium: 0.5 on DM5-N vs 0.08 on DM5-S).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# DM5-N
# ---------------------------------------------------------------------------


def nh4oh_specs() -> dict[str, float]:
    return {
        "Al": 0.1, "Sb": 0.1, "As": 0.1, "Ba": 0.1, "B": 1, "Cd": 0.1,
        "Ca": 0.1, "Cr": 0.1, "Co": 0.1, "Cu": 0.1, "Fe": 0.1, "Pb": 0.1,
        "Li": 0.1, "Mg": 0.1, "Mn": 0.1, "Ni": 0.1, "K": 0.1, "Na": 0.1,
        "Ta": 0.1, "Sn": 0.1, "Ti": 0.1, "W": 0.1, "V": 0.1, "Zn": 0.1,
    }


def h2o2_specs() -> dict[str, float]:
    return {
        "Al": 0.1, "Sb": 0.1, "As": 0.1, "Ba": 0.1, "B": 0.15, "Cd": 0.1,
        "Ca": 0.1, "Cr": 0.1, "Co": 0.1, "Cu": 0.1, "Fe": 0.1, "Pb": 0.1,
        "Li": 0.1, "Mg": 0.1, "Mn": 0.1, "Ni": 0.1, "K": 0.1, "Na": 0.1,
        "Ta": 0.1, "Sn": 0.1, "Ti": 0.1, "W": 0.1, "V": 0.1, "Zn": 0.1,
    }


def ipa_specs() -> dict[str, float]:
    return {
        "Al": 0.5, "Sb": 0.5, "As": 0.5, "Ba": 0.2, "B": 2, "Cd": 0.5,
        "Ca": 1, "Cr": 0.5, "Co": 0.5, "Cu": 0.5, "Fe": 0.5, "Pb": 0.5,
        "Li": 0.5, "Mg": 0.5, "Mn": 0.5, "Ni": 0.5, "K": 0.5, "Na": 5,
        "Ta": 0.5, "Sn": 0.5, "Ti": 0.5, "V": 0.5, "Zn": 0.5,
    }


def bhf_specs() -> dict[str, float]:
    return {
        "Al": 0.5, "Sb": 0.1, "As": 0.5, "Ba": 0.5, "B": 0.5, "Cd": 0.5,
        "Ca": 0.4, "Cr": 0.5, "Co": 0.5, "Cu": 0.5, "Fe": 0.5, "Pb": 0.5,
        "Li": 0.1, "Mg": 0.5, "Mn": 0.5, "Ni": 0.5, "K": 0.5, "Na": 0.5,
        "Ta": 0.1, "Sn": 0.5, "Ti": 0.5, "W": 0.1, "V": 0.5, "Zn": 0.5,
    }


def hf49_specs() -> dict[str, float]:
    return {
        "Al": 0.5, "Sb": 0.03, "As": 0.08, "Ba": 0.08, "B": 3, "Cd": 0.03,
        "Ca": 0.5, "Cr": 0.08, "Co": 0.03, "Cu": 0.03, "Fe": 0.2, "Pb": 0.03,
        "Li": 0.01, "Mg": 0.08, "Mn": 0.03, "Ni": 0.08, "K": 0.08, "Na": 0.4,
        "Ta": 0.01, "Sn": 0.03, "Ti": 0.5, "W": 0.01, "V": 0.01, "Zn": 0.03,
    }


def hcl_specs() -> dict[str, float]:
    return {
        "Al": 0.5, "Sb": 0.1, "As": 0.1, "Ba": 0.1, "B": 0.5, "Cd": 0.1,
        "Ca": 1, "Cr": 0.1, "Co": 0.1, "Cu": 0.1, "Fe": 1, "Pb": 0.1,
        "Li": 0.1, "Mg": 1, "Mn": 0.1, "Ni": 0.1, "K": 0.5, "Na": 1,
        "Ta": 0.1, "Sn": 0.1, "Ti": 1, "W": 0.1, "V": 0.1, "Zn": 0.5,
    }


# ---------------------------------------------------------------------------
# DM5-S. Extracted independently from the real DM5-S template -- NOT
# assumed to match DM5-N's values even where they currently happen to.
# ---------------------------------------------------------------------------


def nh4oh_specs_s() -> dict[str, float]:
    return {
        "Al": 0.1, "Sb": 0.1, "As": 0.1, "Ba": 0.1, "B": 1, "Cd": 0.1,
        "Ca": 0.1, "Cr": 0.1, "Co": 0.1, "Cu": 0.1, "Fe": 0.1, "Pb": 0.1,
        "Li": 0.1, "Mg": 0.1, "Mn": 0.1, "Ni": 0.1, "K": 0.1, "Na": 0.1,
        "Ta": 0.1, "Sn": 0.1, "Ti": 0.1, "W": 0.1, "V": 0.1, "Zn": 0.1,
    }


def h2o2_specs_s() -> dict[str, float]:
    return {
        "Al": 0.1, "Sb": 0.1, "As": 0.1, "Ba": 0.1, "B": 0.15, "Cd": 0.1,
        "Ca": 0.1, "Cr": 0.1, "Co": 0.1, "Cu": 0.1, "Fe": 0.1, "Pb": 0.1,
        "Li": 0.1, "Mg": 0.1, "Mn": 0.1, "Ni": 0.1, "K": 0.1, "Na": 0.1,
        "Ta": 0.1, "Sn": 0.1, "Ti": 0.1, "W": 0.1, "V": 0.1, "Zn": 0.1,
    }


def ipa_specs_s() -> dict[str, float]:
    return {
        "Al": 0.5, "Sb": 0.5, "As": 0.5, "Ba": 0.2, "B": 2, "Cd": 0.5,
        "Ca": 1, "Cr": 0.5, "Co": 0.5, "Cu": 0.5, "Fe": 0.5, "Pb": 0.5,
        "Li": 0.5, "Mg": 0.5, "Mn": 0.5, "Ni": 0.5, "K": 0.5, "Na": 5,
        "Ta": 0.5, "Sn": 0.5, "Ti": 0.5, "V": 0.5, "Zn": 0.5,
    }


def bhf_specs_s() -> dict[str, float]:
    return {
        "Al": 0.5, "Sb": 0.1, "As": 0.5, "Ba": 0.5, "B": 0.5, "Cd": 0.5,
        "Ca": 0.4, "Cr": 0.5, "Co": 0.5, "Cu": 0.5, "Fe": 0.5, "Pb": 0.5,
        "Li": 0.1, "Mg": 0.5, "Mn": 0.5, "Ni": 0.5, "K": 0.5, "Na": 0.5,
        "Ta": 0.1, "Sn": 0.5, "Ti": 0.5, "W": 0.1, "V": 0.5, "Zn": 0.5,
    }


def hf49_specs_s() -> dict[str, float]:
    """Genuinely differs from DM5-N's hf49_specs -- e.g. Calcium is 0.08
    here vs 0.5 on DM5-N."""
    return {
        "Al": 0.08, "Sb": 0.03, "As": 0.08, "Ba": 0.08, "B": 3, "Cd": 0.03,
        "Ca": 0.08, "Cr": 0.08, "Co": 0.03, "Cu": 0.03, "Fe": 0.2, "Pb": 0.03,
        "Li": 0.01, "Mg": 0.08, "Mn": 0.03, "Ni": 0.08, "K": 0.08, "Na": 0.08,
        "Ta": 0.01, "Sn": 0.03, "Ti": 0.08, "W": 0.01, "V": 0.01, "Zn": 0.03,
    }


def hcl_specs_s() -> dict[str, float]:
    return {
        "Al": 0.5, "Sb": 0.1, "As": 0.1, "Ba": 0.1, "B": 0.5, "Cd": 0.1,
        "Ca": 1, "Cr": 0.1, "Co": 0.1, "Cu": 0.1, "Fe": 1, "Pb": 0.1,
        "Li": 0.1, "Mg": 1, "Mn": 0.1, "Ni": 0.1, "K": 0.5, "Na": 1,
        "Ta": 0.1, "Sn": 0.1, "Ti": 1, "W": 0.1, "V": 0.1, "Zn": 0.5,
    }


def surf_etch_specs() -> dict[str, float]:
    """SurfEtch is DM5-S only (no DM5-N equivalent). Much higher thresholds
    than the acid/base chemicals -- expected for a surface etchant."""
    return {
        "As": 50, "Cu": 100, "Fe": 150, "Pb": 25, "Mn": 25, "Ni": 50,
        "K": 50, "Na": 200,
    }


# ---------------------------------------------------------------------------
# Composite chemicals: DM5-N's "0.49%HF", DM5-S's "0.49%HF", and DM5-S's
# "2.5%HF-5%" all combine an element panel with an anions block and a
# deprecated Assay block. Confirmed real, required content "as per the
# template" for these two HF chemicals -- not something to omit, even
# though DM5-N's copy carries a note saying the underlying business no
# longer wants it (kept only because the downstream XML program still
# expects the structure).
#
# Confirmed from real data: the element AND anion specs are IDENTICAL
# across all 3 sheets (DM5-N 0.49%HF, DM5-S 0.49%HF, DM5-S 2.5%HF-5%) --
# only the chemical label, QC code, and Assay spec-range/note differ per
# sheet. One shared function each, not three copies.
# ---------------------------------------------------------------------------


def hf_composite_element_specs() -> dict[str, float]:
    return {
        "Al": 0.08, "Sb": 0.03, "As": 0.08, "Ba": 0.08, "B": 3, "Cd": 0.03,
        "Ca": 0.08, "Cr": 0.08, "Co": 0.03, "Cu": 0.03, "Fe": 0.08, "Pb": 0.03,
        "Li": 0.01, "Mg": 0.08, "Mn": 0.03, "Ni": 0.08, "K": 0.08, "Na": 0.08,
        "Ta": 0.01, "Sn": 0.03, "Ti": 0.08, "W": 0.01, "V": 0.01, "Zn": 0.03,
    }


def hf_composite_anion_specs() -> dict[str, float]:
    """Keyed by symbol, DM5's own order (Chloride, Nitrate, Sulfate,
    Phosphate) -- confirmed to differ from presets.ion_presets.anions_4()'s
    order (Chloride, Sulfate, Nitrate, Phosphate). Order is applied by the
    caller (dm5_element_panel_builder.build_element_panel_with_anions),
    this dict only carries the spec values.
    """
    return {"Cl": 40, "NO3": 60, "SO4": 30, "PO4": 10}
