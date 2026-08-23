"""Tkinter desktop workflow wired to :class:`tpxlab.pipeline.AnalysisService`."""

from __future__ import annotations

import argparse
import json
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
    FitMode,
    PeakModel,
    PeakPolarity,
    PeakSeed,
    RawData,
    SharedWidthParameter,
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
        self.peak_polarity = tk.StringVar(value="positive")
        self.peak_model = tk.StringVar(value="gaussian")
        self.fit_mode = tk.StringVar(value="global")
        self.prominence = tk.StringVar()
        self.smoothing_window = tk.StringVar()
        self.calibration_value = tk.StringVar()
        self.calibration_unit = tk.StringVar(value="millimole / (millivolt * second)")
        self.sample_mass_value = tk.StringVar()
        self.sample_mass_unit = tk.StringVar(value="gram")
        self.peak_center = tk.StringVar()
        self.peak_left = tk.StringVar()
        self.peak_right = tk.StringVar()
        self.component_model = tk.StringVar(value="gaussian")
        self.center_lower = tk.StringVar()
        self.center_upper = tk.StringVar()
        self.width_lower = tk.StringVar()
        self.width_upper = tk.StringVar()
        self.fixed_parameters = tk.StringVar(value="{}")
        self.shared_width_group = tk.StringVar()
        self.shared_width_parameter = tk.StringVar()
        self.status = tk.StringVar(value="Load a CSV or XLSX dataset.")

    def _build_controls(self) -> None:
        controls_host = ttk.Frame(self)
        controls_host.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        control_canvas = tk.Canvas(controls_host, width=390, highlightthickness=0)
        control_scrollbar = ttk.Scrollbar(
            controls_host, orient=tk.VERTICAL, command=control_canvas.yview
        )
        control_canvas.configure(yscrollcommand=control_scrollbar.set)
        control_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        control_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        controls = ttk.Frame(control_canvas)
        controls_window = control_canvas.create_window((0, 0), window=controls, anchor="nw")
        controls.bind(
            "<Configure>",
            lambda _event: control_canvas.configure(scrollregion=control_canvas.bbox("all")),
        )
        control_canvas.bind(
            "<Configure>",
            lambda event: control_canvas.itemconfigure(controls_window, width=event.width),
        )
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
        self._labeled_combo(
            controls,
            9,
            "Peak polarity",
            self.peak_polarity,
            ("positive", "negative"),
        )
        self._labeled_entry(controls, 10, "Smooth window", self.smoothing_window)
        self._labeled_entry(controls, 11, "Prominence", self.prominence)
        self._labeled_combo(
            controls,
            12,
            "Fit mode",
            self.fit_mode,
            ("global", "independent"),
        )
        self._labeled_combo(
            controls, 13, "Default model", self.peak_model, ("gaussian", "lorentzian", "voigt")
        )
        ttk.Button(controls, text="Prepare + detect", command=self.prepare_and_detect).grid(
            row=14, column=0, columnspan=2, sticky="ew", pady=(6, 2)
        )

        peak_columns = (
            "center",
            "left",
            "right",
            "model",
            "center_lower",
            "center_upper",
            "width_lower",
            "width_upper",
            "fixed",
            "shared_group",
            "shared_parameter",
        )
        self.peak_tree = ttk.Treeview(
            controls,
            columns=peak_columns,
            displaycolumns=(
                "center",
                "model",
                "center_lower",
                "center_upper",
                "shared_group",
            ),
            show="headings",
            height=5,
        )
        for name in peak_columns:
            self.peak_tree.heading(name, text=name.replace("_", " ").title())
            self.peak_tree.column(name, width=74, stretch=False)
        self.peak_tree.grid(row=15, column=0, columnspan=2, sticky="ew")
        self.peak_tree.bind("<<TreeviewSelect>>", self._load_selected_peak)
        self._labeled_entry(controls, 16, "Center", self.peak_center)
        self._labeled_entry(controls, 17, "Integration left", self.peak_left)
        self._labeled_entry(controls, 18, "Integration right", self.peak_right)
        self._labeled_combo(
            controls,
            19,
            "Component model",
            self.component_model,
            ("gaussian", "lorentzian", "voigt"),
        )
        self._labeled_entry(controls, 20, "Center lower", self.center_lower)
        self._labeled_entry(controls, 21, "Center upper", self.center_upper)
        self._labeled_entry(controls, 22, "Width lower", self.width_lower)
        self._labeled_entry(controls, 23, "Width upper", self.width_upper)
        self._labeled_entry(controls, 24, "Fixed params JSON", self.fixed_parameters)
        self._labeled_entry(controls, 25, "Shared width group", self.shared_width_group)
        self._labeled_combo(
            controls,
            26,
            "Shared parameter",
            self.shared_width_parameter,
            ("", "sigma", "gamma"),
        )
        peak_buttons = ttk.Frame(controls)
        peak_buttons.grid(row=27, column=0, columnspan=2, sticky="ew")
        ttk.Button(peak_buttons, text="Add", command=self.add_peak).pack(side=tk.LEFT)
        ttk.Button(peak_buttons, text="Update", command=self.update_peak).pack(side=tk.LEFT)
        ttk.Button(peak_buttons, text="Remove", command=self.remove_peak).pack(side=tk.LEFT)

        ttk.Label(controls, text="Optional quantification").grid(
            row=28, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        self._labeled_entry(controls, 29, "Calibration", self.calibration_value)
        self._labeled_entry(controls, 30, "Calibration unit", self.calibration_unit)
        self._labeled_entry(controls, 31, "Sample mass", self.sample_mass_value)
        self._labeled_entry(controls, 32, "Mass unit", self.sample_mass_unit)
        ttk.Button(controls, text="Fit + quantify", command=self.run_analysis).grid(
            row=33, column=0, columnspan=2, sticky="ew", pady=(6, 2)
        )
        ttk.Button(controls, text="Export workbook", command=self.export_result).grid(
            row=34, column=0, columnspan=2, sticky="ew"
        )
        ttk.Button(controls, text="Export figure", command=self.export_figure).grid(
            row=35, column=0, columnspan=2, sticky="ew"
        )
        ttk.Label(controls, textvariable=self.status, wraplength=280).grid(
            row=36, column=0, columnspan=2, sticky="w", pady=(8, 0)
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
            peak_polarity=cast(PeakPolarity, self.peak_polarity.get()),
            smoothing_window=(
                int(self.smoothing_window.get()) if self.smoothing_window.get().strip() else None
            ),
            peak_prominence=(
                float(self.prominence.get()) if self.prominence.get().strip() else None
            ),
            peak_model=cast(PeakModel, self.peak_model.get()),
            fit_mode=cast(FitMode, self.fit_mode.get()),
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
                    seed.model or self.peak_model.get(),
                    "" if seed.center_lower is None else seed.center_lower,
                    "" if seed.center_upper is None else seed.center_upper,
                    "" if seed.width_lower is None else seed.width_lower,
                    "" if seed.width_upper is None else seed.width_upper,
                    json.dumps(seed.fixed_parameters, sort_keys=True),
                    seed.shared_width_group or "",
                    seed.shared_width_parameter or "",
                ),
            )

    def _tree_seeds(self) -> tuple[PeakSeed, ...]:
        seeds = []
        for item in self.peak_tree.get_children():
            values = self.peak_tree.item(item, "values")
            if isinstance(values, str):
                raise ValueError("peak table returned invalid row data")
            (
                center,
                left,
                right,
                model,
                center_lower,
                center_upper,
                width_lower,
                width_upper,
                fixed_parameters,
                shared_width_group,
                shared_width_parameter,
            ) = values
            fixed = json.loads(str(fixed_parameters))
            if not isinstance(fixed, dict) or not all(
                isinstance(name, str)
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                for name, value in fixed.items()
            ):
                raise ValueError("fixed parameters must be a JSON object of numeric values")
            seeds.append(
                PeakSeed(
                    center=float(center),
                    left=float(left) if str(left) else None,
                    right=float(right) if str(right) else None,
                    model=cast(PeakModel, str(model)),
                    center_lower=float(center_lower) if str(center_lower) else None,
                    center_upper=float(center_upper) if str(center_upper) else None,
                    width_lower=float(width_lower) if str(width_lower) else None,
                    width_upper=float(width_upper) if str(width_upper) else None,
                    fixed_parameters={name: float(value) for name, value in fixed.items()},
                    shared_width_group=(
                        str(shared_width_group) if str(shared_width_group) else None
                    ),
                    shared_width_parameter=(
                        cast(SharedWidthParameter, str(shared_width_parameter))
                        if str(shared_width_parameter)
                        else None
                    ),
                )
            )
        return tuple(seeds)

    def _peak_values_from_controls(self) -> tuple[object, ...]:
        fixed_text = self.fixed_parameters.get().strip() or "{}"
        fixed = json.loads(fixed_text)
        if not isinstance(fixed, dict) or not all(
            isinstance(name, str)
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            for name, value in fixed.items()
        ):
            raise ValueError("fixed parameters must be a JSON object of numeric values")

        def optional_float(variable: tk.StringVar) -> float | str:
            return float(variable.get()) if variable.get().strip() else ""

        return (
            float(self.peak_center.get()),
            optional_float(self.peak_left),
            optional_float(self.peak_right),
            self.component_model.get(),
            optional_float(self.center_lower),
            optional_float(self.center_upper),
            optional_float(self.width_lower),
            optional_float(self.width_upper),
            json.dumps(fixed, sort_keys=True),
            self.shared_width_group.get().strip(),
            self.shared_width_parameter.get().strip(),
        )

    def add_peak(self) -> None:
        try:
            self.peak_tree.insert("", tk.END, values=self._peak_values_from_controls())
        except (json.JSONDecodeError, ValueError) as exc:
            messagebox.showerror("Invalid peak", str(exc))

    def update_peak(self) -> None:
        selected = self.peak_tree.selection()
        if not selected:
            messagebox.showerror("Update peak", "select a peak first")
            return
        try:
            self.peak_tree.item(selected[0], values=self._peak_values_from_controls())
        except (json.JSONDecodeError, ValueError) as exc:
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
            (
                center,
                left,
                right,
                model,
                center_lower,
                center_upper,
                width_lower,
                width_upper,
                fixed_parameters,
                shared_width_group,
                shared_width_parameter,
            ) = values
            self.peak_center.set(str(center))
            self.peak_left.set(str(left))
            self.peak_right.set(str(right))
            self.component_model.set(str(model))
            self.center_lower.set(str(center_lower))
            self.center_upper.set(str(center_upper))
            self.width_lower.set(str(width_lower))
            self.width_upper.set(str(width_upper))
            self.fixed_parameters.set(str(fixed_parameters))
            self.shared_width_group.set(str(shared_width_group))
            self.shared_width_parameter.set(str(shared_width_parameter))

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
            fit_status = ""
            if self.result.global_fit is not None:
                diagnostics = self.result.global_fit
                fit_status = (
                    f" Global R²={diagnostics.statistics.r_squared:.5g}; "
                    f"rank={diagnostics.jacobian_rank}/{diagnostics.n_free_parameters}; "
                    f"identifiable={diagnostics.identifiable}."
                )
            self.status.set(
                f"Fit {len(self.result.fits)} peaks; {len(self.result.qc_issues)} QC issues."
                f"{fit_status}{quantity_status}"
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
