"""Extract editable wave ink contours from the user-supplied ukiyo-e reference.

This produces Coil vector source, not a flattened image. The semantic foreground
regions exclude editor text, the sign and frame. Review regenerated paths against
the reference; threshold selection belongs to this specific source artwork.
"""
import argparse
import cv2
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference")
    args = parser.parse_args()
    image = cv2.imread(args.reference)
    if image is None or image.shape[:2] != (1024, 1536):
        parser.error("expected the supplied 1536 × 1024 four-scene collage")
    rgb = cv2.cvtColor(image[:512, 768:], cv2.COLOR_BGR2RGB).astype(np.float32)
    left = [(68, 412), (81, 399), (100, 407), (114, 429), (137, 432),
            (154, 446), (176, 463), (197, 462), (219, 489), (237, 506),
            (267, 511), (69, 511)]
    right = [(381, 511), (409, 494), (432, 470), (451, 462), (473, 466),
             (486, 477), (507, 470), (531, 447), (554, 427), (577, 422),
             (600, 427), (619, 432), (639, 418), (658, 402), (674, 376),
             (694, 361), (712, 357), (731, 346), (750, 352), (767, 341), (767, 511)]
    roi = np.zeros((512, 768), np.uint8)
    cv2.fillPoly(roi, [np.array(left), np.array(right)], 255)
    red, green, blue = rgb.transpose(2, 0, 1)
    ink = ((red < 139) & (blue > red * 1.05) & (green > red * 1.04) & (roi != 0)).astype(np.uint8) * 255
    print('(module paper-scenes.wave-paths)')
    print('(import "paper.surface" :use [move-to curve-to close-path])')
    print(';;; Traced native contours from the supplied ukiyo-e foreground, in 768 × 512 reference coordinates.')
    print(';;; No source pixels or baked lighting enter the renderer. Includes foam counters and spray islands.')
    print('''(defn append-contours [(data (slice i64)) (sx f64) (sy f64)] (-> i64)
  (let [(mut cursor) 0]
    (while (< (load cursor) (len data))
      (let [count (get data (load cursor)) start (+ (load cursor) 1)]
        (for [i 0 count]
          (let [previous (+ start (* (% (+ i (- count 1)) count) 2))
                current (+ start (* i 2)) next (+ start (* (% (+ i 1) count) 2))
                px (* 0.01 (cast f64 (get data previous))) py (* 0.01 (cast f64 (get data (+ previous 1))))
                x (* 0.01 (cast f64 (get data current))) y (* 0.01 (cast f64 (get data (+ current 1))))
                nx (* 0.01 (cast f64 (get data next))) ny (* 0.01 (cast f64 (get data (+ next 1))))
                ax (* 0.5 (+ px x)) ay (* 0.5 (+ py y))
                bx (* 0.5 (+ x nx)) by (* 0.5 (+ y ny))]
            (when (= i 0) (move-to (* ax sx) (* ay sy)))
            (curve-to (* (+ ax (* (- x ax) 0.666666667)) sx) (* (+ ay (* (- y ay) 0.666666667)) sy)
                      (* (+ bx (* (- x bx) 0.666666667)) sx) (* (+ by (* (- y by) 0.666666667)) sy)
                      (* bx sx) (* by sy))))
        (close-path) (set! cursor (+ start (* count 2))))))
  0)''')
    gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    interior = cv2.erode(ink, np.ones((3, 3), np.uint8)) != 0
    medium = ((red > 68) & (ink != 0)).astype(np.uint8) * 255
    highlight = ((gray - cv2.GaussianBlur(gray, (0, 0), 2.0) > 7) & interior).astype(np.uint8) * 255
    for name, mask, minimum in [('ink-path', ink, .45), ('mid-path', medium, 1.0), ('line-path', highlight, .8)]:
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        values = []
        kept = 0
        for contour in contours:
            if abs(cv2.contourArea(contour)) < minimum:
                continue
            if name == 'line-path':
                _, _, cw, ch = cv2.boundingRect(contour)
                if max(cw, ch) < 5:
                    continue
            points = cv2.approxPolyDP(contour, 0.26, True).reshape(-1, 2)
            if len(points) < 3:
                continue
            kept += 1
            values.append(len(points))
            for x, y in points:
                values.extend([int(x) * 100 + 50, int(y) * 100 + 50])
        print(f'(defn {name} [(sx f64) (sy f64)] (-> i64)')
        print('  (let [data [')
        for i in range(0, len(values), 28):
            print('    ' + ' '.join(map(str, values[i:i+28])))
        print('  ]] (append-contours data sx sy)))')
        print(f'; {kept} closed contours; topology from source, rounded native quadratic-to-cubic edges.')


if __name__ == '__main__':
    main()
