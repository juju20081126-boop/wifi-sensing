"""Stationary-presence detection from breathing in WiFi CSI amplitude.

This is the public API. It exists as a single object because the estimator is
only valid on band-filtered input -- routing raw samples straight into
autocorrelation makes low-frequency noise masquerade as a slow breath. Owning
both stages here makes that misuse impossible.

Complements motion detection rather than replacing it: motion catches someone
walking in, breathing catches someone sitting still. Fuse them as an OR at the
state level.

Pure Python -- runs under MicroPython on the ESP32.
"""
from .filters import BreathingBandpass
from .estimator import BreathingEstimator
from .timebase import UniformResampler


class BreathingResult:
    """One detection outcome.

    score is a continuous 0-1 confidence rather than a boolean so the decision
    threshold can be tuned offline against recorded data, and so precision and
    recall can be swept without recollecting.
    """

    def __init__(self, bpm, score, valid):
        self.bpm = bpm
        self.score = score
        self.valid = valid

    def __repr__(self):
        return "BreathingResult(bpm=%.1f, score=%.3f, valid=%s)" % (
            self.bpm, self.score, self.valid)


class BreathingDetector:
    def __init__(self, sample_rate_hz, window_s=30.0):
        self.sample_rate_hz = sample_rate_hz
        self._bandpass = BreathingBandpass(sample_rate_hz)
        self._estimator = BreathingEstimator(sample_rate_hz, window_s=window_s)
        self._resampler = UniformResampler(sample_rate_hz)

    def process(self, sample, timestamp_s=None):
        """Feed one CSI amplitude sample. Filtering happens here, always.

        Pass timestamp_s whenever packet arrival times are known. Without it
        the nominal rate is assumed, which biases the reported BPM by exactly
        the ratio of nominal to actual packet rate.
        """
        if timestamp_s is None:
            self._estimator.process(self._bandpass.process(sample))
            return
        for gridded in self._resampler.push(sample, timestamp_s):
            self._estimator.process(self._bandpass.process(gridded))

    def reset(self):
        self._bandpass.reset()
        self._estimator.reset()
        self._resampler.reset()

    def result(self):
        bpm, confidence = self._estimator.estimate()
        valid = bpm > 0.0
        return BreathingResult(bpm=bpm, score=confidence if valid else 0.0,
                               valid=valid)
