# Methodology

How this project works, not just what it builds. [docs/PLAN.md](PLAN.md) is the
schedule — milestones, gates, owners. This document is the discipline behind
every entry in that schedule: the habits that caught two real bugs, ruled out
a wrong architecture before any hardware was bought, and kept the project from
repeating the mistake that got a similar contribution rejected upstream.

Read this once. Refer back to it whenever a shortcut looks tempting.

---

## 1. Verify claims against the primary source, never a summary

Every third-party claim in this project — a repository's README, a chip's
datasheet line, a paper's abstract — was checked against the underlying
evidence before it was allowed to shape a decision. A summary can be stale,
optimistic, or simply wrong; source code, release assets, and raw bytes are
not.

**Case studies from this project:**

- **RuView's supported hardware.** Its README describes ESP32-S3 and C6
  prominently. Rather than trust that impression, every build script and CI
  file in the repository was grepped for `set-target`. Result: `esp32s3` (13
  occurrences), `esp32c6` (8), `esp32c3` (1), and the original ESP32 (0). Two
  config files that looked like they might cover it —
  `sdkconfig.defaults.devkitc` and `sdkconfig.defaults.4mb` — were opened and
  both turned out to hard-code `CONFIG_IDF_TARGET="esp32s3"`. That single
  grep changed the hardware plan before a wrong firmware was ever flashed.

- **The AGC gain-lock concern.** ESPectre's platform table warns that the
  original ESP32 lacks AGC/FFT gain lock. Read in isolation, that sounds
  disqualifying. `ML_DATA_COLLECTION.md` in the same repository clarifies that
  the limitation only affects the CV-normalized MVS detector; the ML detector
  uses raw standard deviation and is listed as supported on this exact chip.
  The corrected understanding — use the `-ml` firmware, not MVS — came from
  reading a second source rather than stopping at the first warning.

- **The downloaded firmware binary.** After downloading
  `espectre-2.8.0-esp32-ml.bin`, its bytes were inspected directly rather than
  trusting the filename: 0xFF padding from 0x0 to 0xFFF, bootloader magic
  `0xE9` at offset 0x1000, partition table at 0x8000. Bootloader-at-0x1000 is
  the classic ESP32 layout; S3 and C3 images place it at 0x0. The file's own
  structure confirmed the target chip independently of its name.

- **GitHub repository statistics.** Star counts, fork counts, open-issue
  counts, and push timestamps were pulled from the GitHub API
  (`api.github.com/repos/...`) rather than read off the rendered page, and a
  PR's `merged` field was checked directly (`merged: false`, `merged_at:
  null`) rather than inferred from its "closed" badge.

**The rule this produces:** if a decision depends on a claim, find the file,
the byte, or the API response that makes the claim true, and cite it. "The
docs say so" is not sufficient evidence to spend money or write code against.

## 2. Find prior art, and read why it failed, before building anything

Before writing the breathing detector, the project searched for existing
attempts rather than assuming none existed.

- **ESPectre** (8,963 stars) already did motion detection well. The project
  adopted it instead of re-deriving motion detection from scratch.
- **PR #112** on ESPectre had already attempted breathing detection. It was
  read in full — not just its title — including the maintainer's four stated
  reasons for closing it unmerged: the signal was computed but never wired
  into the detection pipeline, no precision/recall evidence was ever produced
  on stationary scenarios, the reset paths were incomplete, and the
  contribution skipped the project's required Python-first prototyping stage.
- **WaveSight** was reviewed for its device-integration patterns (rolling
  K-of-N evidence windows, motion-hold timeouts, empty-room calibration)
  before `src/presence/tracker.py` was written. Its own fusion logic was found
  to conflate "recent motion" with "a stationary person present" — precisely
  the gap this project exists to close — which confirmed the contribution was
  still needed rather than already solved. See
  [docs/WAVESIGHT-REVIEW.md](WAVESIGHT-REVIEW.md).

**The rule this produces:** the target of this project is not "implement
breathing detection." It is "supply the specific, named, previously-attempted
piece of evidence that a real maintainer said was missing." That reframing
came directly from reading a closed PR instead of skipping past it.

## 3. License and provenance discipline

Two different licensing situations were handled two different ways, on
purpose:

- **ESPectre is GPLv3.** Any code eventually merged upstream, or derived
  closely from its architecture, inherits that license. This is recorded
  wherever the integration is discussed (see PLAN.md M5).
- **WaveSight's application code has no license file.** Its bundled
  `esp-radar` component is Apache-2.0, but that does not extend to
  WaveSight's own application logic. Because of that gap,
  `src/presence/tracker.py` was **written from scratch** from the *ideas*
  (K-of-N evidence, hold timeouts, hysteresis) with no source code copied,
  and this boundary is stated explicitly in
  [docs/WAVESIGHT-REVIEW.md](WAVESIGHT-REVIEW.md) rather than left implicit.

**The rule this produces:** reading someone else's implementation for ideas
and copying their code are different acts with different licensing
consequences, and every review document says explicitly which one happened.

## 4. Test-driven development for signal-processing code

Every function in `src/breathing/` and `src/presence/` was written test-first:
a failing test committed to describing the wanted behavior, watched fail for
the right reason, then the minimum code to pass it. This discipline caught two
real defects that inspection would likely have missed.

- **Bug 1 — noise locked onto a slow rate.** An early estimator test fed raw
  Gaussian noise through autocorrelation directly and asserted low confidence.
  It failed: noise produced a large peak at long lags and reported 6 BPM with
  high confidence. The fix was not a parameter tweak but an architecture
  change — `BreathingDetector` now owns the bandpass filter internally so raw
  samples can never reach the autocorrelator unfiltered. The *possibility* of
  misuse was the defect, not any specific input.

- **Bug 2 — smooth drift read as a fast breath.** A test modeling the
  WROOM-32's AGC gain drift (a slow, non-periodic amplitude wander) as a very
  low-frequency sine expected a low score. Instead the estimator reported
  40 BPM — the maximum allowed rate — at 0.84 confidence. A smooth,
  non-periodic signal's autocorrelation decays monotonically, so a plain
  `max()` over lags picked the shortest lag every time. The fix required the
  winning lag to be a genuine **interior local maximum**, which rejects the
  entire class of "smooth but not periodic" signals rather than one
  frequency. This is the project's specific defense against the exact
  hardware limitation the board carries.

Neither bug involved real hardware. Both were found by writing the test that
describes the failure mode *before* trusting the implementation, on synthetic
signals, before a single CSI packet had ever been captured.

**The rule this produces:** for numerical code where a plausible-looking
answer can be silently wrong (an estimator that returns *a* number is not the
same as one that returns the *right* number), write the test that would catch
the wrong-but-plausible answer, and watch it fail before trusting any fix.

## 5. Evidence-first evaluation discipline

Borrowed from the deeper RuView architecture review and applied to this
project's own evaluation plan in [docs/PLAN.md](PLAN.md):

- **Every claim is labeled**: source-backed (the code exists and is
  traceable), measured (a command produced a number on a stated input),
  synthetic (the input was generated, not real), or unverified (plausible but
  not checked against ground truth). The current README says outright that
  every test today is synthetic and that is not evidence of real-world
  performance — the label is applied to this project's own work, not only to
  others'.
- **Splits are by session, never by frame.** Adjacent CSI frames are
  near-identical; splitting randomly at the frame level leaks near-duplicate
  conditions into both train and test and inflates every metric. Milestone M3
  requires the train/test assignment to be made at the session level before
  any model sees the data.
- **Targets are frozen before the final run**, not chosen after seeing
  results. Gate 4's numeric thresholds are written into PLAN.md now, before
  M3's dataset even exists.
- **Baselines are mandatory.** A result is only interesting if it beats
  always-occupied, RSSI-only, and raw-amplitude-variance baselines — not
  merely better than nothing.
- **Failure cases must be published**, not only the cases that worked. A
  report with no documented failures is treated as an incomplete report.

## 6. Physical validation gates software investment

The plan places a "premise test" (Gate 2 in PLAN.md) before any dataset
collection or algorithm work: ten minutes empty, ten minutes moving, ten
minutes sitting nearly still, recorded on the actual board in the actual room,
checking only whether `empty` and `present-still` are even distinguishable.

This is placed deliberately early and cheap. If the hardware and room
geometry cannot separate those two conditions at all, the entire premise of
the project needs to be revisited — and that is a week-one finding, not a
month-three one, precisely because no code was trusted before the room was.

## 7. Explicit, narrow scope

The project's promise is written as one sentence and repeated verbatim across
[README.md](../README.md) and [PLAN.md](PLAN.md): keep the lights on for a
stationary person, in one room, proven with held-out measurement rather than a
demo. People counting, pose estimation, heart rate, and multi-room coverage are
listed as **explicit non-goals** in PLAN.md section 7, not because they are
uninteresting, but because each one individually would have been reason enough
to slip the actual deliverable.

## 8. Two people split by dependency, not by seniority

The two-person plan ([docs/TWO-PERSON-SPLIT.md](TWO-PERSON-SPLIT.md)) is
organized around the one real bottleneck in the whole project: Person B's
evaluation code cannot be *measured* against real conditions until Person A
has produced a labeled dataset. Everything before that point runs in
parallel — Person B builds and unit-tests the detector against synthetic
signals while Person A brings the hardware up — specifically so that neither
person is idle waiting on the other before week four.

---

## How this maps to the plan

| Methodology principle | Where it shows up in PLAN.md |
|---|---|
| Verify against primary sources | Section 2, "Where we actually are," separates verified from unverified line by line |
| Prior art and its failure reasons | Section 1, "The promise," is worded around the specific gap PR #112 left open |
| License and provenance | Section 8 decision log entries for GPLv3 and the WaveSight boundary |
| TDD for numerical code | Every module in section 2's verified table has a named test that would fail if the behavior regressed |
| Evidence-first evaluation | Section 4, "Evidence standards," verbatim |
| Physical validation gates | Gate 2 explicitly cannot fail the project, only redirect it |
| Explicit scope | Section 7, "Explicit non-goals" |
| Dependency-based division of labor | Section 6, and the full detail in TWO-PERSON-SPLIT.md |
