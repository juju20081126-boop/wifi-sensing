# WiFi CSI Stationary-Presence Sensor

An experimental, camera-free presence detector for an ESP32 WROOM-32. It uses
WiFi Channel State Information (CSI) amplitude to detect the breathing-sized
periodic motion of a person sitting still, complementing a conventional motion
detector for room-light automation.

The project grew from reviewing [RuView](https://github.com/ruvnet/RuView),
[ESPectre](https://github.com/francescopace/espectre), and
[WaveSight](https://github.com/ErfanDL/WaveSight). The immediate goal is not pose
estimation or people counting: it is preventing automatic lights from turning
off while someone is present but stationary.

## Active hardware scope — first plan

This repository's active plan is for **one specific board only**:

| Part | Exact scope |
|---|---|
| Sensing module | Original ESP32-WROOM-32 DevKit |
| USB bridge | CH9102X |
| Connector | Micro-USB |
| WiFi | 2.4 GHz 802.11 b/g/n |
| Quantity | One board |

CH9102X is the USB-to-serial bridge used for flashing and serial communication;
the ESP32-WROOM-32 is the module that performs WiFi CSI sensing. ESP32-C6,
ESP32-S3, second-board layouts, meshes, and pose estimation are not part of this
first plan.

## Current status

The signal-processing prototype is implemented in pure Python so it can be
ported to MicroPython:

- 0.08–0.6 Hz cascaded biquad breathing-band filter
- autocorrelation-based breathing-rate estimator (6–40 BPM)
- rejection of smooth, non-periodic AGC drift
- timestamp-aware resampling for irregular CSI packet arrival
- continuous confidence score for later precision/recall tuning
- stateful motion-or-breathing occupancy fusion with K-of-N evidence,
  hysteresis, and a configurable motion hold
- 15 synthetic and state-machine tests passing

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

Fuse that score with an existing motion detector:

```python
from src.presence.tracker import PresenceTracker

presence = PresenceTracker(motion_hold_s=180.0)
state = presence.update(
    timestamp_s=packet_time,
    motion_detected=motion_state,
    breathing_score=result.score,
)
print(state.occupied, state.reason)
```

Breathing evidence must win a K-of-N vote, while motion marks occupancy
immediately and remains held for the configured timeout.

## Repository layout

```text
src/breathing/     Pure-Python filter, resampler, estimator, and public detector
src/presence/      Stateful motion/breathing fusion and occupancy hold
firmware-radar/    Second, independent implementation: ESP-IDF + Espressif's
                    esp-radar component, own web dashboard. See its own README.
tests/             Synthetic-signal regression tests
docs/              Design rationale, two-language plans, and Windows build guide
data/              Local labeled CSI sessions (ignored by Git)
firmware/          Local upstream firmware downloads (ignored by Git)
```

**Two parallel tracks, same board, same promise.** `src/breathing/` +
`src/presence/` process raw CSI in Python via ESPectre/MicroPython.
`firmware-radar/` uses Espressif's own official `esp-radar` component
directly in C via ESP-IDF, with a self-hosted dashboard inspired by
[WaveSight](https://github.com/ErfanDL/WaveSight) but written from scratch —
see [firmware-radar/README.md](firmware-radar/README.md) for why it exists
and its own honest verification status. Both target the original
ESP32-WROOM-32; neither replaces the other yet. Evaluation against
[docs/PLAN.md](docs/PLAN.md)'s gates decides which one this project
eventually builds on, or whether both survive.

## Documentation

| Document | What it covers |
|---|---|
| [docs/VISION.md](docs/VISION.md) | **Read first.** What the finished project looks like — dashboard mockup, evaluation report shape, the eventual PR. All illustrative, none of it measured yet |
| [docs/TODO.md](docs/TODO.md) | **Checklist.** Every stage, what materials it needs, and what to do — check boxes as you go |
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | **Read third.** How the project works: verification discipline, TDD case studies, evidence standards, licensing rules |
| [docs/PLAN.md](docs/PLAN.md) | Milestones M0-M5, gate criteria, evidence standards, risks, decision log |
| [docs/BUILD-GUIDE.md](docs/BUILD-GUIDE.md) | 17 numbered Windows steps from unboxing to first recording |
| [docs/measurements/](docs/measurements/) | Evidence artifacts produced at each gate |
| [docs/WAVESIGHT-REVIEW.md](docs/WAVESIGHT-REVIEW.md) | WaveSight comparison, selected design pattern, and licensing boundary |
| [firmware-radar/README.md](firmware-radar/README.md) | The ESP-IDF/esp-radar track — architecture, the exact gap it fixes, verification status |

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

`PresenceTracker` now implements this design. Its temporal evidence window and
motion hold were inspired by WaveSight's device architecture, but were written
from scratch because WaveSight's root application has no license file. See the
[design review](docs/WAVESIGHT-REVIEW.md) for the comparison and boundary.
