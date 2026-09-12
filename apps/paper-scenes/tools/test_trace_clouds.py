"""Keep occluded-paper reconstruction separate from the visible cloud ribbon."""
import unittest

import numpy as np

from trace_clouds import header_under_branches, inner_cloud_face


class HeaderStockTest(unittest.TestCase):
    def test_inner_face_stays_on_stock_and_preserves_openings(self):
        stock = np.zeros((100, 200), np.uint8)
        stock[10:90, 10:190] = 255
        stock[35:65, 60:90] = 0
        original = stock.copy()
        face = inner_cloud_face(stock)
        self.assertTrue(np.all(face <= stock))
        self.assertEqual(face[40, 62], 0)
        self.assertEqual(face[12, 120], 0)
        self.assertEqual(face[13, 120], 255)
        self.assertEqual(face[50, 120], 255)
        np.testing.assert_array_equal(stock, original)

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
