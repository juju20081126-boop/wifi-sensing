# Two-Person Work Split

How to run the project README as a two-person
project. Technical steps live in
[BUILD-GUIDE.md](BUILD-GUIDE.md).

## Prerequisite: buy a second board

**~$10 for a second ESP32.** Without it, two people share one USB cable and one
board, and the whole split collapses into taking turns.

Get an **ESP32-C6** for the second board rather than another original ESP32. It has
the AGC gain lock the WROOM-32 lacks, so Person B develops on cleaner data, and it
can run RuView later if wanted. Two boards are also needed for Layout B coverage
eventually, so nothing is wasted.

## The two roles

| | Person A — Hardware & Deployment | Person B — Data & Algorithm |
|---|---|---|
| **Owns** | Board 1, placement, Home Assistant, the automation, data collection | Board 2, MicroPython, the breathing filter, evaluation, the PR |
| **Lives in** | ESPHome, Home Assistant UI, the physical room | Python, `micro-espectre/src/`, notebooks |
| **Suits** | Someone who likes tinkering, tuning, physical setup | Someone who likes signal processing, stats, writing code |
| **Ships** | Working lights, then the labeled dataset | The detector, then the evaluation report |

## Stage by stage — what each person produces

| Stage | Person A produces | Person B produces |
|---|---|---|
| **Week 1** | Board flashed, HA running, motion score visible | Board 2 on MicroPython, `micro-espectre` venv working, CSI streaming over UDP |
| **Week 2–3** | Tuned placement, **working lights automation** | Breathing bandpass (0.08–0.6 Hz) in `filters.py`, tested on synthetic and public data |
| **Week 4–6** | **Labeled dataset** — empty / present-moving / present-still | **Evaluation** — precision, recall, and the lift over motion-only |
| **Week 7+** | Integration testing in the real room | **The pull request**, Python-only, with results attached |

## The only hard dependency

**Person A's dataset → Person B's evaluation, at week 4.**

Everything else runs in parallel. Person B does not sit idle waiting, because weeks
1–3 are spent building and unit-testing the filter against synthetic signals and
public datasets. The real data is needed only to *measure* the detector, not to
write it.

## The contract to agree on day one

This is the single thing that keeps two people from blocking each other. Decide
these before either person starts, and write them down:

1. **File format** for CSI recordings — one file per session, timestamps included.
2. **Label vocabulary** — exactly three strings: `empty`, `present-moving`,
   `present-still`. No improvising a fourth mid-project.
3. **Where files live** and how they get shared (a shared folder or a git repo).
4. **What "a session" means** — minimum length, what gets noted (room, board
   position, time of day).

If the format changes later, every recording made before the change becomes
awkward to use. Agree it once, early.

## If you only have one board

Possible but slower. Run it sequentially:

- Person A does weeks 1–3 alone and hands over a working, tuned system.
- Person B takes the board for the research track while Person A does labeling
  sessions and writes documentation.

Expect roughly 1.5× the calendar time, and one person idle for stretches. The $10
is worth spending.

## Splitting credit honestly

Both roles produce something showable:

- Person A can say: *"I built a WiFi sensor that turns lights off automatically,
  and collected the labeled dataset that proved the detector worked."*
- Person B can say: *"I implemented a breathing-band presence detector and measured
  its improvement over the existing motion-only baseline."*

The pull request should credit both — Person B writes the code, Person A produced
the evidence, and the evidence is the part the maintainer said was missing.

## Related

- the project README
- [BUILD-GUIDE.md](BUILD-GUIDE.md)
- [PLAN.md](PLAN.md)
