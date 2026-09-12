"""Exercise frame accounting independently of Metal and the live display."""
import csv
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class PresentationReportTest(unittest.TestCase):
    @staticmethod
    def deadlines(rows):
        for row in rows:
            requested = row['presented_s']
            row.update(requested_s=requested, clock_duration_s=1 / 60,
                       start_s=requested - .012, gpu_start_s=requested - .006,
                       gpu_end_s=requested - .004)

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

    def test_half_period_late_boundary_is_independent_of_uptime_rounding(self):
        for offset in [10, 2_791_000]:
            def cadence(rows):
                elapsed = 0
                for frame, interval in enumerate([0, 1 / 60, .025 - 1e-7,
                                                   .025 + 1e-7, .024, 1 / 60,
                                                   1 / 60, 1 / 60]):
                    elapsed += interval
                    rows[frame]["presented_s"] = offset + elapsed
            with self.subTest(offset=offset):
                result = self.report(cadence)
                self.assertEqual(result.returncode, 0, result.stderr)
                first = next(csv.DictReader(io.StringIO(result.stdout)))
                self.assertEqual(first["missed_intervals"], "2")

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

    def test_deadlines_distinguish_render_lateness_from_actual_cadence(self):
        def late(rows):
            self.deadlines(rows)
            rows[3]['gpu_end_s'] = rows[3]['requested_s'] + .002
            rows[4]['cpu_ms'] = 15
        result = self.report(late)
        self.assertEqual(result.returncode, 0, result.stderr)
        first = next(csv.DictReader(io.StringIO(result.stdout)))
        self.assertEqual(first['gpu_late_frames'], '1')
        self.assertEqual(first['submit_late_frames'], '1')
        self.assertEqual(first['missed_intervals'], '0')
        self.assertEqual(first['requested_long_intervals'], '0')

    def test_requested_gap_does_not_invent_a_presented_gap(self):
        def shifted(rows):
            self.deadlines(rows)
            rows[3]['requested_s'] += 1 / 60
        result = self.report(shifted)
        self.assertEqual(result.returncode, 0, result.stderr)
        first = next(csv.DictReader(io.StringIO(result.stdout)))
        self.assertEqual(first['requested_long_intervals'], '1')
        self.assertEqual(first['nonincreasing_requests'], '1')
        self.assertEqual(first['missed_intervals'], '0')

    def test_invalid_deadline_data_is_rejected(self):
        for field, value in [('requested_s', float('nan')), ('clock_duration_s', 0),
                             ('gpu_end_s', -1), ('gpu_start_s', 10000),
                             ('gpu_end_s', 10000), ('cpu_ms', float('inf'))]:
            def invalid(rows):
                self.deadlines(rows)
                rows[3][field] = value
            with self.subTest(field=field, value=value):
                self.assertNotEqual(self.report(invalid).returncode, 0)

    def test_relative_policy_does_not_fabricate_absolute_deadlines(self):
        def relative(rows):
            self.deadlines(rows)
            for row in rows:
                row.update(requested_s=0, min_duration_s=1 / 60)
        result = self.report(relative)
        self.assertEqual(result.returncode, 0, result.stderr)
        first = next(csv.DictReader(io.StringIO(result.stdout)))
        self.assertEqual(first['minimum_display_duration_ms'], '16.667')
        self.assertNotIn('gpu_late_frames', first)

    def test_mixed_policy_is_rejected(self):
        def mixed(rows):
            self.deadlines(rows)
            for row in rows:
                row['min_duration_s'] = 0
            rows[3].update(requested_s=0, min_duration_s=1 / 60)
        self.assertNotEqual(self.report(mixed).returncode, 0)

    def test_metal_clock_uses_submission_deadline_not_display_prediction(self):
        def metal(rows):
            self.deadlines(rows)
            for row in rows:
                row.update(metal_clock=1, target_s=row['requested_s'] - .008)
            rows[3]['cpu_ms'] = 6
        result = self.report(metal)
        self.assertEqual(result.returncode, 0, result.stderr)
        first = next(csv.DictReader(io.StringIO(result.stdout)))
        self.assertEqual(first['clock_source'], 'metal')
        self.assertEqual(first['submit_late_frames'], '1')
        self.assertEqual(first['gpu_late_frames'], '0')

    def test_invalid_or_mixed_clock_is_rejected(self):
        for value in [None, '', 'invalid', 2, 1]:
            def invalid(rows):
                self.deadlines(rows)
                for row in rows:
                    row['metal_clock'] = 0
                rows[3]['metal_clock'] = value
            with self.subTest(value=value):
                result = self.report(invalid)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)

    def test_metal_clock_rejects_minimum_duration_policy(self):
        def invalid(rows):
            self.deadlines(rows)
            for row in rows:
                row.update(metal_clock=1, min_duration_s=1 / 60, requested_s=0)
        result = self.report(invalid)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('manage their own presentation', result.stderr)


if __name__ == "__main__":
    unittest.main()
