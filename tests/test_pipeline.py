from __future__ import annotations

import numpy as np
import pytest

from tpxlab.models import AnalysisSettings, PeakSeed, RawData
from tpxlab.pipeline import AnalysisService


@pytest.mark.scientific
def test_pipeline_preserves_raw_and_matches_unit_scaling(gaussian_raw: RawData) -> None:
    before = gaussian_raw.signal.copy()
    settings = AnalysisSettings(
        baseline_method="linear",
        peak_model="gaussian",
        calibration_value=1,
        calibration_unit="micromole / (millivolt * second)",
        sample_mass_value=100,
        sample_mass_unit="milligram",
    )
    seed = PeakSeed(400, 300, 500)
    result = AnalysisService().analyze(gaussian_raw, settings, [seed])
    scaled_raw = RawData(
        gaussian_raw.time,
        gaussian_raw.temperature,
        gaussian_raw.signal * 2,
        source="scaled",
    )
    scaled = AnalysisService().analyze(scaled_raw, settings, [seed])
    assert np.array_equal(gaussian_raw.signal, before)
    assert result.raw is gaussian_raw
    assert scaled.integrated_peaks[0].area == pytest.approx(
        2 * result.integrated_peaks[0].area, rel=1e-10
    )
    assert scaled.quantified_peaks[0].value == pytest.approx(
        2 * result.quantified_peaks[0].value, rel=1e-10
    )


def test_pipeline_requires_complete_quantification_configuration(gaussian_raw: RawData) -> None:
    settings = AnalysisSettings(baseline_method="linear", calibration_value=2)
    with pytest.raises(ValueError, match="supplied together"):
        AnalysisService().analyze(gaussian_raw, settings, [PeakSeed(400, 300, 500)])


def test_user_seed_changes_actual_fit_region(gaussian_raw: RawData) -> None:
    settings = AnalysisSettings(baseline_method="linear")
    result = AnalysisService().analyze(
        gaussian_raw, settings, [PeakSeed(center=398, left=350, right=450)]
    )
    assert result.fits[0].left == 350
    assert result.fits[0].right == 450
    assert result.seeds[0].center == 398


@pytest.mark.scientific
def test_global_pipeline_preserves_components_diagnostics_and_integration_source(
    gaussian_raw: RawData,
) -> None:
    before = gaussian_raw.signal.copy()
    settings = AnalysisSettings(
        baseline_method="linear",
        fit_mode="global",
        peak_model="gaussian",
    )
    seed = PeakSeed(
        center=398,
        center_lower=380,
        center_upper=420,
        width_lower=5,
        width_upper=40,
    )
    result = AnalysisService().analyze(gaussian_raw, settings, [seed])

    assert np.array_equal(gaussian_raw.signal, before)
    assert result.global_fit is not None
    assert result.global_fit.identifiable
    assert result.fits[0].statistics_scope == "global"
    assert len(result.component_signals) == 1
    assert np.allclose(result.processed_signal - result.fitted_signal, result.residual_signal)
    assert result.integrated_peaks[0].source == "fitted_component"


def test_independent_mode_does_not_silently_ignore_global_constraints(
    gaussian_raw: RawData,
) -> None:
    seed = PeakSeed(400, 300, 500, fixed_parameters={"sigma": 18})
    with pytest.raises(ValueError, match="require fit_mode='global'"):
        AnalysisService().analyze(
            gaussian_raw,
            AnalysisSettings(baseline_method="linear", fit_mode="independent"),
            [seed],
        )
