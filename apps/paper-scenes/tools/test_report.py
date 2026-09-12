"""Exercise frame accounting independently of Metal and the live display."""
import csv
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class PresentationReportTest(unittest.TestCase):
    def report(self, mutate=lambda rows: None):
        rows = [dict(theme=5, scenario=scenario, frame=frame, cpu_ms=2,
                     presented_s=10 + scenario + frame / 60)
                for scenario in range(3) for frame in range(8)]
        mutate(rows)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "frames.csv"
            with source.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            return subprocess.run(
                [sys.executable, str(Path(__file__).with_name("report.py")),
                 str(source), "--warmup", "1", "--expected-frames", "8",
                 "--expected-themes", "1"], text=True, capture_output=True)

    def test_dropped_frames_are_kept_and_presentation_gaps_counted(self):
        def drop(rows):
            rows[0]["presented_s"] = 0
            rows[3]["presented_s"] = 0
        result = self.report(drop)
        self.assertEqual(result.returncode, 0, result.stderr)
        first = next(csv.DictReader(io.StringIO(result.stdout)))
        self.assertEqual(first["samples"], "7")
        self.assertEqual(first["dropped_frames"], "1")
        self.assertEqual(first["cold_dropped_frames"], "1")
        self.assertEqual(first["missed_intervals"], "1")
        self.assertEqual(first["intervals"], "5")
        self.assertEqual(float(first["fps"]), 50)

    def test_missing_tail_rejected(self):
        self.assertNotEqual(self.report(lambda rows: rows.pop()).returncode, 0)

    def test_shared_presentation_time_is_not_an_extra_refresh(self):
        result = self.report(lambda rows: rows[3].update(
            presented_s=rows[2]["presented_s"]))
        self.assertEqual(result.returncode, 0, result.stderr)
        first = next(csv.DictReader(io.StringIO(result.stdout)))
        self.assertEqual(first["shared_presentation_times"], "1")
        self.assertEqual(first["intervals"], "5")
        self.assertEqual(float(first["fps"]), 50)

    def test_backwards_presentation_time_rejected(self):
        self.assertNotEqual(self.report(lambda rows: rows[3].update(
            presented_s=rows[1]["presented_s"])).returncode, 0)

    def test_duplicate_frame_rejected(self):
        self.assertNotEqual(self.report(lambda rows: rows[1].update(frame=0)).returncode, 0)

    def test_invalid_timestamp_rejected(self):
        for value in [-1, float("nan"), float("inf")]:
            with self.subTest(value=value):
                self.assertNotEqual(self.report(
                    lambda rows: rows[2].update(presented_s=value)).returncode, 0)

    def test_no_presentations_cannot_claim_fps(self):
        def drop_all(rows):
            for row in rows:
                row["presented_s"] = 0
        self.assertNotEqual(self.report(drop_all).returncode, 0)


if __name__ == "__main__":
    unittest.main()
