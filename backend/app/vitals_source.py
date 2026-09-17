"""Loads real bedside-monitor waveforms from VitalDB's open dataset
(https://vitaldb.net, no credentials required) and replays them as a
live vitals feed, standing in for the device layer a real ICU
dashboard (e.g. vTitan's IntelliICU) would read from infusion pumps,
monitors, and ventilators.
"""
from __future__ import annotations

import numpy as np
import vitaldb

# VitalDB track name -> short vital key used throughout the app.
TRACKS = {
    "Solar8000/HR": "HR",
    "Solar8000/PLETH_SPO2": "SPO2",
    "Solar8000/NIBP_SBP": "NIBP_SBP",
    "Solar8000/NIBP_DBP": "NIBP_DBP",
    "Solar8000/RR": "RR",
    "Solar8000/BT": "TEMP",
}
TRACK_NAMES = list(TRACKS.keys())
VITAL_KEYS = list(TRACKS.values())

SAMPLE_INTERVAL_SEC = 1

# High-resolution waveform tracks, loaded lazily per bed only when its
# detail view is opened -- these are much larger than the numerics.
WAVEFORM_TRACKS = {
    "SNUADC/ECG_II": "ECG",
    "SNUADC/PLETH": "PLETH",
}
WAVEFORM_TRACK_NAMES = list(WAVEFORM_TRACKS.keys())
WAVEFORM_KEYS = list(WAVEFORM_TRACKS.values())
WAVEFORM_HZ = 100


class BedSource:
    """Replays one VitalDB case's numeric vitals as a fixed-interval series.

    Bedside monitors hold the last reading between samples rather than
    going blank, so gaps in the source data are forward-filled.
    """

    def __init__(self, bed_id: str, case_id: int, encounter_length: int | None = None):
        self.bed_id = bed_id
        self.case_id = case_id
        raw = vitaldb.load_case(case_id, TRACK_NAMES, interval=SAMPLE_INTERVAL_SEC)
        self.series = _forward_fill(raw)
        self.length = len(self.series)
        self.waveform: np.ndarray | None = None
        self.waveform_length = 0
        # How long one admission-to-discharge encounter lasts, in sim
        # seconds. Defaults to the real case length; a demo bed can
        # pass a short override so the encounter cycle (and the
        # insurance eligibility/claim events it drives) is visible in
        # seconds instead of tens of minutes, while the underlying
        # vitals keep playing continuously off self.length.
        self.encounter_length = encounter_length or self.length

    def tick(self, t: int) -> dict[str, float | None]:
        row = self.series[t % self.length]
        return {key: (None if np.isnan(v) else round(float(v), 1)) for key, v in zip(VITAL_KEYS, row)}

    def ensure_waveform_loaded(self) -> None:
        if self.waveform is not None:
            return
        raw = vitaldb.load_case(self.case_id, WAVEFORM_TRACK_NAMES, interval=1 / WAVEFORM_HZ)
        self.waveform = _forward_fill(raw)
        self.waveform_length = len(self.waveform)

    def waveform_window(self, sim_t_start: int, sim_t_end: int) -> dict[str, list[float | None]]:
        """Samples for sim-time half-open interval [sim_t_start, sim_t_end), wrapped to the case length."""
        self.ensure_waveform_loaded()
        start = (sim_t_start * WAVEFORM_HZ) % self.waveform_length
        n = (sim_t_end - sim_t_start) * WAVEFORM_HZ
        idx = (start + np.arange(n)) % self.waveform_length
        chunk = self.waveform[idx]
        return {
            key: [None if np.isnan(v) else round(float(v), 4) for v in chunk[:, i]]
            for i, key in enumerate(WAVEFORM_KEYS)
        }


def _forward_fill(arr: np.ndarray) -> np.ndarray:
    filled = arr.copy()
    for col in range(filled.shape[1]):
        last = np.nan
        for row in range(filled.shape[0]):
            if np.isnan(filled[row, col]):
                filled[row, col] = last
            else:
                last = filled[row, col]
    return filled


def pick_case_ids(n: int) -> list[int]:
    cases = vitaldb.find_cases(TRACK_NAMES)
    if len(cases) < n:
        raise RuntimeError(f"VitalDB returned only {len(cases)} cases with the required tracks")
    step = max(1, len(cases) // n)
    return [cases[i * step] for i in range(n)]
