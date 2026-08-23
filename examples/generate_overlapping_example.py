"""Regenerate the licensed synthetic overlapping TPx example and actual fit figures."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from tpxlab.configuration import COMPONENT_SCHEMA
from tpxlab.io import load_raw_data
from tpxlab.models import AnalysisSettings, PeakSeed
from tpxlab.peaks import gaussian, lorentzian, voigt
from tpxlab.pipeline import AnalysisService
from tpxlab.plotting import analysis_figure


def component_seeds() -> tuple[PeakSeed, ...]:
    return (
        PeakSeed(
            332,
            220,
            540,
            model="gaussian",
            center_lower=310,
            center_upper=350,
            width_lower=5,
            width_upper=35,
        ),
        PeakSeed(
            373,
            220,
            540,
            model="lorentzian",
            center_lower=355,
            center_upper=390,
            width_lower=4,
            width_upper=25,
        ),
        PeakSeed(
            414,
            220,
            540,
            model="voigt",
            center_lower=395,
            center_upper=430,
            width_lower=4,
            width_upper=28,
        ),
    )


def configuration_payload() -> dict[str, object]:
    components = []
    for seed in component_seeds():
        components.append(
            {
                "center": seed.center,
                "left": seed.left,
                "right": seed.right,
                "model": seed.model,
                "center_lower": seed.center_lower,
                "center_upper": seed.center_upper,
                "width_lower": seed.width_lower,
                "width_upper": seed.width_upper,
                "fixed_parameters": {},
            }
        )
    return {
        "schema": COMPONENT_SCHEMA,
        "fit_mode": "global",
        "components": components,
    }


def main() -> int:
    project = Path(__file__).resolve().parents[1]
    rng = np.random.default_rng(20260823)
    temperature = np.linspace(150, 650, 1001)
    time = 2 * (temperature - temperature[0])
    baseline = 0.12 + 0.00003 * time
    component_1 = gaussian(temperature, 92, 335, 18)
    component_2 = lorentzian(temperature, 58, 372, 10)
    component_3 = voigt(temperature, 112, 410, 13, 7)
    signal = baseline + component_1 + component_2 + component_3
    signal += rng.normal(0, 0.0015, len(signal))

    dataset = project / "examples" / "overlapping_tpr.csv"
    pd.DataFrame({"time": time, "temperature": temperature, "signal": signal}).to_csv(
        dataset, index=False, float_format="%.9g"
    )
    configuration = project / "examples" / "overlapping_components.json"
    configuration.write_text(json.dumps(configuration_payload(), indent=2) + "\n", encoding="utf-8")

    result = AnalysisService().analyze(
        load_raw_data(dataset),
        AnalysisSettings(baseline_method="linear", fit_mode="global"),
        component_seeds(),
    )
    figure = analysis_figure(result)
    figure.savefig(project / "docs" / "tpxlab-global-deconvolution.png", dpi=180)
    figure.set_size_inches(12.8, 6.4)
    figure.savefig(project / "docs" / "tpxlab-social-preview.png", dpi=100)
    diagnostics = result.global_fit
    if diagnostics is None or not diagnostics.identifiable:
        raise RuntimeError("example global fit was unexpectedly non-identifiable")
    print(
        f"Generated {dataset.name}: R2={diagnostics.statistics.r_squared:.8f}, "
        f"rank={diagnostics.jacobian_rank}/{diagnostics.n_free_parameters}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
