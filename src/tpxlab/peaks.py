"""Peak detection and parametric fitting using SciPy optimizers."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import trapezoid
from scipy.optimize import curve_fit
from scipy.signal import find_peaks
from scipy.special import voigt_profile

from tpxlab.models import FitStatistics, FloatArray, PeakFit, PeakModel, PeakSeed

ModelFunction = Callable[..., FloatArray]


def gaussian(x: FloatArray, area: float, center: float, sigma: float) -> FloatArray:
    """Area-normalized Gaussian peak."""

    return np.asarray(
        area * np.exp(-0.5 * ((x - center) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi)),
        dtype=np.float64,
    )


def lorentzian(x: FloatArray, area: float, center: float, gamma: float) -> FloatArray:
    """Area-normalized Lorentzian peak, with ``gamma`` equal to half-width."""

    return np.asarray(area * gamma / (np.pi * ((x - center) ** 2 + gamma**2)), dtype=np.float64)


def voigt(x: FloatArray, area: float, center: float, sigma: float, gamma: float) -> FloatArray:
    """Area-normalized Voigt peak using SciPy's normalized profile."""

    return np.asarray(area * voigt_profile(x - center, sigma, gamma), dtype=np.float64)


def detect_peaks(
    temperature: FloatArray,
    signal: FloatArray,
    *,
    prominence: float | None = None,
    distance: int | None = None,
) -> tuple[PeakSeed, ...]:
    """Detect positive peaks and return editable centers in temperature coordinates."""

    if prominence is None:
        span = float(np.max(signal) - np.min(signal))
        prominence = max(span * 0.05, np.finfo(float).eps)
    if prominence <= 0:
        raise ValueError("peak prominence must be positive")
    indices, _ = find_peaks(signal, prominence=prominence, distance=distance)
    return tuple(PeakSeed(center=float(temperature[index])) for index in indices)


def resolve_peak_regions(
    x: FloatArray, seeds: Sequence[PeakSeed]
) -> tuple[tuple[PeakSeed, float, float], ...]:
    """Resolve explicit bounds or non-overlapping midpoint bounds for each seed."""

    if not seeds:
        return ()
    ordered = sorted(seeds, key=lambda item: item.center)
    low, high = float(np.min(x)), float(np.max(x))
    regions: list[tuple[PeakSeed, float, float]] = []
    for index, seed in enumerate(ordered):
        default_left = low if index == 0 else (ordered[index - 1].center + seed.center) / 2
        default_right = (
            high if index == len(ordered) - 1 else (seed.center + ordered[index + 1].center) / 2
        )
        left = default_left if seed.left is None else seed.left
        right = default_right if seed.right is None else seed.right
        if not left < seed.center < right:
            raise ValueError(f"peak bounds must satisfy left < center < right for {seed.center}")
        if left < low or right > high:
            raise ValueError(
                f"peak bounds [{left}, {right}] exceed the measured range [{low}, {high}]"
            )
        regions.append((seed, float(left), float(right)))
    return tuple(regions)


def _model_spec(
    model: PeakModel,
    region_x: FloatArray,
    region_y: FloatArray,
    center: float,
) -> tuple[ModelFunction, list[float], tuple[list[float], list[float]], tuple[str, ...]]:
    width = float(np.max(region_x) - np.min(region_x))
    unique_x = np.unique(np.sort(region_x))
    if len(unique_x) < 2 or width <= 0:
        raise ValueError("peak fitting requires at least two distinct temperatures")
    x_step = max(float(np.min(np.diff(unique_x))), np.finfo(float).eps)
    positive_area = max(float(trapezoid(np.maximum(region_y, 0), x=region_x)), x_step)
    scale = max(width / 8, x_step)
    center_bounds = [float(np.min(region_x)), float(np.max(region_x))]
    if model == "gaussian":
        return (
            gaussian,
            [positive_area, center, scale],
            (
                [0.0, center_bounds[0], x_step / 10],
                [np.inf, center_bounds[1], width],
            ),
            ("area", "center", "sigma"),
        )
    if model == "lorentzian":
        return (
            lorentzian,
            [positive_area, center, scale],
            (
                [0.0, center_bounds[0], x_step / 10],
                [np.inf, center_bounds[1], width],
            ),
            ("area", "center", "gamma"),
        )
    if model == "voigt":
        return (
            voigt,
            [positive_area, center, scale, scale],
            (
                [0.0, center_bounds[0], x_step / 10, x_step / 10],
                [np.inf, center_bounds[1], width, width],
            ),
            ("area", "center", "sigma", "gamma"),
        )
    raise ValueError(f"unsupported peak model: {model}")


def _fwhm(model: PeakModel, parameters: NDArray[np.float64]) -> float:
    if model == "gaussian":
        return float(2 * np.sqrt(2 * np.log(2)) * parameters[2])
    if model == "lorentzian":
        return float(2 * parameters[2])
    gaussian_width = 2 * np.sqrt(2 * np.log(2)) * parameters[2]
    lorentz_width = 2 * parameters[3]
    return float(0.5346 * lorentz_width + np.sqrt(0.2166 * lorentz_width**2 + gaussian_width**2))


def peak_parameter_names(model: PeakModel) -> tuple[str, ...]:
    """Return the canonical, stable parameter ordering for a peak model."""

    if model in ("gaussian", "lorentzian"):
        return ("area", "center", "sigma" if model == "gaussian" else "gamma")
    if model == "voigt":
        return ("area", "center", "sigma", "gamma")
    raise ValueError(f"unsupported peak model: {model}")


def evaluate_peak(
    temperature: FloatArray, model: PeakModel, parameters: FloatArray | Sequence[float]
) -> FloatArray:
    """Evaluate one area-normalized component using canonical parameter order."""

    values = tuple(float(value) for value in parameters)
    if model == "gaussian":
        return gaussian(temperature, *values)
    if model == "lorentzian":
        return lorentzian(temperature, *values)
    if model == "voigt":
        return voigt(temperature, *values)
    raise ValueError(f"unsupported peak model: {model}")


def peak_fwhm(model: PeakModel, parameters: FloatArray | Sequence[float]) -> float:
    """Calculate analytic/standard approximate FWHM for one component."""

    return _fwhm(model, np.asarray(parameters, dtype=np.float64))


def fit_peaks(
    temperature: FloatArray,
    signal: FloatArray,
    seeds: Sequence[PeakSeed],
    model: PeakModel,
) -> tuple[tuple[PeakFit, ...], FloatArray]:
    """Fit each bounded peak and return fit metadata plus the summed fitted curve."""

    fits: list[PeakFit] = []
    combined = np.zeros_like(signal, dtype=np.float64)
    for peak_id, (seed, left, right) in enumerate(
        resolve_peak_regions(temperature, seeds), start=1
    ):
        mask = (temperature >= left) & (temperature <= right)
        region_x = np.asarray(temperature[mask], dtype=np.float64)
        region_y = np.asarray(signal[mask], dtype=np.float64)
        if len(region_x) < 6:
            raise ValueError(f"peak {peak_id} region has fewer than six observations")
        sort_order = np.argsort(region_x)
        region_x = region_x[sort_order]
        region_y = region_y[sort_order]
        active_model = seed.model or model
        function, initial, bounds, names = _model_spec(
            active_model, region_x, region_y, seed.center
        )
        fitted, covariance = curve_fit(
            function,
            region_x,
            region_y,
            p0=initial,
            bounds=bounds,
            maxfev=50_000,
        )
        predicted = function(region_x, *fitted)
        residuals = region_y - predicted
        rss = float(np.sum(residuals**2))
        dof = len(region_y) - len(fitted)
        total = float(np.sum((region_y - np.mean(region_y)) ** 2))
        r_squared = float(1 - rss / total) if total > 0 else (1.0 if rss == 0 else np.nan)
        errors = np.sqrt(np.maximum(np.diag(covariance), 0))
        center = float(fitted[1])
        peak_height = float(function(np.array([center]), *fitted)[0])
        parameters = dict(zip(names, (float(value) for value in fitted), strict=True))
        standard_errors = dict(zip(names, (float(value) for value in errors), strict=True))
        fits.append(
            PeakFit(
                peak_id=peak_id,
                model=active_model,
                center=center,
                area=float(fitted[0]),
                height=peak_height,
                fwhm=_fwhm(active_model, fitted),
                left=left,
                right=right,
                parameters=parameters,
                standard_errors=standard_errors,
                covariance=np.asarray(covariance, dtype=np.float64),
                statistics=FitStatistics(
                    rss=rss,
                    rmse=float(np.sqrt(rss / len(region_y))),
                    r_squared=r_squared,
                    degrees_of_freedom=dof,
                ),
            )
        )
        combined += function(temperature, *fitted)
    return tuple(fits), combined
