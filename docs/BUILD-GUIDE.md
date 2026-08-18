# Build Guide — ESP32 WROOM-32

Step-by-step execution of the work plan. Written for **Windows**, since that is
what this machine runs. Every command comes from the upstream projects' own
documentation, not from memory.

Plan and rationale: `Obsidian Vault/📁 Projects/WiFi Sensing/ESP32 WROOM-32 Work Plan`

---

## Before you start

| Need | Check |
|---|---|
| ESP32 WROOM-32 board | Bought |
| Micro-USB **data** cable | Charge-only cables are the number one first-hour failure |
| 2.4 GHz WiFi SSID | This chip cannot see 5 GHz networks |
| Google Chrome | Required for Web Serial flashing |
| A machine that stays on | For Home Assistant |

---

# PART 1 — Track A: get the lights working

Goal: one weekend. No code written by you.

## Step 1 — Prove the board enumerates

Plug the board in via USB, then in PowerShell:

```
Get-PnpDevice -Class Ports -Status OK | Select-Object Name, InstanceId
```

**Expected:** a `COM*` entry mentioning CH9102 or USB-SERIAL.

**If nothing appears:**

1. Try a different cable. Most micro-USB cables are charge-only.
2. Install the CH9102 / CH343 driver from WCH, then re-plug.

Do not continue until a COM port appears. Everything downstream depends on it.

## Step 2 — Install Home Assistant

Docker is the least invasive route:

```
docker run -d --name homeassistant --restart=unless-stopped --network=host -v C:/Users/justi/ha-config:/config ghcr.io/home-assistant/home-assistant:stable
```

Open `http://localhost:8123` and create the account.

## Step 3 — Download the firmware

Go to the ESPectre releases page and download **`espectre-2.8.0-esp32-ml.bin`**.

Getting this exactly right matters:

| Part of the name | Why |
|---|---|
| `esp32` | Not `esp32s3` / `c6` / `c3`. Those are different chips. |
| `-ml` | The ML detector. Your chip lacks AGC gain lock, which degrades the MVS detector's CV normalisation. The ML path uses raw sigma and is unaffected. |
| **no** `-ota` | OTA images are for updating an already-flashed board. |

## Step 4 — Flash it

1. Open **Google Chrome**. Not Edge, not Firefox — it needs the Web Serial API.
2. Go to the ESPConnect web flasher.
3. Click **Connect**, pick your COM port.
4. Select the `.bin` you downloaded.
5. Click **Flash**.

**If flashing stalls:** hold the **BOOT** button on the board as it starts, release once it is writing.

## Step 5 — Give it WiFi

Easiest is the Home Assistant Companion app over Bluetooth. Alternatives:

- Plug in and visit `web.esphome.io` in Chrome, then Connect and Configure WiFi
- Join the `ESPectre Fallback` network the board broadcasts, then configure in a browser

**Use your 2.4 GHz SSID.** A 5 GHz-only network fails silently and looks like a dead board.

## Step 6 — Adopt it in Home Assistant

Settings, then Devices and Services. An **ESPHome** device should be discovered automatically.

**Expected:** two new entities, a binary motion sensor and a movement score.

Do **not** enable MQTT on this track. The ESPHome native API is the default and avoids a known watchdog-reset bug on some builds.

## Step 7 — Place the board (Layout A)

- Router in one corner, board in the **opposite** corner
- 3 to 8 m apart; performance degrades past 10 to 15 m
- Keep metal furniture and appliances off the straight line between them
- Leave the room still for 10 seconds after boot so it calibrates

## Step 8 — Prove the link geometry to yourself

Watch the movement score entity, then:

1. Walk **across** the imaginary line between router and board. The score should jump.
2. Walk **parallel** to that line. The score should barely move.

If step 2 moves as much as step 1, you are not on the link. Move the board.

Try three positions, keep the best, then tune thresholds per `TUNING.md` in the repo.

**Gate:** there must be a visible gap between "walking" and "empty room" that you could draw a threshold through. If there is not, stop and fix placement. No software fixes a bad link.

## Step 9 — The automation

Settings, Automations, Create.

- **Trigger:** motion sensor `off` for `00:10:00`
- **Action:** turn the light off
- **Second automation:** motion `on`, turn the light on

Start at 10 minutes, not 2. Add a manual override so a bad threshold cannot leave you in the dark.

**Gate:** leave the room and the lights go off. Walk in and they come on.

### Track A is done. Your original goal is complete.

---

# PART 2 — Track B: the research platform

Start only after Part 1 works. This reflashes the same board. It is reversible and nothing is lost.

## Step 10 — Get the code

```
git clone https://github.com/francescopace/espectre.git
```

Then change into `espectre/micro-espectre`.

## Step 11 — Python environment

**Python 3.12 specifically.** Their docs warn that 3.14 has known issues.

```
py -3.12 -m venv venv
```

```
venv\Scripts\activate
```

```
pip install -r requirements.txt
```

That installs `esptool` for flashing and `mpremote` for deploying code.

## Step 12 — Flash MicroPython with CSI support

```
python me flash --chip esp32 --erase
```

On Windows use `python me`, not `./me`. Auto-detect (`python me flash --erase`) usually works; pass `--chip esp32` explicitly if it guesses wrong, and `--port COM3` if it cannot find the board.

The correct firmware downloads automatically from the `micropython-esp32-csi` releases and is cached locally.

```
python me verify
```

## Step 13 — An MQTT broker

**Track B talks MQTT, not the ESPHome native API.** You need a broker; Track A did not.

In Home Assistant: Settings, Add-ons, **Mosquitto broker**, Install, Start. Then create an MQTT user under Settings, People.

## Step 14 — Configure the node

Copy `src/config_local.py.example` to `src/config_local.py`, then edit:

```python
WIFI_SSID = "YourWiFiSSID"
WIFI_PASSWORD = "YourWiFiPassword"
MQTT_BROKER = "homeassistant.local"
MQTT_USERNAME = "mqtt"
MQTT_PASSWORD = "mqtt"
```

That file is gitignored. Never commit credentials.

## Step 15 — Deploy and run

```
python me deploy
```

```
python me run
```

The board connects to WiFi and MQTT, starts publishing motion data, and self-calibrates subcarriers via the NBVI algorithm.

## Step 16 — Watch it

```
python me
```

That opens the interactive MQTT CLI. To surface it in Home Assistant, add to `configuration.yaml`:

```yaml
mqtt:
  binary_sensor:
    - name: "ESPectre Motion"
      state_topic: "home/espectre/node1"
      value_template: "{{ value_json.state }}"
      payload_on: "motion"
      payload_off: "idle"
      device_class: motion
```

## Step 17 — The first real recording

The single most informative hour of the whole project.

The CLI has a built-in labelled collector, so you do not write a recorder:

```
python me collect --label empty --duration 600 --samples 1
```

```
python me collect --label present-moving --duration 600 --samples 1
```

```
python me collect --label present-still --duration 600 --samples 1
```

Check what you gathered with `python me collect --info`.

Use exactly these three labels — they are the agreed vocabulary from the
two-person split, and changing them later invalidates earlier recordings.

| Block | Label | What you do |
|---|---|---|
| 1 | `empty` | Leave the room and close the door. |
| 2 | `present-moving` | Walking and sitting normally. |
| 3 | `present-still` | **Sit nearly still.** Read something. |

Then check:

- Is the packet rate stable, and what is it actually? Expect 13 to 19 Hz, not 20.
- Does block 1 look different from block 2? It must.
- **Does block 1 look different from block 3?** It probably will not. That is the gap this project exists to close.

**This answers the one question no amount of code can answer: does your hardware, in your room, produce CSI stable enough to work with?**

---

# PART 3 — Wire in the breathing detector

The detector is already written and tested at `C:\Users\justi\wifi-sensing\src\breathing\`.

```
python -m pytest tests/ -v
```

It is deliberately pure Python with no numpy, so it runs unmodified under MicroPython.

Integration points in `micro-espectre/src/`:

| File | What to do |
|---|---|
| `detector_interface.py` | Register the breathing detector alongside MVS and ML |
| `filters.py` | Where the bandpass belongs |
| `features.py` | Extend the 9-feature extractor with the breathing score |

Feed it CSI amplitude with **real timestamps**:

```python
detector.process(amplitude, timestamp_s=packet_time)
```

Passing timestamps is not optional. Without them the nominal rate is assumed and the reported BPM is wrong by exactly the ratio of nominal to actual packet rate.

Fuse as an **OR at the state level**: motion catches someone walking in, breathing catches someone sitting still.

---

# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| No COM port | Charge-only cable | Try another cable first |
| No COM port, cable is fine | Missing driver | Install CH9102 / CH343 from WCH |
| ESPConnect will not connect | Wrong browser | Chrome only, needs Web Serial API |
| Flash starts then fails | Boot mode | Hold BOOT during flash |
| Flashed but never joins WiFi | 5 GHz SSID | This chip is 2.4 GHz only |
| Joins WiFi, nothing in HA | Integration missing | Add ESPHome under Devices and Services |
| Movement score always 0 | Placement | Redo Steps 7 and 8 |
| Score jumps with nobody there | Threshold too low, or AGC drift | Retune, and prefer the `-ml` build |
| Track B, no MQTT messages | No broker | Step 13 |
| `./me` not found | Windows | Use `python me` |

## Known limits of this hardware

- **No AGC gain lock.** Amplitudes carry drift unrelated to people. Use the `-ml` firmware; the ML path uses raw sigma, while MVS uses CV normalisation and is degraded.
- **2.4 GHz only.**
- **Probably no PSRAM**, which caps future on-device ML.
- RuView will **not** run on this chip. It builds only for `esp32s3`, `esp32c6`, and `esp32c3`.
