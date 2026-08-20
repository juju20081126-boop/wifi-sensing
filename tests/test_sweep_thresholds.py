from pathlib import Path

from src.breathing.detector import BreathingResult
from tools.analyze_recording import RecordingAnalysis
from tools.evaluate_recordings import RecordingEvaluation
from tools.sweep_thresholds import sweep, threshold_values


def evaluation(label, score):
    analysis = RecordingAnalysis(
        sample_count=100,
        duration_s=10.0,
        packet_rate_hz=10.0,
        labels=(label,),
        result=BreathingResult(bpm=18.0 if label == "still" else 0.0, score=score, valid=label == "still"),
    )
    return RecordingEvaluation(Path(f"{label}-{score}.csv"), label, analysis)


def test_threshold_values_include_both_endpoints():
    assert threshold_values(0.5) == [0.0, 0.5, 1.0]


def test_sweep_calculates_confusion_matrix_and_ignores_moving_sessions():
    metrics = sweep(
        [
            evaluation("empty", 0.1),
            evaluation("empty", 0.7),
            evaluation("still", 0.2),
            evaluation("still", 0.8),
            evaluation("moving", 0.99),
        ],
        thresholds=[0.5],
        positive_label="still",
        negative_label="empty",
    )

    result = metrics[0]
    assert (result.true_positive, result.false_positive) == (1, 1)
    assert (result.true_negative, result.false_negative) == (1, 1)
    assert result.precision == 0.5
    assert result.recall == 0.5
