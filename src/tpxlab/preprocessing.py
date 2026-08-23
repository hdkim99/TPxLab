"""Optional signal preprocessing that preserves the corrected input array."""

from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter

from tpxlab.models import FloatArray


def smooth_signal(signal: FloatArray, window: int | None, order: int = 3) -> FloatArray:
    """Return a Savitzky-Golay-smoothed copy, or an unchanged copy when disabled."""

    if window is None:
        return np.array(signal, dtype=np.float64, copy=True)
    if window < 3 or window % 2 == 0:
        raise ValueError("smoothing window must be an odd integer of at least three")
    if order < 0 or order >= window:
        raise ValueError("smoothing order must be non-negative and smaller than the window")
    if window > len(signal):
        raise ValueError("smoothing window cannot exceed the signal length")
    return np.asarray(
        savgol_filter(signal, window_length=window, polyorder=order), dtype=np.float64
    )
