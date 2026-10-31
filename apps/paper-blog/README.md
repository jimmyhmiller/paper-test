# Paper Blog

A native macOS, Coil/Papercut dashboard for Jimmy Miller's blog. One screen
shows the last 30 days of recorded views, the daily total, selected-post daily and hourly activity, a day/hour heatmap, and a scrolling index of posts with
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
- Hover the charts to inspect the exact UTC date and count. Inspecting the
  main chart also shows that day's count for the selected post.
- Hover previews a post; leaving restores the all-post view. Click a post or paper band to pin it while inspecting graphs. A bordered row and “Pinned” status show the lock. Click the same post again to unpin, or click the total, empty space, or Escape to restore all posts. Click another post to switch the pin. Arrow keys move through
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

## Live data and offline use

The app launches curl directly, without a shell, using the existing credential
file `~/.jim/dataflow/analytics.curl`. Credentials are never copied into the
bundle, cache, logs, or command-line arguments. Set `PAPER_BLOG_AUTH_CONFIG` to
use another curl configuration file.

It requests `/analytics/timeline?prefix=/api/&n=all&bucket=hour&from=…&to=…`
from `https://computer.jimmyhmiller.com`. This is the backend's blog-scoped
endpoint, not the general multi-project request summaries. Both bounds are
fixed epoch milliseconds, defining a rolling 30-day window. The first and last
UTC calendar days can be partial.

The complete requested date axis is zero-filled, even if no post has views on
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
