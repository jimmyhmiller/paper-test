# Paper Transcript

A podcast editor where you cut the words and the audio follows. Whisper writes
the transcript, you edit the transcript, and the edit resolves to a list of kept
spans that both playback and export read. The source recording is never
modified.

Built on the [Papercut](../../README.md) renderer: every panel, chip, letter and
waveform bar is a real sheet of colored paper at its own elevation, lit by one
warm key light.

## Run

```sh
python3 -c "import os; os.makedirs('apps/paper-transcript/build', exist_ok=True)"
cd apps/paper-transcript
coil build -o build/paper-transcript
./build/paper-transcript
```

`--app N` opens the Nth recording. `--snapshot out.png` renders one frame at
twice the logical resolution and exits.

## The library

Recordings are read from `~/.jim/recordings`; transcripts, legacy waveform envelopes
and edit lists are cached beside them in `~/.jim/transcripts`. These are the
same directories and the same file formats the podcast editor in jim uses, so
an existing corpus opens here with its transcripts and cuts intact, and an edit
made in either editor is visible to the other.

| File | Contents |
| --- | --- |
| `<take>.json` | whisper output: word text with millisecond offsets |
| `<take>.peaks.json` | Legacy normalized 10 ms envelope; compatible with jim, not the source of the native waveform display |
| `<take>.edits.json` | the edit list: deleted words, gaps, trims, regions |

Both whisper shapes are read. `whisper-cli -ojf` writes per-token DTW timings,
where a token beginning with a space opens a word and the tokens after it extend
it; WhisperX forced alignment rewrites the same file as one word per segment.
A cache written before alignment finished still opens.

## Editing

Three surfaces feed one edit list.

**Words.** Click a word to move the playhead there, drag to select a run,
shift-click to extend. Delete cuts the selection; Delete again restores exactly
what it took. Filler words (`um`, `uh`, `er`, …) are detected on their letters
alone, so `Um,` and `um` are the same word, and `Fillers` cuts every one of them
in a single pass.

**Silences.** Any pause over 300 ms gets a pill showing the silence that
survives, not the silence that was there. Tap it to cut that silence entirely or
restore it; drag it to trim the pause shorter. Drag sensitivity scales with the
gap, so a half-second pause and a ten-second one both take a comfortable drag. A
trimmed gap is cut from the middle of its silence, so the kept milliseconds
straddle the word boundary evenly and neither word loses its own breath.

Scroll the transcript, the recording list, or the waveform with the wheel or the
trackpad; pinch over the waveform to zoom around the pointer. A key the editor
has no use for is swallowed rather than passed to AppKit, which would beep at
it — except a ⌘ chord, which belongs to the menu.

Waveform zoom extends down to individual source samples. Each channel has its
own signed lane. The `↕` control changes only vertical display magnification
(0.5× through 16×), never playback or export gain. At 1×, lane height represents
full scale; magnification can move peaks outside that displayed range. The
source-time ruler gains decimal precision as you zoom in.

**Regions.** Drag on the waveform to select a span of audio and cut it — for a
cough or a bump that no word describes. A drag that overlaps an existing cut
restores it rather than stacking another.

Every edit is one undo step: ⌘Z steps back through them and ⇧⌘Z forward again,
each restoring the selection it was made with so you can see what came back. A
step records only the words it touched, so cutting six words costs six entries
and removing every filler in a two-hour transcript costs only the fillers.
Selecting a different take starts a fresh history.

`[` and `]` snap the selected word's start or end to the playhead. Whisper's
alignment is good but not perfect, and a word clipped one frame early is
audible.

Every edit is written to the take's edit list immediately. Reset discards all of
them and asks once before doing it.

## Playback

The take is decoded into memory the first time something is played, and reused
until the edit or the take changes. Each splice builds a new non-interleaved
float buffer from that source, and AVAudioEngine plays it. The
playhead comes from the player node's own sample clock, so the highlighted word
and the waveform cursor track the audio exactly rather than estimating from wall
time. Seeking presents a different window onto the same allocation through
`bufferListNoCopy:`, so it costs nothing regardless of episode length.

Seams are declicked with short equal-power ramps *inside* each kept span rather
than by overlapping neighbours. An overlap would shorten the timeline by a few
milliseconds per seam, and a heavily cut episode has thousands of them: the
transcript would drift visibly out of step with the audio and the exported file
would no longer match the preview. The `crossfade` toggle switches these ramps
on and off; edited duration stays exactly equal to the sum of the kept spans
either way.

Export renders the same spans with ffmpeg, applying the same ramps, so the file
and the preview have identical timing.

## Jobs

`Re-do STT` runs ffmpeg → `whisper-cli` → WhisperX alignment as a detached shell
pipeline and reads whisper's progress back from the job log. If alignment is
unavailable the whisper timings remain, which are already good enough to edit
against. Selecting a take reads its source waveform in the background using
AVAudioFile, without writing a cache or changing the recording. Changing takes
cancels the old scan. Transcription is expensive and stays an explicit request.

Requires `ffmpeg` and `whisper-cli` on `PATH`, a whisper model at
`~/.jim/models/ggml-large-v3.bin`, and — for alignment — `uv` and
`~/.jim/whisperx_align.py`.

## Performance

Both large views are cached and rebuilt only when their inputs change.

The transcript is a wrapped flow of independently positioned words, measured
with the same native fonts the renderer draws with. Positions are computed once
per width change; scrolling binary-searches the first visible word and stops at
the bottom of the viewport, so a two-hour transcript costs the same to scroll as
a two-minute one. Runs of the same state on one line are drawn as one piece of
paper: a hundred consecutive cuts read as a single hole in the page rather than
a hundred adjacent holes with a hundred seams between them.

The waveform reads native-rate, non-interleaved Float32 source samples. A
background scan builds signed min/max trees, separately for each channel, with
256-frame leaves. Overview queries conservatively include boundary leaves:
no transient is discarded, and boundary overcoverage is less than one backing
pixel. Below that resolution, a bounded native PCM cache supplies exact ranges.
At the closest zoom those ranges become individual samples and a connected
trace. There is no mono mix, energy transform, smoothing, resampling, or local
normalization in this display path.

The overview is drawn as separate cut-paper strips on a five-point pitch, with
fine pulp edges and real gaps. Each strip merges **all** signed extrema in its
time slice, including samples whose times fall under the visual gap. This
intentionally aggregates horizontal detail for the paper silhouette: multiple
events within one strip are not individually distinguishable until zoomed in.
Peaks are not averaged away. Sample-level zoom still draws actual samples.
Strip bins are anchored to the source, including partly visible edge strips,
so panning does not change their amplitudes. Tiny ranges have a 1.1-point
minimum paper height for visibility. Display magnification is explicit.

The ledger's `SUN HEIGHT` slider controls shadow length independently of the
sun's x/y position and paper depth (200–2400; lower means longer shadows).
Recording cards lift on hover and grow on selection. Button hover uses a small
pigment adjustment and physical lift rather than washing the color out.
The main title is shallow, dark letterpress; the page uses watercolor stock,
and a deeper kraft tray carries the audio controls. Routine status text is not
printed on the tray. Action notices and errors remain in the window footer.

The earlier scroll-performance baseline below predates the richer materials and
native waveform. Four problems were fixed in that work:

**Every visible word was rasterized again on every frame.** Words under the
transcript's viewport carried the viewport's clip in their mask key, positioned
relative to the word, so each scroll step made every key new. Sheets under a
clip were intersected with it, which rebuilt their paths with rounding that
depended on where they sat, so a pill that had not changed shape still missed
the cache. The renderer now leaves a clip off anything the clip contains
entirely; clipping it would change no pixel.

**Fractional scroll positions defeat the cache too.** A trackpad reports
fractional deltas, and text moved by a fraction of a pixel lands on a new
sub-pixel phase that has to be rasterized afresh. The transcript is drawn at its
scroll offset rounded to a whole backing pixel, as native scroll views are;
moved by whole pixels, each word keeps its cached mask. The stored offset stays
exact, so a slow scroll still accumulates.

**The mask cache was searched linearly.** With twelve thousand masks, finding
six hundred of them cost 8 ms a frame. It is now indexed by a hash of the key,
with the full comparison still deciding every match, and evicts in batches
instead of scanning for the single oldest mask on every insert.

**The tick was out of step with the display.** Anything animated by the tick —
the playhead during playback, the benchmark — was polled on a 16 ms timer
against a 16.7 ms display, and skipped whenever a frame arrived a little early:
it advanced on three frames in four. The tick now runs on the display link,
before the frame is drawn.

| scroll, take 26, trackpad-sized steps | before | after |
| --- | --- | --- |
| frame rate on screen | 36 fps | 60 fps (display-locked) |
| frame rate headless (capacity) | 32–36 fps | 90 fps |
| masks rasterized per frame | 152–236 | 44 |
| mask cache lookup | 8.0 ms | 0.3 ms |
| scene build | 5.3 ms | 2.2 ms |

The transcript is a sheet of its own, laid into a hole in the page, because its
holes move on every scroll and re-rasterizing the whole page with them costs
6 ms a frame. Its boundary is marked seamless — the holes are paper edges, the
join with the page is not — so the two read as one piece of paper.

## Diagnostics

Press **⇧⌘D** for a live overlay and **⇧⌘T** to write a trace — chords, so they
cannot be hit by accident. Start with the overlay
already on with `PAPER_TRANSCRIPT_DIAGNOSTICS=1`.

| line | meaning |
| --- | --- |
| `fps · frame · build · worst` | frame rate and period over the last 120 frames, and the time spent building the scene. Periods over 250 ms are left out, so an idle editor does not report a false low rate. |
| `display` | the display link's rate, and link callbacks, ticks and draws per second, and whether the window is on screen. Draws below callbacks mean frames were offered with nothing new to show; callbacks below the link rate mean macOS slowed the link, which it does for covered windows. |
| `raster parts` | the renderer's CPU stages for the frame: relief resolution, command sort, damage measurement, the mask pass, and remembering the scene for the next frame's damage. |
| `gpu` | GPU execution time and time spent waiting for a drawable, how many frames were presented before the GPU finished the one before, and the mask pass split into preparing masks, material microstructure, visibility and encoding. |
| `mask lookup` | time spent in the mask cache per frame, lookups and misses per frame, and the masks it holds. Misses are masks rasterized that frame. |
| `rail · sheet · text · wave · ledger` | build time of each region for the last frame, in ms. `text` and `wave` are inside `sheet`. |
| `sheets · ink · hits · damage` | what the renderer was handed, and the size of the region it last redrew. |
| `take`, counts | the open recording: words, clips, regions, peak buckets, length. |
| `audio` | decoded format, source and spliced frame counts, transport state. |
| `wave`, `text` | zoom, scroll, native column count, channels, sample rate, extrema/sample mode and display gain; transcript scroll and selection. |

`build` is only the draw callback. Everything after it — composition, shadows,
presentation — is the renderer's, so a frame much longer than its build time
points there rather than at the editor. The trace goes to
`/tmp/paper-transcript-trace.txt` and to stdout, with the view sizes, the edit,
undo depth, background job and status added. Opening a take also prints its
load stages to stdout while the overlay is on.

Two things dominated before they were fixed, both worth knowing about:

**Reading a JSON array by index is quadratic.** `array-nth` on a token tape
scans from the array's start, so pulling 137,000 peak buckets out one at a time
took 11.8 seconds. Arrays are walked sequentially instead — children start at
the array token + 1 and `next-index` steps over each value's subtree. Opening a
23-minute take went from 12.5 s to 14 ms.

**Decoding and splicing happen on demand, not on selection.** Decoding a
23-minute stereo take costs ~640 ms and splicing its edit ~40 ms. Neither is
needed to draw a transcript, so both are deferred to the first press of play and
reused until the edit or the take changes. Selecting a take is 0.3–15 ms; an
edit marks the splice stale rather than performing it.

## Visual verification

The `paper-transcript-fidelity` project pad contains the 45-item mockup audit,
causes, before/after renders, waveform accuracy notes, and measured timings.
It is linked from the `paper-transcript` and `paper-test` index pads.

`tools/visual_fixture.coil` supplies deterministic synthetic words and states
without modifying recordings. `tools/waveform_view.coil` renders a real take at
an explicit source position and zoom; neither harness exports or edits audio.

```sh
coil test
coil test tests/waveform_integration.coil
coil build tools/visual_fixture.coil -o build/visual-fixture
./build/visual-fixture --snapshot build/states.png
TRANSCRIPT_TEST_WIDTH=1120 ./build/visual-fixture --app 1 --snapshot build/narrow.png
coil build tools/waveform_view.coil -o build/waveform-view
TRANSCRIPT_TEST_ZOOM=192000 TRANSCRIPT_TEST_START=367450 TRANSCRIPT_TEST_GAIN=4 \
  ./build/waveform-view --app 26 --snapshot build/samples.png
```

Integration tests read `demo_fillers.wav` from the local recording corpus and
compare the waveform with independently decoded native PCM. The unit tests
also cover isolated impulses, opposite-polarity channels, quiet detail,
sub-sample panning, boundary coverage, and the full-resolution paper rib grid.

## Benchmark

`PAPER_TRANSCRIPT_BENCH` runs a scripted benchmark: every tick it scrolls the
transcript and pans the waveform, then after 240 frames writes a trace and
exits. `=scroll` or `=pan` exercises one gesture alone; any other value does
both.

| variable | effect |
| --- | --- |
| `PAPER_TRANSCRIPT_BENCH_ZOOM` | waveform zoom in points per second |
| `PAPER_TRANSCRIPT_BENCH_STEP` | points scrolled per frame, 14 by default. A fractional step such as 13.3 measures what a trackpad scroll costs. |
| `PAPER_TRANSCRIPT_BENCH_SNAPSHOT` | also write the last frame as a PNG, so two builds can be compared pixel for pixel after the same scripted run |
| `PAPER_HEADLESS=1` | run with no window at all |

```sh
PAPER_TRANSCRIPT_BENCH=scroll PAPER_TRANSCRIPT_BENCH_ZOOM=2.2 PAPER_TRANSCRIPT_BENCH_STEP=13.3 ./build/paper-transcript --app 26
```

A benchmark launches in the background: the window opens behind your other
windows and the application is never activated, so it neither takes keyboard
focus nor covers what you are doing. `PAPER_BACKGROUND=1` does the same for any
Paper application. On screen the frame rate is locked to the display; headless,
frames run back to back, so the rate is the renderer's capacity — the CPU and
GPU cost of a frame in series. The stage costs agree between the two to within
about 10%.

## Layout

`arrange` trees from [lib/layout](../../lib/layout/README.md) solve everything
except the two views above. The window is responsive with one logical unit per
native point, down to 1120 × 760, and unified: the content reaches the top edge
and the traffic lights sit on it, so the header keeps clear of them by
`paper_titlebar_inset`.

## Renderer changes

The editor needed these from `lib/paper`. New calls are opt-in; the behaviour
changes apply to every Paper application.

| addition | purpose |
| --- | --- |
| `paper_unified_window` | responsive windows otherwise keep an ordinary title bar |
| `paper_key_flags`, consumed keys | a key handler can report a key as used, so AppKit does not beep at it |
| event kind 8, `paper_magnification` | trackpad pinch |
| `paper_background_launch`, `PAPER_BACKGROUND` | open behind other windows without activating |
| `PAPER_HEADLESS` | run the tick, draw and render loop with no window |
| `paper_backing_scale` | backing pixels per point, for pixel-aligned scrolling |
| `paper_snapshot` | write the current frame at any point in a run |
| `paper_display_frames`, `paper_display_period`, `paper_tick_count`, `paper_window_visible` | frame pacing diagnostics |
| `seamless-outline` | mark the rest of a sheet's outline as a join with coplanar paper, drawn with no edge |

| behaviour change | effect |
| --- | --- |
| scroll deltas in logical points | scaled up for devices that report lines rather than pixels |
| hashed mask cache, batch eviction | lookup cost no longer grows with the cache |
| contained clips left off | a clip that contains an ink or sheet no longer enters its mask key or its path |
| tick on the display link | a tick of one frame or less runs on every frame, before it is drawn |

The contained-clip change alters a few hundred pixels on pill rims by up to
32/255 in one channel: those shapes now keep their own geometry instead of a
boolean-operation copy of it.

## Verification

```sh
coil test                       # 68 unit tests
coil test --suite integration   # decodes and plays a real take; needs audio
coil fmt --check src/*.coil tests/*.coil
coil lint
(cd ../.. && coil test)         # the renderer's own suite, 111 tests
```

`coil lint` reports findings in `lib/` that predate this editor; it reports
none in the editor's own files.

The unit tests cover edit-list construction, region subtraction, gap trimming,
the edited↔source time mapping in both directions, both whisper JSON shapes,
edit-list round-tripping, word and pill hit testing, scroll clamping, zoom
anchoring, tick cadences, buffer reallocation when a take's channel count
changes, and the splice — including that the spliced length equals the sum of
the kept spans exactly, which is the invariant that keeps the transcript in step
with the audio.

The integration suite is opt-in because it decodes and plays a real recording
from this machine's library and needs an audio device. It checks that the
decoded length agrees with the measured envelope, that the reported playhead
advances in real time, and that seeking lands where it was asked to.

## Known limits

Speaker labels are not shown. Whisper does not diarize, and the pipeline here
does not run `whisperx --diarize`, so the transcript's left margin carries a
paragraph timecode instead of a speaker name. `Word.speaker` exists and the
margin tab will show a name once diarization data is available; inventing one
would be worse than showing the time.

Capacities are fixed and checked rather than grown: 40,000 words, 1 MB of word
text, 720,000 envelope buckets (two hours), 16,384 clips, 512 regions, 512
takes. Exceeding one is reported, not silently truncated.

Export shells out to ffmpeg and does not re-encode to anything but WAV.
