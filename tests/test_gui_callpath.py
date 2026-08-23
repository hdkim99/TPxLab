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
    settings = AnalysisSettings(baseline_method="linear", peak_model="lorentzian")
    edited = (PeakSeed(402, 340, 460),)
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
    assert fake.result.seeds == edited
    assert "Fit 1 peaks" in fake.status.value
