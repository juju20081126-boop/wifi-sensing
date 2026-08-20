"""Summarize breathing-detector results across a directory of CSI recordings."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Callable, Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.analyze_recording import RecordingAnalysis, analyze_recording


@dataclass(frozen=True)
class RecordingEvaluation:
    """One file and its detector result."""

    path: Path
    label: str
    analysis: RecordingAnalysis


@dataclass(frozen=True)
class LabelSummary:
    """Aggregate metrics for one ground-truth recording label."""

    label: str
    recording_count: int
    total_duration_s: float
    mean_packet_rate_hz: float
    valid_count: int
    mean_score: float
    mean_bpm: float | None


def evaluate_directory(
    input_dir: Path,
    analyzer: Callable[[Path], RecordingAnalysis] = analyze_recording,
) -> list[RecordingEvaluation]:
    """Analyze every CSV directly inside ``input_dir``.

    Each recording must carry exactly one label.  A mixed-label CSV is a data
    collection mistake: it cannot be used as a clean evaluation example.
    """
    if not input_dir.is_dir():
        raise ValueError(f"recordings directory does not exist: {input_dir}")

    paths = sorted(input_dir.glob("*.csv"))
    if not paths:
        raise ValueError(f"no CSV recordings found in: {input_dir}")

    evaluations = []
    for path in paths:
        analysis = analyzer(path)
        if len(analysis.labels) != 1:
            raise ValueError(f"{path.name} contains mixed labels: {analysis.labels}")
        evaluations.append(RecordingEvaluation(path, analysis.labels[0], analysis))
    return evaluations


def summarize(evaluations: Iterable[RecordingEvaluation]) -> list[LabelSummary]:
    """Group per-recording detector results by their known label."""
    grouped: dict[str, list[RecordingEvaluation]] = {}
    for evaluation in evaluations:
        grouped.setdefault(evaluation.label, []).append(evaluation)

    summaries = []
    for label in sorted(grouped):
        group = grouped[label]
        valid_results = [item.analysis.result for item in group if item.analysis.result.valid]
        summaries.append(
            LabelSummary(
                label=label,
                recording_count=len(group),
                total_duration_s=sum(item.analysis.duration_s for item in group),
                mean_packet_rate_hz=mean(item.analysis.packet_rate_hz for item in group),
                valid_count=len(valid_results),
                mean_score=mean(item.analysis.result.score for item in group),
                mean_bpm=(mean(result.bpm for result in valid_results) if valid_results else None),
            )
        )
    return summaries


def print_summary(summaries: Iterable[LabelSummary]) -> None:
    print("label           files  duration  packet rate  valid  mean score  mean BPM")
    for summary in summaries:
        bpm = "-" if summary.mean_bpm is None else f"{summary.mean_bpm:.1f}"
        print(
            f"{summary.label:<15} {summary.recording_count:>5} "
            f"{summary.total_duration_s:>8.1f}s {summary.mean_packet_rate_hz:>9.2f}Hz "
            f"{summary.valid_count:>5} {summary.mean_score:>11.3f} {bpm:>9}"
        )


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare BreathingDetector results for recorded CSI sessions"
    )
    parser.add_argument(
        "--input-dir", type=Path, default=Path("data") / "recordings",
        help="Directory containing CSV files made by record_csi.py",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        print_summary(summarize(evaluate_directory(args.input_dir)))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Unable to evaluate recordings: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
