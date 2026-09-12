"""Author native bark engraving from the supplied ukiyo-e reference.

Separate wood from navy, cream, and vermilion before removing broad shading.
Runtime clipping confines the marks to the reconstructed branch stock.
"""
import argparse

import cv2
import numpy as np


def bark_masks(rgb):
    red, green, blue = rgb.astype(np.float32).transpose(2, 0, 1)
    wood = ((red < 135) & (red > green + 2) & (blue < red * .9) &
            (green > red * .65)).astype(np.uint8)
    wood[110:, 75:] = 0
    wood[:, 245:] = 0
    wood[325:] = 0
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    weight = wood.astype(np.float32)
    mean = cv2.GaussianBlur(gray * weight, (0, 0), 1.0) / np.maximum(
        cv2.GaussianBlur(weight, (0, 0), 1.0), 1e-6)
    interior = cv2.erode(wood, np.ones((3, 3), np.uint8)) != 0
    residual = gray - mean
    return [((residual > 2) & interior).astype(np.uint8) * 255,
            ((residual < -2) & interior).astype(np.uint8) * 255]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference')
    args = parser.parse_args()
    image = cv2.imread(args.reference)
    if image is None or image.shape[:2] != (1024, 1536):
        parser.error('expected the supplied 1536 x 1024 collage')
    rgb = cv2.cvtColor(image[:512, 768:], cv2.COLOR_BGR2RGB)
    print('(module paper-scenes.bark-paths)')
    print('(import "paper-scenes.wave-paths" :use [append-contours])')
    print(';;; Reference-derived printed bark marks; no baked broad lighting.')
    for tone, mask in enumerate(bark_masks(rgb)):
        enlarged = (cv2.resize(mask, None, fx=4, fy=4, interpolation=cv2.INTER_LINEAR) > 127).astype(np.uint8)
        contours, _ = cv2.findContours(enlarged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
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
        print(f'(defn marks-{tone} [(sx f64) (sy f64)] (-> i64)')
        print('  (let [data [')
        for start in range(0, len(values), 28):
            print('    ' + ' '.join(map(str, values[start:start + 28])))
        print('  ]] (append-contours data sx sy)))')
    print('(defn marks [(tone i64)] (-> i64)')
    print('  (if (= tone 0) (marks-0 1.0 1.0) (marks-1 1.0 1.0)))')


if __name__ == '__main__':
    main()
