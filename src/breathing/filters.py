"""Breathing-band filtering for WiFi CSI amplitude series.

Pure Python with no numpy, because this runs under MicroPython on the ESP32.
Uses RBJ biquad sections in transposed direct form II.
"""
import math

# Breathing band. 0.08-0.6 Hz is 4.8-36 breaths/min, matching ESPectre PR #112.
BREATHING_LOW_HZ = 0.08
BREATHING_HIGH_HZ = 0.6

# Butterworth Q for a single 2nd-order section.
_BUTTERWORTH_Q = 1.0 / math.sqrt(2.0)


class Biquad:
    """One 2nd-order IIR section, transposed direct form II."""

    def __init__(self, b0, b1, b2, a1, a2):
        self.b0, self.b1, self.b2 = b0, b1, b2
        self.a1, self.a2 = a1, a2
        self.z1 = 0.0
        self.z2 = 0.0

    def process(self, x):
        y = self.b0 * x + self.z1
        self.z1 = self.b1 * x - self.a1 * y + self.z2
        self.z2 = self.b2 * x - self.a2 * y
        return y

    def reset(self):
        self.z1 = 0.0
        self.z2 = 0.0

    @classmethod
    def lowpass(cls, cutoff_hz, sample_rate_hz, q=_BUTTERWORTH_Q):
        w0 = 2.0 * math.pi * cutoff_hz / sample_rate_hz
        cos_w0, alpha = math.cos(w0), math.sin(w0) / (2.0 * q)
        a0 = 1.0 + alpha
        return cls(
            b0=((1.0 - cos_w0) / 2.0) / a0,
            b1=(1.0 - cos_w0) / a0,
            b2=((1.0 - cos_w0) / 2.0) / a0,
            a1=(-2.0 * cos_w0) / a0,
            a2=(1.0 - alpha) / a0,
        )

    @classmethod
    def highpass(cls, cutoff_hz, sample_rate_hz, q=_BUTTERWORTH_Q):
        w0 = 2.0 * math.pi * cutoff_hz / sample_rate_hz
        cos_w0, alpha = math.cos(w0), math.sin(w0) / (2.0 * q)
        a0 = 1.0 + alpha
        return cls(
            b0=((1.0 + cos_w0) / 2.0) / a0,
            b1=(-(1.0 + cos_w0)) / a0,
            b2=((1.0 + cos_w0) / 2.0) / a0,
            a1=(-2.0 * cos_w0) / a0,
            a2=(1.0 - alpha) / a0,
        )


class BreathingBandpass:
    """Cascaded high-pass then low-pass isolating the breathing band.

    Cascading two sections is more numerically stable at these very low
    normalised frequencies than a single bandpass biquad would be.
    """

    def __init__(self, sample_rate_hz,
                 low_hz=BREATHING_LOW_HZ, high_hz=BREATHING_HIGH_HZ):
        self.sample_rate_hz = sample_rate_hz
        self.low_hz = low_hz
        self.high_hz = high_hz
        self._highpass = Biquad.highpass(low_hz, sample_rate_hz)
        self._lowpass = Biquad.lowpass(high_hz, sample_rate_hz)

    def process(self, sample):
        return self._lowpass.process(self._highpass.process(sample))

    def reset(self):
        self._highpass.reset()
        self._lowpass.reset()
