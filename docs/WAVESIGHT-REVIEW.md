# WaveSight design review

Source reviewed: [ErfanDL/WaveSight](https://github.com/ErfanDL/WaveSight) at
commit `61ce3a619a1a73af16362ee60e19f33babaee005` on 2026-08-18.

## What WaveSight adds to the design conversation

WaveSight is an ESP-IDF application around Espressif's `esp-radar` component.
Its useful product-level patterns are:

- Empty-room calibration with thresholds saved in non-volatile storage
- A rolling evidence window that requires K threshold crossings out of N
  samples before declaring movement
- Separate movement and longer-lived `someone` outputs
- A configurable timeout that holds presence after the last movement
- A local web dashboard, GPIO outputs, SoftAP fallback, and device reset paths

These are device-integration ideas, not a stationary-breathing algorithm.

## Important finding

In the reviewed callback, WaveSight first compares the current radar jitter to a
`someone` threshold, but then replaces that result with a timeout based on the
last detected movement. In practice, its final `someone` state is a motion hold,
not proof of a stationary person.

That makes it complementary to this project rather than a replacement. Our
breathing detector supplies the missing stationary evidence; WaveSight supplies
a useful pattern for turning noisy evidence into stable state.

## What we adapted

We added `src/presence/tracker.py`, written from scratch, with:

1. Immediate occupancy on movement
2. A configurable movement hold timeout
3. K-of-N confirmation for weak breathing evidence
4. Separate activation and clearing thresholds for hysteresis
5. A final state reason: `motion`, `breathing`, `motion+breathing`, or `empty`

This closes a real gap in the previous prototype: the README said to fuse motion
and breathing as an OR, but there was no code that performed that fusion.

## What we did not take

- **No source code was copied.** The WaveSight application root does not contain
  a license file. Its bundled Espressif `esp-radar` component is Apache-2.0, but
  that does not automatically license WaveSight's own application code.
- The dashboard and GPIO/NVS code are outside the current Python prototype.
- Empty-room auto-calibration should wait for real CSI recordings. Inventing a
  threshold formula before seeing the score distribution would create false
  confidence.
- We did not replace ESPectre or micro-espectre as the planned firmware/data path.

## Next useful idea after real data exists

WaveSight's empty-room calibration is the next candidate. Once labeled
`empty` sessions exist, calculate an activation threshold from the observed
empty-room breathing-score distribution, save the calibration metadata, and
verify it on a different held-out session before enabling automatic lights.
