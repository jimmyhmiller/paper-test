# Paper Blog

A native macOS, Coil/Papercut dashboard for Jimmy Miller's blog. One screen
shows all recorded views, the daily total, selected-post daily and hourly activity, a day/hour heatmap, and a scrolling index of posts with
views in that period. It uses the live Website analytics service already used
by Jim Editor; there are no comparison metrics or extra dashboard screens.

## Run

```sh
python3 scripts/build.py
python3 scripts/install.py
open '/Applications/Paper Blog.app'
```

The installer verifies the signature, stages the bundle on the destination volume, and replaces any previous installation with rollback on failure. The installed app is independent of the checkout. To keep it in the Dock, open its Dock menu and choose Options → Keep in Dock.

The signed bundle includes its title catalog and a paper-rendered icon. It
requires macOS 14 or later and `/usr/bin/curl`. Builds require the installed Coil
compiler and Apple's command-line tools. No Python process runs inside the app.

## Interactions

- The main chart is a stack of individually cut paper bands, one per post.
  Each band's thickness is that post's actual daily count, on a common absolute
  scale. Hover a band or index row to lift that post's sheet and show its full
  title, count, and daily history in the fixed detail area. The same paper color
  identifies the post in the stack, index, and isolated detail shape.
- Drag across the top graph to select a date range. Its paper frame stays visible on the full-history overview. Hover and click the paper bands normally inside the selection. Drag its interior to move it or either gold grip to resize it. Double-click inside the selection to focus the top graph on those dates; double-click that focused range again to return to full history. Daily bars, hourly totals, and the heatmap all use that same local date range, including zero-view days. A pinned post stays selected. Click the total, empty paper, or Escape to clear the range and post selection.
- Control-click or right-click a post row or paper band to exclude it from totals and all graphs. Excluded rows stay visible with muted titles seated in recessed paper; secondary-click again to include them. The post count shows how many remain included. Exclusions follow post paths across automatic refreshes, and new posts are included. Clicking the total restores all posts and clears the date/post filters. These filters last for the current app session.
- Daily and hourly bars lift toward the viewer with a tiny centered expansion of a single paper face and thin cut edge, then settle back. Their centers stay fixed, with no diagonal slide; the paper texture follows the same scale. Their stationary footprints and hit regions retain the original count scale. Lift follows global paper depth and respects macOS Reduce Motion.
- Hover the charts to inspect the exact local date and count. Inspecting the
  main chart also shows that day's count for the selected post.
- Hover previews a post. Moving across sidebar gaps, gutters, or the scrollbar preserves the current preview; leaving the sidebar restores the all-post view. Click a post or paper band to pin it while inspecting graphs. A bordered row shows the lock. Click the same post again to unpin while keeping the selected dates. Click the total, empty space, or Escape to restore all posts and the full date range. Click another post to switch the pin. Arrow keys move through
  the index. Tab, Shift-Tab, Space, and Return use the native Paper focus system.
- **Command-R** refreshes the data. It also refreshes automatically every five
  minutes. Concurrent refreshes are coalesced.
- **Command-O** opens the selected post on jimmyhmiller.com.
- Resize the window. All posts remain reachable at the minimum
  1280 × 900 content size through a scrolling index, with readable fixed-size rows.

Selected-post daily and hourly bars scale to that post's own peak to show
its activity clearly. Use the printed counts for absolute volume; the main
chart's stacked bands share one absolute scale and sum to the total each day. Long
index labels have editorial abbreviations; the detail area and accessibility
labels expose the full title.

Band hit regions use the actual cut-paper paths, not bounding rectangles. While
the pointer moves within one layer, the exact-day readout updates without
requiring a layer change. Low-count layers retain their true thickness; they
can always be selected through the index even when too thin to point at easily.

The unified window keeps native traffic lights in their system positions. Rich dyed compressed-pulp stocks, exposed sheet edges, and directional shadows give the graphs physical paper relief. Hourly bars show only the selected post; the heatmap follows the selected post and shows its hourly views in fixed absolute-count bins. Hover links dates and hours across the charts; click to pin and Escape to clear.

Click the small gold sun stamped into the upper-right corner of the daily-views sheet to open the persistent paper and sunlight editor. The draggable sun map controls lighting across the entire dashboard. All paper controls apply globally to every sheet, graph, tile, and panel in this dashboard. Each slider shows its value. Hold Shift while dragging for ten-times finer adjustment. Drag the card by its header; close it with the sun, ×, or Escape. It stays open while you hover, scroll, select posts, or inspect uncovered graphs. The editor uses cut-paper pull tabs in recessed tracks and a die-cut sun over a recessed paper map. It only captures its own controls; Escape closes it before clearing any post pin. Reset all restores and saves every default immediately.

| Parameter | Range |
| --- | --- |
| Sun X / Y | −5 to +5 window widths / heights |
| Sun height | 10–20,000 points; curved slider for low-height precision |
| Paper depth | 0–12× |
| Paper grain | 0–10× |
| Texture size | 0.25–16× |
| Texture depth | 0–8× |
| Texture angle | −180° to +180° |
| Hover movement | 0–30; zero disables bar movement |

Hover movement adjusts the lift across both bar graphs and saves automatically. Its built-in default is defined by `DEFAULT_HOVER_LIFT` in `src/tuning.coil`.

The controls edit real renderer/material parameters. Paper elevations stay within the renderer’s canonical 64-point stack; the independent depth multiplier permits exaggerated physical relief. Chart positions, counts, and selection paths do not change. New fields extend the existing preferences dictionary, preserving earlier saved lighting values.

## Live data and offline use

The app launches curl directly, without a shell, using the existing credential
file `~/.jim/dataflow/analytics.curl`. Credentials are never copied into the
bundle, cache, logs, or command-line arguments. Set `PAPER_BLOG_AUTH_CONFIG` to
use another curl configuration file.

It requests `/analytics/timeline?prefix=/api/&n=all&bucket=hour&from=…&to=…`
from `https://computer.jimmyhmiller.com`. This is the backend's blog-scoped
endpoint, not the general multi-project request summaries. Both bounds are
explicit epoch milliseconds: from zero through the current request time, covering all available history. The visible axis begins at the first recorded bucket, with no artificial 1970 start. The first and last local calendar days can be partial. Source buckets are validated in UTC, then regrouped into the Mac’s current timezone before any chart is drawn. Daily totals use local midnight; hourly bars and heatmap rows use local hours. At daylight-saving transitions, repeated fall hours are combined and nonexistent spring hours stay unobserved. View counts are conserved. Legacy daily caches are refreshed from the hourly service because UTC daily totals cannot be accurately split into local days.

The complete recorded date axis is zero-filled, even if no post has views on
a day. Each post's daily counts must add up to its reported total. Invalid JSON,
unexpected schemas, duplicate posts, negative/fractional counts, unaligned or
out-of-range dates, and mismatched totals reject the new snapshot. Empty data
is valid. There is a 16 MiB response limit and a 45-second request timeout.

Only a validated response replaces the screen. The last good snapshot is
written atomically to
`~/Library/Application Support/Paper Blog/timeline.json`. A failed refresh
preserves it and displays an actionable error. With no
snapshot, the screen displays the error and a clean empty state. Set
`PAPER_BLOG_CACHE_DIR` to isolate the cache for development or tests.

The title catalog is bundled, so the app does not need the blog checkout at
runtime. New posts work immediately with a readable slug-based fallback. To
refresh the optional full-title metadata from a local checkout:

```sh
python3 scripts/update_titles.py /path/to/jimmyhmiller.github.io
python3 scripts/build.py
```

## Selection performance

The overview retains cumulative contours and paper outlines until data or layout changes. Its date highlight repaints through a GPU coverage window on the original mask; it adds no cut edges. The heatmap batches each column's cells by paper stock and elevation, with backing-pixel-aligned column edges for coverage-cache reuse. Every cell and relief level remains present, and lower graphs update throughout dragging.

Run the repeatable benchmark with the app's full-history cache or an explicit timeline fixture:

```sh
python3 scripts/benchmark_selection.py --native --frames 3600
python3 scripts/benchmark_selection.py --native --frames 480 --exclude-top 2
python3 scripts/benchmark_selection.py --frames 240 --fixture tests/fixtures/all-time.json
```

The native mode opens a window and drives selection creation, movement, resizing, and pinned-post ranges through actual app event handlers. It reports update intervals, compositor presentation counters, CPU stage costs, and CPU/memory samples. Inspect dropped presentation counts when the window is occluded; processing intervals alone do not establish visible frame rate. The offscreen mode synchronizes CPU/GPU work for each frame. Reports are CSV and JSON in `build/`; native `gpu_ms` is unused because native presentation remains asynchronous. These are measurements, not fixed pass/fail timing tests.

## Verification and previews

```sh
coil verify
coil build
python3 scripts/check_source.py
build/release/paper-blog --fetch-once
build/release/paper-blog --fixture tests/fixtures/sparse.json --fetch-once
build/release/paper-blog --fixture tests/fixtures/empty.json --snapshot build/empty.png
build/release/paper-blog --width 1280 --height 900 --snapshot build/minimum-live.png
```

`--fixture` is explicit, disables networking, and labels the screen as fixture
data. Normal launches always use the real API. Snapshot mode waits for the
request to finish; normal UI launches stay asynchronous. `--fetch-once` prints
only aggregate counts and request status, and exits nonzero on failure even
when a valid cached snapshot is available.

Project notes and rendered previews: [paper-blog](pad://paper-blog), linked from
the [paper-test project index](pad://paper-test).
