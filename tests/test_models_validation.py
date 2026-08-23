from __future__ import annotations

import numpy as np
import pytest

from tpxlab.models import RawData
from tpxlab.validation import DataValidationError, validate_raw_data


def test_raw_data_copies_and_locks_input() -> None:
    source = np.arange(6.0)
    raw = RawData(source, source + 300, source + 1)
    source[0] = 999
    assert raw.time[0] == 0
    with pytest.raises(ValueError):
        raw.signal[0] = 4


def test_validation_rejects_duplicate_time() -> None:
    raw = RawData(
        np.array([0, 1, 1, 3, 4], dtype=float),
        np.arange(5.0) + 300,
        np.ones(5),
    )
    with pytest.raises(DataValidationError, match="duplicate"):
        validate_raw_data(raw)


def test_validation_rejects_incompatible_units() -> None:
    raw = RawData(np.arange(5.0), np.arange(5.0), np.ones(5), time_unit="gram")
    with pytest.raises(DataValidationError, match="unit"):
        validate_raw_data(raw)


def test_validation_reports_irregular_sampling_and_temperature() -> None:
    raw = RawData(
        np.array([0.0, 1.0, 2.0, 5.0, 6.0]),
        np.array([300.0, 310.0, 305.0, 320.0, 330.0]),
        np.ones(5),
    )
    codes = {issue.code for issue in validate_raw_data(raw)}
    assert codes == {"IRREGULAR_SAMPLING", "NON_MONOTONIC_TEMPERATURE"}
