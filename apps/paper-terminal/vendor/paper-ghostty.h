/* Paper's versioned extension to the pinned Ghostty embedding API. */
#ifndef PAPER_GHOSTTY_H
#define PAPER_GHOSTTY_H
#include "ghostty.h"
typedef struct {
    float light_x, light_y, light_height, raster_scale;
    float terminal_x, terminal_y, relief, paper_fill;
    float bevel, grain, cursor_lift, cursor_fold;
    float cut_paper, gap, thickness, shine;
    float roughness, background_depth, selection_depth, reserved;
} ghostty_paper_material_s;
#ifdef __cplusplus
extern "C" {
#endif
/* Copies the latest material and schedules a frame; never compiles a shader. */
void ghostty_surface_set_paper_material(ghostty_surface_t surface,
                                      const ghostty_paper_material_s *material);
#ifdef __cplusplus
}
#endif
#endif
