"""Real-widget smoke executed under a display by CI (not collected by pytest)."""

from __future__ import annotations

import argparse
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import numpy as np

from tpxlab.gui import TpxLabApp
from tpxlab.models import PeakSeed, RawData
from tpxlab.peaks import gaussian


def _assert_result(app: TpxLabApp, expected_seeds: tuple[PeakSeed, ...]) -> None:
    if app.result is None or app.canvas is None:
        raise RuntimeError("GUI did not execute or render the analysis result")
    if app.result.seeds != expected_seeds:
        raise RuntimeError("GUI peak edits did not reach the analysis service")
    if app.result.global_fit is None:
        raise RuntimeError("GUI fit mode did not reach simultaneous fitting")
    if app.result.settings.peak_polarity != "negative":
        raise RuntimeError("GUI peak polarity did not reach the analysis service")


def _synthetic_smoke(app: TpxLabApp) -> None:
    temperature = np.linspace(200, 600, 801)
    raw = RawData(
        time=np.linspace(0, 800, 801),
        temperature=temperature,
        signal=0.2 - gaussian(temperature, 100, 400, 18),
    )
    app.set_raw_data(raw)
    app.baseline_method.set("linear")
    app.peak_polarity.set("negative")
    app.peak_tree.insert(
        "",
        tk.END,
        values=(401, 340, 460, "gaussian", 380, 420, 5, 40, "{}", "", ""),
    )
    expected_seed = PeakSeed(
        401,
        340,
        460,
        model="gaussian",
        center_lower=380,
        center_upper=420,
        width_lower=5,
        width_upper=40,
    )
    app.run_analysis()
    _assert_result(app, (expected_seed,))


def _public_smoke(app: TpxLabApp, data_path: Path, manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    member = next(item for item in manifest["members"] if item["path"].endswith(data_path.name))
    original_dialog = filedialog.askopenfilename
    filedialog.askopenfilename = lambda **_kwargs: str(data_path)
    try:
        app.load_file()
    finally:
        filedialog.askopenfilename = original_dialog
    if app.frame_data is None:
        raise RuntimeError("GUI did not load the public acquisition")
    app.time_column.set("timedelta (min)")
    app.temperature_column.set("T_C")
    app.signal_column.set("TCD_signal/g_cat")
    app.time_unit.set("minute")
    app.temperature_unit.set("degC")
    app.signal_unit.set("dimensionless / gram")
    app.baseline_method.set("linear")
    app.peak_polarity.set("negative")
    app.fit_mode.set("global")
    seeds = tuple(
        PeakSeed(
            center=float(component["center"]),
            left=float(component["left"]),
            right=float(component["right"]),
            model=component["model"],
            center_lower=float(component["center_lower"]),
            center_upper=float(component["center_upper"]),
            width_lower=float(component["width_lower"]),
            width_upper=float(component["width_upper"]),
        )
        for component in member["components"]
    )
    for seed in seeds:
        app.peak_tree.insert(
            "",
            tk.END,
            values=(
                seed.center,
                seed.left,
                seed.right,
                seed.model,
                seed.center_lower,
                seed.center_upper,
                seed.width_lower,
                seed.width_upper,
                "{}",
                "",
                "",
            ),
        )
    app.run_analysis()
    _assert_result(app, seeds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-data", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).parents[1] / "docs" / "public-data-manifest.json",
    )
    arguments = parser.parse_args(argv)
    root = tk.Tk()
    root.withdraw()
    try:
        app = TpxLabApp(root)
        if arguments.public_data is None:
            _synthetic_smoke(app)
        else:
            _public_smoke(app, arguments.public_data.resolve(), arguments.manifest.resolve())
        root.update_idletasks()
    finally:
        root.destroy()
    print("TPxLab real-widget backend smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
