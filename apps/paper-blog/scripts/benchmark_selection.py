#!/usr/bin/env python3
"""Drive actual selection events and record native or synchronized frame costs."""
import argparse
import csv
import json
import os
from pathlib import Path
import statistics
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def summarize(rows):
    # Exclude startup, shader compilation, and the first coverage reservation.
    warm = rows[8:]
    if not warm:
        raise RuntimeError('At least nine frames are required')
    result = {}
    for key in ('event_ms', 'draw_ms', 'raster_ms', 'interval_ms'):
        values = sorted(float(row[key]) for row in warm)
        result[key] = {'median': statistics.median(values),
                       'p95': values[int(.95 * (len(values) - 1))],
                       'max': max(values)}
    result['frames'] = len(rows)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', action='store_true', help='Show a real window and measure its display cadence')
    parser.add_argument('--frames', type=int, default=240)
    parser.add_argument('--fixture', type=Path, default=Path.home() / 'Library/Application Support/Paper Blog/timeline.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/selection-performance.csv')
    args = parser.parse_args()
    if args.frames < 9:
        parser.error('--frames must be at least 9')
    if not args.fixture.is_file():
        parser.error('Supply a timeline fixture or launch the app once to populate its cache')
    env = dict(os.environ, PAPER_BLOG_BENCHMARK_FRAMES=str(args.frames))
    env.pop('PAPER_HEADLESS', None)
    if not args.native:
        env['PAPER_HEADLESS'] = '1'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    memory_path = args.output.with_suffix('.memory.csv')
    stop = threading.Event()
    samples = []
    with args.output.open('w') as output:
        process = subprocess.Popen(['coil', 'run', 'tools/selection_benchmark.coil', '--', '--fixture', str(args.fixture.resolve())],
                                   cwd=ROOT, env=env, stdout=output)
        started = time.monotonic()

        def monitor():
            while not stop.wait(1):
                listing = subprocess.run(['ps', '-axo', 'pid=,ppid=,rss=,pcpu='], text=True, capture_output=True, check=True)
                table = [line.split() for line in listing.stdout.splitlines()]
                family = {process.pid}
                for _ in range(4):
                    family.update(int(row[0]) for row in table if int(row[1]) in family)
                members = [row for row in table if int(row[0]) in family]
                if members:
                    samples.append({'seconds': round(time.monotonic() - started, 3),
                                    'rss_mib': round(sum(int(row[2]) for row in members) / 1024, 2),
                                    'cpu_percent': round(sum(float(row[3]) for row in members), 1)})

        watcher = threading.Thread(target=monitor, daemon=True)
        watcher.start()
        code = process.wait()
        stop.set()
        watcher.join()
    if code:
        raise SystemExit(code)
    with args.output.open() as stream:
        rows = list(csv.DictReader(line for line in stream if not line.startswith('#')))
    result = summarize(rows)
    result['mode'] = 'native window' if args.native else 'CPU/GPU synchronized offscreen'
    result['peak_family_rss_mib'] = max((row['rss_mib'] for row in samples), default=None)
    with memory_path.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=['seconds', 'rss_mib', 'cpu_percent'])
        writer.writeheader()
        writer.writerows(samples)
    args.output.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
