"""Tkinter desktop workflow wired to :class:`tpxlab.pipeline.AnalysisService`."""

from __future__ import annotations

import argparse
import tkinter as tk
from collections.abc import Sequence
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import cast

import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from tpxlab import __version__
from tpxlab.export import export_bundle
from tpxlab.io import ColumnMapping, auto_map_columns, raw_data_from_frame, read_table
from tpxlab.models import (
    AnalysisResult,
    AnalysisSettings,
    BaselineMethod,
    PeakModel,
    PeakSeed,
    RawData,
)
from tpxlab.pipeline import AnalysisService
from tpxlab.plotting import analysis_figure, preparation_figure, raw_figure, save_figure


class TpxLabApp(ttk.Frame):
    """Interactive workflow; every computation delegates to the application service."""

    def __init__(self, master: tk.Misc, service: AnalysisService | None = None) -> None:
        super().__init__(master, padding=8)
        self.service = service or AnalysisService()
        self.frame_data: pd.DataFrame | None = None
        self.source_path = ""
        self.raw: RawData | None = None
        self.result: AnalysisResult | None = None
        self.canvas: FigureCanvasTkAgg | None = None
        self._create_variables()
        self._build_controls()
        self.pack(fill=tk.BOTH, expand=True)

    def _create_variables(self) -> None:
        self.time_column = tk.StringVar()
        self.temperature_column = tk.StringVar()
        self.signal_column = tk.StringVar()
        self.time_unit = tk.StringVar(value="second")
        self.temperature_unit = tk.StringVar(value="degC")
        self.signal_unit = tk.StringVar(value="millivolt")
        self.baseline_method = tk.StringVar(value="als")
        self.peak_model = tk.StringVar(value="gaussian")
        self.prominence = tk.StringVar()
        self.smoothing_window = tk.StringVar()
        self.calibration_value = tk.StringVar()
        self.calibration_unit = tk.StringVar(value="millimole / (millivolt * second)")
        self.sample_mass_value = tk.StringVar()
        self.sample_mass_unit = tk.StringVar(value="gram")
        self.peak_center = tk.StringVar()
        self.peak_left = tk.StringVar()
        self.peak_right = tk.StringVar()
        self.status = tk.StringVar(value="Load a CSV or XLSX dataset.")

    def _build_controls(self) -> None:
        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 8))
        plot_frame = ttk.Frame(self)
        plot_frame.grid(row=0, column=1, sticky="nsew")
        self.plot_frame = plot_frame
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        ttk.Button(controls, text="Load data", command=self.load_file).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Label(controls, text="Columns").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.time_combo = self._labeled_combo(controls, 2, "Time", self.time_column)
        self.temperature_combo = self._labeled_combo(
            controls, 3, "Temperature", self.temperature_column
        )
        self.signal_combo = self._labeled_combo(controls, 4, "Signal", self.signal_column)
        self._labeled_entry(controls, 5, "Time unit", self.time_unit)
        self._labeled_entry(controls, 6, "Temperature unit", self.temperature_unit)
        self._labeled_entry(controls, 7, "Signal unit", self.signal_unit)
        self._labeled_combo(
            controls, 8, "Baseline", self.baseline_method, ("linear", "polynomial", "als")
        )
        self._labeled_entry(controls, 9, "Smooth window", self.smoothing_window)
        self._labeled_entry(controls, 10, "Prominence", self.prominence)
        self._labeled_combo(
            controls, 11, "Peak model", self.peak_model, ("gaussian", "lorentzian", "voigt")
        )
        ttk.Button(controls, text="Prepare + detect", command=self.prepare_and_detect).grid(
            row=12, column=0, columnspan=2, sticky="ew", pady=(6, 2)
        )

        self.peak_tree = ttk.Treeview(
            controls, columns=("center", "left", "right"), show="headings", height=5
        )
        for name in ("center", "left", "right"):
            self.peak_tree.heading(name, text=name.title())
            self.peak_tree.column(name, width=74)
        self.peak_tree.grid(row=13, column=0, columnspan=2, sticky="ew")
        self.peak_tree.bind("<<TreeviewSelect>>", self._load_selected_peak)
        self._labeled_entry(controls, 14, "Center", self.peak_center)
        self._labeled_entry(controls, 15, "Left", self.peak_left)
        self._labeled_entry(controls, 16, "Right", self.peak_right)
        peak_buttons = ttk.Frame(controls)
        peak_buttons.grid(row=17, column=0, columnspan=2, sticky="ew")
        ttk.Button(peak_buttons, text="Add", command=self.add_peak).pack(side=tk.LEFT)
        ttk.Button(peak_buttons, text="Update", command=self.update_peak).pack(side=tk.LEFT)
        ttk.Button(peak_buttons, text="Remove", command=self.remove_peak).pack(side=tk.LEFT)

        ttk.Label(controls, text="Optional quantification").grid(
            row=18, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        self._labeled_entry(controls, 19, "Calibration", self.calibration_value)
        self._labeled_entry(controls, 20, "Calibration unit", self.calibration_unit)
        self._labeled_entry(controls, 21, "Sample mass", self.sample_mass_value)
        self._labeled_entry(controls, 22, "Mass unit", self.sample_mass_unit)
        ttk.Button(controls, text="Fit + quantify", command=self.run_analysis).grid(
            row=23, column=0, columnspan=2, sticky="ew", pady=(6, 2)
        )
        ttk.Button(controls, text="Export workbook", command=self.export_result).grid(
            row=24, column=0, columnspan=2, sticky="ew"
        )
        ttk.Button(controls, text="Export figure", command=self.export_figure).grid(
            row=25, column=0, columnspan=2, sticky="ew"
        )
        ttk.Label(controls, textvariable=self.status, wraplength=280).grid(
            row=26, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

    @staticmethod
    def _labeled_entry(
        parent: ttk.Frame, row: int, label: str, variable: tk.StringVar
    ) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        entry = ttk.Entry(parent, textvariable=variable, width=24)
        entry.grid(row=row, column=1, sticky="ew")
        return entry

    @staticmethod
    def _labeled_combo(
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        values: Sequence[str] = (),
    ) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        combo = ttk.Combobox(parent, textvariable=variable, values=tuple(values), width=21)
        combo.grid(row=row, column=1, sticky="ew")
        return combo

    def load_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("TPx data", "*.csv *.xlsx")])
        if not path:
            return
        try:
            frame = read_table(path)
            self.frame_data = frame
            self.source_path = str(Path(path).resolve())
            columns = tuple(map(str, frame.columns))
            for combo in (self.time_combo, self.temperature_combo, self.signal_combo):
                combo.configure(values=columns)
            try:
                mapping = auto_map_columns(frame)
                self.time_column.set(mapping.time)
                self.temperature_column.set(mapping.temperature)
                self.signal_column.set(mapping.signal)
            except ValueError:
                self.status.set("Loaded data; select time, temperature, and signal columns.")
            else:
                self.status.set("Loaded data and recognized columns. Prepare when ready.")
            if all(
                variable.get()
                for variable in (self.time_column, self.temperature_column, self.signal_column)
            ):
                self._draw_figure(raw_figure(self._mapped_raw()))
        except (FileNotFoundError, ValueError) as exc:
            messagebox.showerror("Load failed", str(exc))

    def set_raw_data(self, raw: RawData) -> None:
        """Set an API-created dataset; useful for examples and GUI integration tests."""

        self.raw = raw
        self._draw_figure(raw_figure(raw))
        self.status.set(f"Loaded {len(raw.time)} observations from API.")

    def _mapped_raw(self) -> RawData:
        if self.frame_data is None:
            if self.raw is None:
                raise ValueError("load data first")
            return self.raw
        mapping = ColumnMapping(
            time=self.time_column.get(),
            temperature=self.temperature_column.get(),
            signal=self.signal_column.get(),
        )
        self.raw = raw_data_from_frame(
            self.frame_data,
            mapping,
            time_unit=self.time_unit.get(),
            temperature_unit=self.temperature_unit.get(),
            signal_unit=self.signal_unit.get(),
            source=self.source_path,
        )
        return self.raw

    def _settings(self) -> AnalysisSettings:
        calibration_value = self.calibration_value.get().strip()
        sample_mass_value = self.sample_mass_value.get().strip()
        return AnalysisSettings(
            baseline_method=cast(BaselineMethod, self.baseline_method.get()),
            smoothing_window=(
                int(self.smoothing_window.get()) if self.smoothing_window.get().strip() else None
            ),
            peak_prominence=(
                float(self.prominence.get()) if self.prominence.get().strip() else None
            ),
            peak_model=cast(PeakModel, self.peak_model.get()),
            calibration_value=float(calibration_value) if calibration_value else None,
            calibration_unit=self.calibration_unit.get() if calibration_value else None,
            sample_mass_value=float(sample_mass_value) if sample_mass_value else None,
            sample_mass_unit=self.sample_mass_unit.get() if sample_mass_value else None,
        )

    def prepare_and_detect(self) -> None:
        try:
            raw = self._mapped_raw()
            settings = self._settings()
            prepared = self.service.prepare(raw, settings)
            seeds = self.service.detect(prepared, settings)
            self._replace_peak_rows(seeds)
            self._draw_figure(preparation_figure(prepared))
            self.status.set(f"Prepared raw-preserving signal; detected {len(seeds)} peaks.")
        except (TypeError, ValueError) as exc:
            messagebox.showerror("Preparation failed", str(exc))

    def _replace_peak_rows(self, seeds: Sequence[PeakSeed]) -> None:
        for item in self.peak_tree.get_children():
            self.peak_tree.delete(item)
        for seed in seeds:
            self.peak_tree.insert(
                "",
                tk.END,
                values=(
                    seed.center,
                    "" if seed.left is None else seed.left,
                    "" if seed.right is None else seed.right,
                ),
            )

    def _tree_seeds(self) -> tuple[PeakSeed, ...]:
        seeds = []
        for item in self.peak_tree.get_children():
            values = self.peak_tree.item(item, "values")
            if isinstance(values, str):
                raise ValueError("peak table returned invalid row data")
            center, left, right = values
            seeds.append(
                PeakSeed(
                    center=float(center),
                    left=float(left) if str(left) else None,
                    right=float(right) if str(right) else None,
                )
            )
        return tuple(seeds)

    def add_peak(self) -> None:
        try:
            center = float(self.peak_center.get())
            left = float(self.peak_left.get()) if self.peak_left.get().strip() else ""
            right = float(self.peak_right.get()) if self.peak_right.get().strip() else ""
            self.peak_tree.insert("", tk.END, values=(center, left, right))
        except ValueError as exc:
            messagebox.showerror("Invalid peak", str(exc))

    def update_peak(self) -> None:
        selected = self.peak_tree.selection()
        if not selected:
            messagebox.showerror("Update peak", "select a peak first")
            return
        try:
            center = float(self.peak_center.get())
            left = float(self.peak_left.get()) if self.peak_left.get().strip() else ""
            right = float(self.peak_right.get()) if self.peak_right.get().strip() else ""
            self.peak_tree.item(selected[0], values=(center, left, right))
        except ValueError as exc:
            messagebox.showerror("Invalid peak", str(exc))

    def remove_peak(self) -> None:
        for item in self.peak_tree.selection():
            self.peak_tree.delete(item)

    def _load_selected_peak(self, _event: tk.Event[tk.Misc]) -> None:
        selected = self.peak_tree.selection()
        if selected:
            values = self.peak_tree.item(selected[0], "values")
            if isinstance(values, str):
                return
            center, left, right = values
            self.peak_center.set(str(center))
            self.peak_left.set(str(left))
            self.peak_right.set(str(right))

    def run_analysis(self) -> None:
        try:
            raw = self._mapped_raw()
            self.result = self.service.analyze(raw, self._settings(), self._tree_seeds())
            self._draw_figure(analysis_figure(self.result))
            quantities = ", ".join(
                f"peak {peak.peak_id}: {peak.value:.6g} {peak.unit}"
                for peak in self.result.quantified_peaks
            )
            quantity_status = f" Quantification: {quantities}." if quantities else ""
            self.status.set(
                f"Fit {len(self.result.fits)} peaks; {len(self.result.qc_issues)} QC issues."
                f"{quantity_status}"
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Analysis failed", str(exc))

    def _draw_figure(self, figure: Figure) -> None:
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()  # type: ignore[no-untyped-call]
        self.canvas = FigureCanvasTkAgg(  # type: ignore[no-untyped-call]
            figure, master=self.plot_frame
        )
        self.canvas.draw()  # type: ignore[no-untyped-call]
        self.canvas.get_tk_widget().pack(  # type: ignore[no-untyped-call]
            fill=tk.BOTH, expand=True
        )

    def export_result(self) -> None:
        if self.result is None:
            messagebox.showerror("Export", "run analysis first")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel workbook", "*.xlsx")]
        )
        if path:
            try:
                export_bundle(self.result, path)
                self.status.set(f"Exported {path}")
            except ValueError as exc:
                messagebox.showerror("Export failed", str(exc))

    def export_figure(self) -> None:
        if self.result is None:
            messagebox.showerror("Export figure", "run analysis first")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG image", "*.png"),
                ("SVG image", "*.svg"),
                ("PDF document", "*.pdf"),
            ],
        )
        if path:
            save_figure(self.result, path)
            self.status.set(f"Exported figure {path}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tpxlab-gui")
    parser.add_argument(
        "--smoke-test", action="store_true", help="verify GUI imports without opening a window"
    )
    args = parser.parse_args(argv)
    if args.smoke_test:
        print("TPxLab GUI dependencies imported successfully")
        return 0
    root = tk.Tk()
    root.title(f"TPxLab {__version__}")
    root.geometry("1180x760")
    TpxLabApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
