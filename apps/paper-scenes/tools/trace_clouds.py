"""Author native cloud-stock contours from the supplied ukiyo-e reference.

Ownership envelopes separate cloud paper from the similarly colored mountain
sky and editor panes. Printed text and tiny fiber holes are not paper cutouts.
"""
import argparse
import cv2
import numpy as np


def inner_cloud_face(level):
    """Inset a quarter-pixel stock mask by 0.75 reference pixels."""
    return cv2.erode(level, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))


def header_under_branches(mask):
    """Reconstruct the paper edge obscured by flowers, not their silhouettes.

    The visible edge enters at (57, 84), rounds under the cherry branch,
    and joins the unobscured top edge at (192, 49). Keep the rest of the
    reference-derived ribbon untouched. These are authored Bezier controls,
    not a color-based guess at the material behind an occluder.
    """
    result = mask.copy()
    result[:85, :193] = 0
    segments = [((57, 84), (57, 66), (76, 51), (96, 49)),
                ((96, 49), (123, 47), (164, 50), (192, 49))]
    points = []
    for a, b, c, d in segments:
        for t in np.linspace(0, 1, 65):
            u = 1 - t
            points.append(u**3 * np.array(a) + 3*u*u*t * np.array(b) +
                          3*u*t*t * np.array(c) + t**3 * np.array(d))
    points.extend([(192, 84), (57, 84)])
    cv2.fillPoly(result, [np.rint(points).astype(np.int32)], 255)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference")
    args = parser.parse_args()
    source = cv2.imread(args.reference)
    if source is None or source.shape[:2] != (1024, 1536):
        parser.error("expected the supplied 1536 × 1024 collage")
    rgb = cv2.cvtColor(source[:512, 768:], cv2.COLOR_BGR2RGB).astype(np.float32)
    red, green, blue = rgb.transpose(2, 0, 1)
    cream = ((red > 120) & (green > 100) & (blue > 65) &
             (red - green < 48) & (red > green * 1.035) & (green > blue * 1.04))
    envelopes = [
        [(191, 0), (767, 0), (767, 69), (747, 54), (717, 51), (692, 39),
         (658, 28), (625, 24), (600, 17), (549, 14), (511, 14),
         (473, 20), (420, 21), (391, 28), (338, 34), (283, 35),
         (235, 31), (191, 36)],
        [(214, 27), (285, 19), (359, 25), (391, 39), (390, 68),
         (365, 88), (316, 100), (279, 78), (221, 60), (214, 49)],
        [(603, 43), (655, 39), (705, 43), (736, 52), (767, 64),
         (767, 183), (729, 185), (707, 168), (663, 158), (637, 143),
         (634, 116), (615, 91), (590, 73), (585, 52)],
        [(65, 49), (94, 41), (184, 46), (246, 48), (282, 66),
         (305, 89), (331, 100), (354, 118), (387, 127), (452, 137),
         (512, 145), (562, 147), (601, 147), (652, 157), (682, 165),
         (713, 181), (736, 194), (767, 199), (767, 221),
         (741, 209), (715, 192), (682, 181), (643, 175), (601, 174),
         (559, 175), (518, 167), (477, 165), (427, 158), (379, 157),
         (348, 146), (324, 128), (290, 124), (254, 123), (207, 135),
         (151, 138), (72, 141), (55, 129), (55, 82)],
        [(305, 0), (767, 0), (767, 180), (275, 180), (275, 90), (315, 90)],
    ]
    print('(module paper-scenes.cloud-paths)')
    print('(import "paper-scenes.wave-paths" :use [append-contours])')
    print(';;; Native cloud-paper boundaries; source pixels are authoring input only.')
    levels = []
    for which, envelope in enumerate(envelopes):
        ownership = np.zeros((512, 768), np.uint8)
        cv2.fillPoly(ownership, [np.array(envelope)], 255)
        mask = cream.astype(np.uint8) * 255 & ownership
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:
            parser.error(f"no cloud stock found in region {which}")
        for contour, relationship in zip(contours, hierarchy[0]):
            if relationship[3] >= 0:
                if cv2.contourArea(contour) < 12 or which == 3:
                    cv2.drawContours(mask, [contour], -1, 255, cv2.FILLED)
        if which == 3:
            mask = header_under_branches(mask)
        level = (cv2.resize(mask, None, fx=4, fy=4, interpolation=cv2.INTER_LINEAR) > 127).astype(np.uint8) * 255
        levels.append(level)
    # A shallow inner face leaves a narrow exposed stock lip on the top band
    # and the foreground header ribbon. Preserve the original outer silhouettes.
    for which in (0, 3):
        levels.append(inner_cloud_face(levels[which]))
    for which, level in enumerate(levels):
        contours, _ = cv2.findContours(level, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        values = []
        for contour in contours:
            if cv2.contourArea(contour) < 8 * 16:
                continue
            points = cv2.approxPolyDP(contour, .24 * 4, True).reshape(-1, 2)
            if len(points) < 3:
                continue
            values.append(len(points))
            for x, y in points:
                values.extend([round((float(x) + .5) * 25), round((float(y) + .5) * 25)])
        print(f'(defn stock-{which} [(sx f64) (sy f64)] (-> i64)')
        print('  (let [data [')
        for start in range(0, len(values), 28):
            print('    ' + ' '.join(map(str, values[start:start + 28])))
        print('  ]] (append-contours data sx sy)))')
    print('(defn stock-path [(which i64) (sx f64) (sy f64)] (-> i64)')
    print('  (case which 0 (stock-0 sx sy) 1 (stock-1 sx sy) 2 (stock-2 sx sy) 3 (stock-3 sx sy) 4 (stock-4 sx sy) 5 (stock-5 sx sy) (stock-6 sx sy)))')


if __name__ == '__main__':
    main()
