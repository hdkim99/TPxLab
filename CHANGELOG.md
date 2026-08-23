# Changelog

## 0.2.0 - Unreleased

- Add genuine simultaneous global deconvolution over one summed residual with mixed
  Gaussian, Lorentzian, and Voigt components.
- Add positive-area/width and center bounds, fixed parameters, named shared widths,
  deterministic parameter ordering, and strict JSON component configuration.
- Report global RSS/RMSE/R²/dof, Jacobian rank/condition, active bounds, covariance and
  explicit uncertainty/identifiability status.
- Connect global constraints through API, CLI, GUI, figures, Excel/CSV exports, and the
  reproducible overlapping example while retaining independent-fit compatibility.
- Change the interchange identifier to the explicitly experimental
  `org.tpxlab.analysis/0.2-draft` contract.

## 0.1.1 - 2026-08-23

- Narrow unit-validation exception handling to expected Pint and parser failures.
- Add undefined-unit, invalid-syntax, and unexpected-registry-failure regression tests.
- Use Node 24 GitHub Actions and document installation from signed release assets.

## 0.1.0 - 2026-08-23

- Initial public release with raw-preserving preprocessing, three baseline methods,
  peak detection, Gaussian/Lorentzian/Voigt fitting, integration, unit-aware
  quantification, CLI, Tkinter GUI, plots, and CSV/XLSX exports.
