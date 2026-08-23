"""Real-widget smoke executed under a display by CI (not collected by pytest)."""

from __future__ import annotations

import tkinter as tk

import numpy as np

from tpxlab.gui import TpxLabApp
from tpxlab.models import PeakSeed, RawData
from tpxlab.peaks import gaussian


def main() -> int:
    temperature = np.linspace(200, 600, 801)
    raw = RawData(
        time=np.linspace(0, 800, 801),
        temperature=temperature,
        signal=0.2 + gaussian(temperature, 100, 400, 18),
    )
    root = tk.Tk()
    root.withdraw()
    try:
        app = TpxLabApp(root)
        app.set_raw_data(raw)
        app.baseline_method.set("linear")
        app.peak_tree.insert("", tk.END, values=(401, 340, 460))
        app.run_analysis()
        root.update_idletasks()
        if app.result is None or app.canvas is None:
            raise RuntimeError("GUI did not execute or render the analysis result")
        if app.result.seeds != (PeakSeed(401, 340, 460),):
            raise RuntimeError("GUI peak edits did not reach the analysis service")
    finally:
        root.destroy()
    print("TPxLab real-widget backend smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
