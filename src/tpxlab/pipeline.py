"""Application service orchestrating the scientific analysis pipeline."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from tpxlab.baseline import estimate_baseline
from tpxlab.global_fit import fit_peaks_global
from tpxlab.integration import integrate_component_signals, integrate_peaks
from tpxlab.models import (
    AnalysisResult,
    AnalysisSettings,
    PeakSeed,
    PreparedData,
    QCIssue,
    QuantifiedPeak,
    RawData,
)
from tpxlab.peaks import detect_peaks, evaluate_peak, fit_peaks, peak_parameter_names
from tpxlab.polarity import (
    correct_detector_signal,
    orient_detector_signal,
    restore_detector_baseline,
)
from tpxlab.preprocessing import smooth_signal
from tpxlab.quantification import quantify_peaks
from tpxlab.validation import validate_raw_data


class AnalysisService:
    """Single application entry point used by API, CLI, and GUI."""

    def prepare(self, raw: RawData, settings: AnalysisSettings) -> PreparedData:
        """Validate, baseline-correct, and optionally smooth without mutating raw data."""

        issues = validate_raw_data(raw)
        oriented_signal = orient_detector_signal(raw.signal, settings.peak_polarity)
        oriented_baseline = estimate_baseline(
            raw.time,
            oriented_signal,
            settings.baseline_method,
            polynomial_degree=settings.polynomial_degree,
            endpoint_fraction=settings.endpoint_fraction,
            als_lambda=settings.als_lambda,
            als_asymmetry=settings.als_asymmetry,
            als_iterations=settings.als_iterations,
        )
        baseline = restore_detector_baseline(oriented_baseline, settings.peak_polarity)
        corrected = correct_detector_signal(raw.signal, baseline, settings.peak_polarity)
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
        global_diagnostics = None
        if active_settings.fit_mode == "global":
            global_result = fit_peaks_global(
                raw.temperature,
                prepared.processed_signal,
                active_seeds,
                active_settings.peak_model,
            )
            fits = global_result.fits
            component_signals = global_result.component_signals
            fitted_signal = global_result.combined_signal
            residual_signal = global_result.residual_signal
            global_diagnostics = global_result.diagnostics
        elif active_settings.fit_mode == "independent":
            if any(
                seed.center_lower is not None
                or seed.center_upper is not None
                or seed.width_lower is not None
                or seed.width_upper is not None
                or bool(seed.fixed_parameters)
                or seed.shared_width_group is not None
                or seed.shared_width_parameter is not None
                for seed in active_seeds
            ):
                raise ValueError(
                    "center/width constraints and fixed/shared parameters require fit_mode='global'"
                )
            fits, fitted_signal = fit_peaks(
                raw.temperature,
                prepared.processed_signal,
                active_seeds,
                active_settings.peak_model,
            )
            component_signals = tuple(
                evaluate_peak(
                    raw.temperature,
                    fit.model,
                    [fit.parameters[name] for name in peak_parameter_names(fit.model)],
                )
                for fit in fits
            )
            residual_signal = np.asarray(
                prepared.processed_signal - fitted_signal, dtype=np.float64
            )
        else:
            raise ValueError(f"unsupported fit mode: {active_settings.fit_mode}")
        if active_settings.fit_mode == "global":
            integrated = integrate_component_signals(
                raw.time,
                raw.temperature,
                component_signals,
                active_seeds,
                fits,
                active_settings.integration_method,
            )
        else:
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
        if global_diagnostics is not None:
            if global_diagnostics.statistics.r_squared < 0.9:
                issues.append(
                    QCIssue(
                        code="POOR_GLOBAL_FIT",
                        severity="warning",
                        message=(
                            "global model has R-squared "
                            f"{global_diagnostics.statistics.r_squared:.4g}"
                        ),
                    )
                )
            if not global_diagnostics.identifiable:
                issues.append(
                    QCIssue(
                        code="NONIDENTIFIABLE_GLOBAL_FIT",
                        severity="warning",
                        message=(
                            f"Jacobian rank {global_diagnostics.jacobian_rank} is below "
                            f"{global_diagnostics.n_free_parameters} free parameters; "
                            "parameter uncertainties are unavailable"
                        ),
                    )
                )
            elif not global_diagnostics.covariance_valid:
                issues.append(
                    QCIssue(
                        code="INVALID_GLOBAL_COVARIANCE",
                        severity="warning",
                        message=(
                            "global Jacobian is full rank but its covariance is non-finite "
                            "or not positive semidefinite; uncertainties are unavailable"
                        ),
                    )
                )
            if global_diagnostics.active_bounds:
                issues.append(
                    QCIssue(
                        code="FIT_PARAMETER_AT_BOUND",
                        severity="warning",
                        message=(
                            "optimizer solution reached bounds for: "
                            + ", ".join(global_diagnostics.active_bounds)
                        ),
                    )
                )
        else:
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
            residual_signal=residual_signal,
            component_signals=component_signals,
            global_fit=global_diagnostics,
        )
