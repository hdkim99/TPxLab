"""Explicit detector-signal orientation for positive peak models.

TPxLab's peak functions have positive areas. Detector responses may nevertheless
increase or decrease when an analyte is consumed or desorbed. ``peak_polarity`` makes
that experimental convention explicit instead of silently changing the imported data.
"""

from __future__ import annotations

import numpy as np

from tpxlab.models import FloatArray, PeakPolarity


def orient_detector_signal(signal: FloatArray, polarity: PeakPolarity) -> FloatArray:
    """Orient detector coordinates so peaks point upward during baseline estimation.

    For negative-going peaks, estimating the baseline on ``-signal`` also makes ALS
    track the upper envelope in the original detector coordinate system.
    """

    if polarity == "positive":
        return np.array(signal, dtype=np.float64, copy=True)
    if polarity == "negative":
        return np.asarray(-signal, dtype=np.float64)
    raise ValueError(f"unsupported peak polarity: {polarity}")


def restore_detector_baseline(oriented_baseline: FloatArray, polarity: PeakPolarity) -> FloatArray:
    """Return an oriented baseline to the original detector coordinates."""

    if polarity == "positive":
        return np.array(oriented_baseline, dtype=np.float64, copy=True)
    if polarity == "negative":
        return np.asarray(-oriented_baseline, dtype=np.float64)
    raise ValueError(f"unsupported peak polarity: {polarity}")


def correct_detector_signal(
    signal: FloatArray, baseline: FloatArray, polarity: PeakPolarity
) -> FloatArray:
    """Apply the declared polarity without modifying either input array.

    Positive peaks use ``raw signal - baseline``. Negative peaks use
    ``baseline - raw signal``. The returned peaks therefore have positive area while
    the raw signal and exported baseline remain in original detector coordinates.
    """

    if polarity == "positive":
        return np.asarray(signal - baseline, dtype=np.float64)
    if polarity == "negative":
        return np.asarray(baseline - signal, dtype=np.float64)
    raise ValueError(f"unsupported peak polarity: {polarity}")
