"""Author native ink contours from the supplied ukiyo-e mountain vignette.

The semantic region excludes the red sun and UI. Colors select woodblock ink;
cream paper and cut-cloud gaps remain unprinted. Output is editable Coil paths.
"""
import argparse
import cv2
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference")
    args = parser.parse_args()
    source = cv2.imread(args.reference)
    if source is None or source.shape[:2] != (1024, 1536):
        parser.error("expected the supplied 1536 × 1024 collage")
    rgb = cv2.cvtColor(source[:512, 768:], cv2.COLOR_BGR2RGB).astype(np.float32)
    region = np.zeros((512, 768), np.uint8)
    boundary = [(350, 117), (397, 95), (432, 64), (469, 25), (482, 21),
                (491, 26), (501, 22), (531, 58), (557, 79), (589, 98),
                (637, 113), (697, 146), (699, 172), (593, 164),
                (532, 147), (485, 143), (431, 141), (384, 132), (356, 125)]
    cv2.fillPoly(region, [np.array(boundary)], 255)
    red, green, blue = rgb.transpose(2, 0, 1)
    ink = ((region != 0) & (red < 147) & (blue > red * .50) &
           (green > red * .65)).astype(np.uint8) * 255
    mid = ((ink != 0) & (red > 61)).astype(np.uint8) * 255
    gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    grain = ((cv2.erode(ink, np.ones((3, 3), np.uint8)) != 0) &
             (gray - cv2.GaussianBlur(gray, (0, 0), 1.2) > 6)).astype(np.uint8) * 255
    # These are cut stocks, not the disconnected marks selected for printed ink.
    # Close fiber-sized pigment breaks and fill interior printing; retain the
    # observed outer contour instead of imposing a polygonal mountain profile.
    below_summit = np.indices(ink.shape)[0] > 94
    blue_stock = ((ink != 0) & below_summit & (red > 53) &
                  (green - red > 14) & (blue - green < 24))
    charcoal_stock = ((ink != 0) & below_summit & (red > 25) &
                      (abs(green - red) < 15) & (blue - green < 7))
    stocks = []
    for name, selection in [('blue-stock-path', blue_stock),
                             ('charcoal-stock-path', charcoal_stock)]:
        connected = cv2.morphologyEx(selection.astype(np.uint8) * 255,
                                    cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        edges, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        stock = np.zeros_like(ink)
        # The two ridge stocks are each one connected piece. Small matching
        # patches elsewhere belong to foreground ink, not additional cut paper.
        if not edges:
            parser.error(f"no ridge stock found for {name}")
        edge = max(edges, key=cv2.contourArea)
        cv2.drawContours(stock, [edge], -1, 255, cv2.FILLED)
        stocks.append((name, stock, 2.0))
    print('(module paper-scenes.mountain-paths)')
    print('(import "paper-scenes.wave-paths" :use [append-contours])')
    print(';;; Native contours of Fuji, summit snow breaks and lower ridges from the supplied reference.')
    for name, mask, minimum in [('ink-path', ink, .2), ('ridge-path', mid, .5),
                                 ('grain-path', grain, .35)] + stocks:
        level_set = (cv2.resize(mask, None, fx=4, fy=4, interpolation=cv2.INTER_LINEAR) > 127).astype(np.uint8) * 255
        contours, _ = cv2.findContours(level_set, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        values = []
        kept = 0
        for contour in contours:
            if abs(cv2.contourArea(contour)) < minimum * 16:
                continue
            points = cv2.approxPolyDP(contour, .18 * 4, True).reshape(-1, 2)
            if len(points) < 3:
                continue
            kept += 1
            values.append(len(points))
            for x, y in points:
                values.extend([round((float(x) + .5) * 25), round((float(y) + .5) * 25)])
        print(f'(defn {name} [(sx f64) (sy f64)] (-> i64)')
        print('  (let [data [')
        for start in range(0, len(values), 28):
            print('    ' + ' '.join(map(str, values[start:start + 28])))
        print('  ]] (append-contours data sx sy)))')
        print(f'; {kept} closed native contours.')


if __name__ == '__main__':
    main()
