"""Replay a recorded CSI CSV file through the breathing detector.

The recorder stores one CSI packet as interleaved I/Q integers.  This tool
reduces each packet to its RMS complex amplitude and passes it to the existing
detector using the packet's real receive timestamp.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence


# Running ``python tools/analyze_recording.py`` makes ``tools`` the first path,
# so add the repository root before importing the existing detector.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.breathing.detector import BreathingDetector, BreathingResult


@dataclass(frozen=True)
class CSISample:
    """One packet reduced to a timestamped scalar amplitude."""

    timestamp_s: float
    amplitude: float
    label: str


@dataclass(frozen=True)
class RecordingAnalysis:
    """Detector output plus enough context to judge the recording quality."""

    sample_count: int
    duration_s: float
    packet_rate_hz: float
    labels: tuple[str, ...]
    result: BreathingResult


def csi_rms_amplitude(values: Sequence[int]) -> float:
    """Return RMS magnitude for interleaved I/Q values from one CSI packet."""
    if not values or len(values) % 2:
        raise ValueError("CSI data must contain a non-empty, even number of I/Q values")

    total_energy = 0.0
    for index in range(0, len(values), 2):
        in_phase = values[index]
        quadrature = values[index + 1]
        if isinstance(in_phase, bool) or isinstance(quadrature, bool):
            raise ValueError("CSI I/Q values must be integers, not booleans")
        if not isinstance(in_phase, int) or not isinstance(quadrature, int):
            raise ValueError("CSI I/Q values must be integers")
        total_energy += in_phase * in_phase + quadrature * quadrature

    return math.sqrt(total_energy / (len(values) // 2))


def timestamp_seconds(value: str) -> float:
    """Parse the recorder's UTC ISO-8601 timestamp into Unix seconds."""
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid received_at_utc timestamp: {value!r}") from exc
    if timestamp.tzinfo is None:
        raise ValueError("received_at_utc must include a UTC offset")
    return timestamp.timestamp()


def iter_samples(path: Path) -> Iterable[CSISample]:
    """Yield valid recorder rows as timestamped aggregate CSI amplitudes."""
    with path.open("r", newline="", encoding="utf-8") as file_handle:
        reader = csv.DictReader(file_handle)
        required = {"received_at_utc", "label", "data"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("CSV must contain received_at_utc, label, and data columns")

        for line_number, row in enumerate(reader, start=2):
            try:
                values = json.loads(row["data"])
                if not isinstance(values, list):
                    raise ValueError("CSI data is not a JSON list")
                yield CSISample(
                    timestamp_s=timestamp_seconds(row["received_at_utc"]),
                    amplitude=csi_rms_amplitude(values),
                    label=row["label"],
                )
            except (KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"invalid CSI row {line_number}: {exc}") from exc


def analyze_recording(
    path: Path, sample_rate_hz: float = 20.0, window_s: float = 30.0
) -> RecordingAnalysis:
    """Replay one CSV recording through ``BreathingDetector``."""
    detector = BreathingDetector(sample_rate_hz=sample_rate_hz, window_s=window_s)
    sample_count = 0
    first_timestamp = None
    last_timestamp = None
    labels: set[str] = set()

    for sample in iter_samples(path):
        detector.process(sample.amplitude, timestamp_s=sample.timestamp_s)
        sample_count += 1
        first_timestamp = sample.timestamp_s if first_timestamp is None else first_timestamp
        last_timestamp = sample.timestamp_s
        labels.add(sample.label)

    if sample_count == 0:
        raise ValueError("recording contains no CSI packets")

    duration_s = 0.0 if last_timestamp is None else last_timestamp - first_timestamp
    packet_rate_hz = (sample_count - 1) / duration_s if duration_s > 0.0 else 0.0
    return RecordingAnalysis(
        sample_count=sample_count,
        duration_s=duration_s,
        packet_rate_hz=packet_rate_hz,
        labels=tuple(sorted(labels)),
        result=detector.result(),
    )


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read a recorded CSI CSV file and run BreathingDetector"
    )
    parser.add_argument("--input", required=True, type=Path, help="CSV made by record_csi.py")
    parser.add_argument("--sample-rate", type=float, default=20.0, help="Detector grid rate")
    parser.add_argument("--window", type=float, default=30.0, help="Estimator window in seconds")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if args.sample_rate <= 0.0 or args.window <= 0.0:
        raise SystemExit("--sample-rate and --window must be greater than zero")

    try:
        analysis = analyze_recording(args.input, args.sample_rate, args.window)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Unable to analyze recording: {exc}") from exc

    print(f"Samples: {analysis.sample_count}")
    print(f"Duration: {analysis.duration_s:.1f} s")
    print(f"Packet rate: {analysis.packet_rate_hz:.2f} Hz")
    print(f"Labels: {', '.join(analysis.labels)}")
    print(f"Breathing: {analysis.result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
