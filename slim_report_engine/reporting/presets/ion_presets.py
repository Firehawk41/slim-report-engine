"""Named preset ion (Anions/GBP/Cations) lists — data, not code — ported
from modIonPresets.bas. Parallel to analyte_presets, but returns Analyte
objects (not bare symbol strings) since ions carry an elute_order used
later by the Anions MS-Authentication rendering (not yet ported).

Extracted directly from the real template:

  Anions master list (elution order in parens):
    Fluoride/F(1), Chloride/Cl(2), Nitrite/NO2(4), Sulfate/SO4(5),
    Bromide/Br(6), Nitrate/NO3(7), Phosphate/PO4(8).
    Elution order 3 is deliberately absent — it belongs to the
    MS-Authentication-only "Chloride + H2O" analyte, a separate follow-up,
    not part of the base Anions list.

  "4 Anions"/"5 Anions"/"7 Anions" are subset SELECTIONS from this one
  master list, not independent lists:
    4 Anions = Chloride, Sulfate, Nitrate, Phosphate
    5 Anions = 4 Anions + Fluoride
    7 Anions = all 7 (adds Nitrite, Bromide)

  GBP group (no elution order):
    Glycolate/C2H3O3, Propionate/C2H5CO2, Butyrate/C4H7O2

  Cations master list (no elution order):
    Lithium/Li, Sodium/Na, Ammonium/NH4, Monomethylamine/MMA,
    Dimethylamine/DMA, Potassium/K, Trimethylamine/TMA, Magnesium/Mg,
    Calcium/Ca.

    6 Cations = Lithium, Sodium, Ammonium, Potassium, Magnesium, Calcium
                (all EXCEPT the 3 amines)
    Methylamines = Monomethylamine, Dimethylamine, Trimethylamine
                   (the complement of 6 Cations)
    NH4 = Ammonium alone
    NH4 + Methylamines = Ammonium, Monomethylamine, Dimethylamine,
                          Trimethylamine
  All four subsets preserve the master list's row order.
"""

from __future__ import annotations

from slim_report_engine.reporting.analyte import Analyte


def anions_master() -> list[Analyte]:
    return [
        Analyte("Fluoride", "F", 1),
        Analyte("Chloride", "Cl", 2),
        Analyte("Nitrite", "NO2", 4),
        Analyte("Sulfate", "SO4", 5),
        Analyte("Bromide", "Br", 6),
        Analyte("Nitrate", "NO3", 7),
        Analyte("Phosphate", "PO4", 8),
    ]


def anions_4() -> list[Analyte]:
    return [
        Analyte("Chloride", "Cl", 2),
        Analyte("Sulfate", "SO4", 5),
        Analyte("Nitrate", "NO3", 7),
        Analyte("Phosphate", "PO4", 8),
    ]


def anions_5() -> list[Analyte]:
    return [
        Analyte("Fluoride", "F", 1),
        Analyte("Chloride", "Cl", 2),
        Analyte("Sulfate", "SO4", 5),
        Analyte("Nitrate", "NO3", 7),
        Analyte("Phosphate", "PO4", 8),
    ]


def anions_7() -> list[Analyte]:
    return anions_master()


def gbp_group() -> list[Analyte]:
    return [
        Analyte("Glycolate", "C2H3O3"),
        Analyte("Propionate", "C2H5CO2"),
        Analyte("Butyrate", "C4H7O2"),
    ]


def cations_master() -> list[Analyte]:
    return [
        Analyte("Lithium", "Li"),
        Analyte("Sodium", "Na"),
        Analyte("Ammonium", "NH4"),
        Analyte("Monomethylamine", "MMA"),
        Analyte("Dimethylamine", "DMA"),
        Analyte("Potassium", "K"),
        Analyte("Trimethylamine", "TMA"),
        Analyte("Magnesium", "Mg"),
        Analyte("Calcium", "Ca"),
    ]


def cations_6() -> list[Analyte]:
    return [
        Analyte("Lithium", "Li"),
        Analyte("Sodium", "Na"),
        Analyte("Ammonium", "NH4"),
        Analyte("Potassium", "K"),
        Analyte("Magnesium", "Mg"),
        Analyte("Calcium", "Ca"),
    ]


def cations_methylamines() -> list[Analyte]:
    return [
        Analyte("Monomethylamine", "MMA"),
        Analyte("Dimethylamine", "DMA"),
        Analyte("Trimethylamine", "TMA"),
    ]


def cations_nh4() -> list[Analyte]:
    return [Analyte("Ammonium", "NH4")]


def cations_nh4_methylamines() -> list[Analyte]:
    return [
        Analyte("Ammonium", "NH4"),
        Analyte("Monomethylamine", "MMA"),
        Analyte("Dimethylamine", "DMA"),
        Analyte("Trimethylamine", "TMA"),
    ]
