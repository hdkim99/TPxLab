"""Input validation and non-destructive quality-control checks."""

from __future__ import annotations

from typing import Any

import numpy as np
from pint import UnitRegistry

from tpxlab.models import QCIssue, RawData

_UREG: Any = UnitRegistry(autoconvert_offset_to_baseunit=True)


class DataValidationError(ValueError):
    """Raised when a dataset cannot be analyzed without changing its meaning."""


def validate_raw_data(data: RawData) -> tuple[QCIssue, ...]:
    """Validate channel lengths, units, finite values, and independent variable order."""

    lengths = {len(data.time), len(data.temperature), len(data.signal)}
    if len(lengths) != 1:
        raise DataValidationError("time, temperature, and signal must have equal lengths")
    if len(data.time) < 5:
        raise DataValidationError("at least five observations are required")
    if not all(np.all(np.isfinite(a)) for a in (data.time, data.temperature, data.signal)):
        raise DataValidationError("input channels contain missing or non-finite values")

    try:
        (1 * _UREG(data.time_unit)).to("second")
        (1 * _UREG(data.temperature_unit)).to("kelvin")
        _UREG(data.signal_unit)
    except Exception as exc:
        raise DataValidationError(
            f"invalid or dimensionally incompatible channel unit: {exc}"
        ) from exc

    issues: list[QCIssue] = []
    time_step = np.diff(data.time)
    if np.any(time_step == 0):
        raise DataValidationError("duplicate time coordinates are not allowed")
    if np.any(time_step < 0):
        raise DataValidationError("time must be strictly increasing")
    if np.any(np.diff(data.temperature) <= 0):
        issues.append(
            QCIssue(
                code="NON_MONOTONIC_TEMPERATURE",
                severity="warning",
                message=(
                    "temperature is not strictly increasing; repeated ranges need manual review"
                ),
            )
        )
    relative_step_spread = float(np.std(time_step) / np.mean(time_step))
    if relative_step_spread > 0.1:
        issues.append(
            QCIssue(
                code="IRREGULAR_SAMPLING",
                severity="warning",
                message=(
                    "time sampling interval varies by more than 10% relative standard deviation"
                ),
            )
        )
    return tuple(issues)
