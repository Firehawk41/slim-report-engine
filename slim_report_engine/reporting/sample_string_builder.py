"""Builds the standard sample-ID string — "mmddyy-Chemical-Customer-SampleID"
— ported verbatim from clsSampleStringBuilder.cls (itself pulled out of the
legacy macro's SetSampleString). NOT DM5-specific: this is the SAME format
every Chemical/Water sample gets, and non-routine DM5 samples get this
exact string too (not the routine path's predictable format) — they arrive
via a normal testing request like every other sample.

Two confirmed real overrides, reproduced verbatim:
  - Customer "UPS" displays as "FUJIFILM UPS"
  - DM5-N's "W2000" chemical displays as "2to1W2000" (matches what the real
    DM5-N template's own W-2000 sheet already has baked into its A1)
"""

from __future__ import annotations

from datetime import date


def build_sample_string(
    date_received: date, chemical_name: str, customer: str, sample_id: str
) -> str:
    display_chemical = chemical_name
    display_customer = customer

    if customer == "DM5N" and chemical_name == "W2000":
        display_chemical = "2to1W2000"
    if customer == "UPS":
        display_customer = "FUJIFILM UPS"

    return f"{date_received.strftime('%m%d%y')}-{display_chemical}-{display_customer}-{sample_id}"
