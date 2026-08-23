"""Baseline estimators for temperature-programmed signals.

All functions return a new array and never alter the measured signal. Linear and
polynomial baselines use the leading/trailing fractions as baseline anchors unless an
explicit boolean anchor mask is supplied. ALS implements the asymmetric least-squares
method of Eilers and Boelens using a second-difference smoothness penalty.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy import sparse
from scipy.sparse.linalg import spsolve

from tpxlab.models import BaselineMethod, FloatArray


def _anchors(
    length: int, endpoint_fraction: float, mask: NDArray[np.bool_] | None
) -> NDArray[np.bool_]:
    if mask is not None:
        result = np.asarray(mask, dtype=np.bool_)
        if result.shape != (length,):
            raise ValueError("anchor mask must have the same length as the signal")
        if np.count_nonzero(result) < 2:
            raise ValueError("at least two baseline anchors are required")
        return result
    if not 0 < endpoint_fraction <= 0.5:
        raise ValueError("endpoint_fraction must be in (0, 0.5]")
    count = max(2, int(np.ceil(length * endpoint_fraction)))
    result = np.zeros(length, dtype=np.bool_)
    result[:count] = True
    result[-count:] = True
    return result


def linear_baseline(
    x: FloatArray,
    signal: FloatArray,
    *,
    endpoint_fraction: float = 0.1,
    anchor_mask: NDArray[np.bool_] | None = None,
) -> FloatArray:
    """Fit a straight line to selected baseline anchor observations."""

    selected = _anchors(len(signal), endpoint_fraction, anchor_mask)
    coefficients = np.polyfit(x[selected], signal[selected], deg=1)
    return np.asarray(np.polyval(coefficients, x), dtype=np.float64)


def polynomial_baseline(
    x: FloatArray,
    signal: FloatArray,
    *,
    degree: int = 2,
    endpoint_fraction: float = 0.1,
    anchor_mask: NDArray[np.bool_] | None = None,
) -> FloatArray:
    """Fit a polynomial to selected baseline anchor observations."""

    if degree < 1 or degree > 6:
        raise ValueError("polynomial degree must be between 1 and 6")
    selected = _anchors(len(signal), endpoint_fraction, anchor_mask)
    if np.count_nonzero(selected) <= degree:
        raise ValueError("baseline anchor count must exceed polynomial degree")
    coefficients = np.polyfit(x[selected], signal[selected], deg=degree)
    return np.asarray(np.polyval(coefficients, x), dtype=np.float64)


def als_baseline(
    signal: FloatArray,
    *,
    smoothness: float = 1.0e6,
    asymmetry: float = 0.01,
    iterations: int = 10,
) -> FloatArray:
    """Estimate a smooth lower envelope using asymmetric least squares.

    The minimized objective is ``sum(w * (y-z)^2) + lambda * sum((D2 z)^2)``.
    Small ``asymmetry`` values down-weight observations above the current baseline,
    which is appropriate for positive detector peaks.
    """

    if smoothness <= 0:
        raise ValueError("ALS smoothness must be positive")
    if not 0 < asymmetry < 1:
        raise ValueError("ALS asymmetry must be in (0, 1)")
    if iterations < 1:
        raise ValueError("ALS iterations must be at least one")
    size = len(signal)
    if size < 3:
        raise ValueError("ALS requires at least three observations")
    second_difference = sparse.diags(
        diagonals=(np.ones(size - 2), -2 * np.ones(size - 2), np.ones(size - 2)),
        offsets=(0, 1, 2),
        shape=(size - 2, size),
        format="csc",
    )
    penalty = smoothness * (second_difference.T @ second_difference)
    weights = np.ones(size, dtype=np.float64)
    baseline = np.array(signal, dtype=np.float64, copy=True)
    for _ in range(iterations):
        weight_matrix = sparse.spdiags(weights, 0, size, size)
        baseline = np.asarray(spsolve(weight_matrix + penalty, weights * signal), dtype=np.float64)
        weights = np.where(signal > baseline, asymmetry, 1.0 - asymmetry)
    return baseline


def estimate_baseline(
    x: FloatArray,
    signal: FloatArray,
    method: BaselineMethod,
    *,
    polynomial_degree: int = 2,
    endpoint_fraction: float = 0.1,
    als_lambda: float = 1.0e6,
    als_asymmetry: float = 0.01,
    als_iterations: int = 10,
    anchor_mask: NDArray[np.bool_] | None = None,
) -> FloatArray:
    """Dispatch to a named baseline method with validated parameters."""

    if method == "linear":
        return linear_baseline(
            x, signal, endpoint_fraction=endpoint_fraction, anchor_mask=anchor_mask
        )
    if method == "polynomial":
        return polynomial_baseline(
            x,
            signal,
            degree=polynomial_degree,
            endpoint_fraction=endpoint_fraction,
            anchor_mask=anchor_mask,
        )
    if method == "als":
        return als_baseline(
            signal,
            smoothness=als_lambda,
            asymmetry=als_asymmetry,
            iterations=als_iterations,
        )
    raise ValueError(f"unsupported baseline method: {method}")
