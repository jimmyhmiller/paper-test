# Profiling Paper scenes

`paper.profile` provides two compile-time forms for measuring a stage without
repeating clock reads and bookkeeping:

```coil
(profile/measure-ms (.build cost)
  (build-scene))

(profile/accumulate-ms (.lookup cost)
  (lookup-mask key))
```

Both evaluate the body once and return its result. `measure-ms` replaces the
destination with milliseconds; `accumulate-ms` adds milliseconds. Generated
local names are fresh, so a caller's bindings cannot be captured. The renderer,
mask preparation, and drawable acquisition use these forms. Their destinations
are ordinary fields or mutable locals, so adding a stage does not require a
new profiler implementation.

For counters that should incur no clock reads until profiling is enabled,
`profile/start` and `profile/elapsed` remain available. Set
`(.enabled (profile/counters))` to true before collecting them. The transcript
diagnostics overlay enables these counters and keeps a rolling frame window.

To measure Paper Transcript's continuous scroll workload, build the app and run:

```sh
PAPER_HEADLESS=1 PAPER_TRANSCRIPT_BENCH=scroll \
  apps/paper-transcript/build/paper-transcript --app 26
```

Headless frames run CPU and GPU work in series and report a conservative
throughput. `PAPER_TRANSCRIPT_BENCH_FOREGROUND=1` runs the same scripted gesture
in a visible window so display callbacks, tick cadence, draw rate, and drawable
waits can be checked separately. Benchmark initialization restores the 16 ms
tick after take selection, so the gesture actually advances every display tick.
