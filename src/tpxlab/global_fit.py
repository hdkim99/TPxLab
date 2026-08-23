"""Simultaneous constrained fitting of overlapping peak components."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from scipy.integrate import trapezoid
from scipy.optimize import least_squares

from tpxlab.models import (
    FitStatistics,
    FloatArray,
    GlobalFitDiagnostics,
    PeakFit,
    PeakModel,
    PeakSeed,
)
from tpxlab.peaks import evaluate_peak, peak_fwhm, peak_parameter_names, resolve_peak_regions


@dataclass(frozen=True)
class GlobalFitResult:
    """Numerical outputs from one simultaneous least-squares problem."""

    fits: tuple[PeakFit, ...]
    component_signals: tuple[FloatArray, ...]
    combined_signal: FloatArray
    residual_signal: FloatArray
    diagnostics: GlobalFitDiagnostics


@dataclass(frozen=True)
class _Component:
    peak_id: int
    seed: PeakSeed
    model: PeakModel
    left: float
    right: float
    names: tuple[str, ...]
    initial: Mapping[str, float]
    lower: Mapping[str, float]
    upper: Mapping[str, float]


@dataclass
class _ParameterLayout:
    order: list[str]
    initial: list[float]
    lower: list[float]
    upper: list[float]
    component_keys: list[dict[str, str | None]]
    fixed: list[dict[str, float]]


def _finite_float(value: float, label: str) -> float:
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _component_specs(
    x: FloatArray,
    y: FloatArray,
    seeds: Sequence[PeakSeed],
    default_model: PeakModel,
) -> tuple[_Component, ...]:
    if not seeds:
        return ()
    unique_x = np.unique(np.sort(x))
    if len(unique_x) < 2:
        raise ValueError("global fitting requires at least two distinct temperatures")
    x_step = float(np.min(np.diff(unique_x)))
    span = float(np.max(unique_x) - np.min(unique_x))
    if x_step <= 0 or span <= 0:
        raise ValueError("global fitting requires a positive temperature span")

    specs: list[_Component] = []
    shared_groups: dict[str, str] = {}
    for peak_id, (seed, left, right) in enumerate(resolve_peak_regions(x, seeds), start=1):
        model = seed.model or default_model
        names = peak_parameter_names(model)
        fixed = {
            name: _finite_float(value, f"peak {peak_id} fixed {name}")
            for name, value in seed.fixed_parameters.items()
        }
        unknown = set(fixed).difference(names)
        if unknown:
            raise ValueError(
                f"peak {peak_id} has fixed parameters unsupported by {model}: {sorted(unknown)}"
            )
        if fixed.get("area", 1.0) <= 0:
            raise ValueError(f"peak {peak_id} fixed area must be positive")
        for width_name in ("sigma", "gamma"):
            if width_name in fixed and fixed[width_name] <= 0:
                raise ValueError(f"peak {peak_id} fixed {width_name} must be positive")

        if (seed.shared_width_group is None) != (seed.shared_width_parameter is None):
            raise ValueError(
                f"peak {peak_id} must set shared_width_group and shared_width_parameter together"
            )
        if seed.shared_width_parameter is not None:
            width_parameter = seed.shared_width_parameter
            if width_parameter not in names:
                raise ValueError(
                    f"peak {peak_id} model {model} has no {width_parameter} parameter to share"
                )
            if width_parameter in fixed:
                raise ValueError(
                    f"peak {peak_id} cannot both fix and share {width_parameter}"
                )
            assert seed.shared_width_group is not None
            prior = shared_groups.setdefault(seed.shared_width_group, width_parameter)
            if prior != width_parameter:
                raise ValueError(
                    f"shared group {seed.shared_width_group!r} mixes {prior} and {width_parameter}"
                )

        center_lower = left if seed.center_lower is None else _finite_float(
            seed.center_lower, f"peak {peak_id} center_lower"
        )
        center_upper = right if seed.center_upper is None else _finite_float(
            seed.center_upper, f"peak {peak_id} center_upper"
        )
        if not center_lower < center_upper:
            raise ValueError(f"peak {peak_id} center bounds must satisfy lower < upper")
        if center_lower < left or center_upper > right:
            raise ValueError(
                f"peak {peak_id} center bounds must lie within its integration region"
            )
        if not center_lower <= seed.center <= center_upper:
            raise ValueError(f"peak {peak_id} initial center lies outside its center bounds")

        width_lower = x_step / 10 if seed.width_lower is None else _finite_float(
            seed.width_lower, f"peak {peak_id} width_lower"
        )
        width_upper = span if seed.width_upper is None else _finite_float(
            seed.width_upper, f"peak {peak_id} width_upper"
        )
        if width_lower <= 0 or not width_lower < width_upper:
            raise ValueError(
                f"peak {peak_id} width bounds must satisfy 0 < lower < upper"
            )

        mask = (x >= left) & (x <= right)
        region_x = np.asarray(x[mask], dtype=np.float64)
        region_y = np.asarray(y[mask], dtype=np.float64)
        if len(region_x) < 2:
            raise ValueError(f"peak {peak_id} integration region has fewer than two observations")
        positive_area = float(trapezoid(np.maximum(region_y, 0), x=region_x))
        area_initial = max(positive_area, float(np.max(np.maximum(region_y, 0))) * x_step)
        area_initial = max(area_initial, np.finfo(float).eps)
        width_initial = min(max((right - left) / 8, width_lower * 1.01), width_upper * 0.99)
        initial = {"area": area_initial, "center": float(seed.center)}
        area_floor = max(np.finfo(float).tiny, np.finfo(float).eps * area_initial)
        lower = {"area": area_floor, "center": center_lower}
        upper = {"area": np.inf, "center": center_upper}
        for name in names[2:]:
            initial[name] = width_initial
            lower[name] = width_lower
            upper[name] = width_upper
        for name, value in fixed.items():
            lower_bound = lower[name]
            upper_bound = upper[name]
            if not lower_bound <= value <= upper_bound:
                raise ValueError(
                    f"peak {peak_id} fixed {name}={value} is outside [{lower_bound}, {upper_bound}]"
                )
            initial[name] = value
        specs.append(
            _Component(
                peak_id=peak_id,
                seed=seed,
                model=model,
                left=left,
                right=right,
                names=names,
                initial=initial,
                lower=lower,
                upper=upper,
            )
        )
    return tuple(specs)


def _layout(components: Sequence[_Component]) -> _ParameterLayout:
    layout = _ParameterLayout([], [], [], [], [], [])
    key_index: dict[str, int] = {}
    for component in components:
        keys: dict[str, str | None] = {}
        fixed_values: dict[str, float] = {}
        for name in component.names:
            if name in component.seed.fixed_parameters:
                keys[name] = None
                fixed_values[name] = float(component.seed.fixed_parameters[name])
                continue
            if name == component.seed.shared_width_parameter:
                assert component.seed.shared_width_group is not None
                key = f"shared.{component.seed.shared_width_group}.{name}"
            else:
                key = f"component.{component.peak_id}.{name}"
            keys[name] = key
            if key not in key_index:
                key_index[key] = len(layout.order)
                layout.order.append(key)
                layout.initial.append(float(component.initial[name]))
                layout.lower.append(float(component.lower[name]))
                layout.upper.append(float(component.upper[name]))
            else:
                index = key_index[key]
                new_lower = max(layout.lower[index], float(component.lower[name]))
                new_upper = min(layout.upper[index], float(component.upper[name]))
                if not new_lower < new_upper:
                    raise ValueError(f"shared parameter {key} has incompatible bounds")
                layout.lower[index] = new_lower
                layout.upper[index] = new_upper
                layout.initial[index] = min(
                    max(layout.initial[index], new_lower * 1.001), new_upper * 0.999
                )
        layout.component_keys.append(keys)
        layout.fixed.append(fixed_values)
    return layout


def _parameter_values(
    vector: FloatArray,
    component: _Component,
    keys: Mapping[str, str | None],
    fixed: Mapping[str, float],
    key_index: Mapping[str, int],
) -> FloatArray:
    values = []
    for name in component.names:
        key = keys[name]
        values.append(fixed[name] if key is None else float(vector[key_index[key]]))
    return np.asarray(values, dtype=np.float64)


def fit_peaks_global(
    temperature: FloatArray,
    signal: FloatArray,
    seeds: Sequence[PeakSeed],
    default_model: PeakModel,
) -> GlobalFitResult:
    """Fit all components by minimizing one total residual vector.

    The free-vector layout is deterministic and exported in diagnostics. Fixed values
    are omitted from the vector; compatible shared width values occupy one vector slot.
    """

    x = np.asarray(temperature, dtype=np.float64)
    y = np.asarray(signal, dtype=np.float64)
    if x.shape != y.shape or x.ndim != 1:
        raise ValueError("temperature and signal must be equal-length one-dimensional arrays")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("global fitting requires finite temperature and signal values")
    components = _component_specs(x, y, seeds, default_model)
    if not components:
        empty = np.zeros_like(y)
        stats = FitStatistics(0.0, 0.0, np.nan, len(y))
        diagnostics = GlobalFitDiagnostics(
            statistics=stats,
            n_observations=len(y),
            n_free_parameters=0,
            jacobian_rank=0,
            condition_number=np.nan,
            identifiable=True,
            uncertainty_status="no components",
            optimizer_status=0,
            optimizer_message="no components were supplied",
            parameter_order=(),
            active_bounds=(),
            covariance=np.empty((0, 0), dtype=np.float64),
        )
        return GlobalFitResult((), (), empty, y.copy(), diagnostics)

    layout = _layout(components)
    n_free = len(layout.order)
    degrees_of_freedom = len(y) - n_free
    if n_free == 0:
        raise ValueError("global fitting requires at least one free parameter")
    if degrees_of_freedom <= 0:
        raise ValueError(
            f"global fitting has {len(y)} observations but {n_free} free parameters; "
            "positive degrees of freedom are required"
        )
    key_index = {key: index for index, key in enumerate(layout.order)}

    def component_curves(vector: FloatArray) -> tuple[FloatArray, ...]:
        return tuple(
            evaluate_peak(
                x,
                component.model,
                _parameter_values(
                    vector,
                    component,
                    layout.component_keys[index],
                    layout.fixed[index],
                    key_index,
                ),
            )
            for index, component in enumerate(components)
        )

    def residual(vector: FloatArray) -> FloatArray:
        curves = component_curves(vector)
        return np.asarray(np.sum(curves, axis=0) - y, dtype=np.float64)

    optimized = least_squares(
        residual,
        np.asarray(layout.initial, dtype=np.float64),
        bounds=(
            np.asarray(layout.lower, dtype=np.float64),
            np.asarray(layout.upper, dtype=np.float64),
        ),
        method="trf",
        x_scale="jac",
        ftol=1.0e-13,
        xtol=1.0e-13,
        gtol=1.0e-13,
        max_nfev=100_000,
    )
    if not optimized.success:
        raise RuntimeError(
            f"global optimizer failed (status {optimized.status}): {optimized.message}"
        )
    curves = component_curves(np.asarray(optimized.x, dtype=np.float64))
    combined = np.asarray(np.sum(curves, axis=0), dtype=np.float64)
    observed_residual = np.asarray(y - combined, dtype=np.float64)
    rss = float(np.sum(observed_residual**2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = float(1 - rss / total) if total > 0 else (1.0 if rss == 0 else np.nan)
    statistics = FitStatistics(
        rss=rss,
        rmse=float(np.sqrt(rss / len(y))),
        r_squared=r_squared,
        degrees_of_freedom=degrees_of_freedom,
    )

    jacobian = np.asarray(optimized.jac, dtype=np.float64)
    rank = int(np.linalg.matrix_rank(jacobian))
    identifiable = rank == n_free
    condition_number = float(np.linalg.cond(jacobian))
    covariance_failure = False
    if identifiable:
        try:
            covariance = np.asarray(
                np.linalg.inv(jacobian.T @ jacobian) * rss / degrees_of_freedom,
                dtype=np.float64,
            )
        except np.linalg.LinAlgError:
            covariance = np.full((n_free, n_free), np.nan, dtype=np.float64)
            covariance_failure = True
            identifiable = False
    else:
        covariance = np.full((n_free, n_free), np.nan, dtype=np.float64)
    active_names: list[str] = []
    for index, name in enumerate(layout.order):
        value = float(optimized.x[index])
        lower = layout.lower[index]
        upper = layout.upper[index]
        scale = max(
            1.0,
            abs(value),
            abs(lower) if np.isfinite(lower) else 0.0,
            abs(upper) if np.isfinite(upper) else 0.0,
        )
        tolerance = np.sqrt(np.finfo(float).eps) * scale
        scipy_active = bool(np.asarray(optimized.active_mask)[index])
        numerically_active = abs(value - lower) <= tolerance or (
            np.isfinite(upper) and abs(upper - value) <= tolerance
        )
        if scipy_active or numerically_active:
            active_names.append(name)
    active_bounds = tuple(active_names)
    if covariance_failure:
        uncertainty_status = "unavailable: covariance matrix inversion failed"
    elif not identifiable:
        uncertainty_status = "unavailable: rank-deficient Jacobian"
    elif active_bounds:
        uncertainty_status = "boundary-limited: local covariance may be unreliable"
    elif not np.all(np.isfinite(covariance)):
        uncertainty_status = "unavailable: non-finite covariance"
        identifiable = False
    else:
        uncertainty_status = "available: local linearized covariance"

    fits: list[PeakFit] = []
    for index, component in enumerate(components):
        parameters_array = _parameter_values(
            np.asarray(optimized.x, dtype=np.float64),
            component,
            layout.component_keys[index],
            layout.fixed[index],
            key_index,
        )
        parameters = dict(zip(component.names, map(float, parameters_array), strict=True))
        component_covariance = np.zeros(
            (len(component.names), len(component.names)), dtype=np.float64
        )
        for row, row_name in enumerate(component.names):
            row_key = layout.component_keys[index][row_name]
            for column, column_name in enumerate(component.names):
                column_key = layout.component_keys[index][column_name]
                if row_key is None or column_key is None:
                    component_covariance[row, column] = 0.0
                else:
                    component_covariance[row, column] = covariance[
                        key_index[row_key], key_index[column_key]
                    ]
        standard_errors = {
            name: (
                0.0
                if layout.component_keys[index][name] is None
                else float(np.sqrt(max(component_covariance[position, position], 0.0)))
            )
            for position, name in enumerate(component.names)
        }
        center = parameters["center"]
        height = float(
            evaluate_peak(
                np.asarray([center], dtype=np.float64), component.model, parameters_array
            )[0]
        )
        component_keys = {
            key for key in layout.component_keys[index].values() if key is not None
        }
        component_at_boundary = any(key in active_bounds for key in component_keys)
        fits.append(
            PeakFit(
                peak_id=component.peak_id,
                model=component.model,
                center=center,
                area=parameters["area"],
                height=height,
                fwhm=peak_fwhm(component.model, parameters_array),
                left=component.left,
                right=component.right,
                parameters=parameters,
                standard_errors=standard_errors,
                covariance=component_covariance,
                statistics=statistics,
                statistics_scope="global",
                uncertainty_status=uncertainty_status,
                at_boundary=component_at_boundary,
            )
        )

    diagnostics = GlobalFitDiagnostics(
        statistics=statistics,
        n_observations=len(y),
        n_free_parameters=n_free,
        jacobian_rank=rank,
        condition_number=condition_number,
        identifiable=identifiable,
        uncertainty_status=uncertainty_status,
        optimizer_status=int(optimized.status),
        optimizer_message=str(optimized.message),
        parameter_order=tuple(layout.order),
        active_bounds=active_bounds,
        covariance=covariance,
    )
    return GlobalFitResult(tuple(fits), curves, combined, observed_residual, diagnostics)
