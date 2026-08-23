from __future__ import annotations

import numpy as np
import pytest

from tpxlab import ReductionDegree, calculate_reduction_degree
from tpxlab.integration import integrate_peaks
from tpxlab.models import IntegratedPeak, PeakSeed
from tpxlab.peaks import gaussian
from tpxlab.quantification import QuantificationError, quantify_peaks


@pytest.mark.scientific
def test_trapezoid_uses_irregular_time_coordinates() -> None:
    time = np.array([0.0, 0.1, 0.4, 1.0, 2.0, 4.0])
    temperature = np.linspace(300, 500, len(time))
    signal = 2 * time
    peak = integrate_peaks(time, temperature, signal, [PeakSeed(400)], "trapezoid")[0]
    assert peak.area == pytest.approx(16.0)


@pytest.mark.scientific
def test_integration_stable_when_sampling_density_changes() -> None:
    def area(count: int) -> float:
        time = np.linspace(0, 20, count)
        temperature = 300 + 10 * time
        signal = gaussian(time, 30, 10, 1.5)
        return integrate_peaks(time, temperature, signal, [PeakSeed(400)], "simpson")[0].area

    assert area(201) == pytest.approx(30.0, rel=1e-8)
    assert area(2001) == pytest.approx(area(201), rel=1e-8)


def test_quantification_converts_area_and_mass_units() -> None:
    peaks = [IntegratedPeak(1, 400, 300, 500, 2500, "trapezoid")]
    quantified = quantify_peaks(
        peaks,
        area_unit="millivolt * second",
        calibration_value=2,
        calibration_unit="micromole / (millivolt * second)",
        sample_mass_value=500,
        sample_mass_unit="milligram",
        output_unit="millimole / gram",
    )
    assert quantified[0].value == pytest.approx(10.0)


def test_quantification_rejects_dimensionally_invalid_calibration() -> None:
    peaks = [IntegratedPeak(1, 400, 300, 500, 1, "trapezoid")]
    with pytest.raises(QuantificationError, match="incompatible"):
        quantify_peaks(
            peaks,
            area_unit="millivolt * second",
            calibration_value=1,
            calibration_unit="kelvin",
            sample_mass_value=1,
            sample_mass_unit="gram",
        )


def test_explicit_stoichiometry_and_unclipped_sanity_result() -> None:
    result = calculate_reduction_degree(
        measured_value=2.2,
        measured_unit="millimole",
        reducible_amount_value=1,
        reducible_amount_unit="millimole",
        consumption_coefficient=2,
    )
    assert result.expected_amount_mol == pytest.approx(0.002)
    assert result.percent == pytest.approx(110)
    assert isinstance(result, ReductionDegree)
