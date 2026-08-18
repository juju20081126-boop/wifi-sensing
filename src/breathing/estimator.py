"""Breathing-rate estimation by autocorrelation.

Autocorrelation rather than zero-crossing on purpose. RuView's zero-crossing
estimator parked at a fixed wrong value because it assumed a constant sample
rate and locked onto harmonics; autocorrelation over a bounded lag range avoids
both failure modes.

Pure Python -- this runs under MicroPython on the ESP32.
"""

# Physiological bounds. Outside this range an estimate is not breathing.
MIN_BPM = 6.0
MAX_BPM = 40.0

# Respiration needs a long window: three cycles of the slowest rate is 30 s.
DEFAULT_WINDOW_S = 30.0


class BreathingEstimator:
    """Estimates breaths per minute from a stream of band-filtered samples."""

    def __init__(self, sample_rate_hz, window_s=DEFAULT_WINDOW_S,
                 min_bpm=MIN_BPM, max_bpm=MAX_BPM):
        self.sample_rate_hz = sample_rate_hz
        self.window_len = int(window_s * sample_rate_hz)
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        # Lag bounds derived from the BPM bounds: lag = fs * 60 / bpm.
        self._lag_min = max(2, int(sample_rate_hz * 60.0 / max_bpm))
        self._lag_max = int(sample_rate_hz * 60.0 / min_bpm)
        self._buf = []

    def process(self, sample):
        self._buf.append(sample)
        if len(self._buf) > self.window_len:
            del self._buf[0:len(self._buf) - self.window_len]

    def reset(self):
        self._buf = []

    def estimate(self):
        """Return (bpm, confidence). bpm is 0.0 when no estimate is possible."""
        n = len(self._buf)
        # Need enough samples to evaluate the longest lag with real overlap.
        if n < self._lag_max * 2:
            return 0.0, 0.0

        mean = sum(self._buf) / n
        x = [v - mean for v in self._buf]

        energy = sum(v * v for v in x)
        if energy <= 0.0:
            return 0.0, 0.0

        lag_max = min(self._lag_max, n // 2)
        correlations = {}
        for lag in range(self._lag_min - 1, lag_max + 2):
            if lag < 1 or lag >= n:
                continue
            acc = 0.0
            for i in range(n - lag):
                acc += x[i] * x[i + lag]
            correlations[lag] = acc / energy

        # Only a true interior local maximum counts as a period. A smooth but
        # non-periodic signal -- AGC gain drift, for instance -- produces an
        # autocorrelation that decays monotonically, so a plain max() would
        # return the shortest allowed lag and report it as a fast breath.
        best_lag, best_r = 0, 0.0
        for lag in range(self._lag_min, lag_max + 1):
            r = correlations.get(lag)
            left = correlations.get(lag - 1)
            right = correlations.get(lag + 1)
            if r is None or left is None or right is None:
                continue
            if r > left and r >= right and r > best_r:
                best_r, best_lag = r, lag

        if best_lag == 0:
            return 0.0, 0.0

        refined = self._interpolate_peak(correlations, best_lag)
        bpm = 60.0 * self.sample_rate_hz / refined
        if bpm < self.min_bpm or bpm > self.max_bpm:
            return 0.0, 0.0
        return bpm, best_r

    @staticmethod
    def _interpolate_peak(correlations, peak_lag):
        """Parabolic interpolation for sub-sample lag resolution."""
        left = correlations.get(peak_lag - 1)
        right = correlations.get(peak_lag + 1)
        if left is None or right is None:
            return float(peak_lag)
        centre = correlations[peak_lag]
        denom = left - 2.0 * centre + right
        if denom == 0.0:
            return float(peak_lag)
        return peak_lag + 0.5 * (left - right) / denom
