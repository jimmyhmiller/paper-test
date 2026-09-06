/* Compile-only ABI audit against the exact vendored Ghostty header. */
#include "ghostty.h"
#include <stddef.h>
_Static_assert(sizeof(ghostty_surface_config_s) == 88, "SurfaceConfig size");
_Static_assert(offsetof(ghostty_surface_config_s, platform) == 8, "platform offset");
_Static_assert(offsetof(ghostty_surface_config_s, userdata) == 16, "userdata offset");
_Static_assert(offsetof(ghostty_surface_config_s, command) == 48, "command offset");
_Static_assert(sizeof(ghostty_input_key_s) == 32, "Key size");
_Static_assert(sizeof(ghostty_runtime_config_s) == 64, "Runtime size");
_Static_assert(sizeof(ghostty_action_s) == 32, "Action size");
_Static_assert(sizeof(ghostty_target_s) == 16, "Target size");
_Static_assert(sizeof(ghostty_surface_size_s) == 20, "SurfaceSize size");
_Static_assert(GHOSTTY_ACTION_NEW_TAB == 2 && GHOSTTY_ACTION_SET_TITLE == 32 && GHOSTTY_ACTION_PWD == 35, "Action tags");
