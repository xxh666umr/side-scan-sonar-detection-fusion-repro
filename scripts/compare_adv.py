import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Compare clean vs PGD-adversarial images and save visual diffs."""
import os

import cv2
import numpy as np

ROOT = REPO
OUT = os.path.join(ROOT, "outputs")
DATA = os.path.join(ROOT, "data", "SWDD")
SAVE = os.path.join(ROOT, "outputs", "adv_compare")
os.makedirs(SAVE, exist_ok=True)
TS = 416


def letterbox(img, size=TS):
    h, w = img.shape[:2]
    r = min(size / h, size / w)
    nw, nh = int(round(w * r)), int(round(h * r))
    resized = cv2.resize(img, (nw, nh))
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    canvas[:nh, :nw] = resized
    return canvas


def compare(name, adv_path, clean_path, tag):
    adv = cv2.imread(adv_path)
    clean_src = cv2.imread(clean_path)
    clean = letterbox(clean_src)
    if adv.shape[:2] != clean.shape[:2]:
        adv = cv2.resize(adv, (clean.shape[1], clean.shape[0]))
    diff = cv2.absdiff(adv, clean)
    print("[%s] adv %s clean %s  max=%d mean=%.2f  changed_px=%.1f%%" % (
        tag, adv.shape, clean.shape, int(diff.max()), float(diff.mean()),
        100.0 * float((diff.max(axis=2) > 0).mean())))
    diff_vis = np.clip(diff.astype(np.float32) * 10, 0, 255).astype(np.uint8)
    h, w = clean.shape[:2]
    canvas = np.full((h, w * 3 + 20, 3), 255, dtype=np.uint8)
    canvas[:, :w] = clean
    canvas[:, w + 10:2 * w + 10] = adv
    canvas[:, 2 * w + 20:] = diff_vis
    cv2.putText(canvas, "clean", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(canvas, "PGD adv", (w + 18, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(canvas, "diff x10", (2 * w + 28, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    out = os.path.join(SAVE, "compare_%s.png" % tag)
    cv2.imwrite(out, canvas)
    print("saved", out)


def main():
    # train-side adversarial sample (adv_train_img, generated from E2)
    a = sorted(os.listdir(os.path.join(OUT, "adv_train_img")))[0]
    src = a[4:]  # strip "adv_"
    compare(a, os.path.join(OUT, "adv_train_img", a),
            os.path.join(DATA, "train2017", src), "train")

    # test-side adversarial sample (E3)
    b = sorted(os.listdir(os.path.join(OUT, "pgd_test_img_E3_final")))[0]
    src2 = b[4:]
    compare(b, os.path.join(OUT, "pgd_test_img_E3_final", b),
            os.path.join(DATA, "test2017", src2), "test")


if __name__ == "__main__":
    main()
