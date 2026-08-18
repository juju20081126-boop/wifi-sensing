"""Stateful room occupancy from motion and breathing evidence.

The design uses two deliberately different time scales:

* Motion immediately marks the room occupied and is held for a configurable
  timeout so a brief pause does not switch the lights off.
* Breathing is weak, noisy evidence, so it must win a K-of-N vote. Separate
  activation and clearing thresholds add hysteresis around the decision.

This module was written from scratch after reviewing WaveSight's public device
architecture, which also separates momentary movement from longer-lived
presence with a temporal evidence window and timeout. No WaveSight source code
is copied here; see docs/WAVESIGHT-REVIEW.md.

Pure Python -- suitable for later MicroPython integration.
"""


class PresenceState:
    """One occupancy decision and the evidence that produced it."""

    def __init__(self, occupied, motion_held, breathing_present, reason):
        self.occupied = occupied
        self.motion_held = motion_held
        self.breathing_present = breathing_present
        self.reason = reason

    def __repr__(self):
        return (
            "PresenceState(occupied=%s, motion_held=%s, "
            "breathing_present=%s, reason=%r)"
            % (self.occupied, self.motion_held,
               self.breathing_present, self.reason)
        )


class PresenceTracker:
    """Fuse movement and breathing confidence into stable room occupancy.

    ``motion_detected`` is expected to come from an existing motion detector
    such as ESPectre. ``breathing_score`` is the continuous score returned by
    :class:`src.breathing.detector.BreathingDetector`.
    """

    def __init__(self, motion_hold_s=180.0,
                 breathing_on_threshold=0.30,
                 breathing_off_threshold=0.15,
                 evidence_window=5, evidence_required=2):
        if motion_hold_s < 0.0:
            raise ValueError("motion_hold_s must be non-negative")
        if not 0.0 <= breathing_off_threshold < breathing_on_threshold <= 1.0:
            raise ValueError(
                "breathing thresholds must satisfy 0 <= off < on <= 1")
        if evidence_window < 1:
            raise ValueError("evidence_window must be at least 1")
        if not 1 <= evidence_required <= evidence_window:
            raise ValueError(
                "evidence_required must be between 1 and evidence_window")

        self.motion_hold_s = float(motion_hold_s)
        self.breathing_on_threshold = float(breathing_on_threshold)
        self.breathing_off_threshold = float(breathing_off_threshold)
        self.evidence_window = int(evidence_window)
        self.evidence_required = int(evidence_required)

        self._last_motion_s = None
        self._last_timestamp_s = None
        self._breathing_scores = []
        self._breathing_present = False

    def update(self, timestamp_s, motion_detected=False,
               breathing_score=0.0):
        """Return the occupancy state after consuming one evidence sample."""
        timestamp_s = float(timestamp_s)
        breathing_score = float(breathing_score)

        if (self._last_timestamp_s is not None and
                timestamp_s < self._last_timestamp_s):
            raise ValueError("timestamps must be monotonic")
        if not 0.0 <= breathing_score <= 1.0:
            raise ValueError("breathing_score must be between 0 and 1")

        self._last_timestamp_s = timestamp_s
        if motion_detected:
            self._last_motion_s = timestamp_s

        self._breathing_scores.append(breathing_score)
        if len(self._breathing_scores) > self.evidence_window:
            del self._breathing_scores[0]

        threshold = (self.breathing_off_threshold
                     if self._breathing_present
                     else self.breathing_on_threshold)
        votes = sum(score >= threshold for score in self._breathing_scores)
        self._breathing_present = votes >= self.evidence_required

        motion_held = (
            self._last_motion_s is not None and
            timestamp_s - self._last_motion_s <= self.motion_hold_s
        )
        occupied = motion_held or self._breathing_present

        if motion_held and self._breathing_present:
            reason = "motion+breathing"
        elif motion_held:
            reason = "motion"
        elif self._breathing_present:
            reason = "breathing"
        else:
            reason = "empty"

        return PresenceState(
            occupied=occupied,
            motion_held=motion_held,
            breathing_present=self._breathing_present,
            reason=reason,
        )

    def reset(self):
        """Clear all temporal evidence and return to an empty state."""
        self._last_motion_s = None
        self._last_timestamp_s = None
        self._breathing_scores = []
        self._breathing_present = False
