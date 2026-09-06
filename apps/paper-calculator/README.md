# Paper Calculator

A standalone native macOS calculator written in Coil using Paper. Cream cotton keys, coral operators, a sage display, and actual CoreText outline cuts share the renderer's paper texture and lighting.

```sh
cd apps/paper-calculator
python3 scripts/build.py
open 'build/Paper Calculator.app'
```

Requires macOS 14+, Coil, Python 3, and Apple command-line tools. The signed app bundle includes its icon and has no external runtime resources.

The inset `123 / ƒx` selector switches between basic and scientific layouts without clearing the calculation. Scientific mode includes sine, cosine, tangent, natural and base-10 logarithms, powers, square root, square, reciprocal, and π. Click DEG/RAD in the display to change angle units.

Use the number keys, decimal point, `+ - * /`, and Return or `=`. Escape or C clears, Backspace deletes an entry digit, `%` computes a percentage, and S switches modes. Tab navigates controls; Return or Space activates a keyboard-focused control. Click ± to change sign. Operators execute immediately from left to right, like a pocket calculator. Repeated equals repeats the last operation. For addition/subtraction, percentages are relative to the left operand; for multiplication/division they divide the entry by 100.

Calculations use double precision, with 15 entry characters and 12 significant display digits. Functions act on the current number; entering a digit after a function starts a new operand. Undefined or overflowing results show Error; AC or a new digit recovers.

The sun indicator inside the display, beside DEG/RAD in scientific mode, opens the shared `paper.lighting` popover. It has no hover or pressed styling. Drag the panel header to reposition it, or drag the golden point to move the light; adjust height and paper relief. Reset restores this app's lighting defaults. Click outside, ×, or Escape to dismiss. Settings and panel position last for the current session.

A short underline marks the pending arithmetic operator while you enter its right operand. It clears when you evaluate or clear the calculation.

## Verification

```sh
coil verify
coil run tests/gallery.coil
```

Tests exercise decimal entry, chaining, operator replacement, repeat equals, percentages, sign, input limits, overflow, domain recovery, scientific functions, native NSEvent characters, rendered hit targets, and the lighting popover. The gallery renders basic, scientific, and lighting previews to `build/`. Automated interaction checks call native event and Paper accessibility handlers; a physical keyboard/trackpad pass is not automated.

The `main.coil` entry is separate from reusable `ui.coil` and `model.coil`, so tests never import an application entry point. Project notes and previews: [paper-calculator](pad://paper-calculator).
