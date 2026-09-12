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
                          missed_intervals=sum(x > 25 for x in intervals),
                          intervals=len(intervals))
        output.append(result)
    writer = csv.DictWriter(sys.stdout, fieldnames=output[0].keys())
    writer.writeheader()
    writer.writerows(output)


if __name__ == "__main__":
    main()
