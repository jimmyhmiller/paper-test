"""Keep occluded-paper reconstruction separate from the visible cloud ribbon."""
import unittest

import numpy as np

from trace_clouds import header_under_branches


class HeaderStockTest(unittest.TestCase):
    def test_fills_stock_and_removes_branch_shaped_islands(self):
        mask = np.zeros((512, 768), np.uint8)
        mask[41:46, 89:94] = 255
        result = header_under_branches(mask)
        self.assertEqual(result[43, 91], 0)
        for x, y in [(70, 75), (95, 60), (130, 55), (180, 55)]:
            self.assertEqual(result[y, x], 255)

    def test_preserves_the_visible_ribbon_outside_reconstruction(self):
        mask = np.random.default_rng(5).integers(0, 2, (512, 768), dtype=np.uint8) * 255
        original = mask.copy()
        result = header_under_branches(mask)
        np.testing.assert_array_equal(result[85:], original[85:])
        np.testing.assert_array_equal(result[:, 193:], original[:, 193:])
        np.testing.assert_array_equal(mask, original)


if __name__ == '__main__':
    unittest.main()
