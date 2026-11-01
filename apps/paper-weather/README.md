# Paper Weather

A native Coil weather app using the existing Paper renderer. Location search and
weather data come from [Open-Meteo](https://open-meteo.com/en/docs) and its
[geocoding API](https://open-meteo.com/en/docs/geocoding-api).

Type a city or postal code in Search locations. Results include region and country;
click a result, or use Up/Down and Return. Searches debounce for 300 ms. Old requests
are canceled and generation checks prevent late replies from replacing newer data.
All networking uses native NSURLSession asynchronously, with responses delivered
on the main operation queue. There is no shell subprocess or blocking network call
in the UI path.

Current temperature, feels-like, weather conditions, humidity and wind; hourly
conditions, temperature, rain probability and wind; and the seven-day outlook,
sunrise/sunset, daily rain chance and maximum UV all use the selected coordinates.
Times are formatted in the selected place's timezone. Units default to Fahrenheit
and mph. The visible °F/°C switch changes all temperatures (including feels-like,
highs/lows and hourly labels) and wind units, saves the preference, and preserves it
when searching another country. Provider values stay canonical Celsius/km/h.
Missing values appear as an em dash. Current conditions are weather-model estimates,
not a claim of an on-site observation.

The app keeps the previous successful forecast visible while another location loads,
with a loading status, and commits the new place and forecast together. Failures show
an error with Refresh available. Refresh also reloads the current place, and successful
forecasts refresh automatically after ten minutes. The last successfully selected
location is saved in the app's native preferences. First launch starts with Aspen.

All scenery, weather symbols, panels and chart geometry use native paper paths and
sheets. Main place and current-condition lettering use raised glyph contours. No
reference-image pixels are loaded. The original alpine composition is the single
art study again; it does not claim to depict every searched location. The generated
world system and Scene studio have been removed. Future work starts with concrete,
beautiful authored scenes, then abstracts construction rules from proven examples.
Resize behavior is also provisional and explicitly needs a separate design pass; the
current layout is not accepted as the final resizing design.

Settings and Adjust lighting open the shared movable lighting popover. Light height,
Relief, Paper height, position, and Reset work on the native renderer. Paper height
uniformly scales the full rendered stack.

Build and open from the repository root:

```sh
python3 apps/paper-weather/scripts/build.py
open "build/Paper Weather.app"
```

From `apps/paper-weather`, run deterministic tests and optional live network checks:

```sh
coil test
coil run tools/live_data_check.coil
```

The live check requests Berlin and Tokyo, checks real forecast fields, exercises a
superseded request, and verifies an empty location result. It can also render the live
Tokyo response without changing saved app preferences:

```sh
coil run tools/live_data_check.coil -- /absolute/path/to/live-weather.png
```

`src/units.coil` converts user-facing units without modifying provider data.
`src/service.coil` owns networking, data validation, formatting and location state;
`src/app.coil` composes controls and weather data; `src/craft.coil` authors paper shapes.
The native entry point is `src/main.coil`. Radar imagery and weather alerts are not
connected and their panes state this explicitly.

Project notes: [paper-test-weather](pad://paper-test-weather), indexed by
[paper-test](pad://paper-test).

The scene studio and generic world generator were scrapped after visual review.
Design notes and the decision to work from concrete scenes are recorded in
[paper-test-weather-design](pad://paper-test-weather-design).

`src/solar.coil` retains an unused solar-position calculation for possible future
scene work, adapted from SunCalc v1.9.0 under its BSD 2-Clause license. Keeping this
math does not enable an automatic day/night scene system.

## Data-driven paper scene proof

A separate native executable proves the proposed AI-to-paper boundary. It leaves
the weather app's original scene intact and does not bring back Scene studio.

```sh
python3 apps/paper-weather/scripts/build_scene_proof.py
build/paper-scene --scene "$PWD/apps/paper-weather/scenes/new-york.json"
```

Other supplied scene documents: `indianapolis.json` and `maroon-bells.json` in that
same directory. They are simplified native studies, not exact reproductions of the
generated images or geographically verified panoramas. No image generation or
bitmap scene artwork is used by the player.

An AI can supply or edit an ordinary scene JSON file. The player checks it every
0.5 seconds and replaces the compiled scene only after validation succeeds. The
animation clock, pause state and craft lighting survive replacement. All geometry
is cached native CoreGraphics paths submitted as real Paper sheets. Geometry is
not baked into renderer code, and changing a document needs no rebuild/restart.
The three examples were supplied during development; an autonomous model service
for arbitrary place names is **not connected**.

The machine-readable contract is `scenes/schema.json`. Documents contain:

- `version`, `title`, `viewBox: [width,height]` in design points;
- named materials with RGB integer `day`, `night`, optional `winter` stocks;
- independent normalized `night`, `winter`, `snow` (settled cover), `snowfall`,
  `rain` and `wind` channels;
- named hierarchical groups, closed `M`/`L`/cubic `C`/`Z` paths, even-odd apertures,
  absolute sheet heights, transforms and optional bounded drift/sway;
- optional bounded rain/snow emitters and visibility masks for authored surface
  pieces. Snow masks and folds are supplied geometry, not invented by the player.

`transform` is `[translateX,translateY,rotationDegrees,pivotX,pivotY]`. Children
inherit their parent's transform and visibility. Motion is analytic in elapsed
seconds, not frame count. OS Reduce Motion, pause and hidden windows stop the
animation clock. The shared paper/light popup includes paper height.

No scripts, URLs, image references or native calls are accepted. Runtime validation
also enforces unique IDs, closed subpaths, hierarchy depth, file size and total
node/command/particle budgets. Invalid/incomplete writes retain the last good scene
and show an error. The JSON Schema describes structure; native validation remains
authoritative for cross-node constraints.

Small AI edits can use the patch publisher. Work on a copy to preserve the examples:

```sh
cp apps/paper-weather/scenes/new-york.json /tmp/my-paper-scene.json
build/paper-scene --scene /tmp/my-paper-scene.json
# In another terminal, while the window is running:
python3 apps/paper-weather/scripts/scene_patch.py /tmp/my-paper-scene.json \
  apps/paper-weather/scenes/patches/new-york-snow.json
python3 apps/paper-weather/scripts/scene_patch.py /tmp/my-paper-scene.json \
  apps/paper-weather/scenes/patches/add-cloud.json
python3 apps/paper-weather/scripts/scene_patch.py /tmp/my-paper-scene.json \
  apps/paper-weather/scenes/patches/clear-after-snow.json
```

Patch operations: `conditions`, `material`, `set` a named piece's geometry/style/
transform/motion, `append` a component into a group or root, and `remove` a named
component. Native validation runs before atomic publication. A stable sidecar lock
serializes publishers; changes made by other editors during validation are checked.
Rejected patches leave the file unchanged.

Validation: `coil test` includes scene acceptance/rollback, named edits and inherited
transforms, stable cached paths, time-based motion, independent snow states, and
invalid/duplicate/budget checks. `tools/scene_live_check.coil` additionally exercises
the actual file watcher with successful and rejected replacements, pause/occlusion,
and adding a new component during an offscreen native animation replay.

This proves a live editable scene-data path. It does not prove autonomous geographic
accuracy, aesthetic parity with imagegen, automatic snow-mask generation, continuous
seasonal topology transitions, or a complete weather-to-art system. Those still
need work on concrete scenes and review. The limited motion vocabulary can expand
from successful authored examples.

## First algorithmic-art definition: folded conifer

`art/trees/folded-conifer.json` defines one specific tree family. Its construction
algorithm is `tools/tree_art.py`; the definition exposes these independent concerns:

- **Form:** equations relating age, vigour, exposure and gesture to height, crown
  ratio, trunk taper, branching-tier count, crown clearance and asymmetry.
- **Variation:** bounded trait distributions, deterministic named random streams,
  and small local variations subordinate to the tree's overall gesture.
- **Constraints:** admissible proportions, taper and tier overlap.
- **Aesthetic preferences:** named measurable losses, targets, tolerances and
  weights. These are artist-authored preferences, not a universal beauty rating.
- **Placement:** Gaussian density fields, ground bounds, perspective scaling,
  root spacing, a protected opening, and weighted preferences for crowding,
  envelope near-tangencies and neighboring repetition.
- **Paper construction:** two curved faces per branch tier sharing an exact seam,
  a tapered trunk, a coordinated stock palette and bounded paper-depth bands.

Generate six diverse individuals and an 18-tree grove from the same definition:

```sh
python3 apps/paper-weather/tools/tree_art.py
build/paper-scene --scene "$PWD/output/tree-art/tree-variations.json"
build/paper-scene --scene "$PWD/output/tree-art/tree-grove.json"
```

Edit the definition and rerun the generator; existing viewers reload the complete
new document atomically. `--definition /path/to/family.json --output /path/to/study`
lets experiments use separate definitions and output directories.

`output/tree-art/tree-report.json` records the exact definition hash, individual
seeds/traits/dimensions, constraint violations, preference losses, placement
rejections and selected placement costs. Trait samples use independent named
streams, so material edits or sampling-order changes do not scramble the tree.
Individual selection balances aesthetic preference with trait diversity. Grove
placement uses density-weighted proposals, hard rejection, and weighted local
selection; it is not a globally optimal layout solver. Near-tangency checks use
conservative crown envelopes rather than exact rendered silhouettes.

The first visual iteration exposed weak tier continuity and insufficient depth
variation. A later render exposed interleaved branches from different trees;
whole-tree paper-depth bands now enforce correct foreground occlusion. These
findings inform the rules instead of being hidden by manually moving instances.

This is a **static tree-family and placement study**, awaiting visual judgment.
Seasonal morphology and motion are not part of this first family yet. The weather
app is unchanged. Test the procedural semantics separately from Coil:

```sh
python3 -m unittest discover -s apps/paper-weather/tests -p 'tree_art_test.py' -v
```

## Cloud-only atlas

The user accepted the first tree-family direction but rejected the combined scene
compositions. Current work focuses on clouds independently of those landscapes.

The cloud library is WMO-informed algorithmic paper art:

- **Ten genera**, with separate fibrous, cloudlet-field, veil/deck, roll/lens and
  convective construction rules.
- **All fifteen named species**, represented in their 29 common genus/species
  associations, plus the two genera without species (31 base studies).
- **Nine varieties**, **eleven supplementary features** and **four accessory
  forms**, each with a labeled example.
- Special-origin cases: flammagenitus, homogenitus (including aircraft contrails),
  homomutatus, cataractagenitus and silvagenitus.
- Nacreous clouds, nitric-acid/water polar stratospheric clouds and noctilucent clouds.

The current atlas contains **66 unique native studies and 13 labeled boards**.
Some overview/species entries share the same underlying study. The optional
Cirrostratus halo is explicitly an optical example, not an additional cloud type.

```sh
python3 apps/paper-weather/tools/cloud_art.py
python3 apps/paper-weather/scripts/render_cloud_atlas.py
open output/cloud-atlas/index.html
```

The HTML is a local review index of actual native PNG renders and their editable
scene documents. It does not use image generation or reference-image pixels.
`manifest.json` records source/definition hashes, seeds, sampled traits, construction
metrics and diagnostic aesthetic losses; `render-report.json` records successful
native validation/rendering of every exported artifact.

Cloud definitions and common-association tables live in
`art/clouds/taxonomy.json`; implementations are in `tools/cloud_art.py`. For one
AI-supplied data specification:

```sh
python3 apps/paper-weather/tools/cloud_art.py \
  --spec apps/paper-weather/art/clouds/examples/storm.json \
  --output /tmp/paper-clouds
build/paper-scene --scene /tmp/paper-clouds/cumulonimbus-capillatus-incus-mamma-pannus.json
```

The specification chooses genus, one compatible species, varieties, supplementary
features, accessories, optional origin, seed and an optional Cirrostratus halo
example. The generator rejects incompatible names, duplicate modifiers and
contradictory opacity choices. Original example inputs cannot be overwritten by
one-cloud export. Regenerating a native document replaces it atomically, so an
already running scene player can reload it.

Morphology is structural: Cirrocumulus has smaller, intrinsically unshaded elements
than Altocumulus; Stratus and Altostratus use broad sheets; deep convection has a
connected tower rather than stacked icon clouds; capillatus adds a fibrous crown;
volutus is detached; cavum/lacunosus are actual cut apertures; cauda attaches to a
murus; pileus is above the parent tower. Bounded native drift preserves each assembly.

**Representation limits:** atmospheric transparency is interpreted using opaque,
sky-coordinated paper stocks; scattering and physical iridescence are not simulated.
Origin labels need environmental/provenance context and cannot always be inferred
from cloud shape. Common-association validation is deliberately conservative and
is not a meteorological classifier. The first art grammar supports one arrangement
operator and one structural-layer feature, and rejects structural-feature plus
arrangement/origin combinations rather than silently dropping a requested operator.
This is an implementation limit, not a claim that those combinations cannot occur.
Aesthetic losses measure specific heuristics and do not certify artistic quality.
The studies remain open to visual review. No weather-code-to-cloud inference or
new scene composition is wired into the main weather app.

Primary references: [WMO classification](https://cloudatlas.wmo.int/en/cloud-classification-summary.html),
[species associations](https://cloudatlas.wmo.int/en/clouds-species-and-genera-most-frequently-occur-table.html),
[varieties](https://cloudatlas.wmo.int/clouds-varieties-and-genera-most-frequently-occur-table.html),
[features](https://cloudatlas.wmo.int/en/clouds-supplementary-features-and-genera-most-frequently-occur-table.html),
[accessories](https://cloudatlas.wmo.int/en/clouds-accessory-and-genera-most-frequently-occur-table.html),
[special clouds](https://cloudatlas.wmo.int/en/clouds-special.html), and
[upper atmosphere](https://cloudatlas.wmo.int/en/upper-atmospheric-clouds.html).
Project review notes: [paper-test-clouds](pad://paper-test-clouds).

### Focused cloud restart

The broad cloud atlas was rejected for visual quality. Its taxonomy is reference material; its rendered forms are not approved assets. Replacement work proceeds one cloud family at a time.

The first study is `art/clouds/cumulus-grammar.json` and `tools/cumulus_study.py`: a parent-attached lobe grammar. Growth activates primary, flank and summit buds, expanding them locally from inside their parents. Analytic circle/line intersections produce a single silhouette. A capsule base and original shoulders remain fixed, and one uniform scale applies to both coordinates at every stage. There is no growth-dependent aspect ratio. Lean guides new buds; breadth sets shoulder spacing. A single continuous face and matching offset backing are drawn through the existing native Paper renderer.

```sh
# Run from the repository root:
python3 apps/paper-weather/tools/cumulus_study.py --review
open output/cumulus-study/index.html
python3 apps/paper-weather/tools/cumulus_study.py --growth .35 --lean -.2 --breadth .6 --output /tmp/cumulus
python3 -m unittest discover -s apps/paper-weather/tests -p 'cumulus_study_test.py' -v
```

The review page compares three native renders of the same family, changing only growth. It is a static comparison, not a live parameter renderer. Exact derivations and native scene documents are exported beside the images. The bounded geometry domain is tested for sampled contour intersections; visual quality still requires review. The weather app's scene is unchanged.
