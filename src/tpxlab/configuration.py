"""Strict JSON configuration for reproducible component constraints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from tpxlab.models import FitMode, PeakModel, PeakSeed, SharedWidthParameter

COMPONENT_SCHEMA = "org.tpxlab.components/0.2-draft"
_TOP_LEVEL_FIELDS = {"schema", "fit_mode", "components"}
_COMPONENT_FIELDS = {
    "center",
    "left",
    "right",
    "model",
    "center_lower",
    "center_upper",
    "width_lower",
    "width_upper",
    "fixed_parameters",
    "shared_width_group",
    "shared_width_parameter",
}
_PEAK_MODELS = {"gaussian", "lorentzian", "voigt"}
_FIT_MODES = {"independent", "global"}
_SHARED_WIDTHS = {"sigma", "gamma"}


@dataclass(frozen=True)
class ComponentConfiguration:
    """Validated configuration loaded from the draft JSON contract."""

    fit_mode: FitMode
    components: tuple[PeakSeed, ...]
    schema: str = COMPONENT_SCHEMA


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be a JSON object with string keys")
    return cast(dict[str, Any], value)


def _optional_number(record: dict[str, Any], field: str, index: int) -> float | None:
    value = record.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"component {index} field {field!r} must be a number or null")
    return float(value)


def _optional_string(record: dict[str, Any], field: str, index: int) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"component {index} field {field!r} must be a non-empty string or null")
    return value


def _component(value: object, index: int) -> PeakSeed:
    record = _object(value, f"component {index}")
    unknown = set(record).difference(_COMPONENT_FIELDS)
    if unknown:
        raise ValueError(f"component {index} has unknown fields: {sorted(unknown)}")
    center = _optional_number(record, "center", index)
    if center is None:
        raise ValueError(f"component {index} requires a numeric center")
    model_value = _optional_string(record, "model", index)
    if model_value is not None and model_value not in _PEAK_MODELS:
        raise ValueError(f"component {index} has unsupported model {model_value!r}")
    shared_parameter = _optional_string(record, "shared_width_parameter", index)
    if shared_parameter is not None and shared_parameter not in _SHARED_WIDTHS:
        raise ValueError(f"component {index} shared_width_parameter must be 'sigma' or 'gamma'")
    fixed_record = _object(
        record.get("fixed_parameters", {}), f"component {index} fixed_parameters"
    )
    fixed: dict[str, float] = {}
    for name, fixed_value in fixed_record.items():
        if isinstance(fixed_value, bool) or not isinstance(fixed_value, (int, float)):
            raise ValueError(f"component {index} fixed parameter {name!r} must be numeric")
        fixed[name] = float(fixed_value)
    return PeakSeed(
        center=center,
        left=_optional_number(record, "left", index),
        right=_optional_number(record, "right", index),
        model=cast(PeakModel | None, model_value),
        center_lower=_optional_number(record, "center_lower", index),
        center_upper=_optional_number(record, "center_upper", index),
        width_lower=_optional_number(record, "width_lower", index),
        width_upper=_optional_number(record, "width_upper", index),
        fixed_parameters=fixed,
        shared_width_group=_optional_string(record, "shared_width_group", index),
        shared_width_parameter=cast(SharedWidthParameter | None, shared_parameter),
    )


def load_component_configuration(path: str | Path) -> ComponentConfiguration:
    """Load a strict component configuration; unknown fields are rejected."""

    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid component configuration JSON: {exc}") from exc
    record = _object(payload, "component configuration")
    unknown = set(record).difference(_TOP_LEVEL_FIELDS)
    if unknown:
        raise ValueError(f"component configuration has unknown fields: {sorted(unknown)}")
    schema = record.get("schema")
    if schema != COMPONENT_SCHEMA:
        raise ValueError(f"component configuration schema must be {COMPONENT_SCHEMA!r}")
    fit_mode = record.get("fit_mode")
    if fit_mode not in _FIT_MODES:
        raise ValueError("component configuration fit_mode must be 'independent' or 'global'")
    values = record.get("components")
    if not isinstance(values, list):
        raise ValueError("component configuration components must be a JSON array")
    components = tuple(_component(value, index) for index, value in enumerate(values, start=1))
    return ComponentConfiguration(cast(FitMode, fit_mode), components)
