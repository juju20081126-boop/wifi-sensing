"""Tests for the breathing-band bandpass filter.

The filter must run on MicroPython on the ESP32, so the implementation is pure
Python -- no numpy. Tests may use numpy since they run on a laptop.
"""
import math

from src.breathing.filters import BreathingBandpass


def _sine(freq_hz, sample_rate_hz, duration_s, amplitude=1.0):
    n = int(sample_rate_hz * duration_s)
    return [amplitude * math.sin(2 * math.pi * freq_hz * i / sample_rate_hz)
            for i in range(n)]


def _settled_amplitude(samples):
    """Peak amplitude over the back half, after filter transients decay."""
    tail = samples[len(samples) // 2:]
    return max(abs(v) for v in tail)


def test_passes_signal_at_centre_of_breathing_band():
    """A 0.25 Hz sine (15 breaths/min) should survive with most of its amplitude."""
    fs = 20.0
    x = _sine(0.25, fs, duration_s=120)

    bp = BreathingBandpass(sample_rate_hz=fs)
    y = [bp.process(v) for v in x]

    assert 0.7 <= _settled_amplitude(y) <= 1.3


def test_rejects_slow_drift_below_the_band():
    """AGC gain drift on the WROOM-32 shows up as very slow amplitude wander.

    At 0.01 Hz it sits well below the 0.08 Hz corner and must be suppressed,
    otherwise it masquerades as breathing.
    """
    fs = 20.0
    x = _sine(0.01, fs, duration_s=600)

    bp = BreathingBandpass(sample_rate_hz=fs)
    y = [bp.process(v) for v in x]

    assert _settled_amplitude(y) < 0.1


def test_rejects_heart_rate_band_above_the_band():
    """1.2 Hz (72 bpm) is cardiac, not respiratory, and must not leak through."""
    fs = 20.0
    x = _sine(1.2, fs, duration_s=120)

    bp = BreathingBandpass(sample_rate_hz=fs)
    y = [bp.process(v) for v in x]

    assert _settled_amplitude(y) < 0.3
