# Vision — what the finished project looks like

Everything in this document is **illustrative, not measured**. Using this
project's own evidence vocabulary (see
[METHODOLOGY.md §5](METHODOLOGY.md#5-evidence-first-evaluation-discipline)):
every number, screenshot mockup, and quote on this page is a **target**, not a
result. Nothing here has been produced by real hardware yet. Its purpose is to
make the destination concrete before the work happens, so progress can be
checked against a picture rather than a vague feeling of "done."

When Gate 4 in [PLAN.md](PLAN.md) actually passes, the real numbers replace
the placeholder numbers below, and this file gets a status change at the top
saying so.

---

## 1. The physical setup

One room, one router already in the house, one ESP32 on the opposite wall.
Nothing about the room changes — no new fixtures, no visible sensor, no app
to install for guests.

```
    +-----------------------------------------+
    |                                         |
    |                              +--------+ |
    |                          .-' | ESP32  | |
    |                      .-'     +--------+ |
    |                  .-'                    |
    |              .-'   <-- sensing link     |
    |          .-'                            |
    | +--------+                              |
    | | router |                              |
    | +--------+                              |
    |                                         |
    +-----------------------------------------+
```

## 2. What the Home Assistant dashboard shows

Three moments, same room, same evening. `motion` and `breathing_score` are
sensor entities the board publishes today (motion is real; `breathing_score`
is what M4 validates). `occupancy` is the fused decision from
`src/presence/tracker.py`. `lights` is the automation's actual action.

| Time | Situation | motion | breathing_score | occupancy | lights |
|---|---|---|---|---|---|
| 20:04 | Walks in, sits down | on → off | 0.10 | **occupied** (reason: `motion`) | on |
| 20:19 | Reading, barely moving | off | 0.71 | **occupied** (reason: `breathing`) | **stays on** |
| 21:47 | Leaves, door closes | off | 0.04 | **empty** | off, after the 10-minute hold |

The middle row is the entire point of the project. Every existing motion-only
system reads that row as empty and turns the light off on a person who is
still in the room.

## 3. What the finished evaluation report contains

`docs/measurements/M4-evaluation.md` does not exist yet — it is a placeholder
folder today (see [docs/measurements/README.md](measurements/README.md)).
When Gate 4 in PLAN.md is met, that file will look roughly like this. The
structure is fixed now; the numbers are not:

```markdown
# M4 evaluation — [fill in date]

Dataset: N sessions, N distinct days (see data/manifest.csv, not committed)
Code/model version: [git commit hash]

## Headline result

| Detector | present-still recall | false-occupied / empty-hour |
|---|---:|---:|
| motion-only (baseline)        | ??% | ??  |
| always-occupied (baseline)    | 100%| high|
| RSSI-only (baseline)          | ??% | ??  |
| motion OR breathing (this project) | ??% | ?? |

## Confusion matrix (session-level)

[actual matrix]

## Failure cases

[at least three real examples, described honestly]

## Per-day / per-subject breakdown

[table]
```

Every `??` is a number this project does not have yet. Gate 4's targets —
recovering at least 50% of the `present-still` intervals motion-only misses,
fewer than one false-occupied event per 24 empty-room hours — were written
into PLAN.md **before** this table has real numbers to put in it, on purpose.

## 4. What the upstream contribution looks like

A pull request against [ESPectre](https://github.com/francescopace/espectre),
written to directly answer the four reasons
[PR #112](https://github.com/francescopace/espectre/pull/112) was closed
unmerged:

> **Title:** Add stationary-presence detection via breathing-band CSI analysis
>
> This adds an optional breathing-band detector that complements the existing
> motion detector for the case where a person is present but not moving.
>
> - Implemented in `micro-espectre` (Python), per the project's
>   Python-before-C++ workflow
> - Registered through `detector_interface.py` as a real, user-facing,
>   opt-in detection mode — not a signal that is computed but unused
> - Evaluation on N held-out sessions attached below, with a session-level
>   train/test split, three baselines, and documented failure cases
> - Reset paths and state ownership covered by unit tests
>
> [Evaluation report linked here]

This is a draft of intent, not a submitted PR. It exists so Milestone M5 in
PLAN.md has a concrete shape to build toward rather than an abstract "open a
PR" checkbox.

## 5. What using the finished library looks like

This part is close to real today — the API below already exists and is
tested (see `README.md` Quick start) — but the two pieces have not yet been
exercised together against a live CSI stream:

```python
from src.breathing.detector import BreathingDetector
from src.presence.tracker import PresenceTracker

breathing = BreathingDetector(sample_rate_hz=15.0)  # measured rate, not assumed
presence = PresenceTracker(motion_hold_s=180.0)

for amplitude, timestamp_s, motion in live_csi_stream():
    breathing.process(amplitude, timestamp_s=timestamp_s)
    result = breathing.result()
    state = presence.update(
        timestamp_s=timestamp_s,
        motion_detected=motion,
        breathing_score=result.score,
    )
    if not state.occupied:
        turn_off_lights()
```

## 6. What "done" means

Not a demo video. Not a single successful walkthrough. Done means:

- Gate 4's frozen targets are met on held-out sessions the code has never
  seen, evaluated by session, with baselines beaten and failures published.
- The PR in §4 is real, open, and references that evaluation.
- Someone who was not involved in building this could read
  [docs/measurements/M4-evaluation.md](measurements/README.md) and trust the
  numbers without re-running the experiment themselves.

That last line is the actual bar. Everything else in this repository exists
to clear it.
