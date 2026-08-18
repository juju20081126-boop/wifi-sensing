# To-do list — ESP32-WROOM-32 DevKit (CH9102X, one board)

A single checklist for the whole project, stage by stage. Each stage lists
exactly what you need before you start it and exactly what to do. Check boxes
as you go — this file is meant to be edited, not just read.

- **What the finished project looks like:** [VISION.md](VISION.md)
- **What to build and why:** [../README.md](../README.md)
- **How we work:** [METHODOLOGY.md](METHODOLOGY.md)
- **Gates, evidence, and the full schedule:** [PLAN.md](PLAN.md)
- **Exact Windows commands for every step below:** [BUILD-GUIDE.md](BUILD-GUIDE.md)

This file is the short version of all three. When a step needs more detail than
fits here, it links to the document that has it.

> **Fixed scope:** Every checkbox in this file is for the one board already
> purchased: an original ESP32-WROOM-32 DevKit with a CH9102X USB-to-serial
> bridge and Micro-USB connector. CH9102X creates the COM port; it is not the
> sensing processor. Do not substitute an ESP32-C6/S3 or add a second board to
> this checklist.

---

## Master materials list

Buy or gather these before Stage 1. Nothing below Stage 4 is needed yet.

| Item | Needed for | Cost | Have it? |
|---|---|---|---|
| ESP32-WROOM-32 DevKit with CH9102X bridge | Everything | Bought (NT$265) | [x] |
| Micro-USB **data** cable (not charge-only) | Flashing | Check what you have first | [ ] |
| 2.4 GHz WiFi network | Provisioning the board | Existing router | [ ] |
| A Windows PC with Chrome | Flashing, everything | This machine | [x] |
| A machine that can stay powered on | Home Assistant | This machine or a Pi | [ ] |
| Docker Desktop | Home Assistant | Installed, daemon needs starting | [ ] |
| Python 3.12 | The research track | Installed via `uv` | [x] |

This is intentionally a **one-board materials list**. Additional boards are a
separate future scope decision, not a later checkbox in this plan.

---

## Stage 1 — Prove the board is alive

**Materials needed:** the board, a micro-USB cable, this PC.

**Do:**

- [ ] Plug the board in
- [ ] Run `Get-PnpDevice -Class Ports -Status OK` in PowerShell
- [ ] A `COM*` port mentioning CH9102X or USB-SERIAL must appear
- [ ] If nothing appears: try a different cable first, then install the
      CH9102X driver from WCH

**Stop here if it fails.** Nothing else works without this. Full detail:
[BUILD-GUIDE.md Step 1](BUILD-GUIDE.md#step-1--prove-the-board-enumerates).

---

## Stage 2 — Get the software platform running

**Materials needed:** Docker Desktop (already installed), this PC, your WiFi
password, 15 minutes.

**Do:**

- [ ] Start Docker Desktop
- [ ] Run the Home Assistant container (command in BUILD-GUIDE Step 2)
- [ ] Open `http://localhost:8123` and create an account
- [ ] Download `espectre-2.8.0-esp32-ml.bin` from the
      [ESPectre releases page](https://github.com/francescopace/espectre/releases/latest) —
      the `esp32` chip, the `-ml` detector, **not** `-ota`

Full detail: [BUILD-GUIDE.md Steps 2–3](BUILD-GUIDE.md#step-2--install-home-assistant).

---

## Stage 3 — Flash and capture movement (current priority)

**Materials needed:** the firmware `.bin` from Stage 2, Google Chrome
specifically, your 2.4 GHz WiFi name and password.

**Goal for right now: reliable movement detection only.** The lights
automation at the bottom of this stage is real and documented but
**deliberately deferred** — do not do it yet. Get movement capture solid
first.

**Do:**

- [ ] Open the [ESPConnect flasher](https://thelastoutpostworkshop.github.io/ESPConnect/)
      in Chrome, connect, select the `.bin`, flash
      (hold BOOT on the board if it stalls)
- [ ] Provision WiFi — BLE via Home Assistant Companion app is easiest.
      **Use the 2.4 GHz network; this chip cannot see 5 GHz**
- [ ] Confirm the board auto-discovers in Home Assistant (Settings → Devices
      and Services)
- [ ] Place the board: router in one corner, board in the opposite corner,
      3–8 m apart, nothing metal in the direct line between them
- [ ] Walk across that line, then parallel to it — the score should jump for
      the first and barely move for the second
- [ ] Try three positions, keep the best, tune thresholds
- [ ] Watch the movement-score entity in Home Assistant over a normal hour —
      confirm it tracks real movement with no obvious false triggers

**Gate — do not skip:** there must be a clear score gap between "walking" and
"empty room." If there isn't, go back and move the board. No software fixes
bad placement.

Full detail: [BUILD-GUIDE.md Steps 4–8](BUILD-GUIDE.md#step-4--flash-it).
Evidence to record: [PLAN.md Gate 1](PLAN.md#m1--motion-baseline-and-lights).

**Movement capture is the deliverable here. Stop at this point for now.**

### Deferred — do later, not now

- [ ] Write the automation: motion off 10 minutes → lights off, plus a manual
      override (Full detail: [BUILD-GUIDE.md Step 9](BUILD-GUIDE.md#step-9--the-automation))

---

## Stage 4 — Set up the research platform

**Materials needed:** the same board (it gets reflashed — reversible, nothing
lost), a second router/broker setup (Mosquitto, inside Home Assistant), 30–45
minutes.

**Do:**

- [ ] `git clone https://github.com/francescopace/espectre.git`
- [ ] Create a Python 3.12 virtual environment inside `micro-espectre/`
- [ ] `pip install -r requirements.txt`
- [ ] `python me flash --chip esp32 --erase`
- [ ] `python me verify`
- [ ] Install the Mosquitto broker add-on in Home Assistant, create an MQTT
      user
- [ ] Copy `src/config_local.py.example` to `src/config_local.py` and fill in
      your WiFi and MQTT credentials — **never commit this file**
- [ ] `python me deploy` then `python me run`

Full detail: [BUILD-GUIDE.md Steps 10–16](BUILD-GUIDE.md#step-10--get-the-code).

---

## Stage 5 — The first real recording

**Materials needed:** the research platform running (Stage 4), 30 quiet
minutes, a way to note start/end times.

**Do:**

- [ ] `python me collect --label empty --duration 600 --samples 1` —
      leave the room
- [ ] `python me collect --label present-moving --duration 600 --samples 1` —
      walk and sit normally
- [ ] `python me collect --label present-still --duration 600 --samples 1` —
      sit and read, barely moving
- [ ] `python me collect --info` to see what was gathered
- [ ] Check: is the packet rate stable, and what is it actually (expect
      13–19 Hz, not 20)?
- [ ] Check: does `empty` look different from `present-moving`? (It must.)
- [ ] Check: does `empty` look different from `present-still`? (This is the
      question the whole project exists to answer.)

**This single recording answers the one question no code can answer.**
Full detail and why it matters:
[PLAN.md Gate 2](PLAN.md#m2--research-platform-and-first-recording).

---

## Stage 6 — Build the labeled dataset

**Materials needed:** the research platform, patience, ideally a second person
(see below), a place to store recordings.

**Do:**

- [ ] Agree the session manifest fields with your project partner **before**
      recording anything (see [PLAN.md §3, M3](PLAN.md))
- [ ] Record at least 12 sessions across at least 4 different days
- [ ] Include long empty periods with fans, HVAC, doors, curtains moving
- [ ] Include entry, exit, walking, sitting, lying down, near-still reading
- [ ] Include a second person present in at least 3 sessions
- [ ] Include one session after moving furniture or the board
- [ ] Use only these three labels — never invent a fourth:
      `empty`, `present-moving`, `present-still`
- [ ] Confirm every session has a complete manifest row

**This is the boring stage. It is also the actual product of the project** —
see [METHODOLOGY.md §2](METHODOLOGY.md#2-find-prior-art-and-read-why-it-failed-before-building-anything).

---

## Stage 7 — Evaluate the detector

**Materials needed:** the dataset from Stage 6, this repo's code
(`src/breathing/`, `src/presence/`), nothing new to buy.

**Do:**

- [ ] Replay recorded sessions through `BreathingDetector` offline
- [ ] Verify the detector runs unmodified under MicroPython on the board
- [ ] Sweep the score threshold and plot precision/recall
- [ ] Evaluate only on windows where the motion detector reports idle
- [ ] Compare motion-only vs. motion-OR-breathing using
      `src/presence/tracker.py`
- [ ] Compare against three baselines: always-occupied, RSSI-only, raw
      amplitude-variance
- [ ] Split every train/test assignment **by session, never by frame**
- [ ] Write up the failure cases honestly, not just the successes

Full detail and frozen targets: [PLAN.md Gate 4](PLAN.md#m4--validate-the-detector).

---

## Stage 8 — Contribute upstream

**Materials needed:** the Stage 7 evaluation report, nothing new to buy.

**Do:**

- [ ] Check ESPectre's forks and open PRs one more time for new breathing work
- [ ] Port the detector into `micro-espectre/src/` — **Python only, no C++**
- [ ] Register it through `detector_interface.py` as a real option, not just
      an exposed number
- [ ] Add tests matching the upstream project's conventions
- [ ] Open the pull request with the Stage 7 evaluation attached
- [ ] Credit both contributors — the code and the evidence are equally the
      contribution

Full detail: [PLAN.md M5](PLAN.md#m5--contribute-upstream). Note: ESPectre is
GPLv3, so this code inherits that license once contributed.

---

## If you are splitting this across two people

Stages 1–3 and 6 are Person A's (hardware, placement, recording). Stages 4–5
and 7–8 are Person B's (software, evaluation, the PR). The only stage that
blocks the other person is Stage 6 → Stage 7 — everything else can run in
parallel.

Both people share the same WROOM-32. Schedule hardware sessions rather than
adding a second board to this plan.
