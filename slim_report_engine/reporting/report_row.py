"""One row of assembled report content — ported from clsReportRow.cls.

Pure data, no Worksheet/Range dependency. Values are a fixed-width 1-based
column map; formulas are a sparse map (column index -> R1C1-relative formula
text) for the few cells that must stay live Excel formulas (e.g. AVERAGE/SUM
over technician-entered results) instead of a baked value. Everything else
is written as a plain value.

StyleName references a named style the writer (kept VBA-side, see this
repo's README) knows how to apply. No per-cell font/border/fill logic lives
here or in any section builder.
"""

from __future__ import annotations

from typing import Any

DEFAULT_MAX_COLUMNS = 12


class ReportRow:
    """MaxColumns defaults to 12 (every existing single-result-column report
    shape). Wafer's multi-sample-column layout is the one exception -- it
    needs up to column 19 for a bare MDL/QL header past as many as 13
    side-by-side sample columns -- so it's a per-row constructor parameter,
    not a global constant, to avoid widening every other report type's row
    writes to columns it has no content for.
    """

    def __init__(self, style_name: str = "Normal", max_columns: int = DEFAULT_MAX_COLUMNS) -> None:
        self.style_name = style_name
        self.max_columns = max_columns
        self._values: dict[int, Any] = {}
        self._formulas: dict[int, str] = {}

    def set_value(self, col_index: int, value: Any) -> None:
        self._require_valid_column(col_index)
        self._values[col_index] = value

    def get_value(self, col_index: int) -> Any:
        return self._values.get(col_index)

    def set_formula(self, col_index: int, formula_r1c1: str) -> None:
        """formula_r1c1: relative R1C1 notation (e.g. "=AVERAGE(R[-36]C:R[-1]C)")
        so the formula is correct regardless of which absolute row this row
        ends up written to -- the builder that computes this never knows
        final sheet placement, only relative offsets to other rows in the
        same section, which is exactly what R1C1-relative expresses.
        """
        self._require_valid_column(col_index)
        self._formulas[col_index] = formula_r1c1

    def has_formula(self, col_index: int) -> bool:
        return col_index in self._formulas

    def get_formula(self, col_index: int) -> str:
        return self._formulas[col_index]

    @property
    def values(self) -> dict[int, Any]:
        return dict(self._values)

    @property
    def formula_columns(self) -> list[int]:
        return list(self._formulas.keys())

    def _require_valid_column(self, col_index: int) -> None:
        if not 1 <= col_index <= self.max_columns:
            raise ValueError(f"column {col_index} out of range 1..{self.max_columns}")
