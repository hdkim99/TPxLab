"""Numerical integration with the measured sampling coordinates."""

from __future__ import annotations

from collections.abc import Sequence

from scipy.integrate import simpson, trapezoid

from tpxlab.models import FloatArray, IntegratedPeak, IntegrationMethod, PeakFit, PeakSeed
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


def integrate_component_signals(
    time: FloatArray,
    temperature: FloatArray,
    component_signals: Sequence[FloatArray],
    seeds: Sequence[PeakSeed],
    fits: Sequence[PeakFit],
    method: IntegrationMethod = "trapezoid",
) -> tuple[IntegratedPeak, ...]:
    """Integrate deconvolved components against measured time coordinates.

    An explicit seed ``left`` or ``right`` truncates that component. With no explicit
    bound, the complete measured interval is used so overlapping component tails are
    not partitioned at arbitrary midpoints.
    """

    ordered_seeds = tuple(sorted(seeds, key=lambda item: item.center))
    if not (len(component_signals) == len(ordered_seeds) == len(fits)):
        raise ValueError("component signals, seeds, and fits must have equal lengths")
    low = float(min(temperature))
    high = float(max(temperature))
    integrated: list[IntegratedPeak] = []
    for fit, seed, signal in zip(fits, ordered_seeds, component_signals, strict=True):
        left = low if seed.left is None else seed.left
        right = high if seed.right is None else seed.right
        if not low <= left < fit.center < right <= high:
            raise ValueError(
                f"component {fit.peak_id} integration bounds must contain its fitted center"
            )
        mask = (temperature >= left) & (temperature <= right)
        region_time = time[mask]
        region_signal = signal[mask]
        if len(region_time) < 2:
            raise ValueError(
                f"component {fit.peak_id} integration region has fewer than two observations"
            )
        if method == "trapezoid":
            area = float(trapezoid(region_signal, x=region_time))
        elif method == "simpson":
            area = float(simpson(region_signal, x=region_time))
        else:
            raise ValueError(f"unsupported integration method: {method}")
        integrated.append(
            IntegratedPeak(
                peak_id=fit.peak_id,
                center=fit.center,
                left=left,
                right=right,
                area=area,
                method=method,
                source="fitted_component",
            )
        )
    return tuple(integrated)
