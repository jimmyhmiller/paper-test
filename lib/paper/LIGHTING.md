# Reusable lighting popover

Import `paper.lighting` alongside `paper.flow`. Each app owns a `Lighting` instance, initialized with `lighting x y height depth grain`. X and Y are fractions of the viewport; negative coordinates place the light outside the window. Height is in paper points, depth controls relief, and grain controls the material texture.

Call `apply-light state viewport` after `paper_begin`, then draw the app. Call `popover state base-id anchor` last; the anchor rectangle is the sun's hit area. Reserve eight consecutive control IDs starting at base-id. For a custom launcher, draw the icon and register base-id yourself, then call `popover-panel` last. Calculator uses this to print a fixed sun indicator inside its display, without hover feedback. The popover fits viewports down to Paper's minimum 320 × 240 logical points.

Drag the panel header to move it. The panel remembers its position across close/reopen and stays inside the viewport. An optional `drag-limits` rectangle restricts movement; Terminal uses its reserved strip to keep the panel clear of the native terminal view. Reset changes lighting values, preserving panel placement.

Route events through `handle state base-id kind id x y` before application controls. A true return means consumed. It supports drag updates, native slider accessibility/keyboard adjustments, reset, outside-click dismissal, and Escape. Ticks continue while the panel is open. The panel establishes a modal Paper input scope so covered controls cannot activate. Its light position map marks the viewport with an inner rectangle and permits positions from −1 to +2 viewport sizes.

`examples/minimal.coil` is the complete small integration. Paper Calculator, all four Studio apps, and Paper Terminal use the same component. Each keeps its own initial lighting and reset values. Studio synchronizes it with the existing workbench controls. Terminal reserves a strip beside its native Metal surface and forwards changes to the terminal shader; its material controls remain available.

Draw the popover at the root elevation, after other sheets. Apps embedding native views must reserve space beside them: native views render above Paper and do not participate in its modal hit scope. `Lighting.bounds` contains the current panel rectangle, and the caller chooses its anchor. Lighting values and open state are app-owned; persistence is optional and no preferences are written by this component.
