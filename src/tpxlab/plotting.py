"""Matplotlib figures for raw, processed, and fitted TPx curves."""

from __future__ import annotations

from pathlib import Path

from matplotlib.figure import Figure

from tpxlab.models import AnalysisResult, PreparedData, RawData


def raw_figure(raw: RawData) -> Figure:
    """Create a raw-curve preview before any analytical transformation."""

    figure = Figure(figsize=(8, 5), constrained_layout=True)
    axis = figure.subplots()
    axis.plot(raw.temperature, raw.signal, color="0.25", label="raw")
    axis.set_xlabel(f"Temperature ({raw.temperature_unit})")
    axis.set_ylabel(f"Signal ({raw.signal_unit})")
    axis.legend()
    return figure


def preparation_figure(prepared: PreparedData) -> Figure:
    """Create a baseline/correction preview before peak fitting."""

    figure = Figure(figsize=(8, 6), constrained_layout=True)
    raw_axis, corrected_axis = figure.subplots(2, 1, sharex=True)
    raw_axis.plot(prepared.raw.temperature, prepared.raw.signal, color="0.25", label="raw")
    raw_axis.plot(prepared.raw.temperature, prepared.baseline, color="tab:orange", label="baseline")
    raw_axis.set_ylabel(f"Signal ({prepared.raw.signal_unit})")
    raw_axis.legend()
    corrected_axis.plot(
        prepared.raw.temperature,
        prepared.corrected_signal,
        color="0.6",
        label="corrected",
    )
    corrected_axis.plot(
        prepared.raw.temperature,
        prepared.processed_signal,
        color="tab:blue",
        label="processed",
    )
    corrected_axis.set_xlabel(f"Temperature ({prepared.raw.temperature_unit})")
    corrected_axis.set_ylabel(f"Corrected signal ({prepared.raw.signal_unit})")
    corrected_axis.legend()
    return figure


def analysis_figure(result: AnalysisResult) -> Figure:
    """Create raw, deconvolution, and residual diagnostics without pyplot state."""

    figure = Figure(figsize=(9, 8), constrained_layout=True)
    raw_axis, processed_axis, residual_axis = figure.subplots(
        3, 1, sharex=True, height_ratios=(1.0, 1.4, 0.6)
    )
    raw_axis.plot(result.raw.temperature, result.raw.signal, color="0.25", label="raw")
    raw_axis.plot(result.raw.temperature, result.baseline, color="tab:orange", label="baseline")
    raw_axis.set_ylabel(f"Signal ({result.raw.signal_unit})")
    raw_axis.legend()
    processed_axis.plot(
        result.raw.temperature, result.processed_signal, color="tab:blue", label="processed"
    )
    if result.fits:
        for fit, component in zip(result.fits, result.component_signals, strict=True):
            processed_axis.plot(
                result.raw.temperature,
                component,
                linewidth=1.1,
                linestyle="--",
                label=f"component {fit.peak_id} ({fit.model})",
            )
        processed_axis.plot(
            result.raw.temperature,
            result.fitted_signal,
            color="black",
            linewidth=1.5,
            label="total fit",
        )
        for fit in result.fits:
            processed_axis.axvline(fit.center, color="0.5", linestyle=":", linewidth=0.8)
    processed_axis.set_ylabel(f"Corrected signal ({result.raw.signal_unit})")
    processed_axis.legend()
    residual_axis.axhline(0, color="0.4", linewidth=0.8)
    residual_axis.plot(
        result.raw.temperature,
        result.residual_signal,
        color="tab:purple",
        linewidth=0.9,
        label="observed - total fit",
    )
    residual_axis.set_xlabel(f"Temperature ({result.raw.temperature_unit})")
    residual_axis.set_ylabel("Residual")
    residual_axis.legend()
    return figure


def save_figure(result: AnalysisResult, path: str | Path, *, dpi: int = 160) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    analysis_figure(result).savefig(destination, dpi=dpi)
    return destination
