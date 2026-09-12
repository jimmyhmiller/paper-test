"""Author fine printed grain for the ukiyo-e navy backing as native paths.

Exclude stock boundaries and remove broad tone changes before tracing local
grain. Foreground surf has its own artwork; do not extract it a second time.
"""
import argparse

import cv2
import numpy as np

from trace_waves import foreground_ownership


def grain_masks(rgb, foreground):
    red, green, blue = rgb.astype(np.float32).transpose(2, 0, 1)
    support = ((red < 115) & (green > red * 1.08) & (blue > red * 1.10) &
               (foreground == 0)).astype(np.uint8) * 255
    # The mountain and sky have separate artwork. This owns the pane surround.
    support[:125] = 0
    support[:180, 230:] = 0
    gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    # Estimate local tone using only this stock. An ordinary blur mixes cream
    # edges into navy, leaving false dark grain beyond the boundary guard.
    weights = support.astype(np.float32) / 255.0
    local_weight = cv2.GaussianBlur(weights, (0, 0), 1.5)
    local_tone = (cv2.GaussianBlur(gray * weights, (0, 0), 1.5) /
                  np.maximum(local_weight, 1e-6))
    support = cv2.erode(support, np.ones((5, 5), np.uint8)) != 0
    residual = gray - local_tone
    return [((residual > 3.5) & support).astype(np.uint8) * 255,
            ((residual < -3.5) & support).astype(np.uint8) * 255]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference')
    args = parser.parse_args()
    source = cv2.imread(args.reference)
    if source is None or source.shape[:2] != (1024, 1536):
        parser.error('expected the supplied 1536 × 1024 collage')
    rgb = cv2.cvtColor(source[:512, 768:], cv2.COLOR_BGR2RGB)
    print('(module paper-scenes.navy-paths)')
    print('(import "paper-scenes.wave-paths" :use [append-contours])')
    print(';;; Fine printed stock grain; broad reference shading is excluded.')
    for which, mask in enumerate(grain_masks(rgb, foreground_ownership())):
        level = (cv2.resize(mask, None, fx=4, fy=4, interpolation=cv2.INTER_LINEAR) > 127).astype(np.uint8) * 255
        contours, _ = cv2.findContours(level, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        values = []
        for contour in contours:
            if cv2.contourArea(contour) < 4:
                continue
            points = cv2.approxPolyDP(contour, .65, True).reshape(-1, 2)
            if len(points) < 3:
                continue
            values.append(len(points))
            for x, y in points:
                values.extend([round((float(x) + .5) * 25), round((float(y) + .5) * 25)])
        print(f'(defn grain-{which} [(sx f64) (sy f64)] (-> i64)')
        print('  (let [data [')
        for start in range(0, len(values), 28):
            print('    ' + ' '.join(map(str, values[start:start + 28])))
        print('  ]] (append-contours data sx sy)))')
    print('(defn grain-path [(which i64) (sx f64) (sy f64)] (-> i64)')
    print('  (if (= which 0) (grain-0 sx sy) (grain-1 sx sy)))')


if __name__ == '__main__':
    main()
