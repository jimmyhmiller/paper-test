"""Extract nested cut-paper pane contours from the supplied ukiyo-e reference.

Fill text/glyph holes: this asset describes the paper, not its printed contents.
Each stock threshold includes the inner stock, preserving nested sheet topology.
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
    red, green, blue = rgb.transpose(2, 0, 1)
    cream = (red > 155) & (green > 135) & (blue > 85) & (red - green < 50)
    outer = (red > 105) & (red > green * 1.10) & (blue < red * .83)
    middle = (red > 142) & (green > 61) & (blue < red * .78)
    rim = (red > 155) & (green > 110) & (blue > 68) & (red - green < 75)
    regions = [(78, 136, 219, 467), (214, 126, 543, 489),
               (543, 179, 706, 312), (540, 308, 728, 485)]
    # Ownership boundaries prevent nearby clouds or foreground foam, whose
    # colors match the pane stock, from joining a pane through a thin bridge.
    envelopes = [
        [(79, 155), (102, 137), (201, 140), (216, 161), (217, 427),
         (194, 459), (151, 466), (85, 448)],
        [(215, 177), (219, 146), (229, 129), (315, 128), (336, 134),
         (343, 155), (360, 161), (514, 161), (538, 174), (541, 426),
         (530, 463), (503, 480), (425, 488), (357, 479), (302, 482),
         (246, 477), (222, 461), (214, 427)],
        [(545, 222), (550, 194), (565, 182), (679, 182), (703, 202),
         (705, 254), (699, 283), (679, 302), (630, 310), (558, 311), (543, 293)],
        [(543, 330), (555, 309), (704, 309), (727, 332), (727, 472),
         (684, 484), (543, 483)],
    ]
    print('(module paper-scenes.pane-paths)')
    print('(import "paper-scenes.wave-paths" :use [append-contours])')
    print(';;; Closed pane-stock boundaries from the supplied reference; text holes are filled.')
    for pane, (x0, y0, x1, y1) in enumerate(regions):
        ownership = np.zeros_like(red, dtype=np.uint8)
        cv2.fillPoly(ownership, [np.array(envelopes[pane])], 255)
        ownership = ownership[y0:y1, x0:x1]
        inner = cream[y0:y1, x0:x1].astype(np.uint8) * 255 & ownership
        components, _ = cv2.findContours(inner, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        inside = np.zeros_like(inner)
        cv2.drawContours(inside, [max(components, key=cv2.contourArea)], -1, 255, cv2.FILLED)
        for layer in range(3, -1, -1):
            if pane == 0:
                selector = ((red > [115, 139, 160, 175][layer]) &
                            (green > [88, 109, 128, 145][layer]) & (blue < red * .92))
            else:
                selector = [outer, middle, rim, cream][layer]
            mask = selector[y0:y1, x0:x1].astype(np.uint8) * 255 & ownership
            mask |= inside
            components, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contour = max(components, key=cv2.contourArea)
            inside = np.zeros_like(inner)
            cv2.drawContours(inside, [contour], -1, 255, cv2.FILLED)
            # The inner stock contributes to the next outer boundary, so every
            # emitted paper sheet is connected and keeps its printed interior.
            points = cv2.approxPolyDP(contour, .28, True).reshape(-1, 2)
            values = [len(points)]
            for x, y in points:
                values.extend([(int(x) + x0) * 100 + 50, (int(y) + y0) * 100 + 50])
            print(f'(defn pane-{pane}-{layer} [(sx f64) (sy f64)] (-> i64)')
            print('  (let [data [')
            for start in range(0, len(values), 28):
                print('    ' + ' '.join(map(str, values[start:start + 28])))
            print('  ]] (append-contours data sx sy)))')
        # Author offset backing silhouettes at quarter-pixel resolution. The
        # output is one simple native contour, avoiding nested stroke/Boolean
        # decomposition and near-coincident curves in the runtime edge stroke.
        whole = np.zeros((512, 768), np.uint8)
        whole[y0:y1, x0:x1] = inside
        enlarged = cv2.resize(whole, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
        for layer, radius in enumerate([8, 4]):
            diameter = radius * 8 + 1
            offset = cv2.dilate(enlarged, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                                                 (diameter, diameter)))
            contours, _ = cv2.findContours(offset, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            points = cv2.approxPolyDP(max(contours, key=cv2.contourArea), .28 * 4, True).reshape(-1, 2)
            values = [len(points)]
            for x, y in points:
                values.extend([round((float(x) + .5) * 25), round((float(y) + .5) * 25)])
            print(f'(defn backing-{pane}-{layer} [(sx f64) (sy f64)] (-> i64)')
            print('  (let [data [')
            for start in range(0, len(values), 28):
                print('    ' + ' '.join(map(str, values[start:start + 28])))
            print('  ]] (append-contours data sx sy)))')
    print('(defn pane-path [(pane i64) (layer i64) (sx f64) (sy f64)] (-> i64)')
    print('  (case (+ (* pane 4) layer)')
    for pane in range(4):
        for layer in range(4):
            index = pane * 4 + layer
            prefix = f'{index} ' if index != 15 else ''
            print(f'    {prefix}(pane-{pane}-{layer} sx sy)')
    print('  ))')
    print('(defn backing-path [(pane i64) (layer i64) (sx f64) (sy f64)] (-> i64)')
    print('  (case (+ (* pane 2) layer)')
    for pane in range(4):
        for layer in range(2):
            index = pane * 2 + layer
            prefix = f'{index} ' if index != 7 else ''
            print(f'    {prefix}(backing-{pane}-{layer} sx sy)')
    print('  ))')


if __name__ == '__main__':
    main()
