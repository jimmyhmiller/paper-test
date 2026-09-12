import unittest

import numpy as np

from trace_waves import ink_details


class EngravingSelectionTests(unittest.TestCase):
    def test_one_pixel_light_cut_survives_missing_blue_pigment(self):
        rgb = np.full((40, 40, 3), [25, 60, 77], np.uint8)
        ink = np.full((40, 40), 255, np.uint8)
        rgb[5:35, 20] = [110, 120, 110]
        ink[5:35, 20] = 0
        details = {name: mask for name, mask, _ in ink_details(rgb, ink)}
        self.assertTrue(np.all(details['line-path'][7:33, 20] == 255))
        self.assertTrue(np.all(details['pale-path'][7:33, 20] == 0))

    def test_broad_cream_opening_is_not_engraving(self):
        rgb = np.full((40, 40, 3), [25, 60, 77], np.uint8)
        ink = np.full((40, 40), 255, np.uint8)
        rgb[10:30, 10:30] = [230, 211, 179]
        ink[10:30, 10:30] = 0
        details = {name: mask for name, mask, _ in ink_details(rgb, ink)}
        for mask in details.values():
            self.assertEqual(np.count_nonzero(mask[10:30, 10:30]), 0)

    def test_uniform_ink_has_no_highlight_ridges(self):
        rgb = np.full((40, 40, 3), [25, 60, 77], np.uint8)
        ink = np.full((40, 40), 255, np.uint8)
        details = {name: mask for name, mask, _ in ink_details(rgb, ink)}
        self.assertEqual(np.count_nonzero(details['line-path']), 0)


if __name__ == '__main__':
    unittest.main()
