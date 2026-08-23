from __future__ import annotations

from types import SimpleNamespace

from tpxlab.gui import TpxLabApp
from tpxlab.models import AnalysisSettings, PeakSeed
from tpxlab.pipeline import AnalysisService


class RecordingService(AnalysisService):
    def __init__(self) -> None:
        self.received = None

    def analyze(self, raw, settings=None, seeds=None):
        self.received = (raw, settings, tuple(seeds or ()))
        return super().analyze(raw, settings, seeds)


class Status:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


def test_gui_run_passes_edited_seeds_and_settings_to_service(gaussian_raw) -> None:
    service = RecordingService()
    settings = AnalysisSettings(
        baseline_method="linear", peak_model="lorentzian", fit_mode="global"
    )
    edited = (
        PeakSeed(
            402,
            340,
            460,
            model="lorentzian",
            center_lower=390,
            center_upper=415,
            width_lower=5,
            width_upper=30,
            fixed_parameters={"gamma": 18},
        ),
    )
    fake = SimpleNamespace(
        service=service,
        result=None,
        status=Status(),
        _mapped_raw=lambda: gaussian_raw,
        _settings=lambda: settings,
        _tree_seeds=lambda: edited,
        _draw_figure=lambda figure: None,
    )
    TpxLabApp.run_analysis(fake)
    assert service.received == (gaussian_raw, settings, edited)
    assert fake.result.settings.peak_model == "lorentzian"
    assert fake.result.settings.fit_mode == "global"
    assert fake.result.seeds == edited
    assert "Fit 1 peaks" in fake.status.value


class PeakTree:
    def get_children(self):
        return ("row",)

    def item(self, _item, field):
        assert field == "values"
        return (
            402,
            340,
            460,
            "voigt",
            395,
            410,
            4,
            30,
            '{"gamma": 7}',
            "instrument",
            "sigma",
        )


def test_gui_component_table_parses_all_global_constraints() -> None:
    fake = SimpleNamespace(peak_tree=PeakTree())
    assert TpxLabApp._tree_seeds(fake) == (
        PeakSeed(
            402,
            340,
            460,
            model="voigt",
            center_lower=395,
            center_upper=410,
            width_lower=4,
            width_upper=30,
            fixed_parameters={"gamma": 7},
            shared_width_group="instrument",
            shared_width_parameter="sigma",
        ),
    )
