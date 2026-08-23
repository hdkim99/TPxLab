# Scientific methods and definitions

## Data preservation

TPxLab copies imported time, temperature, and signal arrays and marks them read-only.
Baseline, corrected, smoothed, fitted, and exported arrays are separate objects. The raw
sheet in an export therefore contains the values received by the analysis service.

## Baselines

- **Linear/polynomial:** least-squares polynomial fit to the first and last 10% of
  observations by default. The fraction and polynomial degree are recorded.
- **Asymmetric least squares (ALS):** minimizes
  `Σ wᵢ(yᵢ-zᵢ)² + λΣ(Δ²zᵢ)²`; weights are updated asymmetrically so positive peaks
  contribute less to the lower envelope. Lambda, asymmetry, and iteration count are
  recorded. This follows the method described by Eilers and Boelens (2005),
  *Baseline Correction with Asymmetric Least Squares Smoothing*.

No baseline is universally correct. Inspect the raw/baseline plot and exported settings.

## Smoothing and detection

Optional smoothing is SciPy's Savitzky-Golay filter with an explicitly validated odd
window and polynomial order. Peak candidates use `scipy.signal.find_peaks` prominence
and distance. Detected centers are initial guesses; GUI and API users can add, update,
or remove them before fitting.

## Parametric fitting

Gaussian, Lorentzian, and Voigt functions are normalized so their fitted `area`
parameter is the integral with respect to temperature. Non-negative area/width bounds
are enforced. Fits use SciPy bounded nonlinear least squares and report covariance,
parameter standard errors, RSS, RMSE, R², and degrees of freedom.

Version 0.1 fits each user-bounded or midpoint-bounded region independently. It does
**not** claim overlapping multi-peak deconvolution. Voigt FWHM uses the standard Olivero-
Longbothum approximation; Gaussian and Lorentzian FWHM values are analytic.

## Numerical integration and quantification

Peak bounds are expressed in temperature, but detector area is numerically integrated
against measured **time**, not sample index. Trapezoid and Simpson methods both receive
the actual time coordinates, so irregular intervals are respected. Consequently the
area unit is `signal_unit × time_unit`.

Quantification evaluates:

`amount / sample mass = integrated area × calibration factor / sample mass`

Pint must be able to reduce that expression to the requested amount-per-mass unit.
Sample mass must be positive. TPxLab does not infer detector response, gas identity,
chemical formula, oxidation state, or stoichiometry.

## Explicit TPR stoichiometry framework

`calculate_reduction_degree` accepts measured gas amount, a user-supplied amount of
reducible entity, and an explicit mol-gas/mol-entity coefficient. It returns the
unclipped percentage so values above 100% remain visible as a possible calibration,
reaction-definition, or data-quality issue.

## Scientific validation

The test suite independently checks exact Gaussian parameter recovery, seeded noisy
recovery, numerical area under irregular sampling, sampling-density stability, unit
scaling, incompatible dimensions, raw immutability, and explicit stoichiometry.

