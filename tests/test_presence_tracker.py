"""Tests for stateful fusion of motion and breathing evidence."""

import pytest

from src.presence.tracker import PresenceTracker


def _tracker(**overrides):
    settings = {
        "motion_hold_s": 10.0,
        "breathing_on_threshold": 0.6,
        "breathing_off_threshold": 0.3,
        "evidence_window": 5,
        "evidence_required": 2,
    }
    settings.update(overrides)
    return PresenceTracker(**settings)


def test_motion_is_held_before_room_becomes_empty():
    tracker = _tracker()

    entered = tracker.update(0.0, motion_detected=True, breathing_score=0.0)
    held = tracker.update(9.0, motion_detected=False, breathing_score=0.0)
    empty = tracker.update(10.1, motion_detected=False, breathing_score=0.0)

    assert entered.occupied is True
    assert entered.reason == "motion"
    assert held.occupied is True
    assert held.motion_held is True
    assert empty.occupied is False
    assert empty.reason == "empty"


def test_k_of_n_breathing_evidence_can_hold_occupancy_without_motion():
    tracker = _tracker()

    first = tracker.update(0.0, breathing_score=0.75)
    second = tracker.update(1.0, breathing_score=0.10)
    confirmed = tracker.update(2.0, breathing_score=0.80)

    assert first.occupied is False
    assert second.occupied is False
    assert confirmed.occupied is True
    assert confirmed.breathing_present is True
    assert confirmed.reason == "breathing"


def test_single_breathing_spike_does_not_mark_room_occupied():
    tracker = _tracker()

    scores = [0.05, 0.90, 0.10, 0.15, 0.05]
    states = [tracker.update(float(i), breathing_score=score)
              for i, score in enumerate(scores)]

    assert all(state.occupied is False for state in states)


def test_hysteresis_keeps_breathing_active_through_moderate_scores():
    tracker = _tracker()

    tracker.update(0.0, breathing_score=0.70)
    active = tracker.update(1.0, breathing_score=0.80)
    for timestamp in (2.0, 3.0, 4.0):
        active = tracker.update(timestamp, breathing_score=0.40)

    assert active.breathing_present is True

    for timestamp in (5.0, 6.0, 7.0, 8.0):
        cleared = tracker.update(timestamp, breathing_score=0.10)

    assert cleared.breathing_present is False
    assert cleared.occupied is False


def test_motion_and_breathing_report_a_combined_reason():
    tracker = _tracker(evidence_window=1, evidence_required=1)

    state = tracker.update(
        0.0, motion_detected=True, breathing_score=0.75)

    assert state.occupied is True
    assert state.motion_held is True
    assert state.breathing_present is True
    assert state.reason == "motion+breathing"


def test_out_of_order_timestamps_are_rejected():
    tracker = _tracker()
    tracker.update(2.0)

    with pytest.raises(ValueError, match="monotonic"):
        tracker.update(1.0)
