"""Measure breathing-score precision and recall across recorded CSI sessions."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.evaluate_recordings import RecordingEvaluation, evaluate_directory


@dataclass(frozen=True)
class ThresholdMetrics:
    """Confusion-matrix counts and derived metrics at one score threshold."""

    threshold: float
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int

    @property
    def precision(self) -> float | None:
        predicted_positive = self.true_positive + self.false_positive
        return self.true_positive / predicted_positive if predicted_positive else None

    @property
    def recall(self) -> float | None:
        actual_positive = self.true_positive + self.false_negative
        return self.true_positive / actual_positive if actual_positive else None


def threshold_values(step: float) -> list[float]:
    """Return inclusive score thresholds from 0.0 to 1.0."""
    if not 0.0 < step <= 1.0:
        raise ValueError("threshold step must be greater than 0 and no more than 1")

    values = []
    current = 0.0
    while current < 1.0:
        values.append(round(current, 10))
        current += step
    if values[-1] != 1.0:
        values.append(1.0)
    return values


def sweep(
    evaluations: Iterable[RecordingEvaluation],
    thresholds: Iterable[float],
    positive_label: str,
    negative_label: str,
) -> list[ThresholdMetrics]:
    """Evaluate ``positive_label`` versus ``negative_label`` at each threshold.

    Other labels, such as a moving-person session, are deliberately excluded:
    the breathing detector is evaluated only during motion-idle periods.
    """
    selected = [
        evaluation
        for evaluation in evaluations
        if evaluation.label in (positive_label, negative_label)
    ]
    if not selected:
        raise ValueError(
            f"no recordings with labels {positive_label!r} or {negative_label!r}"
        )

    results = []
    for threshold in thresholds:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("thresholds must be between 0.0 and 1.0")
        tp = fp = tn = fn = 0
        for evaluation in selected:
            actual_positive = evaluation.label == positive_label
            predicted_positive = evaluation.analysis.result.score >= threshold
            if actual_positive and predicted_positive:
                tp += 1
            elif actual_positive:
                fn += 1
            elif predicted_positive:
                fp += 1
            else:
                tn += 1
        results.append(ThresholdMetrics(threshold, tp, fp, tn, fn))
    return results


def print_metrics(metrics: Iterable[ThresholdMetrics]) -> None:
    print("threshold   TP  FP  TN  FN  precision  recall")
    for metric in metrics:
        precision = "-" if metric.precision is None else f"{metric.precision:.3f}"
        recall = "-" if metric.recall is None else f"{metric.recall:.3f}"
        print(
            f"{metric.threshold:>9.2f} {metric.true_positive:>4} {metric.false_positive:>3} "
            f"{metric.true_negative:>3} {metric.false_negative:>3} {precision:>10} {recall:>7}"
        )


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sweep BreathingDetector scores against labeled CSI recordings"
    )
    parser.add_argument("--input-dir", type=Path, default=Path("data") / "recordings")
    parser.add_argument(
        "--positive-label", default="still",
        help="Label representing a stationary person (default: still)",
    )
    parser.add_argument(
        "--negative-label", default="empty",
        help="Label representing an empty room (default: empty)",
    )
    parser.add_argument("--step", type=float, default=0.05, help="Score step from 0 to 1")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        metrics = sweep(
            evaluate_directory(args.input_dir),
            threshold_values(args.step),
            args.positive_label,
            args.negative_label,
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Unable to sweep thresholds: {exc}") from exc
    print_metrics(metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
