"""Dimensionally checked peak quantification."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from pint import DimensionalityError, UnitRegistry

from tpxlab.models import IntegratedPeak, QuantifiedPeak

UREG: UnitRegistry[Any] = UnitRegistry(autoconvert_offset_to_baseunit=True)


class QuantificationError(ValueError):
    """Raised when calibration or sample-mass units are incompatible."""


def quantify_peaks(
    peaks: Sequence[IntegratedPeak],
    *,
    area_unit: str,
    calibration_value: float,
    calibration_unit: str,
    sample_mass_value: float,
    sample_mass_unit: str,
    output_unit: str = "millimole / gram",
) -> tuple[QuantifiedPeak, ...]:
    """Convert signal*time areas to amount per mass using an explicit calibration.

    ``calibration_value * calibration_unit`` must convert an integrated detector area
    into amount of substance. Division by sample mass must then be convertible to the
    requested amount/mass unit. No detector response or stoichiometry is inferred.
    """

    if not math.isfinite(sample_mass_value) or sample_mass_value <= 0:
        raise QuantificationError("sample mass must be positive")
    if not math.isfinite(calibration_value) or calibration_value == 0:
        raise QuantificationError("calibration factor must be finite and non-zero")
    try:
        mass = sample_mass_value * UREG(sample_mass_unit)
        mass.to("gram")
        calibration = calibration_value * UREG(calibration_unit)
        # Validate even an empty peak sequence using a unit-only trial quantity.
        trial = (1 * UREG(area_unit) * calibration / mass).to(output_unit)
        if trial.dimensionality != UREG(output_unit).dimensionality:
            raise QuantificationError("quantification result is not amount per mass")
        return tuple(
            QuantifiedPeak(
                peak_id=peak.peak_id,
                value=float(
                    (peak.area * UREG(area_unit) * calibration / mass).to(output_unit).magnitude
                ),
                unit=output_unit,
            )
            for peak in peaks
        )
    except (DimensionalityError, TypeError, ValueError) as exc:
        if isinstance(exc, QuantificationError):
            raise
        raise QuantificationError(f"incompatible quantification units: {exc}") from exc
