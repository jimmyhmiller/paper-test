# Paper Terminal

A standalone macOS terminal in Coil. Layered paper tabs surround a Ghostty terminal on warm parchment. The default **Carved** material gives text a dark recessed face, an upper interior shadow, and a thin illuminated lower cut edge. The amber cursor has paper thickness, a soft shadow, and a corner folded back over the face. Ghostty handles text shaping, ANSI colors, Unicode, selection, scrollback, and application cursor modes.

## Build and run

Requires macOS 14+, Apple command-line tools, Coil, Python 3.12+ (safe tar extraction), and Zig **0.16.0**. The first dependency build downloads the pinned Ghostty source and its dependencies.

```sh
cd apps/paper-terminal
python3 scripts/prepare-ghostty.py
python3 scripts/build.py
open 'build/Paper Terminal.app'
```

The app bundles its icon, theme, shader, terminfo, and shell integration. It runs independently of the repository once built. Ghostty is statically linked; no Jim service or Sieve is required. To run directly during development, use `coil run` from this directory.

## Tune the paper effect

The small sun in the bottom-right corner opens Paper's shared lighting popover, with a draggable light, height and relief sliders, and reset. The app reserves space beside the terminal while it is open, retains terminal focus, and sends light changes to both Paper and the terminal shader. The existing Material Lab remains available.

Open **Materials** in the app header for the floating Material Lab. Use the **Material** tab for lettering and cursor controls, or **Light** to move the source. Drag a control to change the running terminals; the app coalesces changes at 120 ms and applies the final value on release. You can see the current values above the tracks. In short windows the panel uses a compact layout, with its preset buttons inside the sheet.

| Control | Effect |
| --- | --- |
| Paper tone | Move the face from ink toward dyed stock, with a contrast limit for legibility. |
| Carved ↔ raised | Negative values carve a cavity; positive values lift the lettering and cast a short shadow. The center gives flat ink. |
| Cut edge | Change the width of the lit rim and inner bevel. |
| Fibre | Change the irregular fibre texture within the letter faces. |
| Cursor lift | Change the cursor's separation from the sheet and the softness of its shadow. |
| Folded corner | Fold back more of the cursor's upper-right corner. |

**Carved** restores the default material, based on the supplied calculator and carved account-form references. **Raised** gives a shallow embossed treatment; **Ink** removes the relief. Use ⌘+ to examine the cut edges at a larger text size. The default is 16 pt Menlo with macOS font smoothing. Fine strokes have less room for an interior shadow than large or bold letters.

In **Light**, drag the golden point across the two-dimensional well. The inner rectangle represents the window; the surrounding area lets you place the source beyond its edges. The coordinate readout uses window points, with the origin at the upper left. **Height** moves the light from 200 to 1600 points above the sheet: lower light extends shadows and strengthens grazing relief. **Reset light** returns to the authored upper-left source.

The Paper sheets, carved and raised text, and folded cursor use the same point-light position and height. The shader converts each terminal pixel back to Paper's coordinates and normalizes the light direction there. Moving the light reverses the glyph rim and interior shadow, redirects the cursor's cast shadow, and lights its cut edge and fold from the new direction. Material presets leave your light position unchanged.

The panel reserves space beside the native Metal terminal view. Its non-text controls keep the terminal as first responder, so you can watch the paper cursor while adjusting the light. Material changes preserve running shells, scrollback, and font zoom. The app reloads the existing Ghostty surfaces from a private temporary directory, which it removes on shutdown. It verifies shader declarations after replacement, so changing a default's decimal formatting cannot disable a control. `config/cursor.glsl` contains the shader defaults.

## Use

| Action | Shortcut / gesture |
| --- | --- |
| New terminal tab | ⌘T or **New tab** |
| Close tab | ⌘W or the tab’s × |
| Previous / next tab | ⌘⇧[ / ⌘⇧] or header arrows |
| Copy / paste / select all | ⌘C / ⌘V / ⌘A |
| Font size | Ghostty’s ⌘+ / ⌘− / ⌘0 |
| Full screen | ⌃⌘F |
| Quit | ⌘Q |
| Move window | Drag the blank top material/header |

Each tab owns an independent PTY and login shell. New tabs inherit the active shell’s reported directory. Long tab lists page automatically to keep the selected tab visible. Window resizing recalculates the layout and real terminal grid. Running work receives a close confirmation; closing a session ends its processes. Shell exit closes its tab, and closing the last tab exits the app. Sessions are not restored after quitting.

The native menus expose terminal editing and window actions. The window uses unified material with standard traffic lights. Buttons and tab close controls respond to hover and press. The terminal is a native `NSTextInputClient` for composition and candidate positioning, with mouse reporting, selection, scrolling, and accessibility text.

## Implementation

- `src/main.coil`: application lifecycle, tab ownership, menus, and responsive layout using `paper.flow` / the reusable Coil layout library.
- `src/terminal.coil`: native AppKit input bridge and Ghostty runtime callbacks. Struct-valued callbacks use Coil’s explicit C ABI exports.
- `src/ghostty.coil`: audited subset of the pinned public C header.
- `config/ghostty`: palette, transparent default cell background, readable Menlo typography, shell integration, and clipboard policy.
- `config/cursor.glsl`: carved and raised material passes, with antialiased cut contours and a folded paper block cursor. The shader reads and writes premultiplied alpha. It converts Ghostty's bottom-edge cursor coordinate to the top of the paper shape and uses that shape for the face, thickness, and shadow. Hidden, unfocused, bar, and underline cursor modes keep their native geometry. The shader has no continuous animation loop.
- `src/snapshot.coil`: test-only export of Paper’s completed buffer composed with Ghostty’s actual IOSurface pixels.

Paper renders the surrounding sheets; Ghostty owns the terminal surface, PTY, text shaping, and grid. The post-process pass shades Ghostty's completed glyph coverage and retains its antialiasing. Opaque selection and ANSI-background interiors retain the native rasterization, since a completed opaque frame does not expose a separate glyph mask. Material thickness follows the window's backing scale, independent of cursor style. Drawing, native view placement, and input share the same layout bounds. Hidden tabs retain their shells and use Ghostty's occlusion flag.

## Verify

```sh
python3 scripts/test.py
GHOSTTY_LOG=stderr coil run tests/gallery.coil
```

The test script checks C and Coil ABI layouts, tab model behavior, real shell output, Unicode, OSC title updates, independent tabs, focus, terminal resize, alternate screen, Ctrl-C, native IME selectors, default login shell, directory inheritance, exit lifecycle, and child-process reaping. A material test compares Ghostty's published IOSurface pixels before and after a preset change, checks premultiplied-alpha bounds, and verifies that the terminal text survives the reload. Light tests dispatch a native mouse event through the inspector, check that the terminal retains first responder, and verify changed IOSurface pixels before mouse-up. They also check the height control and generated world-coordinate constants. The script runs an integration bundle from `/tmp` to check resources and shell integration, rejects shader compilation errors, and verifies the production app's signature.

The gallery exports normal and compact windows, both Material Lab tabs, opposite and lower light positions, and carved/raised studies at 26 pt into `build/paper-terminal*.png`. It waits for shader reloads before taking each image. These previews use Ghostty's rendered pixels and omit macOS window chrome. Automated checks invoke the app's gesture handler; physical trackpad gestures, interactive IME candidate selection, and clipboard gestures still need a manual pass.

Ghostty preserves a shell that exits within 250 ms as a possible startup failure on macOS, displaying its diagnostic. This upstream behavior is retained. There are no splits, session persistence, or multiple windows in this first standalone app.

See [PROVENANCE.md](PROVENANCE.md) for the native bridge’s Jim reference and the exact Ghostty source. Project notes and render previews are in the **paper-terminal** pad, indexed from **paper-test**.
