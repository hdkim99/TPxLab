"""Numerical integration with the measured sampling coordinates."""

from __future__ import annotations

from collections.abc import Sequence

from scipy.integrate import simpson, trapezoid

from tpxlab.models import FloatArray, IntegratedPeak, IntegrationMethod, PeakSeed
from tpxlab.peaks import resolve_peak_regions


def integrate_peaks(
    time: FloatArray,
    temperature: FloatArray,
    signal: FloatArray,
    seeds: Sequence[PeakSeed],
    method: IntegrationMethod = "trapezoid",
) -> tuple[IntegratedPeak, ...]:
    """Integrate each temperature-bounded peak against measured time.

    Integration against time (not point index) gives signal*time area and therefore
    remains correct for irregular sampling and calibration factors expressed per time.
    """

    integrated: list[IntegratedPeak] = []
    for peak_id, (seed, left, right) in enumerate(
        resolve_peak_regions(temperature, seeds), start=1
    ):
        mask = (temperature >= left) & (temperature <= right)
        region_time = time[mask]
        region_signal = signal[mask]
        if len(region_time) < 2:
            raise ValueError(f"peak {peak_id} region has fewer than two observations")
        if method == "trapezoid":
            area = float(trapezoid(region_signal, x=region_time))
        elif method == "simpson":
            area = float(simpson(region_signal, x=region_time))
        else:
            raise ValueError(f"unsupported integration method: {method}")
        integrated.append(
            IntegratedPeak(
                peak_id=peak_id,
                center=seed.center,
                left=left,
                right=right,
                area=area,
                method=method,
            )
        )
    return tuple(integrated)
