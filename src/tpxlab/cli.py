"""Command-line interface for reproducible batch analysis."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from tpxlab import __version__
from tpxlab.configuration import load_component_configuration
from tpxlab.export import export_bundle
from tpxlab.io import ColumnMapping, load_raw_data
from tpxlab.models import (
    AnalysisSettings,
    BaselineMethod,
    FitMode,
    IntegrationMethod,
    PeakModel,
    PeakPolarity,
    PeakSeed,
)
from tpxlab.pipeline import AnalysisService
from tpxlab.plotting import save_figure


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tpxlab",
        description="Reproducible TPx signal analysis with explicit units and settings.",
    )
    parser.add_argument("--version", action="version", version=f"TPxLab {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="analyze a CSV/XLSX TPx dataset")
    analyze.add_argument("input", type=Path)
    analyze.add_argument("--output", type=Path, required=True, help=".xlsx file or CSV directory")
    analyze.add_argument("--figure", type=Path)
    analyze.add_argument("--sheet", default="0")
    analyze.add_argument("--time-column")
    analyze.add_argument("--temperature-column")
    analyze.add_argument("--signal-column")
    analyze.add_argument("--time-unit", default="second")
    analyze.add_argument("--temperature-unit", default="degC")
    analyze.add_argument("--signal-unit", default="millivolt")
    analyze.add_argument("--baseline", choices=("linear", "polynomial", "als"), default="als")
    analyze.add_argument(
        "--peak-polarity",
        choices=("positive", "negative"),
        default="positive",
        help=(
            "detector response direction: positive uses signal-baseline; "
            "negative uses baseline-signal"
        ),
    )
    analyze.add_argument("--polynomial-degree", type=int, default=2)
    analyze.add_argument("--endpoint-fraction", type=float, default=0.1)
    analyze.add_argument("--als-lambda", type=float, default=1.0e6)
    analyze.add_argument("--als-asymmetry", type=float, default=0.01)
    analyze.add_argument("--als-iterations", type=int, default=10)
    analyze.add_argument("--smoothing-window", type=int)
    analyze.add_argument("--smoothing-order", type=int, default=3)
    analyze.add_argument("--prominence", type=float)
    analyze.add_argument("--distance", type=int)
    analyze.add_argument("--model", choices=("gaussian", "lorentzian", "voigt"), default="gaussian")
    analyze.add_argument(
        "--fit-mode",
        choices=("independent", "global"),
        help="independent bounded fits or one simultaneous global residual",
    )
    analyze.add_argument(
        "--components-config",
        type=Path,
        help="strict org.tpxlab.components/0.2-draft JSON component constraints",
    )
    analyze.add_argument("--integration", choices=("trapezoid", "simpson"), default="trapezoid")
    analyze.add_argument(
        "--peak-center",
        type=float,
        action="append",
        help="manual center; repeat for multiple peaks",
    )
    analyze.add_argument("--calibration-value", type=float)
    analyze.add_argument("--calibration-unit")
    analyze.add_argument("--sample-mass-value", type=float)
    analyze.add_argument("--sample-mass-unit")
    analyze.add_argument("--quantification-unit", default="millimole / gram")

    subparsers.add_parser("gui", help="launch the desktop GUI")
    return parser


def _sheet_value(value: str) -> str | int:
    try:
        return int(value)
    except ValueError:
        return value


def _mapping(args: argparse.Namespace) -> ColumnMapping | None:
    supplied = (args.time_column, args.temperature_column, args.signal_column)
    if all(value is None for value in supplied):
        return None
    if any(value is None for value in supplied):
        raise ValueError("time, temperature, and signal columns must be supplied together")
    return ColumnMapping(
        time=cast(str, args.time_column),
        temperature=cast(str, args.temperature_column),
        signal=cast(str, args.signal_column),
    )


def _analyze(args: argparse.Namespace) -> int:
    component_configuration = (
        load_component_configuration(args.components_config)
        if args.components_config is not None
        else None
    )
    if component_configuration is not None and args.peak_center:
        raise ValueError("--components-config and --peak-center cannot be used together")
    fit_mode = cast(
        FitMode,
        args.fit_mode
        or (component_configuration.fit_mode if component_configuration is not None else None)
        or "independent",
    )
    raw = load_raw_data(
        args.input,
        _mapping(args),
        sheet=_sheet_value(args.sheet),
        time_unit=args.time_unit,
        temperature_unit=args.temperature_unit,
        signal_unit=args.signal_unit,
    )
    settings = AnalysisSettings(
        baseline_method=cast(BaselineMethod, args.baseline),
        peak_polarity=cast(PeakPolarity, args.peak_polarity),
        polynomial_degree=args.polynomial_degree,
        endpoint_fraction=args.endpoint_fraction,
        als_lambda=args.als_lambda,
        als_asymmetry=args.als_asymmetry,
        als_iterations=args.als_iterations,
        smoothing_window=args.smoothing_window,
        smoothing_order=args.smoothing_order,
        peak_prominence=args.prominence,
        peak_distance=args.distance,
        peak_model=cast(PeakModel, args.model),
        fit_mode=fit_mode,
        integration_method=cast(IntegrationMethod, args.integration),
        calibration_value=args.calibration_value,
        calibration_unit=args.calibration_unit,
        sample_mass_value=args.sample_mass_value,
        sample_mass_unit=args.sample_mass_unit,
        quantification_unit=args.quantification_unit,
    )
    seeds = component_configuration.components if component_configuration is not None else None
    if component_configuration is None and args.peak_center:
        seeds = tuple(PeakSeed(center=value) for value in args.peak_center)
    result = AnalysisService().analyze(raw, settings, seeds)
    destination = export_bundle(result, args.output)
    if args.figure is not None:
        save_figure(result, args.figure)
    print(
        f"Analyzed {len(raw.time)} observations; {len(result.fits)} peaks; "
        f"{len(result.qc_issues)} QC issues. Exported {destination}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; errors remain non-zero and visible to automation."""

    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "gui":
        from tpxlab.gui import main as gui_main

        return gui_main([])
    try:
        return _analyze(args)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
