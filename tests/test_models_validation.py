from __future__ import annotations

import numpy as np
import pytest

from tpxlab import validation
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


def test_validation_rejects_undefined_unit() -> None:
    raw = RawData(
        np.arange(5.0),
        np.arange(5.0),
        np.ones(5),
        signal_unit="definitely_not_a_defined_unit",
    )
    with pytest.raises(DataValidationError, match=r"undefined|defined|unit"):
        validate_raw_data(raw)


def test_validation_rejects_invalid_unit_syntax() -> None:
    raw = RawData(np.arange(5.0), np.arange(5.0), np.ones(5), time_unit="[broken")
    with pytest.raises(DataValidationError, match="invalid"):
        validate_raw_data(raw)


def test_validation_does_not_misclassify_unexpected_registry_bug(monkeypatch) -> None:
    class BrokenRegistry:
        def __call__(self, _unit: str) -> None:
            raise RuntimeError("unexpected registry failure")

    monkeypatch.setattr(validation, "_UREG", BrokenRegistry())
    raw = RawData(np.arange(5.0), np.arange(5.0), np.ones(5))
    with pytest.raises(RuntimeError, match="unexpected registry failure"):
        validate_raw_data(raw)


def test_validation_reports_irregular_sampling_and_temperature() -> None:
    raw = RawData(
        np.array([0.0, 1.0, 2.0, 5.0, 6.0]),
        np.array([300.0, 310.0, 305.0, 320.0, 330.0]),
        np.ones(5),
    )
    codes = {issue.code for issue in validate_raw_data(raw)}
    assert codes == {"IRREGULAR_SAMPLING", "NON_MONOTONIC_TEMPERATURE"}
