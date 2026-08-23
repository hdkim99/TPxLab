from __future__ import annotations

import numpy as np
import pytest

from tpxlab.baseline import als_baseline, linear_baseline, polynomial_baseline
from tpxlab.preprocessing import smooth_signal


def test_linear_baseline_recovers_line() -> None:
    x = np.linspace(0, 10, 101)
    expected = 2 + 0.3 * x
    assert np.allclose(linear_baseline(x, expected), expected, atol=1e-12)


def test_polynomial_baseline_recovers_quadratic() -> None:
    x = np.linspace(-2, 2, 101)
    expected = 1 + 0.2 * x + 0.05 * x**2
    actual = polynomial_baseline(x, expected, degree=2)
    assert np.allclose(actual, expected, atol=1e-12)


def test_als_tracks_constant_under_positive_peak() -> None:
    x = np.linspace(-5, 5, 301)
    signal = 3 + 8 * np.exp(-(x**2))
    baseline = als_baseline(signal, smoothness=1e6, asymmetry=0.001, iterations=20)
    assert np.median(np.abs(baseline - 3)) < 0.08


def test_smoothing_validates_window_and_does_not_mutate() -> None:
    signal = np.array([0.0, 1.0, 4.0, 1.0, 0.0])
    original = signal.copy()
    smoothed = smooth_signal(signal, 5, 2)
    assert np.array_equal(signal, original)
    assert not np.shares_memory(signal, smoothed)
    with pytest.raises(ValueError, match="odd"):
        smooth_signal(signal, 4, 2)
