"""Tests for breathing-rate estimation from a filtered amplitude series."""
import math
import random

from src.breathing.estimator import BreathingEstimator


def _sine(freq_hz, sample_rate_hz, duration_s, amplitude=1.0):
    n = int(sample_rate_hz * duration_s)
    return [amplitude * math.sin(2 * math.pi * freq_hz * i / sample_rate_hz)
            for i in range(n)]


def test_recovers_breathing_rate_from_clean_signal():
    """0.25 Hz is 15 breaths/min -- a normal resting adult rate."""
    fs = 20.0
    est = BreathingEstimator(sample_rate_hz=fs)
    for v in _sine(0.25, fs, duration_s=120):
        est.process(v)

    bpm, _confidence = est.estimate()

    assert 14.0 <= bpm <= 16.0


def test_noise_alone_yields_low_confidence():
    """An empty room is noise. It must not produce a confident breathing rate.

    This is the false-positive case that decides whether the lights stay on for
    nobody, so confidence has to stay clearly separable from a real signal.
    """
    fs = 20.0
    rng = random.Random(1234)
    est = BreathingEstimator(sample_rate_hz=fs)
    for _ in range(int(fs * 120)):
        est.process(rng.gauss(0.0, 1.0))

    _bpm, confidence = est.estimate()

    assert confidence < 0.2

