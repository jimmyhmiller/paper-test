# Papercut

A native macOS UI library written in Coil. Compose colored sheets at different elevations, cut paths through them, and light the resulting relief. The four example applications share the same geometry, materials, controls, and renderer.

## Run

Requires macOS 14 or newer, the installed Coil compiler, and Apple's command-line developer tools. Tested on this Apple Silicon Mac.

```sh
coil build
coil run tools/bundle.coil
open 'build/Papercut Studio.app'
```

Choose an application from the four tabs. Drag the light-position well or adjust light height, paper depth, and grain in the material workbench. Change the aperture shape, drag the cut, or cycle its paper stock.

```sh
coil test
coil run examples/minimal.coil
build/release/papercut --app 0 --snapshot build/agenthub.png
build/release/papercut --app 1 --snapshot build/herbarium.png
build/release/papercut --app 2 --snapshot build/listening.png
build/release/papercut --app 3 --snapshot build/elsewhere.png
```

Snapshots render at twice the logical canvas resolution. Snapshot mode uses fixture state and does not change saved preferences. Create the output directory before requesting a snapshot within it.

## Four examples

| Application | Material treatment | Working interactions |
| --- | --- | --- |
| AgentHub | Cream cotton, sage recesses, ochre and clay charts | Create named local agents, page the directory, search active agents, navigate tasks and analytics, check tasks, pause the sample cluster |
| Herbarium | Recycled green fibers, pressed-paper botanical shapes | Select plants, check independent care tasks, write and save an observation |
| Listening room | Peach linen, terracotta contours, cut vinyl grooves | Play three original Coil-synthesized ambient loops, change track and volume, save favorites |
| Elsewhere | Blue cotton, green contours, carved coastline | Change destinations, save places, adjust the trip from one to seven days |

These are local example applications. Agent metrics and charts use fixtures; they do not connect to a live agent service. The map is procedural artwork, not geographic navigation data. Herbarium retains the latest observation and a count, not a full journal archive.

The native application stores agent names, care selections, the latest observation, music favorites, and saved destinations with NSUserDefaults. Keys use the `studio.papercut.` prefix. Task checkmarks and trip length are session state. UI verification added a `PaperTester` agent and a sample observation to this machine's example workspace.

## Build your own interface

Start with [examples/minimal.coil](examples/minimal.coil), a complete 640 × 480 application. Import `paper.ui` for the public drawing and component API; import `paper.platform` for the application loop and native text input values.

Add a local `paper` dependency pointing to `lib/paper`. Copy the root manifest's `[link]` settings into your application manifest: the installed Coil compiler does not propagate all native linking settings from local dependencies. The library has no native source build step.

Use logical coordinates with the origin at the top left. Call `paper_configure` before `paper_run` to choose your title and canvas dimensions. The native window maintains the canvas aspect ratio and maps pointer input into those coordinates.

### Sheets and cuts

```coil
(panel (rect 24.0 24.0 592.0 432.0) 28.0 10.0 (clay))
(begin-sheet)
(rounded-path (rect 24.0 24.0 592.0 432.0) 28.0)
(oval-path (rect 365.0 90.0 170.0 170.0))
(finish-sheet 28.0 (cream))
```

This places cream paper at elevation 28 above clay at elevation 10. The enclosed oval is a hole, so you see the clay through it. Build curved outlines with `move-to`, `line-to`, `curve-to`, and `close-path`. Within one sheet, subpaths use the even-odd fill rule.

For a cut across several existing sheets, construct its path and call `cut-through floor`. This subtracts the path from previously submitted sheets above that elevation, including cuts that cross their outside edges. Submit the lower stock first. Cuts do not modify sheets submitted afterward.

`well` carves a three-step recess into the current stack. `frame` and `ring` add sheets with apertures. Wrap a component subtree in `with-elevation` to offset its depths; nested scopes restore the previous geometry and ink depth.

Elevations span 0 to 64 logical paper points. The renderer clamps geometry outside that range. Choose a lower overall depth multiplier for thin stock and a larger one for deep stacked relief.

### Materials and components

Use `cotton`, `linen`, `recycled`, or `smooth` with an RGB pigment. `stock` exposes roughness, fiber strength, and a deterministic texture seed. Presets include `cream`, `sage`, `moss`, `ochre`, `clay`, and `blue`. Texture stays attached to the paper as you move the light.

The component API includes buttons, toggles, checkboxes, sliders, editable inputs, labels, wrapped text, badges, metrics, rules, and progress bars. Compose row, column, and grid cells through `paper.layout`. Use area curves, area bands, annular segments, leaves, and contour paths from `paper.charts` for custom visualizations.

Use `choice-list` for vertical navigation and `tab-strip` for horizontal choices. Pass a slice of `Choice` values, a positive group ID, the selected item ID, bounds, spacing, and a `SelectionStyle`. Customize stock, selected stock, ink, typography, padding, elevation, and carved or raised treatment. Use `selection-row` for individual rows or `selection-surface` beneath custom contents; `leading` reserves room for icons. Item IDs must remain unique across the scene. Group IDs connect sibling choices for keyboard navigation.

For paged data, share `page-count`, `page-index`, `page-start`, and `page-length` between drawing and event handlers. Pages are zero-based. Out-of-range page indices clamp to the available data; empty data yields zero rows. The `pager` component disables Back and Next at their boundaries. AgentHub uses these helpers for its directory.

Wrap controls in `(with-enabled condition ...)` to disable a subtree. Nested scopes preserve a disabled parent. Disabled controls skip keyboard focus, reject activation, and expose their disabled state to accessibility. They block clicks from reaching controls behind them. Buttons and selection controls share hover feedback; pressed buttons carve a lower seat in the parent paper.

Text and rules inherit the last submitted sheet's elevation. Set `ink-height` to print at another depth. Higher sheets obscure lower ink. `cut-through` removes previously submitted text and rules above its floor along with the paper. Repeated cuts accumulate; ink at the floor and drawing commands submitted after a cut remain intact.

Custom control hit regions also follow cuts. A hole exposes an eligible control below it, and a complete cut removes the control from pointer, keyboard, and accessibility interaction. Overlapping controls use elevation first and submission order to break ties. Native text fields still use their separate macOS view geometry.

Use `text-box` for bounded wrapping and last-line truncation. Font indices select Helvetica Neue (0), Georgia (1), Menlo (2), or medium Helvetica Neue (3). Native editable text fields support normal macOS selection and editing; they overlay the rendered image.

### Input and state

Give interactive controls unique positive IDs that remain stable between frames. Keep application state in Coil, mutate it in the event callback, then call `paper_redraw`. Start each draw callback with `paper_begin` and rebuild the current scene.

| Event kind | Meaning | Payload |
| --- | --- | --- |
| 0 | Initialize | ID is the requested `--app` index |
| 1 | Pointer down | Control ID, logical x/y |
| 2 | Captured pointer drag | Control ID, logical x/y |
| 3 | Activate/release | Control ID, logical x/y |
| 4 | Keyboard | ID is the macOS hardware key code |
| 5 | Text changed | Native input ID |
| 6 | Tick | x is native monotonic time |

Use kind 3 for button actions and kinds 1/2 for slider updates. A release outside the pressed control cancels its activation. Accessibility presses and keyboard activations may supply zero coordinates; buttons should respond by ID.

Tab and Shift-Tab traverse native fields and custom controls in submission order. Space/Return activate a focused paper button; arrow keys adjust a focused slider. In a native field, typing and arrow keys stay with the Cocoa editor. The Edit menu provides standard selection, clipboard, and text undo/redo commands.

Within a choice group, Left/Up select the previous enabled item and Right/Down select the next, wrapping at the ends. Home/End select the first/last enabled item. Choices expose selected and disabled states as native accessibility radio buttons.

Call `paper_focus id` to focus a control after the next draw, such as the name field in a new dialog. Use `paper_modal_scope` before drawing a modal to remove underlying controls from hit testing, keyboard traversal, and accessibility and hide underlying native inputs. Hidden or removed controls lose focus. Native accessibility exposes buttons, checkbox values, and slider increment/decrement actions. See AgentHub for an example.

## Rendering architecture and limits

The application, Objective-C bindings, event loop, geometry, native text layout, mask cache, audio synthesis, and packaging tool are Coil. Metal shaders perform GPU composition, material preparation, lighting, and presentation. There is no authored C, C++, Objective-C, Swift, or JavaScript runtime bridge. The shader source is embedded by Coil; no separate shader build step is required.

CoreGraphics rasterizes reusable path and glyph masks. Metal composites these masks into pigment, height, and material textures, then computes full-resolution grain and 32-sample shadows. A conservative maximum-height hierarchy skips shadow work that cannot affect the image. Exact retained commands identify damage; native text measurements are reused by submission order. Scene construction sorts once after submission instead of repeatedly shifting growing arrays.

A native display clock schedules presentation through CAMetalLayer. Composition, lighting, and presentation share one command buffer, with three drawables limiting frames in flight. Interactive frames stay on the GPU. Snapshots explicitly synchronize and read back their pixels. A Coil SIMD worker-pool renderer remains available as a fallback (`PAPER_RENDERER=cpu`).

The default target is 60 Hz. On a compatible display, `PAPER_FPS=120 build/release/papercut` requests 120 Hz. Native tests on the M2 Max verified 60 Hz presentation with 1,296 moving sheets at 5120 × 2880; the 4K stress scene also sustained 120 Hz in the shorter run. See [measurements, reproduction commands, and limits](PERFORMANCE.md). These measurements describe the tested hardware and workloads, not a guarantee for arbitrary scenes or devices.

This is a top-down 2.5D height-field renderer. It supports stacked cutouts and depth-aware shadows, but not an orbiting camera, folded paper meshes, transparency, or multiple lights. Heights use eight bits; shadows use 32 samples with a bounded reach. Extreme low light angles can show sampling artifacts. Rendering redraws on demand, and native text fields remain above the paper image.

The runtime currently owns one window and one global scene. It does not provide virtualized lists, general scroll containers, automatic content-driven reflow, application-level undo/redo, or a visual interface editor. Native text editing does support undo/redo. Designers compose interfaces in Coil.

## Verification and project notes

`coil verify` checks formatting, lint, compilation, and 41 tests. Performance regressions cover incremental/full-frame agreement, odd image dimensions, lighting invalidation, accumulated raster damage, worker-pool completion and restart, empty masks, cached readback, fractional mask placement, and viewport clipping. The accelerated GPU shadow result is compared byte-for-byte with all 32 original samples. Tests cover cutout pixels, cuts crossing outside edges, light reversal, zero-depth shadows, ink occlusion, nested elevation scopes, layout bounds, disabled controls, focus order, choice navigation, pagination boundaries, and native decoding of the three generated audio tracks. I also checked the four examples through the native UI and reviewed their rendered screenshots.

The project index is [paper-test](pad://paper-test). It links the implementation notes and screenshots. Compiler integration issues are recorded in [coil-bugs](pad://coil-bugs): local dependency native-link propagation and void-returning function-pointer casts. The Objective-C bridge follows the existing Jim rewrite's ignored-return convention for void selectors pending that compiler fix.
