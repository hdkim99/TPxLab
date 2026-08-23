"""Immutable data models shared by API, CLI, and GUI."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BaselineMethod = Literal["linear", "polynomial", "als"]
PeakModel = Literal["gaussian", "lorentzian", "voigt"]
IntegrationMethod = Literal["trapezoid", "simpson"]


def _immutable_float_array(values: FloatArray) -> FloatArray:
    copied = np.array(values, dtype=np.float64, copy=True)
    copied.setflags(write=False)
    return copied


@dataclass(frozen=True)
class RawData:
    """Unmodified imported TPx channels.

    Arrays are copied and marked read-only so preprocessing can never overwrite the
    measured values implicitly.
    """

    time: FloatArray
    temperature: FloatArray
    signal: FloatArray
    time_unit: str = "second"
    temperature_unit: str = "degC"
    signal_unit: str = "millivolt"
    source: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "time", _immutable_float_array(self.time))
        object.__setattr__(self, "temperature", _immutable_float_array(self.temperature))
        object.__setattr__(self, "signal", _immutable_float_array(self.signal))


@dataclass(frozen=True)
class PeakSeed:
    """User-editable initial peak definition in temperature coordinates."""

    center: float
    left: float | None = None
    right: float | None = None


@dataclass(frozen=True)
class QCIssue:
    code: str
    severity: Literal["warning", "error"]
    message: str


@dataclass(frozen=True)
class FitStatistics:
    rss: float
    rmse: float
    r_squared: float
    degrees_of_freedom: int


@dataclass(frozen=True)
class PeakFit:
    peak_id: int
    model: PeakModel
    center: float
    area: float
    height: float
    fwhm: float
    left: float
    right: float
    parameters: Mapping[str, float]
    standard_errors: Mapping[str, float]
    covariance: FloatArray
    statistics: FitStatistics

    def __post_init__(self) -> None:
        object.__setattr__(self, "covariance", _immutable_float_array(self.covariance))
        object.__setattr__(self, "parameters", dict(self.parameters))
        object.__setattr__(self, "standard_errors", dict(self.standard_errors))


@dataclass(frozen=True)
class IntegratedPeak:
    peak_id: int
    center: float
    left: float
    right: float
    area: float
    method: IntegrationMethod


@dataclass(frozen=True)
class QuantifiedPeak:
    peak_id: int
    value: float
    unit: str


@dataclass(frozen=True)
class AnalysisSettings:
    baseline_method: BaselineMethod = "als"
    polynomial_degree: int = 2
    endpoint_fraction: float = 0.1
    als_lambda: float = 1.0e6
    als_asymmetry: float = 0.01
    als_iterations: int = 10
    smoothing_window: int | None = None
    smoothing_order: int = 3
    peak_prominence: float | None = None
    peak_distance: int | None = None
    peak_model: PeakModel = "gaussian"
    integration_method: IntegrationMethod = "trapezoid"
    calibration_value: float | None = None
    calibration_unit: str | None = None
    sample_mass_value: float | None = None
    sample_mass_unit: str | None = None
    quantification_unit: str = "millimole / gram"


@dataclass(frozen=True)
class PreparedData:
    raw: RawData
    baseline: FloatArray
    corrected_signal: FloatArray
    processed_signal: FloatArray
    qc_issues: tuple[QCIssue, ...]

    def __post_init__(self) -> None:
        for name in ("baseline", "corrected_signal", "processed_signal"):
            object.__setattr__(self, name, _immutable_float_array(getattr(self, name)))


@dataclass(frozen=True)
class AnalysisResult:
    raw: RawData
    baseline: FloatArray
    corrected_signal: FloatArray
    processed_signal: FloatArray
    seeds: tuple[PeakSeed, ...]
    fits: tuple[PeakFit, ...]
    integrated_peaks: tuple[IntegratedPeak, ...]
    quantified_peaks: tuple[QuantifiedPeak, ...]
    qc_issues: tuple[QCIssue, ...]
    settings: AnalysisSettings
    fitted_signal: FloatArray = field(default_factory=lambda: np.array([], dtype=np.float64))

    def __post_init__(self) -> None:
        for name in ("baseline", "corrected_signal", "processed_signal", "fitted_signal"):
            object.__setattr__(self, name, _immutable_float_array(getattr(self, name)))
