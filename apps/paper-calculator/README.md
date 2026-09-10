# Paper Calculator

A standalone native macOS calculator written in Coil using Paper. Cream textured keys, coral operators, a sage display, and actual CoreText outline cuts share the renderer's paper texture and lighting.

The casing and keys have curved paper shoulders and a lightly reflective,
irregular pressed-paper stock. Large key labels cut eight points into a separate
suede floor; smaller labels use shallower, narrower bevels for legibility.
The edge highlights follow the movable light. The shared Paper library exposes
the same configurable bevels for other applications; see
[sculpted edges](../../lib/paper/MATERIALS.md#sculpted-edges-and-lettering).

The casing is at elevation 44, tray at 24, display at 6, and resting keys at 38.
The display numerals cut down to elevation 1. This gives the large wells depth
while keeping key shadows shorter. Exposed rims use a paler fiber stock with
their own finish. The extra basic and scientific controls retain their layouts.

```sh
cd apps/paper-calculator
python3 scripts/build.py
open 'build/Paper Calculator.app'
```

Requires macOS 14+, Coil, Python 3, and Apple command-line tools. The signed app bundle includes its icon and has no external runtime resources.

The app starts with a calculator-shaped window: transparent outside the casing, tighter rounded corners, and no native traffic lights. Drag the top rim to move it. Hold AC continuously for five seconds to turn it off; a normal click still clears the calculation. Releasing, moving off AC, or switching away cancels shutdown. Keyboard and accessibility clicks clear normally and do not arm shutdown.

Choose **View → Calculator-shaped Window** or press **⇧⌘B** to switch between the shaped treatment and the standard window with traffic lights. The calculation is preserved. To start in the standard style:

```sh
open -n 'build/Paper Calculator.app' --args --window standard
```

The style choice lasts for the current run; `--window shaped` selects the default explicitly. The native mask and snapshot export use the casing's same rounded contour. The GPU rendering path stays on the GPU. The lighting panel stays inside the visible casing when dragged.

The inset `123 / ƒx` selector switches between basic and scientific layouts without clearing the calculation. Scientific mode includes sine, cosine, tangent, natural and base-10 logarithms, powers, square root, square, reciprocal, and π. Click DEG/RAD in the display to change angle units.

The selector thumb eases between modes over 220 ms while the keys change immediately.
Drag any visible casing edge or rounded corner to resize the shaped window proportionally.

Each key is one bevel-aware GPU primitive, with an analytic rounded shoulder and
a signed-distance field for its native lettering outline. It writes color, height,
texture and finish together; lighting and shadows still use actual surface depth.
CPU rendering, arbitrary cuts and interleaved elevations expand the primitive into
vector sheets. Coverage/distance fields are prepared in parallel in an owning
256 MiB cache. A separate 128 MiB GPU cache retains full-resolution material
microstructure, sharing exact pixel-grid translations and falling back to procedural
evaluation when its working set is full. Relighting never regenerates that texture.

There is no alternate-layout startup prewarming. `coil run tests/fidelity.coil`
reports cold switches, CPU stages, completed GPU work, light drags and button
press/release timing at 2× backing resolution. `PAPER_MICRO_REFERENCE=1` disables
material caching, and `PAPER_VISIBILITY_REFERENCE=1` disables opaque-depth culling
in that benchmark. Timings exclude native window presentation/vsync.

Use the number keys, decimal point, `+ - * /`, and Return or `=`. Escape or C clears, Backspace deletes an entry digit, `%` computes a percentage, and S switches modes. Tab navigates controls; Return or Space activates a keyboard-focused control. Click ± to change sign. Operators execute immediately from left to right, like a pocket calculator. Repeated equals repeats the last operation. For addition/subtraction, percentages are relative to the left operand; for multiplication/division they divide the entry by 100.

Calculations use double precision, with 15 entry characters and 12 significant display digits. Functions act on the current number; entering a digit after a function starts a new operand. Undefined or overflowing results show Error; AC or a new digit recovers.

The sun indicator inside the display, beside DEG/RAD in scientific mode, opens the shared `paper.lighting` popover. It has no hover or pressed styling. Drag the panel header to reposition it, or drag the golden point to move the light; adjust height and paper relief. Reset restores this app's lighting defaults. Click outside, ×, or Escape to dismiss. Settings and panel position last for the current session.

A short underline marks the pending arithmetic operator while you enter its right operand. It clears when you evaluate or clear the calculation.

## Verification

```sh
coil verify
coil run tests/gallery.coil
coil run tests/fidelity.coil
```

Tests exercise decimal entry, chaining, operator replacement, repeat equals, percentages, sign, input limits, overflow, domain recovery, scientific functions, native NSEvent characters, rendered hit targets, and the lighting popover. The gallery renders basic, scientific, and lighting previews to `build/`. Automated interaction checks call native event and Paper accessibility handlers; a physical keyboard/trackpad pass is not automated.

The `main.coil` entry is separate from reusable `ui.coil` and `model.coil`, so tests never import an application entry point. Project notes and previews: [paper-calculator](pad://paper-calculator).
