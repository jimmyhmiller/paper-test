// A cut into a sheet, or a raised piece of that sheet. Ghostty supplies the
// original antialiased coverage and colours; it still owns all text layout.
// Distances are framebuffer pixels. The controls specialize these constants.
const float TEXT_RELIEF = -0.8500;
const float TEXT_PAPER_FILL = 0.2500;
const float TEXT_EDGE_PX = 1.7000;
const float TEXT_GRAIN = 0.1000;
const float CURSOR_LIFT_PX = 3.0000;
const float CURSOR_FOLD = 0.3500;
const float RASTER_SCALE = 1.0000;
// Paper scene coordinates are logical points, with +Y down. The host writes
// these from the same light state it passes to paper_light, plus the native
// terminal view origin. Normalize the light separately at each fragment.
const float LIGHT_X = -180.0000;
const float LIGHT_Y = -260.0000;
const float LIGHT_HEIGHT = 820.0000;
const float TERMINAL_X = 46.0000;
const float TERMINAL_Y = 224.0000;

vec3 lightAt(vec2 coord) {
    vec2 world = coord / (RASTER_SCALE * 2.0) + vec2(TERMINAL_X, TERMINAL_Y);
    return vec3(vec2(LIGHT_X, LIGHT_Y) - world, LIGHT_HEIGHT);
}

float hash21(vec2 p) {
    p = fract(p * vec2(0.1031, 0.1030));
    p += dot(p, p.yx + 33.33);
    return fract((p.x + p.y) * p.x);
}

float noise(vec2 p) {
    vec2 cell = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash21(cell), hash21(cell + vec2(1, 0)), f.x),
               mix(hash21(cell + vec2(0, 1)), hash21(cell + vec2(1)), f.x), f.y);
}

float fibre(vec2 p) {
    // Two irregular fibre scales. No periodic bands, animated noise, or
    // damage to the glyph silhouette: texture belongs to the material face.
    return (noise(p * vec2(0.42, 0.91)) - 0.5) * 0.65 +
           (noise(p * vec2(1.30, 0.53) + 19.0) - 0.5) * 0.35;
}

vec4 over(vec4 below, vec3 pigment, float coverage) {
    float a = clamp(coverage, 0.0, 1.0);
    return vec4(pigment * a, a) + below * (1.0 - a);
}

bool hasPaperCursor() {
    return iCursorVisible != 0 && iFocus != 0 &&
           iCurrentCursorStyle == CURSORSTYLE_BLOCK;
}

vec4 cursorBox() {
    // Ghostty's Metal coordinates are +Y down, and the uniform stores the
    // +Y (bottom) edge, not the top. See generic.zig's new_cursor contract.
    return vec4(iCurrentCursor.x, iCurrentCursor.y - iCurrentCursor.w,
                iCurrentCursor.zw);
}

float boxDistance(vec2 p, vec4 b) {
    vec2 q = abs(p - b.xy - b.zw * 0.5) - b.zw * 0.5;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0);
}

float paperDistance(vec2 p, vec4 b, float fold) {
    vec2 local = p - b.xy;
    float cut = (fold - (b.z - local.x + local.y)) * 0.70710678;
    return max(boxDistance(p, b), cut);
}

float glyph(vec2 p) {
    // A block cursor is geometry, not a giant rectangular glyph. Exclude it
    // from neighbouring letter rims and shadows before reconstructing it.
    if (hasPaperCursor() && boxDistance(p, cursorBox()) < 0.0) return 0.0;
    return texture(iChannel0, p / iResolution.xy).a;
}

float softGlyph(vec2 p, vec2 radius) {
    return glyph(p) * 0.40 +
           (glyph(p + vec2(radius.x, 0)) + glyph(p - vec2(radius.x, 0)) +
            glyph(p + vec2(0, radius.y)) + glyph(p - vec2(0, radius.y))) * 0.15;
}

void mainImage(out vec4 color, in vec2 coord) {
    vec4 source = texture(iChannel0, coord / iResolution.xy);
    float mask = glyph(coord);
    float depth = abs(TEXT_RELIEF);
    vec3 toLight = lightAt(coord);
    vec3 light = normalize(toLight);
    float sideways = length(light.xy);
    float strength = smoothstep(0.0, 0.45, depth) * clamp(sideways * 1.4, 0.0, 1.0);
    vec2 down = -light.xy / max(sideways, 0.0001);
    float projection = length(toLight.xy) / toLight.z;
    // The host provides backingScaleFactor / 2. Thickness belongs to the
    // paper, independently of font zoom or an application's cursor style.
    float pixelScale = RASTER_SCALE;
    float bevel = TEXT_EDGE_PX * pixelScale;
    float upper = glyph(coord - down * bevel);
    float lower = glyph(coord + down * bevel);
    float upperInside = max(mask - upper, 0.0);
    float lowerInside = max(mask - lower, 0.0);
    float lowerOutside = max(upper - mask, 0.0);
    float upperOutside = max(lower - mask, 0.0);
    vec3 stock = vec3(0.91, 0.85, 0.73);
    vec3 warmShadow = vec3(0.105, 0.080, 0.047);

    // Both the sampled frame and the completed CALayer use premultiplied
    // alpha. Work on straight pigment only while shading, then premultiply
    // once. This preserves the original glyph antialiasing at every edge.
    vec3 ink = source.a > 0.0001 ? source.rgb / source.a : vec3(0.0);
    color = vec4(0.0);
    bool raised = TEXT_RELIEF > 0.0;
    if (depth > 0.001) {
        if (raised) {
            float distance = (0.45 + depth * 1.05) * pixelScale * projection;
            float shadow = softGlyph(coord - down * distance,
                                     vec2((0.50 + depth * 0.30) * pixelScale));
            color = over(color, warmShadow, shadow * strength * 0.38);
            // A close contact seam anchors the paper edge to the sheet.
            color = over(color, warmShadow, lowerOutside * strength * 0.16);
        } else {
            // The light catches the lower outside lip of a cut. It is one
            // continuous contour, clipped outside the original glyph—not a
            // second offset copy of the entire letter.
            color = over(color, vec3(1.0, 0.98, 0.91), lowerOutside * strength * 0.92);
            color = over(color, warmShadow, upperOutside * strength * 0.09);
        }
    }

    if (mask > 0.0001) {
        // Preserve ANSI hue. At the paper end of the control the pigment is
        // a dyed paper face with enough contrast for terminal-size letters.
        vec3 face = mix(ink, mix(ink, stock, raised ? 0.79 : 0.45), TEXT_PAPER_FILL);
        face *= 1.0 + fibre(coord) * TEXT_GRAIN * 1.8;
        if (raised) {
            face += stock * (upperInside / mask) * strength * 0.15;
            face *= 1.0 - (lowerInside / mask) * strength * 0.30;
        } else if (depth > 0.001) {
            float interior = max(mask - softGlyph(coord - down * (0.6 + depth * 1.65) * pixelScale * projection,
                                                  vec2(0.50 * pixelScale)), 0.0);
            face *= 1.0 - (interior / mask) * strength * 0.70;
            face += stock * (lowerInside / mask) * strength * 0.105;
        }
        color = over(color, clamp(face, 0.0, 1.0), mask);
    }

    // Opaque selected/coloured backgrounds retain their native rasterization.
    // There is no hidden glyph mask behind their completed alpha, so avoid
    // inventing lettering from colour or applying paper fill to a whole cell.
    float backgroundRadius = 6.0 * pixelScale;
    float solid = min(min(glyph(coord + vec2(0, backgroundRadius)), glyph(coord - vec2(0, backgroundRadius))),
                      min(glyph(coord + vec2(backgroundRadius, 0)), glyph(coord - vec2(backgroundRadius, 0))));
    if (solid > 0.999 && source.a > 0.999) color = source;

    if (!hasPaperCursor()) return;
    vec4 cursor = cursorBox();
    vec3 cursorToLight = lightAt(cursor.xy + cursor.zw * 0.5);
    vec3 cursorLight = normalize(cursorToLight);
    float cursorSideways = length(cursorLight.xy);
    vec2 cursorDown = -cursorLight.xy / max(cursorSideways, 0.0001);
    float cursorProjection = length(cursorToLight.xy) / cursorToLight.z;
    vec2 local = coord - cursor.xy;
    float lift = CURSOR_LIFT_PX * pixelScale;
    float foldSize = min(cursor.z * CURSOR_FOLD, cursor.w * 0.28);
    float bodyDistance = paperDistance(coord, cursor, foldSize);
    float body = 1.0 - smoothstep(-0.65, 0.65, bodyDistance);
    // Clip the original top-right corner; the diagonal exposes a lighter
    // underside. The fold and shadow share the same cut geometry.
    float diagonal = cursor.z - local.x + local.y;
    float flap = smoothstep(cursor.z - foldSize - 0.5, cursor.z - foldSize + 0.5, local.x) *
                 (1.0 - smoothstep(foldSize - 0.5, foldSize + 0.5, local.y));
    float paperMask = body;
    vec4 shifted = vec4(cursor.xy + cursorDown * lift * cursorProjection, cursor.zw);
    float shadowDistance = paperDistance(coord, shifted, foldSize);
    float softness = 0.75 + lift * (0.22 + cursorProjection * 0.10);
    float shadow = (1.0 - smoothstep(-softness, softness * 1.8, shadowDistance)) *
                   (1.0 - body) * (0.22 + min(lift, 6.0) * 0.045);
    color = over(color, warmShadow, shadow);

    // The stock has an actual lower cut edge before the face is laid on it.
    float thickness = 1.0 + lift * 0.10;
    vec4 edgeBox = vec4(cursor.xy + vec2(0.25, thickness), cursor.zw);
    float edge = 1.0 - smoothstep(-0.5, 0.5, paperDistance(coord, edgeBox, foldSize));
    color = over(color, vec3(0.54, 0.31, 0.10) * (0.82 + 0.18 * max(cursorLight.y, 0.0)), edge * (1.0 - body));
    if (paperMask > 0.0) {
        vec3 amber = vec3(0.84, 0.59, 0.28);
        amber *= 1.0 + fibre(coord + 31.0) * 0.22;
        amber *= 0.86 + 0.14 * cursorLight.z;
        vec2 normal = vec2(paperDistance(coord + vec2(0.5, 0.0), cursor, foldSize) -
                           paperDistance(coord - vec2(0.5, 0.0), cursor, foldSize),
                           paperDistance(coord + vec2(0.0, 0.5), cursor, foldSize) -
                           paperDistance(coord - vec2(0.0, 0.5), cursor, foldSize));
        float rimLight = dot(normal / max(length(normal), 0.001), cursorLight.xy);
        float rim = 1.0 - smoothstep(0.0, 1.25 * pixelScale, -bodyDistance);
        amber += vec3(0.20, 0.17, 0.11) * max(rimLight, 0.0) * rim;
        amber -= vec3(0.20, 0.15, 0.08) * max(-rimLight, 0.0) * rim;
        float foldLight = max(dot(normalize(vec3(0.5, -0.5, 0.7)), cursorLight), 0.0);
        vec3 underside = vec3(0.97, 0.83, 0.56) * (0.82 + foldLight * 0.18) * (1.0 + fibre(coord) * 0.10);
        float crease = 1.0 - smoothstep(0.0, 1.4, abs(diagonal - foldSize));
        amber = mix(amber, underside, flap);
        amber += vec3(0.08, 0.07, 0.04) * crease * step(0.8, foldSize) * foldLight;
        // Retain any real character under the cursor. Its original foreground
        // is encoded in the cursor-colour raster, including antialiasing.
        float cursorInk = clamp(length(ink - iCursorColor) / max(length(iCursorText - iCursorColor), 0.01), 0.0, 1.0);
        amber = mix(amber, iCursorText, cursorInk * source.a);
        color = over(color, amber, paperMask);
    }
}
