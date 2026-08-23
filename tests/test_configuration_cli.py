from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tpxlab.cli import main
from tpxlab.configuration import COMPONENT_SCHEMA, load_component_configuration
from tpxlab.models import PeakSeed


def _configuration() -> dict[str, object]:
    return {
        "schema": COMPONENT_SCHEMA,
        "fit_mode": "global",
        "components": [
            {
                "center": 300,
                "model": "gaussian",
                "center_lower": 280,
                "center_upper": 320,
                "width_lower": 5,
                "width_upper": 40,
                "fixed_parameters": {},
            }
        ],
    }


def test_component_configuration_loads_typed_constraints(tmp_path: Path) -> None:
    path = tmp_path / "components.json"
    path.write_text(json.dumps(_configuration()), encoding="utf-8")
    loaded = load_component_configuration(path)
    assert loaded.fit_mode == "global"
    assert loaded.components == (
        PeakSeed(
            300,
            model="gaussian",
            center_lower=280,
            center_upper=320,
            width_lower=5,
            width_upper=40,
        ),
    )


def test_component_configuration_rejects_unknown_fields(tmp_path: Path) -> None:
    payload = _configuration()
    payload["silently_ignored"] = True
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown fields"):
        load_component_configuration(path)


def test_cli_global_configuration_exports_diagnostics_and_provenance(tmp_path: Path) -> None:
    source = Path(__file__).parents[1] / "examples" / "synthetic_tpr.csv"
    configuration = tmp_path / "components.json"
    configuration.write_text(json.dumps(_configuration()), encoding="utf-8")
    destination = tmp_path / "bundle"
    status = main(
        [
            "analyze",
            str(source),
            "--output",
            str(destination),
            "--baseline",
            "linear",
            "--components-config",
            str(configuration),
        ]
    )
    assert status == 0
    settings = pd.read_csv(destination / "settings.csv")
    metadata = pd.read_csv(destination / "metadata.csv")
    components = pd.read_csv(destination / "components.csv")
    diagnostics = pd.read_csv(destination / "global_fit.csv")
    assert settings.loc[settings["parameter"] == "fit_mode", "value"].item() == "global"
    assert metadata.loc[metadata["key"] == "schema", "value"].item() == (
        "org.tpxlab.analysis/0.2-draft"
    )
    assert components.loc[0, "model"] == "gaussian"
    assert "covariance_json" in set(diagnostics["metric"])
    assert "parameter_order_json" in set(diagnostics["metric"])
