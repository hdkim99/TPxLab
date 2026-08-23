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
