"""Application service orchestrating the scientific analysis pipeline."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from tpxlab.baseline import estimate_baseline
from tpxlab.integration import integrate_peaks
from tpxlab.models import (
    AnalysisResult,
    AnalysisSettings,
    PeakSeed,
    PreparedData,
    QCIssue,
    QuantifiedPeak,
    RawData,
)
from tpxlab.peaks import detect_peaks, fit_peaks
from tpxlab.preprocessing import smooth_signal
from tpxlab.quantification import quantify_peaks
from tpxlab.validation import validate_raw_data


class AnalysisService:
    """Single application entry point used by API, CLI, and GUI."""

    def prepare(self, raw: RawData, settings: AnalysisSettings) -> PreparedData:
        """Validate, baseline-correct, and optionally smooth without mutating raw data."""

        issues = validate_raw_data(raw)
        baseline = estimate_baseline(
            raw.time,
            raw.signal,
            settings.baseline_method,
            polynomial_degree=settings.polynomial_degree,
            endpoint_fraction=settings.endpoint_fraction,
            als_lambda=settings.als_lambda,
            als_asymmetry=settings.als_asymmetry,
            als_iterations=settings.als_iterations,
        )
        corrected = np.asarray(raw.signal - baseline, dtype=np.float64)
        processed = smooth_signal(corrected, settings.smoothing_window, settings.smoothing_order)
        return PreparedData(
            raw=raw,
            baseline=baseline,
            corrected_signal=corrected,
            processed_signal=processed,
            qc_issues=issues,
        )

    def detect(self, prepared: PreparedData, settings: AnalysisSettings) -> tuple[PeakSeed, ...]:
        """Detect editable peak candidates from prepared data."""

        return detect_peaks(
            prepared.raw.temperature,
            prepared.processed_signal,
            prominence=settings.peak_prominence,
            distance=settings.peak_distance,
        )

    def analyze(
        self,
        raw: RawData,
        settings: AnalysisSettings | None = None,
        seeds: Sequence[PeakSeed] | None = None,
    ) -> AnalysisResult:
        """Run the complete deterministic pipeline with optional user-edited seeds."""

        active_settings = settings or AnalysisSettings()
        prepared = self.prepare(raw, active_settings)
        active_seeds = tuple(seeds) if seeds is not None else self.detect(prepared, active_settings)
        fits, fitted_signal = fit_peaks(
            raw.temperature, prepared.processed_signal, active_seeds, active_settings.peak_model
        )
        integrated = integrate_peaks(
            raw.time,
            raw.temperature,
            prepared.processed_signal,
            active_seeds,
            active_settings.integration_method,
        )

        calibration_fields = (
            active_settings.calibration_value,
            active_settings.calibration_unit,
            active_settings.sample_mass_value,
            active_settings.sample_mass_unit,
        )
        if any(value is not None for value in calibration_fields) and not all(
            value is not None for value in calibration_fields
        ):
            raise ValueError(
                "calibration value/unit and sample mass value/unit must be supplied together"
            )
        quantified: tuple[QuantifiedPeak, ...] = ()
        if all(value is not None for value in calibration_fields):
            assert active_settings.calibration_value is not None
            assert active_settings.calibration_unit is not None
            assert active_settings.sample_mass_value is not None
            assert active_settings.sample_mass_unit is not None
            quantified = quantify_peaks(
                integrated,
                area_unit=f"{raw.signal_unit} * {raw.time_unit}",
                calibration_value=active_settings.calibration_value,
                calibration_unit=active_settings.calibration_unit,
                sample_mass_value=active_settings.sample_mass_value,
                sample_mass_unit=active_settings.sample_mass_unit,
                output_unit=active_settings.quantification_unit,
            )

        issues = list(prepared.qc_issues)
        for peak in integrated:
            if peak.area < 0:
                issues.append(
                    QCIssue(
                        code="NEGATIVE_PEAK_AREA",
                        severity="warning",
                        message=f"integrated area for peak {peak.peak_id} is negative",
                    )
                )
        for fit in fits:
            if fit.statistics.r_squared < 0.9:
                issues.append(
                    QCIssue(
                        code="POOR_PEAK_FIT",
                        severity="warning",
                        message=(
                            f"peak {fit.peak_id} has R-squared {fit.statistics.r_squared:.4g}"
                        ),
                    )
                )
        for quantified_peak in quantified:
            if quantified_peak.value < 0:
                issues.append(
                    QCIssue(
                        code="NEGATIVE_QUANTIFIED_AMOUNT",
                        severity="warning",
                        message=(
                            f"quantified amount for peak {quantified_peak.peak_id} is negative"
                        ),
                    )
                )
        return AnalysisResult(
            raw=raw,
            baseline=prepared.baseline,
            corrected_signal=prepared.corrected_signal,
            processed_signal=prepared.processed_signal,
            seeds=active_seeds,
            fits=fits,
            integrated_peaks=integrated,
            quantified_peaks=quantified,
            qc_issues=tuple(issues),
            settings=active_settings,
            fitted_signal=fitted_signal,
        )
