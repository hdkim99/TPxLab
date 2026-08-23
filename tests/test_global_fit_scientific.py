from __future__ import annotations

import numpy as np
import pytest

from tpxlab.global_fit import fit_peaks_global
from tpxlab.models import PeakSeed
from tpxlab.peaks import gaussian, lorentzian, voigt


def _overlapping_gaussian_seeds(*, shared: bool = False) -> tuple[PeakSeed, PeakSeed]:
    shared_values = (
        {"shared_width_group": "thermal", "shared_width_parameter": "sigma"} if shared else {}
    )
    return (
        PeakSeed(
            326,
            240,
            450,
            model="gaussian",
            center_lower=305,
            center_upper=345,
            width_lower=5,
            width_upper=45,
            **shared_values,
        ),
        PeakSeed(
            369,
            240,
            450,
            model="gaussian",
            center_lower=350,
            center_upper=390,
            width_lower=5,
            width_upper=45,
            **shared_values,
        ),
    )


@pytest.mark.scientific
def test_global_noiseless_fit_recovers_two_overlapping_gaussians() -> None:
    x = np.linspace(200, 500, 801)
    observed = gaussian(x, 250, 330, 25) + gaussian(x, 160, 365, 18)
    result = fit_peaks_global(x, observed, _overlapping_gaussian_seeds(), "gaussian")

    assert [(fit.center, fit.area, fit.parameters["sigma"]) for fit in result.fits] == [
        pytest.approx((330, 250, 25), rel=1e-8),
        pytest.approx((365, 160, 18), rel=1e-8),
    ]
    assert np.max(np.abs(result.combined_signal - observed)) < 1e-9
    assert np.allclose(sum(result.component_signals), result.combined_signal)
    assert result.diagnostics.statistics.r_squared == pytest.approx(1.0, abs=1e-12)
    assert result.diagnostics.jacobian_rank == result.diagnostics.n_free_parameters == 6
    assert result.diagnostics.identifiable
    assert result.diagnostics.covariance_valid
    covariance_eigenvalues = np.linalg.eigvalsh(result.diagnostics.covariance)
    covariance_tolerance = np.sqrt(np.finfo(float).eps) * max(
        float(np.max(np.abs(covariance_eigenvalues))), np.finfo(float).tiny
    )
    assert np.min(covariance_eigenvalues) >= -covariance_tolerance
    assert result.diagnostics.parameter_order == (
        "component.1.area",
        "component.1.center",
        "component.1.sigma",
        "component.2.area",
        "component.2.center",
        "component.2.sigma",
    )


@pytest.mark.scientific
def test_global_noisy_mixed_models_recover_three_components() -> None:
    rng = np.random.default_rng(20260823)
    x = np.linspace(220, 470, 701)
    clean = gaussian(x, 100, 310, 12) + lorentzian(x, 80, 345, 9) + voigt(x, 120, 385, 10, 5)
    observed = clean + rng.normal(0, 0.0015, len(x))
    seeds = (
        PeakSeed(307, 235, 450, "gaussian", 295, 325, 3, 25),
        PeakSeed(347, 235, 450, "lorentzian", 330, 360, 3, 25),
        PeakSeed(389, 235, 450, "voigt", 370, 400, 3, 25),
    )
    result = fit_peaks_global(x, observed, seeds, "gaussian")

    assert [fit.model for fit in result.fits] == ["gaussian", "lorentzian", "voigt"]
    assert [fit.center for fit in result.fits] == pytest.approx([310, 345, 385], abs=0.1)
    assert [fit.area for fit in result.fits] == pytest.approx([100, 80, 120], rel=0.01)
    assert result.fits[0].parameters["sigma"] == pytest.approx(12, rel=0.01)
    assert result.fits[1].parameters["gamma"] == pytest.approx(9, rel=0.01)
    assert result.fits[2].parameters["sigma"] == pytest.approx(10, rel=0.03)
    assert result.fits[2].parameters["gamma"] == pytest.approx(5, rel=0.05)
    assert result.diagnostics.statistics.r_squared > 0.999


@pytest.mark.scientific
def test_global_fit_area_scales_but_location_and_width_do_not() -> None:
    x = np.linspace(200, 500, 601)
    observed = gaussian(x, 250, 330, 25) + gaussian(x, 160, 365, 18)
    base = fit_peaks_global(x, observed, _overlapping_gaussian_seeds(), "gaussian")
    scaled = fit_peaks_global(x, 7.5 * observed, _overlapping_gaussian_seeds(), "gaussian")

    assert [fit.area for fit in scaled.fits] == pytest.approx(
        [7.5 * fit.area for fit in base.fits], rel=1e-7
    )
    assert [fit.center for fit in scaled.fits] == pytest.approx(
        [fit.center for fit in base.fits], abs=1e-7
    )
    assert [fit.fwhm for fit in scaled.fits] == pytest.approx(
        [fit.fwhm for fit in base.fits], rel=1e-7
    )


@pytest.mark.scientific
def test_fixed_center_and_shared_sigma_use_one_validated_parameter() -> None:
    x = np.linspace(220, 470, 701)
    observed = gaussian(x, 110, 320, 14) + gaussian(x, 90, 355, 14)
    first, second = _overlapping_gaussian_seeds(shared=True)
    seeds = (
        PeakSeed(
            center=320,
            left=first.left,
            right=first.right,
            model=first.model,
            center_lower=310,
            center_upper=330,
            width_lower=5,
            width_upper=30,
            fixed_parameters={"center": 320},
            shared_width_group=first.shared_width_group,
            shared_width_parameter=first.shared_width_parameter,
        ),
        PeakSeed(
            center=357,
            left=second.left,
            right=second.right,
            model=second.model,
            center_lower=340,
            center_upper=370,
            width_lower=5,
            width_upper=30,
            shared_width_group=second.shared_width_group,
            shared_width_parameter=second.shared_width_parameter,
        ),
    )
    result = fit_peaks_global(x, observed, seeds, "gaussian")

    assert result.fits[0].center == 320
    assert result.fits[0].standard_errors["center"] == 0
    assert result.fits[0].parameters["sigma"] == pytest.approx(14, rel=1e-8)
    assert result.fits[1].parameters["sigma"] == pytest.approx(14, rel=1e-8)
    assert result.fits[0].standard_errors["sigma"] == pytest.approx(
        result.fits[1].standard_errors["sigma"]
    )
    assert result.diagnostics.parameter_order.count("shared.thermal.sigma") == 1
    assert result.diagnostics.n_free_parameters == 4


@pytest.mark.parametrize(
    ("seed", "message"),
    [
        (PeakSeed(320, center_lower=330, center_upper=310), "center bounds"),
        (PeakSeed(320, width_lower=0, width_upper=10), "width bounds"),
        (PeakSeed(320, fixed_parameters={"area": -1}), "area must be positive"),
        (
            PeakSeed(
                320,
                model="gaussian",
                shared_width_group="bad",
                shared_width_parameter="gamma",
            ),
            "has no gamma",
        ),
        (PeakSeed(320, fixed_parameters={"not_a_parameter": 1}), "unsupported"),
    ],
)
def test_global_fit_rejects_physical_or_model_invalid_constraints(
    seed: PeakSeed, message: str
) -> None:
    x = np.linspace(250, 400, 101)
    with pytest.raises(ValueError, match=message):
        fit_peaks_global(x, gaussian(x, 10, 320, 10), [seed], "gaussian")


def test_shared_width_bounds_must_have_a_nonempty_intersection() -> None:
    x = np.linspace(250, 450, 301)
    y = gaussian(x, 10, 320, 8) + gaussian(x, 12, 360, 15)
    seeds = (
        PeakSeed(
            320,
            width_lower=5,
            width_upper=10,
            shared_width_group="g",
            shared_width_parameter="sigma",
        ),
        PeakSeed(
            360,
            width_lower=12,
            width_upper=20,
            shared_width_group="g",
            shared_width_parameter="sigma",
        ),
    )
    with pytest.raises(ValueError, match="incompatible bounds"):
        fit_peaks_global(x, y, seeds, "gaussian")


@pytest.mark.scientific
def test_rank_deficiency_is_reported_without_invented_uncertainty() -> None:
    x = np.linspace(250, 450, 401)
    y = gaussian(x, 100, 350, 15)
    duplicate = PeakSeed(
        350,
        270,
        430,
        fixed_parameters={"center": 350, "sigma": 15},
    )
    result = fit_peaks_global(x, y, [duplicate, duplicate], "gaussian")

    assert result.diagnostics.jacobian_rank == 1
    assert result.diagnostics.n_free_parameters == 2
    assert result.diagnostics.rank_tolerance > 0
    assert not result.diagnostics.identifiable
    assert not result.diagnostics.covariance_valid
    assert "rank-deficient" in result.diagnostics.uncertainty_status
    assert np.isnan(result.diagnostics.covariance).all()
    assert all(np.isnan(fit.standard_errors["area"]) for fit in result.fits)


def test_too_few_observations_are_rejected_before_optimization() -> None:
    x = np.linspace(0, 4, 5)
    y = gaussian(x, 10, 1.5, 0.5) + gaussian(x, 8, 2.5, 0.5)
    seeds = (PeakSeed(1.5, 0, 4), PeakSeed(2.5, 0, 4))
    with pytest.raises(ValueError, match="positive degrees of freedom"):
        fit_peaks_global(x, y, seeds, "gaussian")


@pytest.mark.scientific
def test_parameter_recovery_is_stable_across_sampling_density() -> None:
    def fitted(count: int) -> list[tuple[float, float, float]]:
        x = np.linspace(200, 500, count)
        y = gaussian(x, 250, 330, 25) + gaussian(x, 160, 365, 18)
        result = fit_peaks_global(x, y, _overlapping_gaussian_seeds(), "gaussian")
        return [(fit.center, fit.area, fit.parameters["sigma"]) for fit in result.fits]

    assert np.asarray(fitted(301)) == pytest.approx(np.asarray(fitted(1201)), rel=1e-7, abs=1e-7)


def test_boundary_solution_marks_uncertainty_as_boundary_limited() -> None:
    x = np.linspace(250, 400, 401)
    y = gaussian(x, 100, 300, 12)
    result = fit_peaks_global(
        x,
        y,
        [PeakSeed(304, center_lower=300, center_upper=320, width_lower=5, width_upper=25)],
        "gaussian",
    )
    assert result.fits[0].center == pytest.approx(300, abs=1e-6)
    assert "component.1.center" in result.diagnostics.active_bounds
    assert result.fits[0].at_boundary
    assert "boundary-limited" in result.diagnostics.uncertainty_status
