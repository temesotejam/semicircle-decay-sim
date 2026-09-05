from analysis.extract_free_decay_events import Peak, Sample, extract_events


def test_extracts_consecutive_free_halfcycles_with_interpolated_cross_rate() -> None:
    peaks = [
        Peak(15, 100.0, -1, -10.0),
        Peak(16, 300.0, +1, +8.0),
        Peak(17, 500.0, -1, -6.0),
    ]
    samples = [
        Sample(100.0, -10.0, 0.0),
        Sample(190.0, -1.0, +50.0),
        Sample(210.0, +1.0, +70.0),
        Sample(300.0, +8.0, 0.0),
        Sample(390.0, +1.0, -45.0),
        Sample(410.0, -1.0, -55.0),
        Sample(500.0, -6.0, 0.0),
    ]

    rows = extract_events(peaks, samples, "fixture")

    assert len(rows) == 2
    assert rows[0]["prev_peak_side"] == -1
    assert rows[0]["prev_peak_deg"] == -10.0
    assert rows[0]["next_peak_deg"] == +8.0
    assert rows[0]["zero_cross_interpolated_ms"] == 200.0
    assert rows[0]["zero_cross_rate_dps"] == 60.0
    assert rows[1]["prev_peak_side"] == +1
    assert rows[1]["next_peak_deg"] == -6.0
    assert rows[1]["zero_cross_interpolated_ms"] == 400.0
    assert rows[1]["zero_cross_rate_dps"] == -50.0
