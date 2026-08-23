"""Explicit stoichiometric reduction-degree calculation.

The module intentionally accepts only user-supplied amounts and a consumption
coefficient. It does not infer oxidation states, sample formulas, or reactions.
"""

from __future__ import annotations

from dataclasses import dataclass

from pint import DimensionalityError

from tpxlab.quantification import UREG


@dataclass(frozen=True)
class ReductionDegree:
    measured_amount_mol: float
    expected_amount_mol: float
    percent: float


def calculate_reduction_degree(
    *,
    measured_value: float,
    measured_unit: str,
    reducible_amount_value: float,
    reducible_amount_unit: str,
    consumption_coefficient: float,
) -> ReductionDegree:
    """Compare measured consumption with explicit stoichiometric consumption.

    ``consumption_coefficient`` is mol consumed gas per mol supplied reducible entity.
    Values above 100% are returned rather than clipped because they are diagnostically
    useful and may reveal calibration or stoichiometry errors.
    """

    if reducible_amount_value <= 0 or consumption_coefficient <= 0:
        raise ValueError("reducible amount and consumption coefficient must be positive")
    try:
        measured = (measured_value * UREG(measured_unit)).to("mole")
        reducible = (reducible_amount_value * UREG(reducible_amount_unit)).to("mole")
    except DimensionalityError as exc:
        raise ValueError(
            f"stoichiometry inputs must have amount-of-substance units: {exc}"
        ) from exc
    expected = reducible * consumption_coefficient
    return ReductionDegree(
        measured_amount_mol=float(measured.magnitude),
        expected_amount_mol=float(expected.magnitude),
        percent=float(100 * measured.magnitude / expected.magnitude),
    )
