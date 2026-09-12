# Complex Paper scenes

Work in progress against Jimmy's two 1536 × 1024 reference collages. The current
focus is the top-right ukiyo-e scene from the second collage. It has a Fuji
vignette, notched cherry petals with stamens, shoji lattice, cut-paper panes and
engraved surf. The other seven scenes remain exploratory workload fixtures.
The earlier botanical example did not meet the reference's detail or visual quality.
Visual acceptance and measured frame pacing remain separate requirements.

## Run

From this directory on macOS, with the installed Coil toolchain:

```sh
coil run
```

The app opens with ukiyo-e. Click the large red sun in the artwork to open its
lighting popover; Escape dismisses it. Click filenames to change selection and
press Space to animate the blossoms. Left/right arrows switch scenes. Other
scenes retain the theme strip and standalone lighting control. Source text and
search are demonstration content, not an editor or working workspace search.

The package depends on `../../lib/paper` and runs independently of the parent
demo's coil-experiments dependencies. Keep `src/main.coil` as a thin entry point.
Tests import the entry-free gallery and workload modules because the current
Coil test runner can skip test synthesis if an imported module defines `main`.
The `coil-bugs` pad contains the upstream report.

## Verify and measure

```sh
coil test
python3 tools/test_report.py
coil build tools/inspect.coil -o build/inspect
PAPER_BENCH_THEME=5 ./build/inspect build/ukiyo.png
coil build tools/benchmark.coil -o build/benchmark
PAPER_BENCH_WIDTH=3840 PAPER_BENCH_HEIGHT=2520 PAPER_BENCH_FRAMES=120 ./build/benchmark > build/completed.csv
python3 tools/report.py build/completed.csv --warmup 30 --expected-frames 120 --expected-themes 8
coil build tools/native_benchmark.coil -o build/native-benchmark
PAPER_BENCH_THEME=5 PAPER_BENCH_FRAMES=600 ./build/native-benchmark > build/presented.csv
python3 tools/report.py build/presented.csv --warmup 30 --expected-frames 600 --expected-themes 1
```

The native benchmark opens a window and requests a 60 Hz display clock. Leave it
visible during the run. It retains source frame IDs and waits for GPU completion
and presentation callbacks before releasing a sample. Zero presentation times
count as dropped frames. Multiple callbacks with the same timestamp count as one
display instant; the report lists the additional shared timestamps. The CSV includes
cold frames. Expected counts detect missing tails, and the report rejects duplicate
IDs and backwards timestamps. Intervals over 25 ms count as long presentation gaps.
Average fps can hide uneven pacing, so inspect interval percentiles too.
CPU submission time excludes asynchronous GPU execution.

For a deadline investigation, inspect `requested_s`, `clock_duration_s`, and the
absolute `gpu_start_s`/`gpu_end_s` fields. The report counts CPU submissions and
GPU completions after the requested presentation time, apart from actual display
gaps. It also reports requested interval spacing. On-time rendering does not prove
on-time display.

To compare Metal minimum-duration presentation with the default absolute-time
policy, run the native benchmark with `PAPER_BENCH_MIN_DURATION=1`. This requests
1/60 second of display time for the previous drawable. In that mode, `requested_s`
is zero and `min_duration_s` records the policy; the report omits absolute-deadline
lateness metrics. See Apple's [minimum-duration presentation documentation](https://developer.apple.com/documentation/metal/mtldrawable/present(afterminimumduration:)).

The completed-frame benchmark waits for the GPU on each frame and includes scene
construction. It excludes screenshot readback. It does not measure display fps.

Both benchmarks accept `PAPER_BENCH_WIDTH`, `PAPER_BENCH_HEIGHT`,
`PAPER_BENCH_FRAMES`, `PAPER_BENCH_THEME` (first theme) and `PAPER_BENCH_THEMES`
(count). The completed-frame benchmark also accepts `PAPER_BENCH_DENSITY`.
Raster dimensions use a backing scale of 2. Themes 0 and 5 scale their authored
geometry to the viewport; the remaining fixtures have responsive point layouts.

Scenarios: 0 moves the light, 1 changes selection and inserts/removes cursor ink,
2 moves decorative geometry. Early CSVs had no-op scenario-2 rows for themes
1, 6 and 7; discard those rows when evaluating animation performance.

The repository root has a separate 110-test regression suite: run `coil test`
there. Its manifest needs the sibling coil-experiments checkout.

## Renderer changes

For damage comparison we merge sheets and ink in painter order, strip equal ends,
and use an exact Myers edit comparison to retain unchanged interior commands.
A selection change and cursor insertion can now share a frame without invalidating
the paper stocks between them. We cap the search at 64 edits and use conservative
redraw beyond that budget. Reordering remains an edit; raster quality is unchanged.
For Metal material composition we retain up to 32 separated damage regions,
merge touching regions, and collapse to their union if fragmentation exceeds
that bound. We prepare the frame mask working set once, encode the pixel-aligned
regions in one shared render pass, then allow cache eviction. Overlapping regions
retain the same painter ranks and preserve depth/coverage results.
Normal/material preparation accumulates changed
bounds with a two-pixel dependency halo; we still rebuild the shadow-height
hierarchy. The CPU fallback covers the enclosing bounds. GPU lighting expands
those bounds by the maximum shader ray reach for the current light and viewport,
including the sample offset and edge margin. This changes dispatch coverage only;
the shadow samples and their appearance stay unchanged.
`masks/last-composed-area` records the summed pixel area
of the composition passes, including any overlap from antialias padding.

For a stage-cost diagnostic, build `tools/stage_benchmark.coil` and run it with
`PAPER_BENCH_THEME=5 PAPER_BENCH_FRAMES=300`. It reports scene construction,
material composition, and preparation/lighting separately, including completed
GPU times and composed pixel area. It inserts waits between stages, so use the
native benchmark to assess presentation cadence. Empty stages report zero GPU
time rather than repeating the preceding command buffer's measurement.
The `micro_pixels` column counts regenerated material-texture samples separately
from the pixels composed onto the scene. Rendering requests these samples only
where the sheet intersects damage, retaining the original pattern phase, origin
and scale. Cached supersets remain reusable; shader sampling is unchanged.

In the 60 fps native report, `missed_intervals` counts presentation gaps of at
least 25 ms, with a 1 µs timestamp tolerance. Earlier reports used a strict
greater-than comparison and undercounted 25 ms gaps; regenerate those summaries
from their source CSVs before comparing results.

Coverage masks use a lossless RG8 atlas for large sparse or solid shapes. A
64 × 64 tile is empty, solid, or contains exact mixed-coverage samples. Mixed tiles
retain both antialiasing and edge coverage channels. Dense masks remain preferable
for small shapes or incompressible data. Distance fields retain their own format.
CPU packing and Metal decoding use the same backing-pixel phase; tests compare
final GPU output byte-for-byte with dense masks, including fractional placement
and embossed glyph counters.

The cache pins current-frame masks through encoding and accounts for stored texture
payloads. A frame larger than the 256 MiB persistent budget may use temporary
resources; after encoding, the cache releases its excess copies while the command
buffer retains the textures it needs. This avoids preparation/encoding eviction
loops without reducing resolution or increasing the persistent budget.

Mask lookup hashes exact path elements, text and geometry, then checks full equality
on hash matches. Positive and negative zero share a hash. The cache tracks recency
with linked entry indices and queues raster work for unbuilt masks only. Eviction
remaps moved slots and rebuilds the hash index after the batch.

## Scene authoring

`src/ukiyo.coil` uses a 768 × 512 design coordinate system. Cut-paper geometry has
height and material; printed ornament uses `paper_path_ink` without changing the
paper surface. For the red sun, we use the same visible path for drawing and
`paper_path_hit`, subtracting the foreground cloud from the circle.

Use `tools/trace_waves.py`, `tools/trace_mountain.py`, `tools/trace_panels.py`,
and `tools/trace_clouds.py`
to extract vector contours from the surf, Fuji, and paper stocks in the supplied
second collage. Each takes the reference image path, requires OpenCV and NumPy,
and emits Coil source on stdout. The corresponding editable assets are
`src/wave_paths.coil`, `src/mountain_paths.coil`, `src/pane_paths.coil`, and
`src/cloud_paths.coil`.
At runtime we combine these native contours with hand-authored engraving paths;
we do not load reference image pixels or baked reference lighting.

For the Fuji foothills, we author blue-gray and charcoal stock contours apart
from the printed ink. We close fiber-sized pigment breaks and fill interior
printing during extraction, then retain the largest connected piece of each
stock. The native scene puts these ridges above supporting mountain paper and
prints clipped grain on their surfaces. We cache the canonical stock paths and
grain intersections; viewport changes require transformed copies.

The pane tests check continuous printable interiors and stock containment at
1×, 2×, and 3×. They allow a 0.05-reference-unit boundary tolerance for Core
Graphics Boolean-curve precision. Runtime paths do not use that test expansion.

## Remaining work

Compare the cloud lips and flat navy backing against the reference.
The red pane folds need more crease detail, and the surf engraving needs closer
alignment with the reference currents. Inspect the contour extraction boundaries
before accepting the composition.
The remaining themes also need reference-specific artwork.

Cold preparation still exceeds 16.67 ms. Warm 60 fps does not cover first appearance,
theme switches, prolonged resize, or long runs under memory pressure. Next renderer
work should measure cold path construction, rasterization and upload separately
before choosing an approach.

See the indexed `paper-test-complex-scenes` pad for reference images, bug reports,
visual revisions and measurements. Local benchmark CSVs and screenshots are ignored
under `build/`; regenerate them using the commands above.
