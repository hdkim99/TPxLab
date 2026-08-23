from __future__ import annotations

import numpy as np
import pytest

from tpxlab.models import PeakSeed
from tpxlab.peaks import detect_peaks, fit_peaks, gaussian, lorentzian, voigt


@pytest.mark.scientific
def test_noiseless_gaussian_recovers_center_sigma_and_area() -> None:
    temperature = np.linspace(200, 600, 1601)
    signal = gaussian(temperature, area=250.0, center=410.0, sigma=17.0)
    fits, predicted = fit_peaks(
        temperature,
        signal,
        [PeakSeed(center=408.0, left=300.0, right=520.0)],
        "gaussian",
    )
    fit = fits[0]
    assert fit.center == pytest.approx(410.0, abs=1e-7)
    assert fit.parameters["sigma"] == pytest.approx(17.0, rel=1e-7)
    assert fit.area == pytest.approx(250.0, rel=1e-7)
    assert fit.statistics.r_squared == pytest.approx(1.0, abs=1e-12)
    assert np.max(np.abs(predicted - signal)) < 1e-8


@pytest.mark.scientific
def test_seeded_noisy_gaussian_recovers_parameters() -> None:
    rng = np.random.default_rng(20260823)
    temperature = np.linspace(250, 550, 1001)
    clean = gaussian(temperature, area=180.0, center=395.0, sigma=21.0)
    signal = clean + rng.normal(0, 0.002, len(clean))
    fit = fit_peaks(
        temperature,
        signal,
        [PeakSeed(center=400.0, left=300.0, right=500.0)],
        "gaussian",
    )[0][0]
    assert fit.center == pytest.approx(395.0, abs=0.2)
    assert fit.parameters["sigma"] == pytest.approx(21.0, rel=0.01)
    assert fit.area == pytest.approx(180.0, rel=0.01)
    assert fit.statistics.r_squared > 0.999


@pytest.mark.parametrize(
    ("model", "function", "parameters"),
    [
        ("lorentzian", lorentzian, (90.0, 350.0, 12.0)),
        ("voigt", voigt, (90.0, 350.0, 8.0, 5.0)),
    ],
)
def test_supported_profiles_fit_their_own_exact_model(model, function, parameters) -> None:
    x = np.linspace(200, 500, 1201)
    y = function(x, *parameters)
    fit = fit_peaks(x, y, [PeakSeed(350, 230, 470)], model)[0][0]
    assert fit.center == pytest.approx(350.0, abs=1e-5)
    assert fit.area == pytest.approx(90.0, rel=1e-5)
    assert fit.fwhm > 0


def test_peak_detection_returns_physical_coordinate() -> None:
    x = np.linspace(100, 500, 401)
    y = gaussian(x, 50, 320, 8)
    seeds = detect_peaks(x, y, prominence=0.1)
    assert len(seeds) == 1
    assert seeds[0].center == pytest.approx(320)
