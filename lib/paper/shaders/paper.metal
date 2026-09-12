#include <metal_stdlib>
using namespace metal;

// BEGIN GENERATED MATERIAL KERNELS
// Generated from texture.coil and finish_light.coil by tools/generate-material-shader.py.
inline float tex_hash(long x, long y, long seed) {
    const auto a = ((uint(x) * uint(374761393)) ^ ((uint(y) * uint(668265263)) ^ (uint(seed) * uint(1274126177))));
    const auto b = ((a ^ (a >> uint(13))) * uint(1274126177));
    return (float(((b ^ (b >> uint(16))) & uint(65535))) / 65535.0f);
}
inline float tex_fract(float x) {
    return (x - floor(x));
}
inline float tex_abs(float x) {
    return ((x < 0.0f) ? (0.0f - x) : x);
}
inline float tex_min(float x, float y) {
    return ((x < y) ? x : y);
}
inline float tex_max(float x, float y) {
    return ((x > y) ? x : y);
}
inline float tex_smooth(float x) {
    const auto t = tex_max(0.0f, tex_min(1.0f, x));
    return ((t * t) * (3.0f - (2.0f * t)));
}
inline float tex_mix(float a, float b, float t) {
    return (a + ((b - a) * t));
}
inline float tex_noise(float x, float y, long seed) {
    const auto ix = long(floor(x));
    const auto iy = long(floor(y));
    const auto u = tex_smooth(tex_fract(x));
    const auto v = tex_smooth(tex_fract(y));
    return (tex_mix(tex_mix(tex_hash(ix, iy, seed), tex_hash((ix + 1), iy, seed), u), tex_mix(tex_hash(ix, (iy + 1), seed), tex_hash((ix + 1), (iy + 1), seed), u), v) - 0.5f);
}
inline float tex_thread(float x, float gap) {
    const auto d = tex_abs((tex_fract(x) - 0.5f));
    return tex_smooth(((0.5f - d) / gap));
}
inline float tex_weave(float x, float y, long seed, float spacing, float irregular, float gap) {
    const auto u = ((x / spacing) + (irregular * tex_noise((y / 18.0f), (x / 40.0f), seed)));
    const auto v = ((y / spacing) + (irregular * tex_noise((x / 21.0f), (y / 37.0f), (seed + 7))));
    const auto warp = tex_thread(u, gap);
    const auto weft = tex_thread(v, gap);
    const auto crossing = tex_fract(((floor(u) + floor(v)) * 0.5f));
    const auto top = ((crossing < 0.25f) ? warp : weft);
    const auto lower = ((crossing < 0.25f) ? weft : warp);
    const auto fibers = tex_noise((x * 1.6f), (y / 8.0f), (seed + 17));
    return ((((top * 0.65f) + ((lower * (1.0f - top)) * 0.35f)) - 0.4f) + (fibers * 0.045f));
}
inline float tex_cell_distance(float x, float y, long ix, long iy, long seed) {
    const auto dx = (x - (float(ix) + (0.2f + (0.6f * tex_hash(ix, iy, seed)))));
    const auto dy = (y - (float(iy) + (0.2f + (0.6f * tex_hash(ix, iy, (seed + 31))))));
    return ((dx * dx) + (dy * dy));
}
inline float tex_cells(float x, float y, long seed) {
    const auto ix = long(floor(x));
    const auto iy = long(floor(y));
    const auto a = tex_min(tex_cell_distance(x, y, (ix - 1), (iy - 1), seed), tex_min(tex_cell_distance(x, y, ix, (iy - 1), seed), tex_cell_distance(x, y, (ix + 1), (iy - 1), seed)));
    const auto b = tex_min(tex_cell_distance(x, y, (ix - 1), iy, seed), tex_min(tex_cell_distance(x, y, ix, iy, seed), tex_cell_distance(x, y, (ix + 1), iy, seed)));
    const auto c = tex_min(tex_cell_distance(x, y, (ix - 1), (iy + 1), seed), tex_min(tex_cell_distance(x, y, ix, (iy + 1), seed), tex_cell_distance(x, y, (ix + 1), (iy + 1), seed)));
    return sqrt(tex_min(a, tex_min(b, c)));
}
inline float tex_chip(float x, float y, long seed) {
    const auto ix = long(floor(x));
    const auto iy = long(floor(y));
    const auto a = tex_cell_distance(x, y, (ix - 1), (iy - 1), seed);
    const auto b = tex_cell_distance(x, y, ix, (iy - 1), seed);
    const auto c = tex_cell_distance(x, y, (ix + 1), (iy - 1), seed);
    const auto d = tex_cell_distance(x, y, (ix - 1), iy, seed);
    const auto e = tex_cell_distance(x, y, ix, iy, seed);
    const auto f = tex_cell_distance(x, y, (ix + 1), iy, seed);
    const auto g = tex_cell_distance(x, y, (ix - 1), (iy + 1), seed);
    const auto h = tex_cell_distance(x, y, ix, (iy + 1), seed);
    const auto i = tex_cell_distance(x, y, (ix + 1), (iy + 1), seed);
    const auto best = tex_min(tex_min(a, tex_min(b, c)), tex_min(tex_min(d, tex_min(e, f)), tex_min(g, tex_min(h, i))));
    const auto cx = ((a <= best) ? (ix - 1) : ((b <= best) ? ix : ((c <= best) ? (ix + 1) : ((d <= best) ? (ix - 1) : ((e <= best) ? ix : ((f <= best) ? (ix + 1) : ((g <= best) ? (ix - 1) : ((h <= best) ? ix : (ix + 1)))))))));
    return (tex_hash(cx, ((tex_min(a, tex_min(b, c)) <= best) ? (iy - 1) : ((tex_min(d, tex_min(e, f)) <= best) ? iy : (iy + 1))), (seed + 73)) - 0.5f);
}
inline float tex_height(long kind, float x, float y, long seed) {
    switch (kind) {
    case 1: {
        return ((0.10f * tex_noise((x / 7.0f), (y / 9.0f), seed)) + ((0.15f * tex_noise((x / 0.7f), (y / 3.7f), (seed + 5))) + (0.11f * tex_noise((x / 1.5f), (y / 0.5f), (seed + 8)))));
    }
    case 2: {
        return ((0.09f * tex_noise((x * 1.8f), (y * 1.8f), seed)) + (0.045f * tex_noise((x / 5.0f), (y / 5.0f), (seed + 3))));
    }
    case 3: {
        return ((0.32f * tex_noise((x / 1.6f), (y / 1.6f), seed)) + ((0.09f * tex_noise((x / 6.0f), (y / 6.0f), (seed + 5))) + (0.12f * tex_noise((x * 1.2f), (y * 1.2f), (seed + 11)))));
    }
    case 4: {
        return ((0.13f * cos((y * 3.141592653589793f))) + ((0.07f * tex_thread((x / 26.0f), 0.07f)) + (0.07f * tex_noise(x, y, seed))));
    }
    case 5: {
        return ((0.14f * tex_noise(((x + (y * 0.31f)) / 0.65f), (y / 19.0f), seed)) + ((0.12f * tex_noise(((x - (y * 0.7f)) / 0.8f), (y / 13.0f), (seed + 6))) + (0.09f * tex_noise((x / 13.0f), (y / 13.0f), (seed + 12)))));
    }
    case 6: {
        return ((0.10f * tex_noise((x * 1.5f), (y * 1.5f), seed)) + ((0.12f * tex_noise((x / 11.0f), (y / 9.0f), (seed + 3))) + (-0.18f * tex_smooth(((tex_noise(x, y, (seed + 9)) - 0.22f) * 5.0f)))));
    }
    case 7: {
        return ((0.42f * cos(((x * 0.6981317007977318f) + (0.06f * tex_noise((x / 30.0f), (y / 20.0f), seed))))) + (0.08f * tex_noise((x * 1.2f), (y / 3.0f), (seed + 8))));
    }
    case 8: {
        return ((0.21f * tex_noise((((x + (y * 0.6f)) + (1.5f * tex_noise((x / 6.0f), (y / 6.0f), (seed + 3)))) / 0.55f), (y / 4.5f), seed)) + ((0.20f * tex_noise((((x - (y * 0.8f)) + (1.3f * tex_noise((x / 5.0f), (y / 5.0f), (seed + 11)))) / 0.6f), (y / 5.5f), (seed + 7))) + ((0.18f * tex_noise(((y + (x * 0.3f)) / 0.5f), (x / 4.0f), (seed + 17))) + (0.10f * tex_noise((x / 8.0f), (y / 8.0f), (seed + 21))))));
    }
    case 9: {
        return tex_weave(x, y, seed, 3.2f, 0.28f, 0.36f);
    }
    case 10: {
        return tex_weave(x, y, seed, 2.6f, 0.035f, 0.42f);
    }
    case 11: {
        const auto u = (x / 2.0f);
        const auto v = (y / 2.0f);
        const auto twill = tex_fract(((floor(u) + floor(v)) / 3.0f));
        const auto warp = tex_thread(u, 0.38f);
        const auto weft = tex_thread(v, 0.38f);
        return ((((twill < 0.6f) ? ((warp * 0.7f) + ((weft * (1.0f - warp)) * 0.2f)) : ((weft * 0.45f) + ((warp * (1.0f - weft)) * 0.2f))) - 0.35f) + (0.08f * tex_noise((x * 2.0f), (y / 7.0f), seed)));
    }
    case 12: {
        return (tex_weave(x, y, seed, 5.2f, 0.38f, 0.48f) + (0.10f * tex_noise((x * 1.7f), (y / 2.0f), (seed + 27))));
    }
    case 13: {
        const auto u = (tex_fract((x / 6.0f)) - 0.5f);
        const auto v = tex_fract((y / 8.0f));
        const auto center = (0.06f + (0.29f * sin((v * 3.141592653589793f))));
        const auto distance = tex_abs((tex_abs(u) - center));
        const auto yarn = tex_smooth(((0.21f - distance) / 0.15f));
        const auto rib = cos(((v * 31.41592653589793f) + (u * 27.0f)));
        return (((yarn * (0.62f + (rib * 0.055f))) - 0.3f) + (0.07f * tex_noise((x * 1.6f), (y * 1.6f), seed)));
    }
    case 14: {
        return ((0.52f * tex_chip((x / 5.5f), (y / 5.5f), seed)) + ((0.15f * tex_noise((x / 2.0f), (y / 2.0f), (seed + 5))) + (0.12f * tex_noise((x * 1.5f), (y * 1.5f), (seed + 11)))));
    }
    case 15: {
        const auto cells = tex_cells((x / 2.8f), (y / 2.8f), seed);
        return (((0.45f * (1.0f - tex_smooth((cells * 1.8f)))) - 0.25f) + (0.09f * tex_noise((x * 1.8f), (y * 1.8f), (seed + 9))));
    }
    case 16: {
        return ((0.18f * tex_noise((x * 2.2f), (y / 1.6f), seed)) + (0.12f * tex_noise((x / 9.0f), (y / 16.0f), (seed + 17))));
    }
    case 17: {
        const auto cx = (x - (32.0f + (48.0f * tex_hash(0, 0, seed))));
        const auto cy = (y - (70.0f + (120.0f * tex_hash(1, 0, seed))));
        const auto radius = sqrt(((cx * cx) + ((cy * cy) * 0.045f)));
        const auto warp = (2.4f * tex_noise((x / 32.0f), (y / 75.0f), seed));
        const auto rings = ((radius * 0.7f) + warp);
        const auto lines = tex_smooth(((sin(rings) - 0.48f) * 2.1f));
        const auto fine = tex_noise((x * 1.2f), (y / 18.0f), (seed + 21));
        return ((0.08f - (0.23f * lines)) + ((0.09f * fine) + (0.10f * tex_noise((x / 12.0f), (y / 45.0f), (seed + 9)))));
    }
    case 18: {
        return ((0.13f * tex_noise((x * 1.7f), (y * 1.7f), seed)) + (0.04f * tex_noise((x / 6.0f), (y / 6.0f), (seed + 3))));
    }
    case 19: {
        return ((0.10f * tex_noise((x * 2.0f), (y / 2.8f), seed)) + (0.08f * tex_noise((x / 12.0f), (y / 22.0f), (seed + 9))));
    }
    case 20: {
        return ((0.11f * tex_noise((x * 2.5f), (y / 35.0f), seed)) + (0.025f * tex_noise((x * 0.7f), (y / 90.0f), (seed + 11))));
    }
    case 21: {
        return ((0.15f * tex_weave(x, y, seed, 1.8f, 0.08f, 0.28f)) + (0.06f * tex_noise((x * 1.5f), (y / 18.0f), (seed + 9))));
    }
    case 22: {
        return ((0.05f * tex_noise((x / 6.0f), (y / 6.0f), seed)) + (0.025f * tex_noise((x * 1.4f), (y * 1.4f), (seed + 3))));
    }
    case 23: {
        const auto u = (x + (1.4f * tex_noise((x / 5.0f), (y / 5.0f), (seed + 7))));
        const auto v = (y + (1.4f * tex_noise((x / 5.0f), (y / 5.0f), (seed + 13))));
        const auto ridge = (1.0f - tex_smooth((4.5f * tex_abs(tex_noise((u / 1.7f), (v / 0.85f), seed)))));
        return (((0.22f * ridge) - 0.11f) + ((0.13f * tex_noise((x * 2.1f), (y * 2.1f), (seed + 19))) + (0.045f * tex_noise((x / 7.0f), (y / 7.0f), (seed + 29)))));
    }
    default: {
        return 0.0f;
    }
    }
}
inline float tex_contrast(long kind) {
    switch (kind) {
    case 1: {
        return 0.65f;
    }
    case 2: {
        return 0.35f;
    }
    case 3: {
        return 0.22f;
    }
    case 4: {
        return 0.3f;
    }
    case 5: {
        return 0.55f;
    }
    case 6: {
        return 0.6f;
    }
    case 7: {
        return 0.35f;
    }
    case 8: {
        return 0.65f;
    }
    case 9: {
        return 0.6f;
    }
    case 10: {
        return 0.55f;
    }
    case 11: {
        return 0.75f;
    }
    case 12: {
        return 0.8f;
    }
    case 13: {
        return 0.65f;
    }
    case 14: {
        return 0.85f;
    }
    case 15: {
        return 0.3f;
    }
    case 16: {
        return 0.6f;
    }
    case 17: {
        return 0.8f;
    }
    case 18: {
        return 0.4f;
    }
    case 19: {
        return 0.35f;
    }
    case 20: {
        return 0.45f;
    }
    case 21: {
        return 0.4f;
    }
    case 22: {
        return 0.3f;
    }
    case 23: {
        return 0.4f;
    }
    default: {
        return 0.0f;
    }
    }
}
inline float fin_alpha_u(float roughness, float anisotropy) {
    return tex_min(1.0f, tex_max(0.08f, (roughness * (1.0f + anisotropy))));
}
inline float fin_alpha_v(float roughness, float anisotropy) {
    return tex_min(1.0f, tex_max(0.08f, (roughness * (1.0f - anisotropy))));
}
inline float fin_quadratic(float x, float y, float a, float b, float axis_x, float axis_y) {
    const auto amount = sqrt(((axis_x * axis_x) + (axis_y * axis_y)));
    const auto c = ((amount > 0.00001f) ? (axis_x / amount) : 1.0f);
    const auto s = ((amount > 0.00001f) ? (axis_y / amount) : 0.0f);
    const auto sum = (0.5f * (a + b));
    const auto difference = (0.5f * (a - b));
    return ((sum * ((x * x) + (y * y))) + (difference * ((c * ((x * x) - (y * y))) + ((2.0f * s) * (x * y)))));
}
inline float fin_specular(float dx, float dy, float lx, float ly, float lz, float roughness, float axis_x, float axis_y) {
    const auto n = sqrt((1.0f + ((dx * dx) + (dy * dy))));
    const auto t = sqrt((1.0f + (dx * dx)));
    const auto length = sqrt(((lx * lx) + ((ly * ly) + (lz * lz))));
    const auto ux = (lx / length);
    const auto uy = (ly / length);
    const auto uz = (lz / length);
    const auto nl = ((uz - ((dx * ux) + (dy * uy))) / n);
    const auto nv = (1.0f / n);
    const auto hl = sqrt(((ux * ux) + ((uy * uy) + ((uz + 1.0f) * (uz + 1.0f)))));
    const auto hx = (ux / hl);
    const auto hy = (uy / hl);
    const auto hz = ((uz + 1.0f) / hl);
    const auto ht = ((hx + (dx * hz)) / t);
    const auto hb = (((((1.0f + (dx * dx)) * hy) - ((dx * dy) * hx)) + (dy * hz)) / (n * t));
    const auto hn = ((hz - ((dx * hx) + (dy * hy))) / n);
    const auto lt = ((ux + (dx * uz)) / t);
    const auto lb = (((((1.0f + (dx * dx)) * uy) - ((dx * dy) * ux)) + (dy * uz)) / (n * t));
    const auto vt = (dx / t);
    const auto vb = (dy / (n * t));
    const auto amount = tex_min(0.9f, sqrt(((axis_x * axis_x) + (axis_y * axis_y))));
    const auto au = fin_alpha_u(roughness, amount);
    const auto av = fin_alpha_v(roughness, amount);
    const auto au2 = (au * au);
    const auto av2 = (av * av);
    const auto q = (fin_quadratic(ht, hb, (1.0f / au2), (1.0f / av2), axis_x, axis_y) + (hn * hn));
    const auto d = (1.0f / ((3.141592653589793f * (au * av)) * (q * q)));
    const auto lambda_l = (0.5f * (sqrt((1.0f + (fin_quadratic(lt, lb, au2, av2, axis_x, axis_y) / tex_max(0.000001f, (nl * nl))))) - 1.0f));
    const auto lambda_v = (0.5f * (sqrt((1.0f + (fin_quadratic(vt, vb, au2, av2, axis_x, axis_y) / (nv * nv)))) - 1.0f));
    const auto g = (1.0f / (1.0f + (lambda_l + lambda_v)));
    return ((nl <= 0.0f) ? 0.0f : ((3.141592653589793f * (d * g)) / (4.0f * nv)));
}
inline float fin_fresnel(float lx, float ly, float lz) {
    const auto length = sqrt(((lx * lx) + ((ly * ly) + (lz * lz))));
    const auto cosine = sqrt((0.5f * (1.0f + (lz / length))));
    const auto f = (1.0f - cosine);
    const auto f2 = (f * f);
    return ((f2 * f2) * f);
}
inline float fin_sheen(float dx, float dy, float lx, float ly, float lz, float roughness, float axis_x, float axis_y) {
    const auto n = sqrt((1.0f + ((dx * dx) + (dy * dy))));
    const auto length = sqrt(((lx * lx) + ((ly * ly) + (lz * lz))));
    const auto ux = (lx / length);
    const auto uy = (ly / length);
    const auto uz = (lz / length);
    const auto nl = ((uz - ((dx * ux) + (dy * uy))) / n);
    const auto nv = (1.0f / n);
    const auto hl = sqrt(((ux * ux) + ((uy * uy) + ((uz + 1.0f) * (uz + 1.0f)))));
    const auto hn = (((uz + 1.0f) - ((dx * ux) + (dy * uy))) / (n * hl));
    const auto inverse = (1.0f / tex_max(0.12f, roughness));
    const auto d = (((2.0f + inverse) * pow(tex_max(0.0f, (1.0f - (hn * hn))), (0.5f * inverse))) / 6.283185307179586f);
    const auto horizontal = ((ux * ux) + (uy * uy));
    const auto directional = (1.0f + (((axis_x * ((ux * ux) - (uy * uy))) + ((2.0f * axis_y) * (ux * uy))) / tex_max(0.000001f, horizontal)));
    const auto visibility = (1.0f / tex_max(0.00001f, (4.0f * ((nl + nv) - (nl * nv)))));
    return ((nl <= 0.0f) ? 0.0f : (3.141592653589793f * ((d * visibility) * (nl * directional))));
}
inline float fin_base(float specular, float metallic, float sheen) {
    return ((1.0f - (0.04f * specular)) * ((1.0f - (0.75f * (metallic * specular))) * (1.0f - (0.45f * sheen))));
}
inline float fin_channel(float pigment, float base, float reflection, float white) {
    const auto diffuse = tex_min(1.0f, tex_max(0.0f, (pigment * base)));
    const auto reflected = tex_max(0.0f, ((pigment * reflection) + white));
    return ((diffuse + reflected) / (1.0f + reflected));
}
// END GENERATED MATERIAL KERNELS

struct PaperParams {
    float light_x, light_y, elevation, depth, grain, scale;
    uint origin_x, origin_y, width, height;
};

inline float height_at(texture2d<float, access::read> heights, int2 p) {
    if (any(p < int2(0)) || any(p >= int2(heights.get_width(), heights.get_height()))) return 0.0f;
    return heights.read(uint2(p)).r * 64.0f;
}

// Only the low 32 bits of b participate in the final hash. Keep a wide until
// its shift, then use unsigned wrapping arithmetic, matching Coil's low bits.
inline float grain_hash(uint x, uint y, uint seed) {
    ulong a = (ulong(x) * 374761393ul) ^ (ulong(y) * 668265263ul) ^ (ulong(seed) * 1274126177ul);
    uint b = uint(a ^ (a >> 13)) * 1274126177u;
    return float((b ^ (b >> 16)) & 65535u) / 65535.0f - 0.5f;
}

kernel void prepare_paper(texture2d<float, access::read> heights [[texture(1)]],
                          texture2d<float, access::read> materials [[texture(2)]],
                          texture2d<float, access::read> micro [[texture(7)]],
                          texture2d<uint, access::write> prepared [[texture(4)]],
                          constant PaperParams& p [[buffer(0)]], uint2 tid [[thread_position_in_grid]]) {
    uint2 xy = tid + uint2(p.origin_x, p.origin_y);
    if (any(xy >= uint2(p.width, p.height))) return;
    int2 q = int2(xy);
    float dx = height_at(heights, q + int2(1,0)) - height_at(heights, q - int2(1,0));
    float dy = height_at(heights, q + int2(0,1)) - height_at(heights, q - int2(0,1));
    float3 material = materials.read(xy).rgb;
    uint seed = uint(round(material.b * 255.0f));
    float pulp = grain_hash(xy.x, xy.y, seed);
    float strands = grain_hash(xy.x / 7, xy.y, seed);
    float cloud = grain_hash(xy.x / 37, xy.y / 37, seed);
    float3 detail = micro.read(xy).xyz;
    float texture = detail.z + material.r * (pulp * 0.10f + strands * material.g * 0.07f + cloud * 0.018f);
    uint nx = uint(round(dx * (255.0f / 64.0f)) + 255.0f);
    uint ny = uint(round(dy * (255.0f / 64.0f)) + 255.0f);
    uint z = uint(round(heights.read(xy).r * 255.0f));
    prepared.write(uint4(nx | (ny << 9) | (z << 18), as_type<uint>(texture), 0, 0), xy);
}

// A maximum hierarchy conservatively rejects rays that cannot reach higher
// paper. Mip texels contain maxima, never averaged heights.
kernel void height_maximum(texture2d<float, access::read> heights [[texture(1)]],
                           texture2d<float, access::read> previous [[texture(5)]],
                           texture2d<float, access::write> maximum [[texture(6)]],
                           constant uint& level [[buffer(1)]], uint2 xy [[thread_position_in_grid]]) {
    float value = 0.0f;
    if (level == 0) {
        for (uint y = 0; y < 16; ++y)
            for (uint x = 0; x < 16; ++x)
                value = max(value, height_at(heights, int2(xy * 16 + uint2(x,y))) / 64.0f);
    } else {
        uint2 size(previous.get_width(level - 1), previous.get_height(level - 1));
        for (uint y = 0; y < 2; ++y)
            for (uint x = 0; x < 2; ++x) {
                uint2 q = xy * 2 + uint2(x,y);
                if (all(q < size)) value = max(value, previous.read(q, level - 1).r);
            }
    }
    maximum.write(float4(value), xy, level);
}

inline float ray_maximum(texture2d<float, access::read> maximum, float2 start, float2 end) {
    // Include truncation, floating-point boundary rounding, and both endpoints.
    float2 lo = max(min(start, end) - 2.0f, 0.0f) / 16.0f;
    float2 hi = max(max(start, end) + 2.0f, 0.0f) / 16.0f;
    uint level = min(uint(ceil(log2(max(max(hi.x - lo.x, hi.y - lo.y), 1.0f)))), maximum.get_num_mip_levels() - 1);
    uint2 size(maximum.get_width(level), maximum.get_height(level));
    uint2 a = min(uint2(lo / float(1u << level)), size - 1);
    uint2 b = min(uint2(hi / float(1u << level)), size - 1);
    return 64.0f * max(max(maximum.read(a, level).r, maximum.read(b, level).r),
                       max(maximum.read(uint2(a.x,b.y), level).r, maximum.read(uint2(b.x,a.y), level).r));
}

template<bool accelerated>
inline void shade_impl(texture2d<float, access::read> colors,
                        texture2d<float, access::read> heights,
                        texture2d<float, access::write> output,
                        texture2d<uint, access::read> prepared,
                        texture2d<float, access::read> maximum,
                        texture2d<float, access::read> micro,
                        texture2d<float, access::read> finish_shape,
                        texture2d<float, access::read> finish_weight,
                        constant PaperParams& p, uint2 tid) {
    uint2 xy = tid + uint2(p.origin_x, p.origin_y);
    if (any(xy >= uint2(p.width, p.height))) return;
    uint2 packed = prepared.read(xy).rg;
    float4 surface(float(int(packed.x & 511u) - 255) * (64.0f / 255.0f),
                   float(int((packed.x >> 9) & 511u) - 255) * (64.0f / 255.0f),
                   as_type<float>(packed.y), float((packed.x >> 18) & 255u) * (64.0f / 255.0f));
    float z = surface.w * p.depth;
    float2 light = float2(p.light_x, p.light_y) - float2(xy) / p.scale;
    float horizontal = sqrt(dot(light, light) + 0.001f);
    float norm = sqrt(horizontal * horizontal + p.elevation * p.elevation);
    float2 direction = light / horizontal;
    float slope = p.elevation / horizontal;
    float reach = clamp(64.0f * p.depth / slope, 1.0f, 180.0f);
    float visibility = 1.0f;
    float minimum_unit = 1.0f;
    float local_max = (accelerated ? ray_maximum(maximum, float2(xy), float2(xy) + direction * (reach + 0.6f) * p.scale) : 64.0f) * p.depth;
    if (local_max > z + 0.125f) {
        for (uint step = 1; step <= 32; ++step) {
            float d = 0.6f + reach * (float(step * step) / 1024.0f);
            float penumbra = 0.75f + d * 0.55f;
            if (slope > 0.55f && z + d * slope - local_max >= penumbra) break;
            int2 sample = int2(float2(xy) + direction * d * p.scale);
            float obstacle = height_at(heights, sample) * p.depth;
            if (obstacle > z + 0.125f) {
                float gap = z + d * slope - obstacle;
                if (accelerated) {
                    // Smoothstep is monotone: reduce its input and evaluate it
                    // once. A sample whose ratio cannot lower the current
                    // minimum needs neither division nor another smoothstep.
                    float numerator = gap + penumbra;
                    float denominator = 2.0f * penumbra;
                    if (numerator <= 0.0f) { minimum_unit = 0.0f; break; }
                    if (numerator <= denominator * minimum_unit)
                        minimum_unit = min(minimum_unit, numerator / denominator);
                } else {
                    float unit = clamp((gap + penumbra) / (2.0f * penumbra), 0.0f, 1.0f);
                    visibility = min(visibility, unit * unit * (3.0f - 2.0f * unit));
                    if (visibility <= 0.0f) break;
                }
            }
        }
    }
    if (accelerated) visibility = minimum_unit * minimum_unit * (3.0f - 2.0f * minimum_unit);
    float2 gradient = surface.xy * p.depth + micro.read(xy).xy * p.grain;
    float n = sqrt(1.0f + dot(gradient, gradient));
    float diffuse = 0.80f + 0.20f * clamp((p.elevation - dot(gradient, light)) / (n * norm), 0.0f, 1.0f);
    float shade = 1.07f * (diffuse * (0.53f + 0.47f * visibility) + p.grain * surface.z);
    float3 pigment = colors.read(xy).rgb;
    float3 weights = finish_weight.read(xy).rgb;
    float3 radiance = pigment * shade;
    if (weights.x > 0.0f || weights.z > 0.0f) {
        float3 shape = finish_shape.read(xy).rgb;
        float lobe = weights.x > 0.0f ? weights.x * fin_specular(gradient.x, gradient.y, light.x, light.y, p.elevation, shape.x, shape.y, shape.z) : 0.0f;
        float fuzz = weights.z > 0.0f ? weights.z * fin_sheen(gradient.x, gradient.y, light.x, light.y, p.elevation, shape.x, shape.y, shape.z) : 0.0f;
        float fresnel = fin_fresnel(light.x, light.y, p.elevation);
        float dielectric = 0.04f * (1.0f - weights.y);
        float tint = lobe * weights.y * (1.0f - fresnel) + 2.0f * fuzz;
        float white = lobe * (dielectric + (1.0f - dielectric) * fresnel);
        float base = shade * fin_base(weights.x, weights.y, weights.z);
        radiance = float3(fin_channel(pigment.r, base, visibility * tint, visibility * white),
                          fin_channel(pigment.g, base, visibility * tint, visibility * white),
                          fin_channel(pigment.b, base, visibility * tint, visibility * white));
    }
    float3 rgb = floor(clamp(radiance * 255.0f, 0.0f, 255.0f)) / 255.0f;
    output.write(float4(rgb, 1.0f), xy);
}

kernel void shade_paper(texture2d<float, access::read> colors [[texture(0)]],
                        texture2d<float, access::read> heights [[texture(1)]],
                        texture2d<float, access::write> output [[texture(3)]],
                        texture2d<uint, access::read> prepared [[texture(4)]],
                        texture2d<float, access::read> maximum [[texture(5)]],
                        texture2d<float, access::read> micro [[texture(7)]],
                        texture2d<float, access::read> finish_shape [[texture(8)]],
                        texture2d<float, access::read> finish_weight [[texture(9)]],
                        constant PaperParams& p [[buffer(0)]], uint2 tid [[thread_position_in_grid]]) {
    shade_impl<true>(colors, heights, output, prepared, maximum, micro, finish_shape, finish_weight, p, tid);
}
kernel void shade_paper_reference(texture2d<float, access::read> colors [[texture(0)]],
                        texture2d<float, access::read> heights [[texture(1)]],
                        texture2d<float, access::write> output [[texture(3)]],
                        texture2d<uint, access::read> prepared [[texture(4)]],
                        texture2d<float, access::read> maximum [[texture(5)]],
                        texture2d<float, access::read> micro [[texture(7)]],
                        texture2d<float, access::read> finish_shape [[texture(8)]],
                        texture2d<float, access::read> finish_weight [[texture(9)]],
                        constant PaperParams& p [[buffer(0)]], uint2 tid [[thread_position_in_grid]]) {
    shade_impl<false>(colors, heights, output, prepared, maximum, micro, finish_shape, finish_weight, p, tid);
}

struct ScreenVertex { float4 position [[position]]; float2 uv; };
vertex ScreenVertex paper_vertex(uint id [[vertex_id]]) {
    float2 p = float2(id == 1 ? 3.0f : -1.0f, id == 2 ? 3.0f : -1.0f);
    return {float4(p, 0.0f, 1.0f), float2((p.x + 1.0f) * 0.5f, (1.0f - p.y) * 0.5f)};
}
fragment float4 paper_fragment(ScreenVertex v [[stage_in]], texture2d<float> paper [[texture(0)]]) {
    constexpr sampler filtered(coord::normalized, address::clamp_to_edge, filter::linear);
    return paper.sample(filtered, v.uv);
}

struct MaskDraw { float4 rect; float4 pigment_height; float4 material_kind; float2 canvas; float2 padding; float4 pattern; float4 origin_scale_seed; float4 finish_shape; float4 finish_weight; float4 mask_info; };
// Lossless coverage: constant tiles need no storage, mixed tiles preserve the
// exact original RG8 samples and backing-pixel phase.
inline float2 mask_coverage(float2 uv, constant MaskDraw& d, texture2d<float, access::read> mask) {
    if (d.mask_info.x < 0.5f) {
        uint2 size(mask.get_width(), mask.get_height());
        return mask.read(min(uint2(uv * float2(size)), size - 1)).rg;
    }
    uint2 size = uint2(d.rect.zw);
    uint2 pixel = min(uint2(uv * float2(size)), size - 1);
    uint columns = (size.x + 63) / 64, rows = (size.y + 63) / 64;
    uint tile = (pixel.y / 64) * columns + pixel.x / 64;
    uint2 code = uint2(round(mask.read(uint2(tile % 1024, tile / 1024)).rg * 255.0f));
    uint id = code.x + code.y * 256;
    if (id == 0) return float2(0);
    if (id == 1) return float2(1, 0);
    id -= 2;
    uint header = (columns * rows + 1023) / 1024;
    return mask.read(uint2((id % 16) * 64 + pixel.x % 64,
                           header + (id / 16) * 64 + pixel.y % 64)).rg;
}
struct MaskVertex { float4 position [[position]]; float2 uv; };
vertex MaskVertex mask_vertex(uint id [[vertex_id]], constant MaskDraw& d [[buffer(0)]]) {
    const float2 corners[] = {float2(0,0),float2(1,0),float2(0,1),float2(0,1),float2(1,0),float2(1,1)};
    float2 uv = corners[id];
    float2 xy = d.rect.xy + uv * d.rect.zw;
    return {float4(xy.x / d.canvas.x * 2 - 1, 1 - xy.y / d.canvas.y * 2, d.padding.x, 1), uv};
}
// Only fully opaque paper can hide all six attachments. Ink never occludes
// the height/material buffers; fractional paper coverage must blend normally.
fragment void opaque_fragment(MaskVertex v [[stage_in]], constant MaskDraw& d [[buffer(0)]],
                              texture2d<float, access::read> mask [[texture(0)]]) {
    if (d.material_kind.w > 0.5f || mask_coverage(v.uv, d, mask).r < 1.0f)
        discard_fragment();
}
struct MaskOutput { float4 pigment [[color(0)]]; float4 height [[color(1)]]; float4 material [[color(2)]]; float4 micro [[color(3)]]; float4 finish_shape [[color(4)]]; float4 finish_weight [[color(5)]]; };
// Evaluated before coverage blending: material identities never interpolate at edges.
inline float3 procedural_material_micro(float2 xy, constant MaskDraw& d) {
    long kind = long(d.pattern.x);
    if (kind == 0) return float3(0.0f);
    float c = cos(d.pattern.z), s = sin(d.pattern.z);
    // Normalize the integer pixel origin first: translated sheets sample the
    // exact same grid, without large-world-coordinate cancellation differences.
    float2 origin = d.origin_scale_seed.xy * d.origin_scale_seed.z;
    float2 anchor = floor(origin);
    float2 point = ((xy - anchor) - (origin - anchor)) / d.origin_scale_seed.z;
    float2 uv = float2(c * point.x + s * point.y, c * point.y - s * point.x) / d.pattern.y;
    long seed = long(floor(d.origin_scale_seed.w * 65535.0f + 0.5f));
    float footprint = 1.0f / (d.origin_scale_seed.z * d.pattern.y);
    float step = max(0.25f, footprint * 0.5f);
    float attenuation = 1.0f / max(1.0f, footprint);
    float h = tex_height(kind, uv.x, uv.y, seed);
    float dx = (tex_height(kind, uv.x + step, uv.y, seed) - tex_height(kind, uv.x - step, uv.y, seed)) / (2.0f * step * d.pattern.y);
    float dy = (tex_height(kind, uv.x, uv.y + step, seed) - tex_height(kind, uv.x, uv.y - step, seed)) / (2.0f * step * d.pattern.y);
    return float3(float2(c * dx - s * dy, s * dx + c * dy) * (attenuation * d.pattern.w),
                  attenuation * tex_contrast(kind) * h);
}
kernel void prepare_material_micro(texture2d<float, access::write> output [[texture(0)]],
                                   constant MaskDraw& d [[buffer(0)]], uint2 xy [[thread_position_in_grid]]) {
    if (xy.x >= output.get_width() || xy.y >= output.get_height()) return;
    output.write(float4(procedural_material_micro(d.rect.xy + float2(xy) + 0.5f, d), 1.0f), xy);
}
inline float3 material_micro(float2 xy, constant MaskDraw& d, texture2d<float, access::read> cached) {
    if (d.padding.y > 0.5f) return cached.read(uint2(xy - float2(d.finish_shape.w, d.finish_weight.w))).xyz;
    return procedural_material_micro(xy, d);
}
[[early_fragment_tests]]
fragment MaskOutput mask_fragment(MaskVertex v [[stage_in]], constant MaskDraw& d [[buffer(0)]], texture2d<float, access::read> mask [[texture(0)]], texture2d<float, access::read> micro [[texture(2)]]) {
    float2 coverage = mask_coverage(v.uv, d, mask);
    // Draw kinds: -1 continuous height contour, 0 cut sheet, 1 printed ink.
    float a = coverage.r, b = d.material_kind.w < -0.5f ? 0.0f : coverage.g;
    if (a == 0.0f && b == 0.0f) { discard_fragment(); return {}; }
    float z = clamp(d.pigment_height.w,0.0f,64.0f) / 64.0f;
    float edge = clamp(d.pigment_height.w - 0.7f,0.0f,64.0f) / 64.0f;
    float ha = a * (1-b) + b;
    if (d.material_kind.w > 0.5f) {ha = 0; z = 0; edge = 0; b = 0;}
    return {float4(d.pigment_height.rgb * a,a), float4(z * a * (1-b) + edge*b,0,0,ha),
            float4(d.material_kind.rgb * (d.material_kind.w > 0.5f ? 0.0f : a), d.material_kind.w > 0.5f ? 0.0f : a),
            d.material_kind.w > 0.5f ? float4(0.0f) : float4(material_micro(v.position.xy, d, micro) * a, a),
            d.material_kind.w > 0.5f ? float4(0.0f) : float4(d.finish_shape.rgb * a, a),
            float4(d.material_kind.w > 0.5f ? float3(0.0f) : d.finish_weight.rgb * a, a)};
}

struct ReliefDraw {
    MaskDraw panel, edge, bottom;
    float4 bounds; // logical coordinates
    float4 shape;  // radius, shoulder width/depth, carving depth
    float4 glyph;  // distance texture bounds in backing pixels
    float4 carving; // lip width
};

inline MaskOutput relief_stock(float2 xy, constant MaskDraw& d, float z, float a, texture2d<float, access::read> micro) {
    return {float4(d.pigment_height.rgb * a, a), float4(clamp(z, 0.0f, 64.0f) / 64.0f * a, 0, 0, a),
            float4(d.material_kind.rgb * a, a), float4(material_micro(xy, d, micro) * a, a),
            float4(d.finish_shape.rgb * a, a), float4(d.finish_weight.rgb * a, a)};
}

inline MaskOutput relief_mix(MaskOutput a, MaskOutput b, float t) {
    return {mix(a.pigment,b.pigment,t), mix(a.height,b.height,t), mix(a.material,b.material,t),
            mix(a.micro,b.micro,t), mix(a.finish_shape,b.finish_shape,t), mix(a.finish_weight,b.finish_weight,t)};
}

// One material evaluation for interior pixels; a second only on antialiased
// stock boundaries. Continuous bevel heights feed the shared lighting pass.
[[early_fragment_tests]]
fragment MaskOutput relief_fragment(MaskVertex v [[stage_in]], constant ReliefDraw& d [[buffer(0)]],
        texture2d<float, access::read> mask [[texture(0)]], texture2d<float> sdf [[texture(1)]],
        texture2d<float, access::read> top_micro [[texture(2)]], texture2d<float, access::read> edge_micro [[texture(3)]]) {
    float a = mask_coverage(v.uv, d.panel, mask).r;
    if (a == 0.0f) { discard_fragment(); return {}; }
    float scale = d.panel.origin_scale_seed.z;
    float2 xy = v.position.xy / scale;
    float radius = min(d.shape.x, min(d.bounds.z, d.bounds.w) * 0.5f);
    float2 q = abs(xy - d.bounds.xy - d.bounds.zw * 0.5f) - d.bounds.zw * 0.5f + radius;
    float inside = radius - length(max(q, 0.0f)) - min(max(q.x,q.y), 0.0f);
    float shoulder = clamp(1.0f - inside / max(d.shape.y, 0.0001f), 0.0f, 1.0f);
    float z = d.panel.pigment_height.w - d.shape.z * shoulder * shoulder;
    constexpr sampler filtered(coord::pixel, address::clamp_to_edge, filter::linear);
    float2 gp = v.position.xy - d.glyph.xy;
    float distance = 1.0e6f;
    if (all(gp >= 0.0f) && all(gp < d.glyph.zw)) distance = sdf.sample(filtered, gp).r / scale;
    float lip = clamp(1.0f - distance / max(d.carving.x, 0.0001f), 0.0f, 1.0f);
    z -= min(d.carving.x * 0.4f, d.shape.w) * lip * lip;
    float aa = 1.0f / scale;
    float floorWeight = clamp(0.5f - distance / aa, 0.0f, 1.0f);
    float edgeWeight = max(clamp(0.5f + (d.shape.y - inside) / aa, 0.0f, 1.0f),
                           clamp(0.5f + (d.carving.x - distance) / aa, 0.0f, 1.0f));
    float floorZ = d.panel.pigment_height.w - d.shape.w;
    if (floorWeight >= 1.0f) return relief_stock(v.position.xy, d.bottom, floorZ, a, top_micro);
    MaskOutput surface;
    if (edgeWeight <= 0.0f) surface = relief_stock(v.position.xy, d.panel, z, a, top_micro);
    else if (edgeWeight >= 1.0f) surface = relief_stock(v.position.xy, d.edge, z, a, edge_micro);
    else surface = relief_mix(relief_stock(v.position.xy, d.panel, z, a, top_micro),
                              relief_stock(v.position.xy, d.edge, z, a, edge_micro), edgeWeight);
    if (floorWeight > 0.0f) surface = relief_mix(surface, relief_stock(v.position.xy, d.bottom, floorZ, a, top_micro), floorWeight);
    return surface;
}

// Scissored clear for retained material attachments. All six values exactly
// match the full render-pass clear; blending is disabled for this pipeline.
fragment MaskOutput clear_material_fragment(MaskVertex v [[stage_in]], constant MaskDraw& d [[buffer(0)]]) {
    return {float4(d.pigment_height.rgb, 1.0f), float4(0.0f,0.0f,0.0f,1.0f),
            float4(0.6f,0.4f,0.12f,1.0f), float4(0.0f,0.0f,0.0f,1.0f),
            float4(0.5f,0.0f,0.0f,1.0f), float4(0.0f,0.0f,0.0f,1.0f)};
}
