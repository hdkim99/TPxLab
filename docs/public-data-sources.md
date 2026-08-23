# Public research data validation sources

This register separates dataset permissions from article permissions and records enough
provenance to detect upstream changes. Public source files are **not** vendored in TPxLab.
Access date for this review: **2026-08-23**.

## TPX-PUB-001 — selected validation source

### Identity and permissions

- Dataset: *Dataset for: Dopant-Controlled Oxygen Vacancy Dynamics Define
  CO2-to-Methanol Catalysis on In2O3*.
- Authors: Matthias Becker, Margareth Baidun, Annelies Landuyt, Agnieszka Kierzkowska,
  Felix Donat, Alexander Kolganov, Evgeny Pidko, Paula Abdala, Alexey Fedorov, and
  Christoph Müller.
- Current dataset DOI: [`10.5281/zenodo.21884075`](https://doi.org/10.5281/zenodo.21884075).
  The concept DOI is `10.5281/zenodo.19450659`. The deposited README still names prior
  version DOI `10.5281/zenodo.19450660`; validation therefore pins the current record and
  file checksum rather than relying on the README DOI alone.
- Dataset license: **CC BY 4.0**. Dataset redistribution and adaptation are permitted with
  attribution, a license link, and indication of changes. TPxLab does not redistribute the
  source archive.
- Article: [*Dopant-controlled oxygen vacancy dynamics define CO2-to-methanol catalysis
  on In2O3*](https://doi.org/10.1038/s41467-026-72876-w), Nature Communications 17,
  6435 (2026).
- Article license: **CC BY-NC-ND 4.0**, distinct from the dataset license. The article can
  be shared non-commercially with attribution but adapted article material cannot be
  redistributed under that license. TPxLab uses only factual protocol and reported-value
  comparisons and does not redistribute article figures.

The Zenodo README describes original instrument files as exported to text-readable
formats. The selected CSVs are actual acquisition exports with detector and sparse MS
channels, not synthetic curves or values digitized from a plot.

### Immutable source identity

Source:
[`08_Figure_5_d_e_f_g_TPR.zip`](https://zenodo.org/api/records/21884075/files/08_Figure_5_d_e_f_g_TPR.zip/content)

- Size: `4,401,662` bytes
- SHA-256: `f1489430b9cf1f664f64ca27a117e26cadb597e6d250ff0ec4c82758578886e8`

| ZIP member | Size (bytes) | SHA-256 | Validation role |
|---|---:|---|---|
| `In2O3_5Sn_CO2_pulses.csv` | 2,665,308 | `c4c6021e8a1ae9210087d46f03e20d103b6f30c97814aa74cdce7b4dbc02627d` | Pulse reference; outside current TPxLab scope |
| `In2O3_5Sn_TPR_5H2Ar.csv` | 1,760,032 | `291e11d5c7aa46849cc98a358b7ca64c36f849e469f1b3524c1a9205f3c5c77f` | TPR validation |
| `In2O3_5Sn_TPR_5H2Ar01CO2.csv` | 2,082,893 | `4a1f66b3a53ae2e617684b2b64bb18737dba6edc97bfef3387392a76acc2ffd5` | TPR/reaction validation |
| `In2O3_5Zr_CO2_pulses.csv` | 2,669,724 | `92c6d9be16559fa02e90b8c37cefb8fd1e24b926e9204800752c9e181ec94a32` | Pulse reference; outside current TPxLab scope |
| `In2O3_5Zr_TPR_5H2Ar.csv` | 1,875,667 | `3c69fabd077049d8434d07a15d6dc01c0b5349be14bac4111c205b8a0fe9b0ad` | TPR validation |
| `In2O3_5Zr_TPR_5H2Ar01CO2.csv` | 2,953,645 | `505f3ad32e7756213016dcef90bc6c5a911ca3fa899666ef7ab26843d75a0485` | TPR/reaction validation |

The machine-readable source and analysis constraints are in
[`public-data-manifest.json`](https://github.com/hdkim99/TPxLab/blob/main/docs/public-data-manifest.json).

### Measured structure and sampling

The four TPR acquisitions contain 14,368–16,665 rows with these principal channels:

```text
timestamp
timedelta (min)
T_C
TCD_signal
TCD_signal/g_cat
```

They also contain asynchronously merged MS scan, mass-channel, sum, and total-pressure
columns. The principal TCD channels have no missing observations, and `timedelta (min)` is
strictly increasing with a median interval of 0.01666667 min, i.e. 1 s. The sparse MS
sampling is approximately 4.07 s and is not analyzed by this TPx validation.

The constant ratios of `TCD_signal` to `TCD_signal/g_cat` imply run-specific masses of
17.7, 20.8, 15.9, and 19.8 mg. This is a provenance check, not an independently supplied
sample-mass calibration. The article describes typical samples of 15–20 mg.

### Paper comparison and protocol discrepancy

Hydrogen consumption is negative-going in the original TCD coordinates. Raw minima in
the explicitly derived 50–940 °C ramp interval compare with the article as follows:

| Run | Paper Tmax (°C) | Observed raw minimum (°C) |
|---|---:|---:|
| In2O3-5Sn, 5% H2/Ar | 577 | 577.05 |
| In2O3-5Sn, 5% H2/Ar + 0.1% CO2 | 598 | 598.18 |
| In2O3-5Zr, 5% H2/Ar | 591 | 591.20 |
| In2O3-5Zr, 5% H2/Ar + 0.1% CO2 | 630 | 631.22 |

The observed Sn shift is 21.13 °C versus the reported 21 °C. The observed Zr shift is
40.02 °C versus the reported rounded value of 39 °C.

Supplementary Table 18 reports a 10 °C min-1 heating rate. In contrast, the measured
`timedelta (min)` and `T_C` channels give 4.97–4.98 °C min-1 between the first observation
at or above 50 °C and the first subsequent observation at or above 940 °C. TPxLab records
this discrepancy and integrates against measured time. It does not replace measured time
with a rate reconstructed from the article.

### Scientific use and limits

The source supplies a raw TCD signal and a mass-normalized signal, but no absolute TCD
calibration factor or uncertainty. Validation therefore reports only detector-coordinate
and relative signal-time areas. It must not report H2 consumption in mmol/g.

The complete acquisition includes low/high-temperature holds and small local temperature
reversals. TPxLab keeps the full acquisition, emits `NON_MONOTONIC_TEMPERATURE`, and uses
explicit peak seeds/bounds. It does not silently select a ramp or smooth the data. The
50–940 °C selection is used only by the opt-in validation script for reported Tmax and
observed heating-rate comparisons, and its exact criteria are recorded in the manifest.

The validation fit uses two empirical Gaussian components in one summed-residual global
optimization. These components exercise polarity propagation, fitting diagnostics,
time-aware integration, and export. They are not assigned to chemical species, and a
full-rank local Jacobian does not establish a unique physical decomposition.

Before adding explicit polarity, the reviewed Sn/H2 acquisition was run through the
legacy positive-only path with a linear baseline and an explicit main-peak seed. At the
raw consumption minimum the corrected value was -2.5299, the fitted positive area
collapsed to `5.4e-23`, global R2 was -0.256, area/center/width were bound-active, and the
Jacobian was rank deficient. This source-based failure established that polarity had to be
part of the scientific settings rather than an undocumented input-file sign change.

Run the opt-in check from a source checkout using either an already downloaded archive or
an explicit network request:

```bash
PYTHONPATH=src python scripts/validate_public_data.py --archive /path/to/08_Figure_5_d_e_f_g_TPR.zip
PYTHONPATH=src python scripts/validate_public_data.py --download
```

Extraction and default exports occur only in a temporary `/tmp/tpxlab-TPX-PUB-001-*`
directory. Use `--output-dir` to retain the generated validation report and CSV exports.
Normal `pytest` never downloads this dataset.

After extracting one reviewed TPR member, the real Tk load, explicit column mapping,
negative-polarity setting, constrained peak table, simultaneous fit, and plot rendering
can be exercised under a display (or `xvfb-run`):

```bash
python tests/gui_widget_smoke.py \
  --public-data /path/to/In2O3_5Sn_TPR_5H2Ar.csv
```

The public headers are deliberately not auto-mapped: the GUI requires the user to select
`timedelta (min)`, `T_C`, and `TCD_signal/g_cat`, avoiding an ambiguous guess among the
many TCD and sparse-MS channels.

## Secondary and conditional candidates

### TPX-PUB-002 — H2-TPR figure-data XLSX

- Dataset: [*Waste-to-energy Valorization of food waste into renewable fuels via
  anaerobic digestion and inline CO2 reforming over Ni-based catalysts*](https://doi.org/10.5281/zenodo.15719085).
- Dataset license: **CC BY 4.0**.
- Article DOI: [`10.1016/j.fuproc.2025.108348`](https://doi.org/10.1016/j.fuproc.2025.108348).
- Article license: **CC BY 4.0**.
- Relevant XLSX: 135,575 bytes; SHA-256
  `4b64d4b90553d238b1f9e5ae205e764a0336a97fb48da59267ce0ec475b7fc50`.
- Level: near-raw final-figure data containing six positive temperature/signal curves,
  877–996 observations each.
- Limitation: no measured time, detector unit, or sample-specific calibration. It is useful
  for positive/global-fit stress testing but not measured-time integration or quantitative
  public-data regression.

### TPX-PUB-003 — H2-TPR and NH3-TPD Origin projects

- Dataset: [*Enhanced low-temperature NH3-SCR performance of Ce/TiO2 modified by Ho
  catalyst*](https://zenodo.org/records/4989086), dataset DOI
  `10.5061/dryad.c86d5m0`.
- Dataset license: **CC0 1.0**; redistribution is permitted without copyright conditions,
  although citation remains scientific best practice.
- Article DOI: [`10.1098/rsos.182120`](https://doi.org/10.1098/rsos.182120).
- Article license: **CC BY 4.0**.
- `Raw data.rar`: 2,445,836 bytes; SHA-256
  `d201201b105dc810ba69013fcccff104a1a6be464d2b82a6952da0136294dedc`.
- Relevant members are actual `H2-TPR.opj` and `NH3-TPD.opj` projects. Their proprietary
  Origin format prevents transparent column and sampling inspection in the supported
  CSV/XLSX path. A provenance-preserving author export is required before use.

### TPX-PUB-004 — Dryad CO/CO2-TPD CSV

- Dataset DOI: [`10.5061/dryad.6wwpzgncd`](https://doi.org/10.5061/dryad.6wwpzgncd),
  **CC0 1.0**.
- Article DOI: [`10.1126/sciadv.adz7504`](https://doi.org/10.1126/sciadv.adz7504),
  **CC BY-NC 4.0** according to the article distribution notice.
- Official metadata lists `6.CO-TPD.csv` (63,916 bytes, SHA-256
  `2623eb8618f850db8d859387b0cad60d7dc43fe0d6e7afc8360c21bfc4f50914`) and
  `13.CO2-TPD.csv` (3,332 bytes, SHA-256
  `df6a7a1360f969f4f452216e1ecefe8ee6ddefd9d86c2fe42ee8153d00c6f348`).
- Conditional because the file endpoint returned HTTP 401/403 during this review and the
  official description gives temperature/signal a.u., not measured time or calibration.

### TPX-PUB-005 — Dryad CO2-TPD XLSX

- Dataset DOI: [`10.5061/dryad.kg76k5b`](https://doi.org/10.5061/dryad.kg76k5b),
  **CC0 1.0**.
- Article DOI: [`10.1098/rsos.190750`](https://doi.org/10.1098/rsos.190750),
  **CC BY 4.0**.
- Relevant XLSX: 41,738 bytes; official MD5
  `1213b3a62883c16427a68233289e187f`; described as raw data for Figure 5.
- Conditional because its file endpoint returned HTTP 401/403 and time/calibration could
  not be inspected.

## Excluded search results

| Source | Dataset/article license distinction | Exclusion reason |
|---|---|---|
| Zenodo 10624754 | Zenodo record CC BY 4.0; linked MDPI article CC BY 4.0 | Article PDF only; no raw TPx table |
| Zenodo 8107273 | Zenodo record CC BY 4.0; article license not independently confirmed | Article PDF only |
| Figshare 28951979 | Figshare asset CC BY-NC 4.0; linked ACS article rights are separate | ZIP contains DFT XYZ structures, not TPx data |
| Figshare 25866112 | Figshare asset CC BY 4.0; article rights are separate | DOCX and figure media only; no raw worksheet |
| Figshare 28970753 | Figshare asset CC BY-NC 4.0; article rights are separate | Supplementary PDF only |
| Figshare 29157313 | Figshare figure CC BY 4.0; article rights are separate | NH3-TPD figure-only record |
| GitHub/OSF search results | No candidate with verified data and article permissions | No licensed, attributable raw time-temperature-signal candidate found |

Licenses attached to a repository dataset do not automatically govern the associated
article, and article licenses do not override the explicitly deposited dataset license.
