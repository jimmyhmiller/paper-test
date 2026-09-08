# Materials

Papercut supports 24 opaque material presets alongside the original paper stocks. The original 18 have matte surface patterns and fine relief. Six more add light-dependent gloss or cloth sheen. They work with existing panels, components, stacked sheets, and cuts.

Run the interactive library:

```sh
coil run examples/materials.coil
```

Select a swatch for a larger view. Rotate the texture, change its size, cycle materials, toggle the finish, or open the sun control to move the light. Escape returns to the overview. For a reproducible screenshot:

```sh
mkdir -p build/material-gallery
coil build examples/materials.coil -o build/materials
build/materials --snapshot build/material-gallery/overview.png
build/materials --app 8 --snapshot build/material-gallery/felt.png
```

`--app 1` through `--app 24` open the corresponding detail view; omit it for the overview.

## Available stocks

Every constructor takes an RGB pigment, such as `(felt 0x798a6f)`.

| ID | Constructor | Surface |
| --- | --- | --- |
| 1 | `kraft` | Short pulp fibers and irregular mottling |
| 2 | `cardstock` | Subtle, dense matte grain |
| 3 | `watercolor` | Irregular fine pits and hills |
| 4 | `laid-paper` | Parallel laid lines and sparse cross-lines |
| 5 | `washi` | Long embedded fibers in multiple directions |
| 6 | `newsprint` | Fine pulp, mottling, and sparse dark flecks |
| 7 | `corrugated` | Exposed parallel flutes |
| 8 | `felt` | Dense, wandering fibers in several directions |
| 9 | `woven-linen` | Irregular over-under threads |
| 10 | `canvas` | Dense regular weave |
| 11 | `denim` | Diagonal twill with alternating thread prominence |
| 12 | `burlap` | Coarse, uneven weave and dark interstices |
| 13 | `knitted-wool` | Repeating yarn loops and fine yarn ribbing |
| 14 | `cork` | Irregular cellular fragments with fine pores |
| 15 | `leather` | Matte pebbled surface |
| 16 | `suede` | Fine directional nap and soft mottling |
| 17 | `wood-veneer` | Curved growth lines and long fine grain |
| 18 | `rubber` | Fine matte stipple |
| 19 | `velvet` | Fine pile with broad, directional cloth sheen |
| 20 | `brushed-aluminum` | Long scratches and a directional metallic highlight |
| 21 | `satin` | Fine weave with elongated gloss and a softer cloth lobe |
| 22 | `glazed-ceramic` | Subtle surface variation beneath a compact white highlight |
| 23 | `polished-leather` | The pebbled leather surface with a glossy finish |
| 24 | `varnished-wood` | The veneer pattern with a glossy finish |

The original `stock`, `cotton`, `linen`, `recycled`, `smooth`, and color presets keep their original grain formula. In particular, `linen` remains the original paper stock; use `woven-linen` for fabric.

## Controlling a surface

```coil
(let [fabric (texture-angle (texture-scale (felt 0x798a6f) 1.5) 30.0)]
  (panel (rect 24.0 24.0 360.0 220.0) 18.0 20.0 fabric))
```

- `texture-scale material size`: pattern size in logical points relative to the stock's default; range 0.25–16, default 1. A larger value makes larger threads or pores.
- `texture-angle material degrees`: clockwise rotation.
- `texture-offset material x y`: origin offset in logical points relative to the uncut, unclipped sheet's bounds.
- `texture-relief material amount`: fine surface slope strength, range 0–2. Zero removes micro-relief while retaining color texture.
- `texture-seed material seed`: deterministic variation, range 0–1.
- `tint material pigment amount`: changes pigment while preserving all texture settings.

Patterns follow a sheet when it moves. Cuts and layout clips retain the original pattern origin instead of restarting the texture at the new bounds. Independently submitted sheets have independent origins. Use `texture-offset` if several pieces should share a common origin.

The lighting control's grain setting scales both texture brightness and micro-relief. A zero grain value removes both, while retaining the finish highlight. The sheet-depth setting controls the larger cutout relief and shadows; setting it to zero does not flatten the material's fine surface normals.

## Sheen and gloss

The six new constructors work anywhere a material does:

```coil
(panel (rect 24.0 24.0 360.0 220.0) 18.0 20.0
       (texture-angle (brushed-aluminum 0xb7bec5) 30.0))
```

To add a finish to another stock:

```coil
(surface-finish (cardstock 0xd9aaa0) 0.25 0.8 0.0 0.0 0.0)
```

The arguments after the material are:

| Control | Range | Meaning |
| --- | --- | --- |
| Roughness | 0.12–1 | Microfacet highlight width; larger is broader |
| Specular | 0–1 | Strength of the glossy reflection |
| Metallic | 0–1 | Mix from a neutral dielectric highlight to pigment-colored metallic reflection |
| Sheen | 0–1 | Strength of the broad cloth lobe |
| Anisotropy | 0–0.9 | Difference between highlight widths across and along the texture axes |

Finish roughness is independent of the original paper `Material.roughness`, which controls grain. `texture-angle` rotates both the pattern and highlight axis. `tint` and all texture modifiers preserve the finish. `without-finish` removes gloss and sheen while preserving the stock's pigment and pattern.

Printed text and rules act as matte ink: their coverage suppresses surface reflections underneath them. Cuts reveal the lower sheet's own finish. Raised opaque sheets cover the finish below, and direct highlights are attenuated by the existing cast shadows. Moving a light reuses the composited material buffers.

The reflection model uses anisotropic GGX with height-correlated Smith masking, based on [PBRT's microfacet formulation](https://www.pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory). Cloth uses Charlie's grazing distribution with the Neubelt visibility approximation described in [Filament's cloth model](https://google.github.io/filament/Filament.md.html). A bounded azimuthal modulation adds a stylized directional pile response.

These lobes are adapted to Papercut's existing lighting: a fixed top-down view, one white direct light, a stylized diffuse baseline, and pigment values in the existing display color space. Reflection strength includes a fixed light-intensity scale. Reflected radiance is compressed into the display range while preserving the unlit matte baseline, preventing broad highlights from clipping to featureless white. This is not a full linear-light, environment-lit PBR renderer.

## Rendering and maintenance

`Material` carries explicit `Pattern` and `Finish` descriptors. Sheet submission, retained-command comparison, and GPU draw uniforms preserve its type, scale, angle, relief, origin, and finish controls. Material changes invalidate the affected sheet. No material IDs are encoded into pigment or seed channels.

Pure scalar `tex-*` functions in `src/texture.coil` define the patterns; `fin-*` functions in `src/finish_light.coil` define the reflection lobes. A restricted development-time translator generates their Metal equivalents into `shaders/paper.metal`:

```sh
python3 tools/generate-material-shader.py
python3 tools/generate-material-shader.py --check
```

There is no Python dependency at runtime or during normal Coil builds. Unsupported kernel forms cause the generator to fail. `texture/sample` and Metal's `material_micro` apply the same coordinate transform and finite-difference sampling; renderer comparison tests cover the resulting surfaces.

Metal evaluates surface detail while compositing each sheet, blends numeric surface values using the existing coverage mask, and stores signed fine normals and brightness variation in a separate RGBA16Float attachment. Two more RGBA16Float attachments store finish shape and reflection weights. Together, the three detail/finish attachments add 24 bytes per backing pixel to the original GPU buffers. The highlight axis is encoded as anisotropy times `(cos(2 angle), sin(2 angle))`, so coverage blending has no angle-wrap discontinuity. Lighting reads the cached detail, so moving a light does not regenerate the patterns. The existing eight-bit sheet heights and shadow hierarchy remain independent.

The CPU fallback rasterizes coverage into a separate grayscale mask and composites the same samples into float arrays for detail and finish parameters. It processes ink in the same elevation and submission order as pigment compositing. Workers own disjoint complete rows. Its scalar and SIMD lighting both use the fine normals and reflection lobes, with one final color quantization. Unchanged frames retain the prepared detail; moving lights only rerun shading.

Patterns use logical coordinates and attenuate subpixel detail. Very small patterns can still lose definition; this is not an image texture system with mipmaps.

## Scope

These are opaque surfaces viewed from above. Cut boundaries remain clean geometric edges. The renderer does not simulate loose felt fibers beyond an edge, cloth deformation, translucency, open weave holes, cardboard cross-sections, environment reflections, or an orbiting camera. The finishes approximate gloss and sheen under the existing single light; they are not measured material models. `leather` and `rubber` remain explicitly matte, while the new glossy variants are opt-in.

## Validation

```sh
coil test tests/material_test.coil
coil test tests/finish_test.coil
PAPER_RENDERER=cpu coil test tests/material_test.coil
coil verify
coil run tools/material_performance.coil
```

The material tests cover finish-only invalidation, reflection direction, grazing-angle stability, highlight compression, ink and shadow suppression, seeded variation, finite samples, preservation through tinting, anchoring after movement and cuts, material-only invalidation, incremental/full redraw agreement, and CPU/Metal interior pixel agreement. Existing geometry, rendering, and performance regressions remain applicable. The benchmark measures the 24-material, 2560 × 1840 gallery under moving light, rotating materials, and unchanged redraws; it excludes startup, window presentation, and PNG encoding.

Project notes and rendered previews: [Material library](pad://paper-test-materials), linked from [paper-test](pad://paper-test).
