#!/usr/bin/env python3
"""Summarize completed-frame CSVs; reject duplicate or missing source frame IDs."""
import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def deadline_summary(rows, warmup):
    """Report recorded deadlines without attributing display gaps to a cause."""
    fields = ('requested_s', 'clock_duration_s', 'gpu_start_s', 'gpu_end_s',
              'start_s', 'cpu_ms', 'presented_s')
    try:
        minimums = [float(row.get('min_duration_s', 0)) for row in rows]
    except (TypeError, ValueError) as error:
        raise ValueError('invalid minimum display duration') from error
    if any(not math.isfinite(value) or value < 0 for value in minimums):
        raise ValueError('invalid minimum display duration')
    if len(set(minimums)) != 1:
        raise ValueError('mixed presentation policies within one scenario')
    relative = minimums[0] > 0
    try:
        clocks = [int(row.get('metal_clock', 0)) for row in rows]
    except (TypeError, ValueError) as error:
        raise ValueError('invalid display-link source') from error
    if len(set(clocks)) != 1 or clocks[0] not in (0, 1):
        raise ValueError('invalid or mixed display-link source')
    metal = clocks[0] == 1
    if metal:
        if relative:
            raise ValueError('Metal display-link drawables manage their own presentation')
        fields += ('target_s',)
    for row in rows:
        try:
            values = {field: float(row[field]) for field in fields}
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('incomplete deadline timestamps') from error
        if any(not math.isfinite(value) or value < 0 for value in values.values()):
            raise ValueError('invalid deadline timestamp')
        if (values['requested_s'] != 0 if relative else values['requested_s'] <= 0) or values['clock_duration_s'] <= 0:
            raise ValueError('invalid requested deadline or clock duration')
        if values['gpu_end_s'] < values['gpu_start_s']:
            raise ValueError('backwards GPU timestamps')
        if abs(values['gpu_end_s'] - values['start_s']) >= 10:
            raise ValueError('GPU/host timestamps exceed benchmark watchdog window')
    if relative:
        # This policy has no requested absolute deadline. Do not fabricate CPU
        # or GPU deadline-lateness statistics from the display-link prediction.
        return dict(minimum_display_duration_ms=round(minimums[0] * 1000, 3))
    warm = rows[warmup:]
    requests = [float(row['requested_s']) for row in warm]
    intervals = [(b - a) * 1000 for a, b in zip(requests, requests[1:])]
    offsets = [(float(row['presented_s']) - float(row['requested_s'])) * 1000
               for row in warm if float(row['presented_s']) > 0]
    return dict(
        clock_source='metal' if metal else 'view',
        requested_interval_p95_ms=round(percentile(intervals, .95), 3),
        requested_long_intervals=sum(value >= 25 - .001 for value in intervals),
        nonincreasing_requests=sum(value <= 0 for value in intervals),
        submit_late_frames=sum(float(row['start_s']) + float(row['cpu_ms']) / 1000 >
                               float(row['target_s' if metal else 'requested_s']) + .000001 for row in warm),
        gpu_late_frames=sum(float(row['gpu_end_s']) > float(row['requested_s']) + .000001
                            for row in warm),
        presentation_offset_p95_ms=round(percentile(offsets, .95), 3))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv")
    parser.add_argument("--warmup", type=int, default=4)
    parser.add_argument("--expected-frames", type=int)
    parser.add_argument("--expected-themes", type=int)
    args = parser.parse_args()
    if args.warmup < 0:
        parser.error("warmup must be nonnegative")
    groups = defaultdict(list)
    with open(args.csv, newline="") as source:
        for row in csv.DictReader(source):
            groups[int(row["theme"]), int(row["scenario"])].append(row)
    if not groups:
        parser.error("no completed frame records")
    themes = {theme for theme, _ in groups}
    if args.expected_themes is not None and len(themes) != args.expected_themes:
        parser.error("missing theme records")
    if set(groups) != {(theme, scenario) for theme in themes for scenario in range(3)}:
        parser.error("missing scenario records")
    output = []
    for (theme, scenario), rows in sorted(groups.items()):
        rows.sort(key=lambda row: int(row["frame"]))
        ids = [int(row["frame"]) for row in rows]
        if ids != list(range(len(rows))):
            parser.error(f"theme {theme}, scenario {scenario}: duplicate or missing frame IDs")
        if args.expected_frames is not None and len(rows) != args.expected_frames:
            parser.error(f"theme {theme}, scenario {scenario}: incomplete frame count")
        warm = rows[args.warmup:]
        if len(warm) < 2:
            parser.error("need at least two frames after warmup")
        native = "presented_s" in rows[0]
        field = "cpu_ms" if native else "total_ms"
        times = [float(row[field]) for row in warm]
        result = dict(theme=theme, scenario=scenario, samples=len(warm),
                      timed="CPU submission" if native else "CPU + completed GPU",
                      cold_ms=round(float(rows[0][field]), 3),
                      median_ms=round(statistics.median(times), 3),
                      p95_ms=round(percentile(times, .95), 3),
                      p99_ms=round(percentile(times, .99), 3), max_ms=round(max(times), 3))
        if native:
            if any(not math.isfinite(float(row["presented_s"])) or
                   float(row["presented_s"]) < 0 for row in rows):
                parser.error("invalid presentation timestamp")
            presented = [float(row["presented_s"]) for row in warm
                         if float(row["presented_s"]) > 0]
            if len(presented) < 2:
                parser.error("need at least two actually presented frames after warmup")
            if any(b < a for a, b in zip(presented, presented[1:])):
                parser.error("backwards actual presentation timestamps")
            # Metal can report the same display instant for multiple drawables.
            # Preserve/count those outcomes, but never count them as additional
            # display refreshes (or invent a zero-duration frame interval).
            unique_presented = list(dict.fromkeys(presented))
            if len(unique_presented) < 2:
                parser.error("need at least two distinct actual presentation times")
            intervals = [1000 * (b - a) for a, b in
                         zip(unique_presented, unique_presented[1:])]
            result.update(dropped_frames=len(warm) - len(presented),
                          shared_presentation_times=len(presented) - len(unique_presented),
                          cold_dropped_frames=sum(float(row["presented_s"]) == 0
                                                  for row in rows[:args.warmup]),
                          fps=round(1000 / statistics.mean(intervals), 3),
                          interval_p95_ms=round(percentile(intervals, .95), 3),
                          # At 60 fps, 25 ms is already 1.5 frame periods.
                          # Include that boundary with 1 us timestamp tolerance:
                          # subtraction of large uptime values can straddle it.
                          missed_intervals=sum(x >= 25 - .001 for x in intervals),
                          intervals=len(intervals))
            if 'requested_s' in rows[0]:
                try:
                    result.update(deadline_summary(rows, args.warmup))
                except ValueError as error:
                    parser.error(str(error))
        output.append(result)
    writer = csv.DictWriter(sys.stdout, fieldnames=output[0].keys())
    writer.writeheader()
    writer.writerows(output)


if __name__ == "__main__":
    main()
