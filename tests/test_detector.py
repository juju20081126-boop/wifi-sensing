"""Tests for BreathingDetector -- the public API that owns filter + estimator.

These are the realistic tests. The detector is what the ESPectre integration
calls, and it is the only entry point that guarantees samples are band-filtered
before autocorrelation sees them.
"""
import math
import random

from src.breathing.detector import BreathingDetector


def _feed(detector, samples):
    for v in samples:
        detector.process(v)


def test_finds_breathing_buried_in_noise():
    """Breathing at half the noise amplitude, roughly real-world SNR."""
    fs = 20.0
    rng = random.Random(99)
    det = BreathingDetector(sample_rate_hz=fs)
    _feed(det, [0.5 * math.sin(2 * math.pi * 0.3 * i / fs) + rng.gauss(0.0, 1.0)
                for i in range(int(fs * 180))])

    result = det.result()

    assert 16.0 <= result.bpm <= 20.0        # 0.3 Hz is 18 breaths/min
    assert result.score > 0.2


def test_empty_room_noise_produces_low_score():
    """No periodic component means no breathing, however the noise falls."""
    fs = 20.0
    rng = random.Random(4321)
    det = BreathingDetector(sample_rate_hz=fs)
    _feed(det, [rng.gauss(0.0, 1.0) for _ in range(int(fs * 180))])

    assert det.result().score < 0.2


def test_slow_gain_drift_does_not_look_like_breathing():
    """The WROOM-32 lacks AGC gain lock, so amplitude wanders on its own.

    A 0.01 Hz drift is far slower than any breath and must not be reported as
    one, or an empty room reads as occupied on this specific hardware.
    """
    fs = 20.0
    det = BreathingDetector(sample_rate_hz=fs)
    _feed(det, [3.0 * math.sin(2 * math.pi * 0.01 * i / fs)
                for i in range(int(fs * 300))])

    assert det.result().score < 0.2


def test_uses_real_timestamps_when_packet_rate_differs_from_nominal():
    """CSI packets do not arrive at the configured rate.

    Here the true rate is 13 Hz while the detector is configured for 20 Hz.
    Assuming the nominal rate would scale the answer by 20/13 and report about
    28 bpm for an 18 bpm signal. Timestamps must win over configuration.
    """
    nominal_fs, true_fs = 20.0, 13.0
    det = BreathingDetector(sample_rate_hz=nominal_fs)
    n = int(true_fs * 240)
    for i in range(n):
        t = i / true_fs
        det.process(math.sin(2 * math.pi * 0.3 * t), timestamp_s=t)

    result = det.result()

    assert 16.0 <= result.bpm <= 20.0     # 0.3 Hz is 18 bpm
