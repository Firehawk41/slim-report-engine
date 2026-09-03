"""The lab's own identity block for the report header's left section
(name/address/phone) -- see report_writer.apply_header_footer's
lab_header_lines parameter.

Deliberately placeholder, not real company information, per this repo's
de-branding policy (see DOMAIN_BRIEF.md) -- this is the one place that
policy leaves a gap to fill. The private fork replaces the tuple below
with the real values; nothing else in the codebase needs to change.
"""

from __future__ import annotations

LAB_HEADER_LINES: tuple[str, ...] = (
    "[LAB NAME PLACEHOLDER]",
    "[Lab Street Address, City, State ZIP]",
    "[Lab Phone Number]",
)
