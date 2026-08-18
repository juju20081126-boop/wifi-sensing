# Project plan

Detailed, gated plan for the WiFi CSI stationary-presence sensor.

Last updated 2026-08-18. Every "verified" claim below has evidence recorded
against it; every unverified claim says so.

---

## 1. The promise

One sentence, deliberately narrow:

> In one instrumented room, keep the lights on while a person is present but
> sitting still, without a camera, and prove it with held-out measurements
> rather than a demo.

Everything else — counting, pose, vital signs, multi-room — is out of scope.
See §7.

## 2. Where we actually are

### Verified

| Item | Evidence |
|---|---|
| Breathing detector implemented | `src/breathing/`, 4 modules, pure Python |
| 9 tests passing | `python -m pytest -q` |
| Rejects AGC-style drift | `test_slow_gain_drift_does_not_look_like_breathing` |
| Handles wrong nominal packet rate | `test_uses_real_timestamps_when_packet_rate_differs_from_nominal` |
| Finds breathing at half noise amplitude | `test_finds_breathing_buried_in_noise` |
| Firmware targets this chip | Downloaded image is 0xFF-padded to 0x1000 with `0xE9` there — classic ESP32 layout, not S3/C3 |
| `me flash` accepts our chip | `--chip {esp32,c3,s3,c5,c6}` |
| Toolchain ready | Python 3.12.13, all 18 `requirements.txt` packages, esptool 5.2.0 |

### Not verified — and load-bearing

| Gap | Why it matters |
|---|---|
| **No real CSI has ever touched this code** | Every test signal is synthetic. Synthetic success is not evidence. |
| **Never run under MicroPython** | CPython uses 64-bit floats; the ESP32 port may use 32-bit. At 0.08 Hz normalised to a ~20 Hz sample rate, biquad coefficients are numerically delicate. |
| **Board never powered on** | No COM port has ever appeared on this machine. |
| **Whether the room separates `empty` from `present-still` at all** | If it does not, the project's premise fails and we should know in week one. |

## 3. Milestones and gates

No milestone starts before the previous gate passes. A gate is a measurement,
not an opinion.

---

### M0 — Hardware bring-up

**Goal:** the board is alive and talking.

| # | Task | Owner |
|---|---|---|
| 0.1 | Connect board, confirm a COM port appears | A |
| 0.2 | Install CH9102/CH343 driver if absent | A |
| 0.3 | Start Docker Desktop, install Home Assistant | A |
| 0.4 | Flash `espectre-2.8.0-esp32-ml.bin` via ESPConnect in Chrome | A |
| 0.5 | Provision WiFi on the 2.4 GHz SSID | A |
| 0.6 | Confirm ESPHome auto-discovery in Home Assistant | A |

**Gate 0:** a movement-score entity in Home Assistant changes when you wave a
hand in front of the board.

**Fails if:** no COM port after trying a second cable and installing the driver.

---

### M1 — Motion baseline and lights

**Goal:** the original goal, working. Also the control condition every later
claim is measured against.

| # | Task | Owner |
|---|---|---|
| 1.1 | Place router and board per Layout A, 3–8 m apart | A |
| 1.2 | Walk perpendicular to the link, then parallel; record both score ranges | A |
| 1.3 | Repeat at three board positions, keep the best | A |
| 1.4 | Tune thresholds per upstream `TUNING.md` | A |
| 1.5 | Automation: motion off 10 min → lights off, plus manual override | A |

**Gate 1:** written down, not remembered —

- score while walking across the link ≥ 3× score in an empty room
- no false "occupied" during a 2-hour empty-room soak
- lights turn off within 30 s of the timeout expiring

**Artifact:** `docs/measurements/M1-placement.md` with the three positions tried
and their score ranges.

---

### M2 — Research platform and first recording

**Goal:** answer the premise question before investing weeks.

| # | Task | Owner |
|---|---|---|
| 2.1 | Reflash to MicroPython: `python me flash --chip esp32 --erase` | B |
| 2.2 | Fill `config_local.py` with WiFi and MQTT credentials | A |
| 2.3 | Install Mosquitto in Home Assistant, create MQTT user | A |
| 2.4 | `python me deploy` and `python me run` | B |
| 2.5 | Record 10 min each: `empty`, `present-moving`, `present-still` | A |
| 2.6 | Measure the actual packet rate and loss | B |
| 2.7 | Plot amplitude variance for all three blocks | B |

**Gate 2 — the premise test:**

- packet rate is stable and its actual value is recorded (expect 13–19 Hz)
- `empty` and `present-moving` are visually separable — **must pass**
- `empty` versus `present-still` is characterised, separable or not

**This gate cannot fail the project, but it can redirect it.** If `present-still`
is indistinguishable from `empty` in raw variance, that is the gap confirmed and
M3 proceeds. If it is *already* separable, the problem is easier than assumed and
the contribution shrinks — say so publicly rather than inventing difficulty.

**Artifact:** `docs/measurements/M2-first-recording.md` with plots and the
measured packet rate.

---

### M3 — The labeled dataset

**Goal:** the thing PR #112 lacked. This is the real product work.

| # | Task | Owner |
|---|---|---|
| 3.1 | Agree the session manifest format before recording anything | A + B |
| 3.2 | Record ≥ 12 sessions across ≥ 4 different days | A |
| 3.3 | Include long empty periods with HVAC, doors, curtains moving | A |
| 3.4 | Include entry, exit, walking, sitting, lying, near-still reading | A |
| 3.5 | Include a second person in at least 3 sessions | A |
| 3.6 | Include one session after moving furniture or the board | A |
| 3.7 | Verify every session has complete labels and a manifest entry | B |

**Session manifest fields**, fixed before the first recording:

```
session_id, date, start_time, end_time, room, board_position,
router_position, label, subject_count, wifi_channel, packet_rate_hz,
firmware_version, notes
```

**Label vocabulary — exactly three, no improvising a fourth:**
`empty`, `present-moving`, `present-still`

**Gate 3:**

- ≥ 12 sessions, ≥ 4 distinct days
- ≥ 2 hours total of `present-still`
- ≥ 3 hours total of `empty`
- every session has a complete manifest row
- a train/test split assigned **by session**, never by frame

**Artifact:** `data/manifest.csv` (local, gitignored) plus a committed summary.

---

### M4 — Validate the detector

**Goal:** the evidence the maintainer asked for and never received.

| # | Task | Owner |
|---|---|---|
| 4.1 | Replay recorded sessions through `BreathingDetector` offline | B |
| 4.2 | Verify it runs unmodified under MicroPython on-device | B |
| 4.3 | Sweep the score threshold, plot precision/recall | B |
| 4.4 | Evaluate **only on windows where the motion detector reports idle** | B |
| 4.5 | Compare motion-only vs motion-OR-breathing | B |
| 4.6 | Report per-session, per-day, per-subject breakdowns | B |
| 4.7 | Document the failure cases honestly | B |

**Baselines that must be beaten, or the result is not interesting:**

1. always-occupied (majority class)
2. RSSI-only threshold
3. raw amplitude-variance threshold

**Gate 4:**

- on held-out sessions, motion-OR-breathing recovers ≥ 50% of `present-still`
  intervals that motion-only misses
- fewer than 1 false "occupied" per 24 empty-room hours
- results reported **by session**, with no frame-level splitting anywhere

Numbers are frozen before the final test run, not chosen after seeing results.

**Artifact:** `docs/measurements/M4-evaluation.md` — confusion matrix, PR curve,
baseline comparison, failure examples.

---

### M5 — Contribute upstream

Only after Gate 4 passes.

| # | Task | Owner |
|---|---|---|
| 5.1 | Check ESPectre forks and open PRs for existing breathing work | B |
| 5.2 | Port the detector into `micro-espectre/src/` — **Python only, no C++** | B |
| 5.3 | Register through `detector_interface.py` as a real user-facing option | B |
| 5.4 | Add tests matching upstream conventions | B |
| 5.5 | Open the PR with the M4 evaluation attached | B |
| 5.6 | Credit both contributors — code and evidence | A + B |

**Gate 5:** PR opened with evaluation evidence, addressing all four reasons
PR #112 was closed.

Note ESPectre is GPLv3; derivative work inherits that licence.

---

## 4. Evidence standards

Non-negotiable, because they are how the last attempt failed.

1. **Split by session, never by frame.** Adjacent frames are near-identical;
   random frame splitting leaks the test set into training and inflates accuracy.
2. **Hold out a day, a person, and a board position.**
3. **Report event-level metrics**, not frame accuracy — false transitions per
   empty hour, missed occupied intervals, detection latency.
4. **Freeze targets before the final run.**
5. **Publish failure cases.** A report with no failures is not a report.
6. **Label every claim** as measured, synthetic, or unverified.

## 5. Risks

| Risk | Consequence | Mitigation |
|---|---|---|
| AGC drift on WROOM-32 confounds the breathing band | False occupancy | Already mitigated in code by requiring a true local autocorrelation maximum; verify on real data at M2 |
| MicroPython 32-bit floats destabilise the biquads | Filter misbehaves on-device | Task 4.2 tests on-device early; fall back to a higher sample rate or fixed-point if needed |
| Room overfitting | Works in one room only | Gate 3 requires a furniture-moved session; scope claims to the tested room |
| `present-still` never separates | Premise fails | Gate 2 finds this in week one, not month three |
| Only one board | Two people take turns | Buy a second (~$10); prefer ESP32-C6 |
| Dataset collection stalls | Project dies quietly | It is the boring stage; M3 has explicit session counts so progress is visible |
| Someone else lands breathing detection first | Contribution redundant | Task 5.1, and check again before M4 |

## 6. Two-person split

Full detail in [TWO-PERSON-SPLIT.md](TWO-PERSON-SPLIT.md).

- **Person A — hardware and data.** M0, M1, M2 recording, M3 collection.
- **Person B — code and evaluation.** M2 analysis, M4, M5.

The only hard dependency is **A's dataset → B's evaluation at M4**. B is not
blocked before then: the detector is already written and can be exercised on
synthetic and public data.

## 7. Explicit non-goals

Stated so scope cannot creep in quietly:

- people counting (interesting, but ~4–5 per link is the physical ceiling)
- pose estimation (needs research-grade MIMO; ~3% accuracy on ESP32)
- heart rate (harder than breathing, and unnecessary here)
- multi-room or whole-home coverage
- anything safety-critical or medical
- rebuilding RuView's architecture — it does not target this chip

## 8. Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-08-17 | ESPectre, not RuView | RuView builds only for esp32s3/c6/c3; the bought board is unsupported |
| 2026-08-17 | `-ml` firmware, not MVS | MVS uses CV normalisation (σ/μ) which this chip's missing gain lock degrades; ML uses raw σ |
| 2026-08-17 | Target presence, not counting | The lighting use case is binary; crowd limits do not apply |
| 2026-08-17 | Continuous score, not boolean | Needed to sweep a threshold and plot precision/recall offline |
| 2026-08-17 | Pure Python, no numpy | Must run unmodified under MicroPython |
| 2026-08-18 | Detector owns the filter | A test proved raw samples reaching autocorrelation directly produce a wrong answer; easy-to-misuse was the defect |
| 2026-08-18 | Repository stays private for now | Prototype unvalidated on real CSI |
