"""TPxLab public API."""

from tpxlab.models import (
    AnalysisResult,
    AnalysisSettings,
    GlobalFitDiagnostics,
    PeakFit,
    PeakSeed,
    RawData,
)
from tpxlab.pipeline import AnalysisService
from tpxlab.stoichiometry import ReductionDegree, calculate_reduction_degree

__all__ = [
    "AnalysisResult",
    "AnalysisService",
    "AnalysisSettings",
    "GlobalFitDiagnostics",
    "PeakFit",
    "PeakSeed",
    "RawData",
    "ReductionDegree",
    "calculate_reduction_degree",
]
__version__ = "0.1.1"
