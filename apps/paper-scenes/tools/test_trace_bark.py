"""Bark engraving excludes other materials and broad constant tones."""
import unittest

import numpy as np

from trace_bark import bark_masks


class BarkTest(unittest.TestCase):
    def test_uniform_wood_does_not_create_marks_at_ownership_edges(self):
        rgb = np.full((512, 768, 3), [80, 65, 45], np.uint8)
        self.assertFalse(any(mask.any() for mask in bark_masks(rgb)))

    def test_marks_stay_in_wood_and_exclude_other_stock(self):
        rgb = np.full((512, 768, 3), [80, 65, 45], np.uint8)
        rgb[130:300:4, :60] = [98, 80, 60]
        rgb[132:300:4, :60] = [65, 51, 37]
        rgb[160:185, :60] = [40, 65, 80]
        rgb[210:230, :60] = [220, 200, 170]
        rgb[260:280, :60] = [120, 55, 35]
        masks = bark_masks(rgb)
        self.assertTrue(all(mask.any() for mask in masks))
        for mask in masks:
            self.assertFalse(mask[160:185].any())
            self.assertFalse(mask[210:230].any())
            self.assertFalse(mask[260:280].any())
            self.assertFalse(mask[110:, 75:].any())


if __name__ == '__main__':
    unittest.main()
