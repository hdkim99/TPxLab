"""CSV/XLSX import with explicit column mapping."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from tpxlab.models import RawData


@dataclass(frozen=True)
class ColumnMapping:
    time: str
    temperature: str
    signal: str


def read_table(path: str | Path, *, sheet: str | int = 0) -> pd.DataFrame:
    """Read a CSV or XLSX table without modifying its values."""

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source)
    if suffix == ".xlsx":
        return pd.read_excel(source, sheet_name=sheet, engine="openpyxl")
    raise ValueError("only .csv and .xlsx inputs are supported")


def _normalized(column: object) -> str:
    return "".join(character for character in str(column).lower() if character.isalnum())


def auto_map_columns(frame: pd.DataFrame) -> ColumnMapping:
    """Recognize conservative aliases, failing rather than guessing ambiguous columns."""

    aliases = {
        # Unit-bearing aliases are intentionally excluded: accepting `elapsed_min`
        # while applying a default of seconds would silently alter the experiment.
        "time": {"time", "times", "elapsedtime"},
        "temperature": {"temperature", "temp", "temperaturec"},
        "signal": {"signal", "detectorsignal", "response", "intensity", "tcd", "ms"},
    }
    resolved: dict[str, str] = {}
    for role, names in aliases.items():
        matches = [str(column) for column in frame.columns if _normalized(column) in names]
        if len(matches) != 1:
            available = ", ".join(map(str, frame.columns))
            raise ValueError(f"could not uniquely map {role}; choose one of: {available}")
        resolved[role] = matches[0]
    return ColumnMapping(**resolved)


def raw_data_from_frame(
    frame: pd.DataFrame,
    mapping: ColumnMapping,
    *,
    time_unit: str = "second",
    temperature_unit: str = "degC",
    signal_unit: str = "millivolt",
    source: str = "",
) -> RawData:
    """Build immutable raw channels from explicit column names."""

    missing = [
        name for name in (mapping.time, mapping.temperature, mapping.signal) if name not in frame
    ]
    if missing:
        raise ValueError(f"mapped columns are absent: {', '.join(missing)}")
    try:
        time = frame[mapping.time].to_numpy(dtype=np.float64)
        temperature = frame[mapping.temperature].to_numpy(dtype=np.float64)
        signal = frame[mapping.signal].to_numpy(dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"mapped channels must contain numeric values: {exc}") from exc
    return RawData(
        time=time,
        temperature=temperature,
        signal=signal,
        time_unit=time_unit,
        temperature_unit=temperature_unit,
        signal_unit=signal_unit,
        source=source,
    )


def load_raw_data(
    path: str | Path,
    mapping: ColumnMapping | None = None,
    *,
    sheet: str | int = 0,
    time_unit: str = "second",
    temperature_unit: str = "degC",
    signal_unit: str = "millivolt",
) -> RawData:
    """Read and map a supported file into an immutable :class:`RawData`."""

    frame = read_table(path, sheet=sheet)
    active_mapping = mapping or auto_map_columns(frame)
    return raw_data_from_frame(
        frame,
        active_mapping,
        time_unit=time_unit,
        temperature_unit=temperature_unit,
        signal_unit=signal_unit,
        source=str(Path(path).resolve()),
    )
