from pathlib import Path

from src.breathing.detector import BreathingResult
from tools.analyze_recording import RecordingAnalysis
from tools.evaluate_recordings import RecordingEvaluation, evaluate_directory, summarize


def make_analysis(label, score, bpm, valid, rate=13.0, duration=60.0):
    return RecordingAnalysis(
        sample_count=int(rate * duration),
        duration_s=duration,
        packet_rate_hz=rate,
        labels=(label,),
        result=BreathingResult(bpm=bpm, score=score, valid=valid),
    )


def test_summarize_groups_recordings_and_ignores_invalid_bpm():
    evaluations = [
        RecordingEvaluation(Path("empty-a.csv"), "empty", make_analysis("empty", 0.1, 0.0, False)),
        RecordingEvaluation(Path("empty-b.csv"), "empty", make_analysis("empty", 0.3, 0.0, False, rate=15.0)),
        RecordingEvaluation(Path("still-a.csv"), "still", make_analysis("still", 0.8, 18.0, True)),
    ]

    summaries = {summary.label: summary for summary in summarize(evaluations)}

    assert summaries["empty"].recording_count == 2
    assert summaries["empty"].valid_count == 0
    assert summaries["empty"].mean_bpm is None
    assert summaries["empty"].mean_score == 0.2
    assert summaries["still"].valid_count == 1
    assert summaries["still"].mean_bpm == 18.0


def test_evaluate_directory_rejects_csv_with_mixed_labels(tmp_path):
    recording = tmp_path / "mixed.csv"
    recording.touch()

    def explicit_mixed_analyzer(_path):
        return RecordingAnalysis(
            sample_count=1,
            duration_s=0.0,
            packet_rate_hz=0.0,
            labels=("empty", "still"),
            result=BreathingResult(bpm=0.0, score=0.0, valid=False),
        )

    try:
        evaluate_directory(tmp_path, analyzer=explicit_mixed_analyzer)
    except ValueError as exc:
        assert "mixed labels" in str(exc)
    else:
        raise AssertionError("mixed-label recordings must be rejected")
