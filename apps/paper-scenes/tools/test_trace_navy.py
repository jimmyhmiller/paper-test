"""Keep backing grain separate from silhouettes and foreground artwork."""
import unittest

import numpy as np

from trace_navy import grain_masks


class NavyGrainTest(unittest.TestCase):
    def test_uniform_stock_and_broad_constant_tone_have_no_grain(self):
        rgb = np.full((512, 768, 3), [35, 65, 82], np.uint8)
        masks = grain_masks(rgb, np.zeros((512, 768), np.uint8))
        self.assertFalse(any(mask.any() for mask in masks))

    def test_broad_lighting_gradient_is_not_printed_as_grain(self):
        rgb = np.full((512, 768, 3), [35, 65, 82], np.uint8)
        light = np.rint(12 * np.sin(np.arange(768) * np.pi / 768)).astype(np.uint8)
        rgb += light[None, :, None]
        masks = grain_masks(rgb, np.zeros((512, 768), np.uint8))
        self.assertFalse(any(mask.any() for mask in masks))

    def test_grain_excludes_foreground_and_stock_boundaries(self):
        rgb = np.full((512, 768, 3), [35, 65, 82], np.uint8)
        rgb[200:300:4, 300:500] = [50, 85, 100]
        rgb[200:300:4, 500:600] = [20, 40, 60]
        rgb[180:320, 290:295] = [220, 200, 165]
        foreground = np.zeros((512, 768), np.uint8)
        foreground[:, 450:550] = 255
        masks = grain_masks(rgb, foreground)
        self.assertTrue(all(mask.any() for mask in masks))
        for mask in masks:
            self.assertFalse(mask[:, 450:550].any())
            self.assertFalse(mask[:, 289:297].any())
            self.assertFalse(mask[:180, 230:].any())


if __name__ == '__main__':
    unittest.main()
