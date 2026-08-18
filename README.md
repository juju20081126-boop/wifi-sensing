# WiFi CSI Stationary-Presence Sensor

An experimental, camera-free presence detector for an ESP32 WROOM-32. It uses
WiFi Channel State Information (CSI) amplitude to detect the breathing-sized
periodic motion of a person sitting still, complementing a conventional motion
detector for room-light automation.

The project grew from reviewing [RuView](https://github.com/ruvnet/RuView) and
[ESPectre](https://github.com/francescopace/espectre). The immediate goal is not
pose estimation or people counting: it is preventing automatic lights from
turning off while someone is present but stationary.

## Current status

The signal-processing prototype is implemented in pure Python so it can be
ported to MicroPython:

- 0.08–0.6 Hz cascaded biquad breathing-band filter
- autocorrelation-based breathing-rate estimator (6–40 BPM)
- rejection of smooth, non-periodic AGC drift
- timestamp-aware resampling for irregular CSI packet arrival
- continuous confidence score for later precision/recall tuning
- 9 synthetic-signal tests passing

This has **not yet been validated on real CSI data or on-device MicroPython**.
The next evidence gate is a labeled recording from the actual room and ESP32.

Toolchain is prepared locally (Python 3.12, micro-espectre environment, esptool,
verified firmware image) but the board has never been powered on. Gate 0 in
[docs/PLAN.md](docs/PLAN.md) is the current blocker and it needs physical access
to the hardware.

## Quick start

Requires Python 3.11+ for local tests. The detector itself uses only the Python
standard library.

```powershell
git clone https://github.com/juju20081126-boop/wifi-sensing.git
cd wifi-sensing
python -m pip install pytest
python -m pytest -q
```

Minimal use:

```python
from src.breathing.detector import BreathingDetector

detector = BreathingDetector(sample_rate_hz=20.0)

for amplitude, timestamp_s in csi_samples:
    detector.process(amplitude, timestamp_s=timestamp_s)

result = detector.result()
print(result.bpm, result.score, result.valid)
```

Use real timestamps whenever available. Assuming a nominal packet rate scales
the reported BPM by the ratio between the nominal and actual rates.

## Repository layout

```text
src/breathing/   Pure-Python filter, resampler, estimator, and public detector
tests/           Synthetic-signal regression tests
docs/            Design rationale, two-language plans, and Windows build guide
data/            Local labeled CSI sessions (ignored by Git)
firmware/        Local upstream firmware downloads (ignored by Git)
```

## Documentation

| Document | What it covers |
|---|---|
| [docs/PLAN.md](docs/PLAN.md) | Milestones M0-M5, gate criteria, evidence standards, risks, decision log |
| [docs/BUILD-GUIDE.md](docs/BUILD-GUIDE.md) | 17 numbered Windows steps from unboxing to first recording |
| [docs/TWO-PERSON-SPLIT.md](docs/TWO-PERSON-SPLIT.md) | Roles, per-stage deliverables, and the one hard dependency |
| [docs/measurements/](docs/measurements/) | Evidence artifacts produced at each gate |

## Hardware path

The detailed Windows instructions are in [docs/BUILD-GUIDE.md](docs/BUILD-GUIDE.md).
The intended progression is:

1. Run ESPectre's ML firmware on an original ESP32 WROOM-32.
2. Verify motion-based lighting automation in Home Assistant.
3. Reflash to micro-espectre for labeled CSI collection.
4. Record `empty`, `present-moving`, and `present-still` sessions.
5. Evaluate motion-only versus motion-or-breathing on held-out sessions.
6. Integrate only if the real-data precision/recall evidence supports it.

The ESPectre firmware binary and upstream source are deliberately not committed
here. Download them from the
[ESPectre releases](https://github.com/francescopace/espectre/releases) and
repository instead.

## Known limitations

- Synthetic tests are not evidence of real-world CSI performance.
- The original ESP32 lacks AGC/FFT gain lock, adding amplitude drift.
- Link placement matters: sensing is strongest along the router-to-ESP32 path.
- WiFi CSI presence sensing is not suitable for safety-critical or medical use.
- RuView itself does not currently target the original ESP32 WROOM-32.

## Design principle

Motion and breathing are complementary. Fuse their decisions as an OR at the
state level: motion catches someone entering; breathing helps retain occupancy
when that person becomes still. Keep the breathing score continuous so its
threshold can be selected from real precision/recall data instead of guesswork.
