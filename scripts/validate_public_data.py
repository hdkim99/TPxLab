#!/usr/bin/env python3
"""Opt-in validation of TPX-PUB-001 without vendoring public research data."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any, cast

import numpy as np
import pandas as pd

from tpxlab.export import export_csv_bundle
from tpxlab.io import ColumnMapping, load_raw_data
from tpxlab.models import AnalysisSettings, PeakModel, PeakSeed
from tpxlab.pipeline import AnalysisService

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "docs" / "public-data-manifest.json"
TMP_ROOT = Path("/tmp")


class PublicDataValidationError(RuntimeError):
    """Raised when a public source differs from the reviewed immutable manifest."""


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for a local file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_zip_member(archive: zipfile.ZipFile, name: str) -> str:
    """Return a streaming SHA-256 digest for one archive member."""

    digest = hashlib.sha256()
    with archive.open(name) as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    """Load the reviewed public-data manifest."""

    with path.open(encoding="utf-8") as stream:
        return cast(dict[str, Any], json.load(stream))


def validate_archive(archive_path: Path, manifest: dict[str, Any]) -> None:
    """Verify archive and member sizes/digests before extraction."""

    archive_spec = manifest["archive"]
    if archive_path.stat().st_size != archive_spec["size_bytes"]:
        raise PublicDataValidationError("archive size does not match the reviewed manifest")
    if sha256_file(archive_path) != archive_spec["sha256"]:
        raise PublicDataValidationError("archive SHA-256 does not match the reviewed manifest")

    expected = {member["path"]: member for member in manifest["members"]}
    with zipfile.ZipFile(archive_path) as archive:
        actual = {info.filename for info in archive.infolist() if not info.is_dir()}
        if actual != set(expected):
            raise PublicDataValidationError("archive member list differs from the manifest")
        for name, member in expected.items():
            info = archive.getinfo(name)
            if info.file_size != member["size_bytes"]:
                raise PublicDataValidationError(f"member size mismatch: {name}")
            if sha256_zip_member(archive, name) != member["sha256"]:
                raise PublicDataValidationError(f"member SHA-256 mismatch: {name}")


def extract_reviewed_members(
    archive_path: Path, manifest: dict[str, Any], destination: Path
) -> None:
    """Extract only reviewed members after rejecting unsafe paths."""

    with zipfile.ZipFile(archive_path) as archive:
        for member in manifest["members"]:
            name = member["path"]
            pure_path = PurePosixPath(name)
            if pure_path.is_absolute() or ".." in pure_path.parts:
                raise PublicDataValidationError(f"unsafe archive member path: {name}")
            output = destination.joinpath(*pure_path.parts)
            output.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, output.open("wb") as target:
                shutil.copyfileobj(source, target)


def _download_source(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "TPxLab-public-validation/0.2"})
    with urllib.request.urlopen(request, timeout=120) as source, destination.open("wb") as target:
        shutil.copyfileobj(source, target)


def _derived_ramp_indices(
    temperature: np.ndarray[Any, np.dtype[np.float64]], manifest: dict[str, Any]
) -> tuple[int, int]:
    criteria = manifest["derived_ramp_selection"]
    starts = np.flatnonzero(temperature >= criteria["start_temperature_degC"])
    if len(starts) == 0:
        raise PublicDataValidationError("derived ramp start temperature is absent")
    start = int(starts[0])
    stops = np.flatnonzero(
        (np.arange(len(temperature)) > start) & (temperature >= criteria["stop_temperature_degC"])
    )
    if len(stops) == 0:
        raise PublicDataValidationError("derived ramp stop temperature is absent")
    return start, int(stops[0])


def _peak_seed(component: dict[str, Any]) -> PeakSeed:
    return PeakSeed(
        center=float(component["center"]),
        left=float(component["left"]),
        right=float(component["right"]),
        model=cast(PeakModel, component["model"]),
        center_lower=float(component["center_lower"]),
        center_upper=float(component["center_upper"]),
        width_lower=float(component["width_lower"]),
        width_upper=float(component["width_upper"]),
    )


def analyze_member(
    path: Path,
    member: dict[str, Any],
    manifest: dict[str, Any],
    export_root: Path,
) -> dict[str, Any]:
    """Validate one complete acquisition and run the actual TPxLab service."""

    frame = pd.read_csv(path)
    missing = set(manifest["required_columns"]) - set(frame.columns)
    if missing:
        raise PublicDataValidationError(f"missing required columns in {path.name}: {missing}")
    if len(frame) != member["expected_rows"]:
        raise PublicDataValidationError(f"row count differs from manifest: {path.name}")

    raw = load_raw_data(
        path,
        ColumnMapping("timedelta (min)", "T_C", "TCD_signal/g_cat"),
        time_unit="minute",
        temperature_unit="degC",
        signal_unit="dimensionless / gram",
    )
    raw_before = raw.signal.copy()
    if np.any(np.diff(raw.time) <= 0):
        raise PublicDataValidationError(f"time is not strictly increasing: {path.name}")

    start, stop = _derived_ramp_indices(raw.temperature, manifest)
    observed_rate = float(
        (raw.temperature[stop] - raw.temperature[start]) / (raw.time[stop] - raw.time[start])
    )
    expected_rate = manifest["derived_ramp_selection"]["expected_observed_rate_degC_per_min"]
    if not expected_rate[0] <= observed_rate <= expected_rate[1]:
        raise PublicDataValidationError(
            f"observed heating rate is outside review bounds: {path.name}"
        )
    ramp_slice = slice(start, stop + 1)
    local_minimum = int(np.argmin(raw.signal[ramp_slice])) + start
    observed_tmax = float(raw.temperature[local_minimum])
    if abs(observed_tmax - member["paper_tmax_degC"]) > 1.5:
        raise PublicDataValidationError(f"paper Tmax comparison failed: {path.name}")

    analysis_spec = manifest["analysis"]
    settings = AnalysisSettings(
        baseline_method="linear",
        peak_polarity="negative",
        fit_mode="global",
        integration_method="trapezoid",
    )
    seeds = tuple(_peak_seed(component) for component in member["components"])
    result = AnalysisService().analyze(raw, settings, seeds)
    if not np.array_equal(raw.signal, raw_before):
        raise PublicDataValidationError(f"raw detector signal was mutated: {path.name}")
    if not np.allclose(result.corrected_signal, result.baseline - raw.signal):
        raise PublicDataValidationError(f"negative polarity formula was not applied: {path.name}")
    if result.settings.peak_polarity != analysis_spec["peak_polarity"]:
        raise PublicDataValidationError(f"polarity setting was not preserved: {path.name}")
    if result.quantified_peaks:
        raise PublicDataValidationError(f"uncalibrated source was quantified: {path.name}")
    if "NON_MONOTONIC_TEMPERATURE" not in {issue.code for issue in result.qc_issues}:
        raise PublicDataValidationError(f"temperature QC warning is missing: {path.name}")
    if result.global_fit is None:
        raise PublicDataValidationError(f"global diagnostics are missing: {path.name}")

    destination = export_csv_bundle(result, export_root / path.stem)
    raw_export = pd.read_csv(destination / "raw.csv")
    processed_export = pd.read_csv(destination / "processed.csv")
    settings_export = pd.read_csv(destination / "settings.csv")
    metadata_export = pd.read_csv(destination / "metadata.csv")
    if not np.array_equal(raw_export["signal"].to_numpy(), raw.signal):
        raise PublicDataValidationError(f"raw export changed detector values: {path.name}")
    if not np.allclose(processed_export["baseline"].to_numpy(), result.baseline):
        raise PublicDataValidationError(
            f"baseline export changed detector coordinates: {path.name}"
        )
    exported_polarity = settings_export.loc[
        settings_export["parameter"] == "peak_polarity", "value"
    ].item()
    transformation = metadata_export.loc[
        metadata_export["key"] == "signal_transformation", "value"
    ].item()
    if exported_polarity != "negative" or transformation != "baseline - raw_signal":
        raise PublicDataValidationError(f"polarity export provenance is incomplete: {path.name}")

    diagnostics = result.global_fit
    return {
        "path": member["path"],
        "rows": len(raw.time),
        "sampling_interval_s_median": float(np.median(np.diff(raw.time)) * 60),
        "derived_ramp_start_index": start,
        "derived_ramp_stop_index": stop,
        "observed_rate_degC_per_min": observed_rate,
        "paper_tmax_degC": member["paper_tmax_degC"],
        "observed_raw_tmax_degC": observed_tmax,
        "fit_component_centers_degC": [fit.center for fit in result.fits],
        "fit_component_areas_signal_temperature": [fit.area for fit in result.fits],
        "integrated_areas_signal_time": [peak.area for peak in result.integrated_peaks],
        "global_r_squared": diagnostics.statistics.r_squared,
        "global_rmse": diagnostics.statistics.rmse,
        "jacobian_rank": diagnostics.jacobian_rank,
        "n_free_parameters": diagnostics.n_free_parameters,
        "condition_number": diagnostics.condition_number,
        "identifiable": diagnostics.identifiable,
        "covariance_valid": diagnostics.covariance_valid,
        "active_bounds": list(diagnostics.active_bounds),
        "uncertainty_status": diagnostics.uncertainty_status,
        "qc_codes": [issue.code for issue in result.qc_issues],
        "quantification_performed": False,
    }


def _validate_delta_tmax(results: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    by_path = {result["path"]: result for result in results}
    for member in manifest["members"]:
        reference = member.get("delta_reference")
        if reference is None:
            continue
        observed_delta = (
            by_path[member["path"]]["observed_raw_tmax_degC"]
            - by_path[reference]["observed_raw_tmax_degC"]
        )
        if abs(observed_delta - member["paper_delta_tmax_degC"]) > 1.5:
            raise PublicDataValidationError(f"paper delta Tmax comparison failed: {member['path']}")
        by_path[member["path"]]["observed_delta_tmax_degC"] = observed_delta
        by_path[member["path"]]["paper_delta_tmax_degC"] = member["paper_delta_tmax_degC"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Opt-in TPX-PUB-001 validation. No network is used unless --download is explicit."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", type=Path, help="reviewed Zenodo ZIP already on disk")
    source.add_argument("--download", action="store_true", help="download the reviewed Zenodo ZIP")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="retain CSV exports and JSON report; default outputs exist only in /tmp",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    manifest = load_manifest()
    with tempfile.TemporaryDirectory(prefix="tpxlab-TPX-PUB-001-", dir=TMP_ROOT) as work:
        workdir = Path(work)
        archive_path = args.archive
        if args.download:
            archive_path = workdir / manifest["archive"]["name"]
            _download_source(manifest["source_url"], archive_path)
        assert archive_path is not None
        validate_archive(archive_path, manifest)
        extracted = workdir / "source"
        extracted.mkdir()
        extract_reviewed_members(archive_path, manifest, extracted)

        if args.output_dir is None:
            export_root = workdir / "validation-output"
        else:
            export_root = args.output_dir.resolve()
            if export_root.exists() and any(export_root.iterdir()):
                raise PublicDataValidationError("--output-dir must be absent or empty")
        export_root.mkdir(parents=True, exist_ok=True)

        results = [
            analyze_member(extracted / member["path"], member, manifest, export_root)
            for member in manifest["members"]
            if member["analysis_role"] == "tpr_validation"
        ]
        _validate_delta_tmax(results, manifest)
        report = {
            "schema": manifest["schema"],
            "dataset_id": manifest["dataset_id"],
            "archive_sha256": manifest["archive"]["sha256"],
            "full_acquisition_pipeline_analysis": True,
            "ramp_statistics_use_recorded_derived_selection": True,
            "calibration_available": False,
            "chemical_component_assignment": False,
            "fit_uniqueness_claimed": False,
            "results": results,
        }
        report_text = json.dumps(report, indent=2, sort_keys=True)
        (export_root / "validation-report.json").write_text(report_text + "\n", encoding="utf-8")
        print(report_text)
        if args.output_dir is None:
            print(f"Validation exports were temporary: {export_root}")
        else:
            print(f"Validation exports retained at: {export_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
