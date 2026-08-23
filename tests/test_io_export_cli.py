from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tpxlab.cli import main
from tpxlab.export import export_csv_bundle, export_excel
from tpxlab.io import ColumnMapping, auto_map_columns, load_raw_data
from tpxlab.models import AnalysisSettings, PeakSeed
from tpxlab.pipeline import AnalysisService


def test_csv_and_xlsx_explicit_mapping(tmp_path: Path) -> None:
    frame = pd.DataFrame({"seconds": range(6), "oven": range(300, 306), "TCD A": range(6)})
    csv_path = tmp_path / "data.csv"
    xlsx_path = tmp_path / "data.xlsx"
    frame.to_csv(csv_path, index=False)
    frame.to_excel(xlsx_path, index=False)
    mapping = ColumnMapping("seconds", "oven", "TCD A")
    csv_raw = load_raw_data(csv_path, mapping)
    xlsx_raw = load_raw_data(xlsx_path, mapping)
    assert csv_raw.signal.tolist() == xlsx_raw.signal.tolist() == list(range(6))


def test_auto_mapping_is_conservative() -> None:
    frame = pd.DataFrame({"time": range(5), "temp": range(5), "signal": range(5)})
    assert auto_map_columns(frame) == ColumnMapping("time", "temp", "signal")
    with pytest.raises(ValueError, match="uniquely"):
        auto_map_columns(frame.assign(response=range(5)))


def test_excel_and_csv_export_are_complete(tmp_path: Path, gaussian_raw) -> None:
    result = AnalysisService().analyze(
        gaussian_raw,
        AnalysisSettings(baseline_method="linear"),
        [PeakSeed(400, 300, 500)],
    )
    workbook = export_excel(result, tmp_path / "result.xlsx")
    assert set(pd.ExcelFile(workbook).sheet_names) == {
        "Raw",
        "Processed",
        "Peaks",
        "Components",
        "Global_fit",
        "Settings",
        "Metadata",
        "Qc",
    }
    bundle = export_csv_bundle(result, tmp_path / "csv")
    assert {path.name for path in bundle.glob("*.csv")} == {
        "raw.csv",
        "processed.csv",
        "peaks.csv",
        "components.csv",
        "global_fit.csv",
        "settings.csv",
        "metadata.csv",
        "qc.csv",
    }


def test_cli_smoke_exports_real_workbook(tmp_path: Path) -> None:
    source = Path(__file__).parents[1] / "examples" / "synthetic_tpr.csv"
    output = tmp_path / "analysis.xlsx"
    figure = tmp_path / "analysis.png"
    status = main(
        [
            "analyze",
            str(source),
            "--output",
            str(output),
            "--figure",
            str(figure),
            "--baseline",
            "linear",
            "--peak-center",
            "300",
        ]
    )
    assert status == 0
    assert output.stat().st_size > 5000
    assert figure.stat().st_size > 5000
