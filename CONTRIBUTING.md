# Contributing

Thank you for helping make temperature-programmed analysis reproducible.

## Before opening an issue

Use the dataset-compatibility or scientific-result form when applicable. Never upload
unpublished, confidential, proprietary, licensed, identifying, or sensitive research
data to a public issue. Prefer a minimal synthetic reproducer or sanitized headers.

## Development checks

Create a focused branch, add tests for behavioral and scientific changes, and run:

```bash
ruff format --check .
ruff check .
mypy src
pytest
python -m build
```

## Scientific changes

A change to baseline transformation, smoothing, peak integration, component model,
constraints, fitting residuals, uncertainty, or calibration must document:

- its definition/equation, coordinate, units, assumptions, and bounds;
- a primary reference or DOI when relevant;
- whether existing numerical results change and why;
- an independent benchmark plus normal, boundary, invalid, and regression cases; and
- the impact on API, CLI, GUI controls, figures, and exports.

`pytest` passing alone does not establish scientific correctness. Do not modify raw
arrays in place, infer chemistry or peak assignments from sample names, or treat a high
R² as proof of identifiability. Public-data-derived fixtures must record source,
license, checksum, and reduction method. Never commit credentials, private paths, or
unlicensed source files.

The DGX CI jobs deliberately skip fork pull requests. Maintainers must review external
changes before reproducing them on a same-repository branch; do not weaken that boundary.
