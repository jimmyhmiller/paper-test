#include <metal_stdlib>
using namespace metal;

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
    float texture = material.r * (pulp * 0.10f + strands * material.g * 0.07f + cloud * 0.018f);
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
            float penumbra = 0.5f + d * 0.19f;
            if (slope > 0.19f && z + d * slope - local_max >= penumbra) break;
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
    float2 gradient = surface.xy * p.depth;
    float n = sqrt(1.0f + dot(gradient, gradient));
    float diffuse = 0.80f + 0.20f * clamp((p.elevation - dot(gradient, light)) / (n * norm), 0.0f, 1.0f);
    float shade = 1.07f * (diffuse * (0.53f + 0.47f * visibility) + p.grain * surface.z);
    float3 rgb = floor(clamp(colors.read(xy).rgb * (255.0f * shade), 0.0f, 255.0f)) / 255.0f;
    output.write(float4(rgb, 1.0f), xy);
}

kernel void shade_paper(texture2d<float, access::read> colors [[texture(0)]],
                        texture2d<float, access::read> heights [[texture(1)]],
                        texture2d<float, access::write> output [[texture(3)]],
                        texture2d<uint, access::read> prepared [[texture(4)]],
                        texture2d<float, access::read> maximum [[texture(5)]],
                        constant PaperParams& p [[buffer(0)]], uint2 tid [[thread_position_in_grid]]) {
    shade_impl<true>(colors, heights, output, prepared, maximum, p, tid);
}
kernel void shade_paper_reference(texture2d<float, access::read> colors [[texture(0)]],
                        texture2d<float, access::read> heights [[texture(1)]],
                        texture2d<float, access::write> output [[texture(3)]],
                        texture2d<uint, access::read> prepared [[texture(4)]],
                        texture2d<float, access::read> maximum [[texture(5)]],
                        constant PaperParams& p [[buffer(0)]], uint2 tid [[thread_position_in_grid]]) {
    shade_impl<false>(colors, heights, output, prepared, maximum, p, tid);
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

struct MaskDraw { float4 rect; float4 pigment_height; float4 material_kind; float2 canvas; float2 padding; };
struct MaskVertex { float4 position [[position]]; float2 uv; };
vertex MaskVertex mask_vertex(uint id [[vertex_id]], constant MaskDraw& d [[buffer(0)]]) {
    const float2 corners[] = {float2(0,0),float2(1,0),float2(0,1),float2(0,1),float2(1,0),float2(1,1)};
    float2 uv = corners[id];
    float2 xy = d.rect.xy + uv * d.rect.zw;
    return {float4(xy.x / d.canvas.x * 2 - 1, 1 - xy.y / d.canvas.y * 2, 0, 1), uv};
}
struct MaskOutput { float4 pigment [[color(0)]]; float4 height [[color(1)]]; float4 material [[color(2)]]; };
fragment MaskOutput mask_fragment(MaskVertex v [[stage_in]], constant MaskDraw& d [[buffer(0)]], texture2d<float, access::read> mask [[texture(0)]]) {
    uint2 size(mask.get_width(),mask.get_height());
    float2 coverage = mask.read(min(uint2(v.uv * float2(size)), size - 1)).rg;
    float a = coverage.r, b = coverage.g;
    float z = clamp(d.pigment_height.w,0.0f,64.0f) / 64.0f;
    float edge = clamp(d.pigment_height.w - 0.7f,0.0f,64.0f) / 64.0f;
    float ha = a * (1-b) + b;
    if (d.material_kind.w > 0.5f) {ha = 0; z = 0; edge = 0; b = 0;}
    return {float4(d.pigment_height.rgb * a,a), float4(z * a * (1-b) + edge*b,0,0,ha),
            float4(d.material_kind.rgb * (d.material_kind.w > 0.5f ? 0.0f : a), d.material_kind.w > 0.5f ? 0.0f : a)};
}
