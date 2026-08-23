# TPxLab

> Reproducible global deconvolution and quantification of temperature-programmed catalyst data.

[![CI](https://github.com/hdkim99/TPxLab/actions/workflows/ci.yml/badge.svg)](https://github.com/hdkim99/TPxLab/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/hdkim99/TPxLab/blob/main/LICENSE)

TPxLab turns CSV/XLSX TPR, TPD, and TPO curves into inspectable baseline corrections,
editable peak components, simultaneous mixed-model fits, coordinate-aware integrals,
unit-checked quantities, diagnostics, figures, and reproducible exports. One
`AnalysisService` powers the Python API, CLI, and Tkinter GUI.

![Actual TPxLab global deconvolution of the bundled overlapping example](https://raw.githubusercontent.com/hdkim99/TPxLab/main/docs/tpxlab-global-deconvolution.png)

## Install

Main is the tested `0.2.0` development line and is not yet a GitHub or PyPI release:

```bash
git clone https://github.com/hdkim99/TPxLab.git
cd TPxLab
python -m pip install .
```

The latest immutable release remains `0.1.1` (independent peak fitting):

```bash
python -m pip install \
  https://github.com/hdkim99/TPxLab/releases/download/v0.1.1/tpxlab-0.1.1-py3-none-any.whl
```

TPxLab is not yet published on PyPI. The release workflow is prepared for PyPI Trusted
Publishing but does not contain an API token or password.

The repository social-preview candidate is the
[actual bundled-example result](https://raw.githubusercontent.com/hdkim99/TPxLab/main/docs/tpxlab-social-preview.png),
not a mock interface.

## 30-second global quickstart

From a source checkout:

```bash
tpxlab analyze examples/overlapping_tpr.csv \
  --components-config examples/overlapping_components.json \
  --baseline linear \
  --output examples/output/global-analysis.xlsx \
  --figure examples/output/global-analysis.png

tpxlab-gui
```

The GUI follows: load and map columns/units -> baseline and detect -> add/update/remove
components -> choose model, center/width bounds, fixed/shared width constraints -> fit and
quantify -> inspect components/total/residual -> export. Every edit is passed through the
service to the same scientific core used by the CLI.

## Python API

```python
from tpxlab import AnalysisService, AnalysisSettings, PeakSeed
from tpxlab.io import load_raw_data

raw = load_raw_data("examples/overlapping_tpr.csv")
components = [
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
]
result = AnalysisService().analyze(
    raw,
    AnalysisSettings(baseline_method="linear", fit_mode="global"),
    components,
)
print(result.global_fit.identifiable, result.global_fit.statistics.r_squared)
```

## Support status in v0.2.0

| Capability | Status | Notes |
|---|---|---|
| CSV and XLSX import | Supported | explicit or conservative automatic 3-column mapping |
| Linear, polynomial, ALS baseline | Supported | raw data is copied and read-only |
| Optional Savitzky-Golay smoothing | Supported | parameters exported |
| Peak detection and manual edits | Supported | positive peaks; add/update/remove in GUI |
| Simultaneous global deconvolution | Supported | one summed residual; mixed Gaussian/Lorentzian/Voigt |
| Center/width constraints | Supported | positive areas; validated bounds and fixed parameters |
| Shared width constraint | Supported | named shared `sigma` or `gamma` groups only |
| Identifiability diagnostics | Supported | ordering, dof, rank, condition, active bounds, covariance status |
| Independent bounded fitting | Supported | v0.1-compatible mode; not overlapping deconvolution |
| Trapezoid/Simpson integration | Supported | actual time coordinates, including irregular sampling |
| Calibration + sample-mass quantification | Supported | Pint dimensional validation |
| Explicit reduction degree | Experimental | API only; user supplies stoichiometry |
| Draft interchange metadata | Experimental | `org.tpxlab.analysis/0.2-draft`; no integration adapter yet |
| Asymmetric peaks, automatic model selection | Planned | not implemented |
| TPSR and pulse chemisorption workflows | Planned | not implemented |

## Outputs

XLSX contains Raw, Processed, Peaks, Components, Global_fit, Settings, Metadata, and QC
sheets; a directory destination writes the same layers as CSV. Exports include original
channels, component curves, total curve, residual, exact constraints, parameter ordering,
component parameters/Tmax/area/height/FWHM, local standard errors, component and global
covariance, RSS/RMSE/R²/dof, Jacobian rank, condition number, optimizer status, active
bounds, integration source, units, source file, and QC issues. PNG/SVG/PDF figures include
raw/baseline, components/total, and residual.

## Scientific scope and limitations

- Global mode minimizes one residual vector between the complete processed signal and the
  sum of all components. It is not a sum of separately fitted curves.
- Nonlinear decomposition can be non-unique. A full-rank local Jacobian is necessary, not
  sufficient, for physical uniqueness. Rank-deficient fits report unavailable covariance;
  boundary solutions report boundary-limited uncertainty.
- Reported covariance is the local linearized least-squares approximation. It does not
  replace replicate experiments, profile likelihood, or domain-informed uncertainty.
- A shared `sigma` or `gamma` should be used only when components have a defensible common
  broadening mechanism. TPxLab never decides that assumption automatically.
- Global component quantification integrates each fitted component against measured time.
  Independent mode integrates the observed bounded region. The export labels this source.
- Peak fit `area` is with respect to temperature; calibrated detector integration is with
  respect to time. Both are labeled separately.
- Baseline and model choices remain analytical assumptions requiring residual review.
  TPxLab fits positive peaks and does not infer gas identity, chemistry, oxidation state,
  stoichiometry, or expected consumption.
- Non-monotonic temperature programs are flagged; repeated temperature ranges require
  user review.

Definitions, equations, parameter ordering, and validation details are in
[Scientific methods](https://github.com/hdkim99/TPxLab/blob/main/docs/scientific-methods.md).
The provisional, explicitly non-stable export contract is in
[Interchange metadata](https://github.com/hdkim99/TPxLab/blob/main/docs/interchange.md).

## Related tools

- [Ordifile](https://github.com/hdkim99/ordifile) — chromatographic data standardization.
- [ReactorCheck](https://github.com/hdkim99/ReactorCheck) — catalytic reactor calculation
  and QC.
- [OperandoMerge](https://github.com/hdkim99/OperandoMerge) — heterogeneous experiment
  timeline alignment.

These are independent repositories. Direct cross-project adapters are planned
interoperability, not a current TPxLab feature.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check .
mypy src
pytest
python -m build
twine check dist/*
```

Runtime dependencies use permissive licenses compatible with MIT: NumPy/SciPy/pandas
(BSD), Pint (BSD), Matplotlib (PSF-based), and openpyxl (MIT). See `pyproject.toml` for
the declared dependency set and [CONTRIBUTING.md](https://github.com/hdkim99/TPxLab/blob/main/CONTRIBUTING.md)
for the scientific contribution policy.
