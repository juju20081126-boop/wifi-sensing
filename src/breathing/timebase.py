"""Resampling irregular CSI packets onto a uniform grid.

CSI packets do not arrive at a fixed cadence -- rates between 13 and 19 Hz have
been observed where 20 was nominal. Autocorrelation and every frequency-domain
method assume uniform spacing, so converting a measured BPM with an assumed
rate silently scales the answer. This stage removes that error.

Pure Python -- runs under MicroPython on the ESP32.
"""


class UniformResampler:
    """Linearly interpolates irregular (timestamp, value) pairs onto a grid."""

    def __init__(self, sample_rate_hz):
        self.sample_rate_hz = sample_rate_hz
        self._dt = 1.0 / sample_rate_hz
        self._prev_t = None
        self._prev_v = None
        self._next_t = None

    def reset(self):
        self._prev_t = None
        self._prev_v = None
        self._next_t = None

    def push(self, value, timestamp_s):
        """Return the list of grid samples completed by this input."""
        if self._prev_t is None:
            self._prev_t = timestamp_s
            self._prev_v = value
            self._next_t = timestamp_s
            return []

        # Ignore out-of-order or duplicate timestamps rather than extrapolate.
        if timestamp_s <= self._prev_t:
            return []

        out = []
        span = timestamp_s - self._prev_t
        while self._next_t <= timestamp_s:
            frac = (self._next_t - self._prev_t) / span
            out.append(self._prev_v + frac * (value - self._prev_v))
            self._next_t += self._dt

        self._prev_t = timestamp_s
        self._prev_v = value
        return out
