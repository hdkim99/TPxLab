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
parameter is the integral with respect to temperature. Positive area/width bounds are
enforced. Fits use SciPy bounded nonlinear least squares and report covariance,
parameter standard errors, RSS, RMSE, R², and degrees of freedom.

Gaussian and Lorentzian have parameter order `(area, center, sigma|gamma)`; Voigt has
`(area, center, sigma, gamma)`. Voigt FWHM uses the Olivero-Longbothum approximation;
Gaussian and Lorentzian FWHM values are analytic.

### Simultaneous global mode

For components `f_k(x; theta_k)`, global mode solves one problem over all observations:

`min_theta sum_i [y_i - sum_k f_k(x_i; theta_k)]^2`

using `scipy.optimize.least_squares` with bounded trust-region reflective optimization.
Area and width parameters are positive. A fixed parameter is removed from the free
vector. A named shared `sigma` or `gamma` occupies one free-vector position used by all
members; the intersection of their bounds must be nonempty. Mixed Gaussian, Lorentzian,
and Voigt components are allowed. Free-vector ordering is deterministic and exported.

The complete model reports RSS, RMSE, R², observations, free-parameter count, degrees of
freedom, Jacobian rank and condition number, active bounds, optimizer status, and the
global covariance matrix. Covariance is mathematically `RSS/dof * (J.T J)^-1` and is
computed only for a full-rank Jacobian with positive degrees of freedom. Rank deficiency
or invalid covariance validation yields explicit unavailable (NaN) uncertainties. A
bound-active result is labeled
boundary-limited because an unconstrained local covariance can be misleading there.
Numerical rank uses singular values above
`sqrt(machine epsilon) * largest singular value`; this finite-difference-aware cutoff is
included in exports as `rank_tolerance`.

The implementation constructs covariance from the Jacobian SVD rather than directly
inverting `J.T J`, symmetrizes it, and verifies finite positive-semidefinite eigenvalues
within a `sqrt(machine epsilon)` relative tolerance. Numerically valid tiny negative
eigenvalues are clipped to zero; an invalid covariance is exported as NaN with
`covariance_valid = false` and an explicit QC issue.

These diagnostics describe local numerical identifiability; they do not prove unique
physical interpretation. Closely coincident components, weak components, excessive model
complexity, or broad parameter bounds can remain ill-conditioned. Users must inspect the
component sum and residual and justify model/bound/shared-width assumptions.

### Independent compatibility mode

Independent mode retains the v0.1 behavior: each user-bounded or midpoint-bounded region
is fitted separately. Its sum is plotted for convenience but is not overlapping
deconvolution. Global-only fixed/shared/center/width constraints are rejected rather than
silently ignored.

## Numerical integration and quantification

Peak bounds are expressed in temperature, but detector area is numerically integrated
against measured **time**, not sample index. Trapezoid and Simpson methods both receive
the actual time coordinates, so irregular intervals are respected. Consequently the
area unit is `signal_unit × time_unit`.

Independent mode integrates the observed signal inside each resolved region. Global mode
integrates each fitted component separately across the measured interval, or inside
explicit user bounds, which avoids double-counting an overlapped observed region. Export
field `integration_source` distinguishes `observed_region` from `fitted_component`.

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

The test suite independently checks exact and noisy recovery of two to three overlapping
components, mixed model families, scaling, fixed/shared constraints, invalid bounds,
rank deficiency, insufficient degrees of freedom, boundary uncertainty, sampling-density
stability, irregular-time integration, unit scaling/dimensional errors, raw immutability,
GUI/service call paths, export provenance, and explicit stoichiometry.
