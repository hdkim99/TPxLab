"""Reproducible tabular exports for complete analysis results."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from tpxlab.models import AnalysisResult


def result_tables(result: AnalysisResult) -> dict[str, pd.DataFrame]:
    """Convert every result layer to tables without dropping settings or QC."""

    raw = pd.DataFrame(
        {
            "time": result.raw.time,
            "temperature": result.raw.temperature,
            "signal": result.raw.signal,
        }
    )
    processed = pd.DataFrame(
        {
            "time": result.raw.time,
            "temperature": result.raw.temperature,
            "raw_signal": result.raw.signal,
            "baseline": result.baseline,
            "corrected_signal": result.corrected_signal,
            "processed_signal": result.processed_signal,
            "fitted_signal": result.fitted_signal,
        }
    )
    peak_rows: list[dict[str, Any]] = []
    integrated_by_id = {peak.peak_id: peak for peak in result.integrated_peaks}
    quantified_by_id = {peak.peak_id: peak for peak in result.quantified_peaks}
    for fit in result.fits:
        integrated = integrated_by_id[fit.peak_id]
        quantified = quantified_by_id.get(fit.peak_id)
        peak_rows.append(
            {
                "peak_id": fit.peak_id,
                "model": fit.model,
                "Tmax": fit.center,
                "fit_area_signal_temperature": fit.area,
                "height": fit.height,
                "FWHM_temperature": fit.fwhm,
                "left_temperature": fit.left,
                "right_temperature": fit.right,
                "integrated_area_signal_time": integrated.area,
                "integration_method": integrated.method,
                "quantified_value": None if quantified is None else quantified.value,
                "quantified_unit": None if quantified is None else quantified.unit,
                "rss": fit.statistics.rss,
                "rmse": fit.statistics.rmse,
                "r_squared": fit.statistics.r_squared,
                "degrees_of_freedom": fit.statistics.degrees_of_freedom,
                "parameters_json": json.dumps(fit.parameters, sort_keys=True),
                "standard_errors_json": json.dumps(fit.standard_errors, sort_keys=True),
                "covariance_json": json.dumps(fit.covariance.tolist()),
            }
        )
    settings = asdict(result.settings)
    settings_rows = [{"parameter": key, "value": value} for key, value in settings.items()]
    metadata_rows = [
        {"key": "schema", "value": "org.tpxlab.analysis/1.0"},
        {"key": "source_file", "value": result.raw.source},
        {"key": "time_unit", "value": result.raw.time_unit},
        {"key": "temperature_unit", "value": result.raw.temperature_unit},
        {"key": "signal_unit", "value": result.raw.signal_unit},
    ]
    qc_rows = [asdict(issue) for issue in result.qc_issues]
    return {
        "raw": raw,
        "processed": processed,
        "peaks": pd.DataFrame(peak_rows),
        "settings": pd.DataFrame(settings_rows),
        "metadata": pd.DataFrame(metadata_rows),
        "qc": pd.DataFrame(qc_rows, columns=["code", "severity", "message"]),
    }


def export_excel(result: AnalysisResult, path: str | Path) -> Path:
    """Write a multi-sheet XLSX workbook with raw data and full provenance."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(destination, engine="openpyxl") as writer:
        for name, table in result_tables(result).items():
            table.to_excel(writer, sheet_name=name.capitalize(), index=False)
    return destination


def export_csv_bundle(result: AnalysisResult, directory: str | Path) -> Path:
    """Write one CSV per result layer plus machine-readable analysis settings."""

    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    for name, table in result_tables(result).items():
        table.to_csv(destination / f"{name}.csv", index=False)
    return destination


def export_bundle(result: AnalysisResult, destination: str | Path) -> Path:
    """Export XLSX when the suffix is `.xlsx`, otherwise export a CSV directory."""

    path = Path(destination)
    if path.suffix.lower() == ".xlsx":
        return export_excel(result, path)
    if path.suffix:
        raise ValueError("export destination must be an .xlsx file or a directory")
    return export_csv_bundle(result, path)
