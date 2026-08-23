from __future__ import annotations

import numpy as np
import pytest

from tpxlab.models import RawData
from tpxlab.peaks import gaussian


@pytest.fixture
def gaussian_raw() -> RawData:
    temperature = np.linspace(200.0, 600.0, 801)
    time = np.linspace(0.0, 800.0, 801)
    signal = 0.2 + 0.0001 * time + gaussian(temperature, 120.0, 400.0, 18.0)
    return RawData(time=time, temperature=temperature, signal=signal)
