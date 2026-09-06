# Coil layout

A renderer-independent layout package. It resolves rows, columns, overlays, measured content, and scrolling into ordinary `Rect` values. It owns no window, font, paint commands, control IDs, allocator, or application state. The Paper adapter uses those rectangles for sheets, paths, text, native inputs, and hit regions.

Add `layout = { path = "path/to/lib/layout" }` to your Coil dependencies. Import `layout.core` and `layout.syntax`. The package itself requires no native frameworks.

```coil
(import "layout.core" :use *)
(import "layout.syntax" :use [arrange])

(arrange viewport
  [page (padded (column (grow 1.0) (grow 1.0) 20.0) (padding 24.0))
    [header (box (grow 1.0) (fixed 44.0))]
    [body (row (grow 1.0) (grow 1.0) 20.0)
      [navigation (box (fixed 220.0) (grow 1.0))]
      [content (box (grow 1.0) (grow 1.0))]]]
  (draw-header header)
  (draw-navigation navigation)
  (draw-content content))
```

Each name becomes a rectangle in the body. Drawing functions are supplied by your application. Styles are ordinary expressions, so state can choose a dimension, spacing, or topology branch without a second configuration language. The macro creates exactly enough stack storage for its tree, builds it, solves it, and executes its body once. Nested drawing functions can arrange their own rectangle. Runtime-length lists use the lower-level API below.

## Dimensions and placement

| Operation | Meaning |
| --- | --- |
| `fit` | Natural content size, including children, padding, and gaps |
| `fixed points` | Requested point size, not compressed to make siblings fit |
| `grow weight` | Share remaining main-axis space above minimums by positive weight; fill the cross axis |
| `percent fraction` | Fraction from 0 to 1 of the parent's inner size, before gaps |
| `bounded size minimum maximum` | Hard lower and upper constraints on any sizing mode |
| `row width height gap` | Left-to-right flow |
| `column width height gap` | Top-to-bottom flow |
| `box width height` | Column with zero gap, convenient for leaves |
| `stack width height` | Children share one content rectangle |
| `padded style edges` | Add insets; use `padding amount` or `edges left top right bottom` |
| `aligned style cross main` | Alignment fractions: 0 start, 0.5 center, 1 end |
| `spaced style` | Distribute spare main-axis space between children, retaining the minimum gap |
| `aspect style ratio` | Derive fit height as resolved width / ratio |
| `floating style x y dx dy` | Anchor child to parent's content rectangle, with fractional anchors and point offsets |
| `scrolled style x y` | Clip descendants and offset their positions |

Grow children reaching a maximum release their unused allocation to siblings. Under pressure, fit and grow children shrink proportionally to their starting size down to their minimums. Fixed and percentage sizes remain fixed. If minimums, fixed dimensions, or gaps exceed the available size, content overflows explicitly; it does not acquire negative dimensions. Choose clipping or adjust your responsive composition at that point.

The root always receives the supplied viewport, regardless of its sizing modes. A fit parent measures percentage children at their minimum contribution, avoiding a circular dependency on its own size. Floating children neither contribute to natural size nor consume flow space. To attach an overlay to another node, add it as a floating child of that node. Alignment applies to normal children as a group; stack uses cross for x and main for y. Aspect sizing is width-first and only changes a fit height.

There is no implicit wrapping of a row into additional rows. Compose rows, calculate a column count, or construct another tree for the available width. Fit dimensions on a cross axis preserve their natural size; use grow or a bounded size when content should wrap to the container.

## Text and custom measurement

The kernel accepts a C-calling-convention callback:

```coil
(defn measure [(data (ptr i8)) (offered-width f64)] (-> Extent)
  ;; Return content dimensions, excluding the node's padding.
  ...)
```

A solve asks for natural size at `unlimited`, resolves widths, then asks again at the available content width. Wrapped height propagates through fit parents before vertical placement. Keep callback data alive through every solve that uses it. Return finite, nonnegative dimensions. Measurement can be cached by the adapter; the kernel retains no text or external resources.

A measured leaf in the macro is `[name style :measure callback data]`. The imperative equivalent is `measured ctx parent style callback data`. `measure-data [T] pointer` erases a borrowed typed pointer for a callback. Put padding on the measured node or its container, and draw inside the corresponding inset rectangle.

Paper provides `TextMeasure`, `text-measure`, `text-data`, `measure-text`, and `text-width` through `paper.flow` / `paper.text-layout`. It measures with the same native fonts and NSString wrapping options used to draw. Its bounded cache owns copied string keys and distinguishes content, font, size, and offered width. `clear-text-cache` releases those copies. It follows Paper's single UI thread ownership.

See [the minimal application](../../examples/minimal.coil) for actual native text measurement in an `arrange` tree.

## Dynamic trees and storage

```coil
(let [(mut storage) (zeroed (array Node 128))
      (mut ctx) (layout (index storage 0) 128)
      root (add ctx -1 (column (grow 1.0) (grow 1.0) 8.0))]
  (for [i 0 item-count]
    (add ctx root (box (grow 1.0) (fixed 40.0))))
  (solve ctx viewport)
  (for [i 0 item-count]
    (draw-item i (bounds ctx (+ i 1)))))
```

The caller supplies initialized contiguous storage, from a stack array or an allocator. Capacity includes the root. Out-of-capacity insertion asserts before writing. The first node must be the single root with parent -1; all other parents must already exist. Insertion can interleave subtrees and need not be depth-first. Handles are dense indices, valid until `reset`; application identity remains separate.

Reuse storage by calling `reset`, or solve an existing tree again with another viewport. Changes to styles require another solve before using geometry. `node` exposes storage for deliberate style changes; tree links and scratch fields belong to the solver. Do not resize or release storage while its context is in use. Large dynamic trees should use caller-owned heap or arena storage rather than large stack arrays.

## Scrolling and clipping

`bounds` returns full positioned geometry. `visible-bounds` intersects it with all ancestor clips and the root viewport. `hit?` tests that visible rectangle. Scrolling preserves offscreen geometry so artwork, text wrapping, and hit transforms remain consistent.

After solving, `scroll-range ctx id` returns maximum nonnegative x/y offsets. `scroll-to ctx id x y` clamps offsets and updates positions and clips without remeasuring. Save the returned offsets in application state if rebuilding the tree next frame. `scrolled` accepts raw offsets deliberately, for caller-controlled overscroll. Extents include normal children and gaps, exclude floating children, and do not include descendants overflowing their own direct-child bounds.

The layout package supplies scroll geometry, not input policies, inertia, scrollbars, or virtualization. An adapter decides how wheel or touch events change offsets. Paper's `with-clip` intersects nested clip scopes across sheets, cuts, ink, hit paths, focus participation, accessibility frames, and native field containers. Use full layout bounds for drawing and the ancestor clip for the render scope; do not replace a text box's full rectangle with its clipped rectangle, which would rewrap text while scrolling.

## Design and cost

The design was informed by [Clay](https://github.com/nicbarker/clay/tree/e6cc36941ab2af5d81107617039d6f527a1c660b): bounded contiguous storage, ordered measurement passes, and a strict separation from rendering. This implementation is original Coil code and has no Clay runtime dependency. Returning named rectangles fits Paper's custom cutouts and elevation-based rendering without imposing a second render-command tree.

The solver uses iterative bottom-up and top-down passes; deeply nested trees do not consume a recursive call stack. Normal sizing is O(n). Bounded sibling distribution uses up to four linear freeze passes, then an allocation-free heapsort and breakpoint sweep for an O(n log n) worst case. Each node currently occupies 376 bytes on the tested arm64 compiler, including layout and scratch storage. Build and solve allocate nothing internally. External measurement costs are additional.

See [LAYOUT.md](../../LAYOUT.md) for integration, benchmark reproduction, and validation evidence. This is a layout engine with the capabilities listed above, not a CSS engine or a claim of complete Clay API compatibility.
