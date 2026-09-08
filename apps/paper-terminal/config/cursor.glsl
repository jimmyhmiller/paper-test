// A cut into a sheet, or a raised piece of that sheet. Ghostty supplies the
// original antialiased coverage and colours; it still owns all text layout.
// Distances are framebuffer pixels. The controls specialize these constants.
// Live native uniforms. Light/material drags never rebuild this program.
#define LIGHT_X iPaperMaterial[0].x
#define LIGHT_Y iPaperMaterial[0].y
#define LIGHT_HEIGHT iPaperMaterial[0].z
#define RASTER_SCALE iPaperMaterial[0].w
#define TERMINAL_X iPaperMaterial[1].x
#define TERMINAL_Y iPaperMaterial[1].y
#define TEXT_RELIEF iPaperMaterial[1].z
#define TEXT_PAPER_FILL iPaperMaterial[1].w
#define TEXT_EDGE_PX iPaperMaterial[2].x
#define TEXT_GRAIN iPaperMaterial[2].y
#define CURSOR_LIFT_PX iPaperMaterial[2].z
#define CURSOR_FOLD iPaperMaterial[2].w
#define TEXT_CUT_PAPER iPaperMaterial[3].x
#define TEXT_GAP_PT iPaperMaterial[3].y
#define TEXT_THICKNESS_PT iPaperMaterial[3].z
#define SHINE iPaperMaterial[3].w
#define ROUGHNESS iPaperMaterial[4].x
#define BACKGROUND_DEPTH iPaperMaterial[4].y
#define SELECTION_DEPTH iPaperMaterial[4].z

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
    // Supplied by Paper's native Metal glyph pass, before ink-dependent
    // coverage correction. Backgrounds, emoji and cursors are not geometry.
    if (any(lessThan(p, vec2(0.0))) || any(greaterThanEqual(p, iResolution.xy))) return 0.0;
    return texture(iChannel1, p / iResolution.xy).a;
}

vec3 paperPigment(vec3 ink) {
    // Pigment dyes the stock rather than darkening every paper face into ink.
    vec3 dye = ink / max(max(ink.r, ink.g), max(ink.b, 0.001));
    return vec3(0.96, 0.91, 0.81) * mix(vec3(1.0), dye, 0.32);
}

// A dielectric coating, with GGX distribution, Smith masking and Schlick
// Fresnel (F0=0.04). Roughness controls highlight width; the coat is optional.
// See PBRT, Roughness Using Microfacet Theory and Rough Dielectric BSDF.
vec3 coated(vec3 base, vec3 n, vec3 l, float visibility) {
    if (SHINE <= 0.0) return base;
    vec3 h = normalize(l + vec3(0.0, 0.0, 1.0));
    float nv = max(n.z, 0.001), nl = max(dot(n, l), 0.0);
    float nh = max(dot(n, h), 0.0), vh = max(h.z, 0.0);
    float alpha = max(ROUGHNESS * ROUGHNESS, 0.025);
    float a2 = alpha * alpha;
    float d = nh * nh * (a2 - 1.0) + 1.0;
    float distribution = a2 / (3.14159265 * d * d);
    float masking = 0.5 / max(nl * sqrt(a2 + (1.0 - a2) * nv * nv) +
                              nv * sqrt(a2 + (1.0 - a2) * nl * nl), 0.001);
    float fresnel = 0.04 + 0.96 * pow(1.0 - vh, 5.0);
    float reflected = distribution * masking * fresnel * nl * visibility * 3.14159265;
    return base * (1.0 - SHINE * fresnel) + vec3(1.0, 0.98, 0.93) * reflected * SHINE;
}

vec4 backgroundAt(vec2 p) {
    if (any(lessThan(p, vec2(0))) || any(greaterThanEqual(p, iResolution.xy))) return vec4(0);
    return texture(iChannel2, p / iResolution.xy);
}

float backgroundHeight(vec2 p) {
    vec4 bg = backgroundAt(p);
    if (bg.a < 0.001) return 0.0;
    vec3 pigment = bg.rgb / bg.a;
    float selected = 1.0 - smoothstep(0.005, 0.025, length(pigment - iSelectionBackgroundColor));
    float density = 1.0 - dot(pigment, vec3(0.2126, 0.7152, 0.0722));
    float depth = mix(BACKGROUND_DEPTH * (0.35 + 0.65 * density), SELECTION_DEPTH, selected);
    return -depth * 2.0 * RASTER_SCALE * bg.a;
}

vec4 recessedBackground(vec4 source, vec2 p, vec3 light) {
    float r = max(0.75, 1.25 * RASTER_SCALE);
    float height = backgroundHeight(p);
    vec2 gradient = vec2(backgroundHeight(p + vec2(r, 0)) - backgroundHeight(p - vec2(r, 0)),
                         backgroundHeight(p + vec2(0, r)) - backgroundHeight(p - vec2(0, r))) / (2.0 * r);
    vec3 normal = normalize(vec3(-gradient, 1.0));
    float visibility = 1.0;
    // Recessed cell surfaces shadow one another at colour boundaries.
    if (height < -0.001) {
        vec2 towardLight = light.xy / max(light.z, 0.08);
        for (int i = 1; i <= 4; ++i) {
            float rise = -height * float(i) / 4.0;
            float blocker = backgroundHeight(p + towardLight * rise);
            visibility = min(visibility, smoothstep(-r * 0.3, r * 0.3, height + rise - blocker));
        }
    }
    float diffuse = (0.28 + 0.72 * max(dot(normal, light), 0.0) * visibility) / (0.28 + 0.72 * light.z);
    diffuse *= 1.0 - min(-height / (2.0 * RASTER_SCALE), 6.0) * 0.025;
    if (source.a > 0.0) {
        vec3 stock = source.rgb / source.a * diffuse;
        stock *= 1.0 + fibre(p / RASTER_SCALE) * TEXT_GRAIN;
        vec3 face = coated(stock, normal, light, visibility);
        return vec4(clamp(face, 0.0, 1.0) * source.a, source.a);
    }
    // The exposed outer lip belongs to the surrounding paper.
    vec4 rim = over(vec4(0), vec3(0.14, 0.10, 0.055), clamp(1.0 - diffuse, 0.0, 1.0) * 0.8);
    return over(rim, vec3(1.0, 0.98, 0.91), clamp(diffuse - 1.0, 0.0, 1.0));
}

float paperShadow(vec2 p, vec2 offset, float radius) {
    // Deterministic area-light integration. The face is never blurred. The
    // shadow's penumbra grows with the gap, independently of sheet thickness.
    float result = 0.0;
    const float angle = 2.39996323;
    for (int i = 0; i < 16; ++i) {
        float r = sqrt((float(i) + 0.5) / 16.0) * radius;
        vec2 disk = vec2(cos(float(i) * angle), sin(float(i) * angle)) * r;
        result += glyph(p - offset + disk);
    }
    return result / 16.0;
}

vec4 cutPaper(vec2 p, vec4 pigment, vec3 light) {
    float scale = RASTER_SCALE * 2.0;
    float thickness = TEXT_THICKNESS_PT * scale;
    float height = (TEXT_GAP_PT + TEXT_THICKNESS_PT) * scale;
    vec2 shadowOffset = -light.xy / max(light.z, 0.08) * height;
    float shadow = paperShadow(p, shadowOffset, (0.18 + TEXT_GAP_PT * 0.12) * scale);
    vec4 result = over(vec4(0.0), vec3(0.15, 0.115, 0.065), shadow * 0.52);

    // A thin sheet has a cut sidewall, not an extrusion down to the ground.
    // This small fixed view slope reveals its bottom edge. Gap never changes
    // this geometry: the open space must remain visibly open.
    vec2 edgeOffset = vec2(0.22, 0.86) * thickness;
    float side = 0.0;
    for (int i = 1; i <= 4; ++i) {
        side = max(side, glyph(p - edgeOffset * (float(i) / 4.0)));
    }
    vec3 edgeStock = vec3(0.54, 0.43, 0.28) * (0.65 + 0.35 * max(light.y, 0.0));
    float coverage = max(side, pigment.a);
    vec4 sheet = vec4(edgeStock * max(side - pigment.a, 0.0), coverage);

    if (pigment.a > 0.0001) {
        vec3 ink = pigment.rgb / pigment.a;
        vec3 face = mix(ink, paperPigment(ink), TEXT_PAPER_FILL);
        float r = 0.45 * scale;
        vec2 gradient = vec2(glyph(p + vec2(r, 0)) - glyph(p - vec2(r, 0)),
                             glyph(p + vec2(0, r)) - glyph(p - vec2(0, r)));
        float edgeLight = dot(-gradient, light.xy);
        // Only the very edge turns toward the light. Flat, unbroken paper
        // occupies the rest of a stroke, even at the smallest font sizes.
        face *= 0.94 + 0.06 * light.z;
        face += vec3(0.12, 0.105, 0.08) * max(edgeLight, 0.0);
        face -= vec3(0.07, 0.06, 0.04) * max(-edgeLight, 0.0);
        face *= 1.0 + fibre(p / RASTER_SCALE) * TEXT_GRAIN;
        vec3 normal = normalize(vec3(-gradient * 0.55, 1.0));
        face = coated(face, normal, light, 1.0);
        sheet.rgb += clamp(face, 0.0, 1.0) * pigment.a;
    }
    // Face and side partition one silhouette. Over-compositing both masks
    // would count fractional edge coverage twice and fatten small glyphs.
    return sheet + result * (1.0 - coverage);
}

// A separable binomial filter reconstructs coverage as a compact height field.
// Its central-difference gradient uses the same nine samples as its height, so
// diagonal walls and corners have continuous normals, not offset outlines.
// This is a local coverage reconstruction, not a font distance field.
vec3 reliefField(vec2 p, float radius) {
    vec3 field = vec3(0.0);
    for (int y = -1; y <= 1; ++y) {
        for (int x = -1; x <= 1; ++x) {
            vec2 offset = vec2(float(x), float(y));
            float wx = x == 0 ? 0.5 : 0.25;
            float wy = y == 0 ? 0.5 : 0.25;
            float a = glyph(p + offset * radius);
            field.x += a * wx * wy;
            field.yz += a * offset * vec2(wy, wx) * (0.5 / radius);
        }
    }
    return field;
}

// March toward the light across the same reconstructed surface. A growing
// penumbra approximates finite light size without blurring the glyph.
float reliefVisibility(vec2 p, float height, float signedDepth,
                       float radius, vec3 light) {
    float visibility = 1.0;
    float travel = abs(signedDepth) * length(light.xy) / max(light.z, 0.08) + radius * 2.0;
    vec2 direction = light.xy / max(length(light.xy), 0.0001);
    for (int i = 1; i <= 6; ++i) {
        float t = travel * float(i) / 6.0;
        float surface = reliefField(p + direction * t, radius).x * signedDepth;
        float ray = height + t * light.z / max(length(light.xy), 0.0001);
        float penumbra = 0.20 * RASTER_SCALE + t * 0.16;
        visibility = min(visibility, smoothstep(-penumbra, penumbra, ray - surface));
    }
    return visibility;
}

void mainImage(out vec4 color, in vec2 coord) {
    vec4 source = texture(iChannel0, coord / iResolution.xy);
    vec4 pigment = texture(iChannel1, coord / iResolution.xy);
    float mask = pigment.a;
    float depth = abs(TEXT_RELIEF);
    vec3 toLight = lightAt(coord);
    vec3 light = normalize(toLight);
    // The host provides backingScaleFactor / 2. All relief dimensions are
    // physical paper dimensions, independent of the font and cursor style.
    float pixelScale = RASTER_SCALE;
    float bevel = max(TEXT_EDGE_PX * pixelScale, 0.65);
    vec3 stock = vec3(0.91, 0.85, 0.73);
    vec3 warmShadow = vec3(0.105, 0.080, 0.047);
    vec3 ink = source.a > 0.0001 ? source.rgb / source.a : vec3(0.0);
    color = source;
    if (TEXT_CUT_PAPER > 0.5) {
        color = cutPaper(coord, pigment, light);
    } else if (depth > 0.001) {
        bool raised = TEXT_RELIEF > 0.0;
        // Estimate available stroke width before choosing the bevel radius.
        // Thin strokes keep a narrow edge instead of becoming rounded tubes.
        vec3 broad = reliefField(coord, bevel);
        float room = smoothstep(0.65, 0.98, broad.x);
        bevel = mix(min(bevel, 0.55 * pixelScale), bevel, room);
        float signedDepth = TEXT_RELIEF * 3.2 * pixelScale;
        vec3 field = reliefField(coord, bevel);
        vec3 normal = normalize(vec3(-signedDepth * field.yz, 1.0));
        float wall = 1.0 - normal.z;
        // A receiver at the maximum possible surface height cannot be
        // shadowed. In carved mode this skips the march on blank paper.
        float visibility = 1.0;
        if ((raised && field.x < 0.9999) || (!raised && field.x > 0.0001)) {
            visibility = reliefVisibility(coord, field.x * signedDepth,
                                          signedDepth, bevel, light);
        }
        // Ambient keeps dyed paper legible; directional diffuse describes the
        // cut walls. Normalize against the flat sheet's illumination.
        float diffuse = (0.30 + 0.70 * max(dot(normal, light), 0.0) * visibility) /
                        (0.30 + 0.70 * light.z);
        float cavity = raised ? 0.0 : field.x * (1.0 - field.x) * 4.0;
        float occlusion = 1.0 - 0.24 * cavity * min(depth, 1.0);
        vec3 halfVector = normalize(light + vec3(0.0, 0.0, 1.0));
        float sheen = pow(max(dot(normal, halfVector), 0.0), 18.0) * wall * visibility;
        // Outside the ink silhouette these are the compressed stock walls of
        // the impression, or the foot and shadow of the raised letter.
        color = vec4(0.0);
        float darkness = clamp(1.0 - diffuse * occlusion, 0.0, 1.0);
        float brightness = clamp((diffuse - 1.0) * 0.85 + sheen * 0.22, 0.0, 1.0);
        color = over(color, warmShadow, darkness * 0.85);
        color = over(color, vec3(1.0, 0.98, 0.91), brightness);
        if (mask > 0.0001) {
            // Ink settles in the floor; sloping walls expose more of the
            // underlying stock. This makes depth visible even in dark text.
            vec3 dye = pigment.rgb / mask;
            vec3 face = mix(dye, paperPigment(dye), TEXT_PAPER_FILL);
            face = mix(face, paperPigment(dye), wall * 0.25);
            face *= diffuse * occlusion;
            face += stock * sheen * 0.08;
            face = coated(face, normal, light, visibility);
            face *= 1.0 + fibre(coord / pixelScale) * TEXT_GRAIN * 1.2;
            color = over(color, clamp(face, 0.0, 1.0), mask);
        }
    }

    // Native content excluded by the glyph pass keeps its original pixels.
    // In particular, selected/ANSI backgrounds and colour emoji never become
    // rectangular paper cutouts. No neighbourhood-based background guessing.
    if (mask == 0.0 && source.a > 0.0) color = source;
    if (BACKGROUND_DEPTH > 0.0 || SELECTION_DEPTH > 0.0) {
        vec4 bg = backgroundAt(coord);
        if (bg.a > 0.001) color = recessedBackground(source, coord, light);
        else {
            vec4 lip = recessedBackground(vec4(0.0), coord, light);
            color = color + lip * (1.0 - color.a);
        }
    }

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
