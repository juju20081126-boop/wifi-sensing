# Presence radar (ESP-IDF)

A second, independent implementation of stationary-presence detection for
this project, built directly on Espressif's official `esp-radar` component
instead of raw CSI processing in Python. Inspired by
[WaveSight](https://github.com/ErfanDL/WaveSight) — read in full before this
was written — but no WaveSight source code is included here. See
[../docs/WAVESIGHT-REVIEW.md](../docs/WAVESIGHT-REVIEW.md) for the original
review and [the finding below](#the-gap-this-fixes) for what changed after
reading WaveSight's actual code, not just its README.

This is a parallel track alongside the Python/ESPectre work in
`../src/breathing/` and `../src/presence/`, not a replacement for it. Both
approaches target the same problem from this project's promise in
[../docs/PLAN.md](../docs/PLAN.md).

## Verification status

**Read this before trusting anything else in this document.**

| Claim | Status |
|---|---|
| `esp_radar.h` API used correctly (function signatures, struct fields) | Verified — read directly from the header, not from memory |
| `esp-radar` targets the original ESP32 | Verified — `components/espressif__esp-radar/lib/esp32/libesp-radar.a` exists |
| CSI-enable sdkconfig options | Verified — read from WaveSight's own checked-in, working `sdkconfig` |
| **The project compiles** | **Verified.** Built clean in `espressif/idf:v5.4` (Docker) for `esp32`, all 998 build steps, zero errors or warnings in `presence_fusion.c`, `radar_app.c`, `web_server.c`, or `app_main.c`. Produced `presence-radar.bin`, 838,880 bytes, 20% of the app partition free. Reproduce with the command in "Building" below. |
| It runs correctly on real hardware | **Not verified. Never flashed. No board has run this code.** Compiling is not the same as working — see PLAN.md's evidence discipline. |
| `presence_fusion.c`'s logic is correct | Host-side tests exist in `main/test_presence_fusion.c` and have **not been run** — no plain C compiler was available for that, only the ESP-IDF cross-toolchain used for the firmware build above. Run them before trusting the fusion logic. |

## The gap this fixes

Espressif's `esp_radar.h` defines:

```c
typedef struct {
    float waveform_jitter;  /* for movement */
    float waveform_wander;  /* documented: for detecting human presence */
} wifi_radar_info_t;
```

WaveSight's `radar_cb()` in `app_main.c` reads `waveform_jitter` for movement,
but **never reads `waveform_wander` at all**. Its `someone_status` output —
labeled "presence" in its dashboard — is computed once from a jitter
threshold and then unconditionally overwritten by a motion-hold timeout:

```c
someone_status = (info->waveform_jitter > g_someone_threshold);  // dead code
if (esp_log_timestamp() - s_last_move_time < someone_timeout * 1000)
    someone_status = true;
else
    someone_status = false;
```

`s_last_move_time` only advances on confirmed movement, so WaveSight's
"someone" is a motion-hold timeout, not stationary-presence detection. This
is the same gap [ESPectre's PR #112](https://github.com/francescopace/espectre/pull/112)
was closed for lacking evidence on, confirmed independently in a second,
unrelated codebase.

`main/presence_fusion.c` is the fix: `waveform_wander` gets its own K-of-N
evidence vote with hysteresis (mirroring `../src/presence/tracker.py`'s
treatment of the breathing score), fused with the jitter-based movement
decision as an OR.

## Architecture

```text
esp_radar (Espressif, Apache-2.0, vendored in components/)
  |  wifi_radar_info_t { waveform_jitter, waveform_wander }
  v
radar_app.c        -- K-of-N movement filter, calls presence_fusion,
                       drives GPIO, holds a mutex-guarded status snapshot
  |
  +--> presence_fusion.c   -- pure C, no ESP-IDF includes, hardware-
  |                           independent, unit-testable on a host compiler
  |
  v
web_server.c        -- /api/status (JSON), /api/calibrate (POST),
                        one embedded HTML/JS dashboard page
```

## What this does not do yet

Real gaps relative to WaveSight, accepted deliberately to keep the first pass
buildable and its unverified surface small:

- **No SoftAP WiFi-configuration UI.** Credentials are set via
  `idf.py menuconfig` → "Presence radar configuration" (Kconfig), not entered
  from a phone after first boot.
- **No login / session auth** on the dashboard. Do not expose this device
  directly to an untrusted network as shipped.
- **No LED feedback, no button handling, no factory reset flow.**
- **The dashboard is one status page**, not WaveSight's full settings UI
  (~1,470 lines of embedded HTML). `main/web_server.c` is under 150.
- **Wander/jitter thresholds are placeholders** (`presence_fusion_default_config()`)
  until `/api/calibrate` has actually been run against a real empty room and
  the result checked against PLAN.md Gate 2's premise test.

## Licensing

Two different pieces, two different rules — same discipline as documented in
[../docs/METHODOLOGY.md §3](../docs/METHODOLOGY.md#3-license-and-provenance-discipline):

- `components/espressif__esp-radar/` is **Apache-2.0**, copied here verbatim
  including its `LICENSE` file and the header's copyright notice. Safe to
  use and redistribute under Apache-2.0's terms.
- `main/*.c` and `main/*.h` in this directory are **written from scratch**.
  No WaveSight source was copied. This project's own top-level license has
  not been decided yet — that is a real open decision, not an oversight; see
  the note in the repository root.

## Building

Requires ESP-IDF v5.4 (matching the version WaveSight's own README
specifies and the version this was checked against). If you do not have
ESP-IDF installed natively, use Docker from the repository root:

```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  -v "$(pwd)/firmware-radar:/project" -w /project \
  espressif/idf:v5.4 \
  bash -c "idf.py set-target esp32 && idf.py build"
```

## Flashing (not yet attempted)

```bash
idf.py -p COM3 flash monitor
```

Then open `http://<device-ip>/` once it joins WiFi (check the serial monitor
or your router for the assigned address).

## Calibration

**Do this before trusting any presence reading.** POST to `/api/calibrate`
(or use the dashboard button) with the room completely empty for 60 seconds.
This calls `esp_radar_train_start()` / `esp_radar_train_stop()`, which return
calibrated jitter and wander thresholds directly from the library, and
`radar_app.c` derives the wander hysteresis band from them at a fixed 0.5
ratio, the same fixed-ratio hysteresis pattern already used in
`../src/presence/tracker.py`'s breathing-score thresholds. This ratio is a
design choice, not a measured value, and should be revisited once real
calibration data exists.

## Relationship to the rest of this project

This does not change any milestone in [../docs/PLAN.md](../docs/PLAN.md).
The premise gate (empty vs. present-still must be separable), the evidence
standards (session-level splits, frozen targets, published failures), and
the eventual upstream-contribution goal all still apply — this is a second
implementation to evaluate against the same gates, not a shortcut around them.
