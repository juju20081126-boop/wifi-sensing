import csv
import math
from datetime import datetime, timezone

from tools.analyze_recording import analyze_recording, csi_rms_amplitude


def test_csi_rms_amplitude_uses_both_i_and_q_components():
    # (3, 4) and (0, 5) both have magnitude 5, so RMS is also 5.
    assert csi_rms_amplitude([3, 4, 0, 5]) == 5.0


def test_analyze_recording_replays_timestamped_csi_amplitudes(tmp_path):
    path = tmp_path / "present-still.csv"
    packet_rate_hz = 13.0
    with path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=["received_at_utc", "label", "data"])
        writer.writeheader()
        for index in range(int(packet_rate_hz * 120)):
            timestamp_s = index / packet_rate_hz
            amplitude = round(100 + 20 * math.sin(2 * math.pi * 0.3 * timestamp_s))
            received_at = datetime.fromtimestamp(timestamp_s, timezone.utc).isoformat()
            writer.writerow(
                {
                    "received_at_utc": received_at,
                    "label": "still",
                    "data": f"[0, {amplitude}]",
                }
            )

    analysis = analyze_recording(path, sample_rate_hz=20.0)

    assert analysis.sample_count == int(packet_rate_hz * 120)
    assert 12.9 <= analysis.packet_rate_hz <= 13.1
    assert analysis.labels == ("still",)
    assert analysis.result.valid
    assert 16.0 <= analysis.result.bpm <= 20.0
