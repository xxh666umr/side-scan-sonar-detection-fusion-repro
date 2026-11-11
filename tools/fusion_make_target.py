import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Create a simulated SSS target domain (domain shift) and shifted test split.

Domain shift simulates a different sonar setup/water condition: stronger speckle,
contrast change, blur, horizontal dropout lines and illumination gradient.
"""
import argparse
import json
import os

import cv2
import numpy as np

SWDD = _os.path.join(REPO, "data", "SWDD")
OUT = _os.path.join(REPO, "data", "SWDD_domain")


def shift(img, rng):
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = img.shape[:2]
    x = img.astype(np.float32)
    # illumination gradient
    grad = np.linspace(1.15, 0.85, w)[None, :]
    x = x * grad
    # contrast / brightness
    x = (x - 128.0) * rng.uniform(0.75, 1.15) + 128.0 + rng.uniform(-20, 20)
    # speckle noise
    x = x + x * rng.normal(0, 0.12, size=x.shape).astype(np.float32)
    x = np.clip(x, 0, 255).astype(np.uint8)
    # blur
    k = rng.choice([3, 5])
    x = cv2.GaussianBlur(x, (k, k), 0)
    # horizontal dropout lines (transducer leaving water)
    n_lines = rng.integers(0, 5)
    for _ in range(n_lines):
        y = rng.integers(0, h - 3)
        t = rng.integers(1, 4)
        x[y:y + t, :] = 0
    # grayscale -> 3ch
    if x.ndim == 2:
        x = cv2.cvtColor(x, cv2.COLOR_GRAY2BGR)
    return x


def copy_ann(src_json, dst_json, name_map):
    with open(src_json, encoding="utf-8") as f:
        d = json.load(f)
    id_map = {}
    images = []
    for i, img in enumerate(d["images"]):
        new_id = i + 1
        id_map[img["id"]] = new_id
        images.append({"id": new_id, "file_name": img["file_name"],
                       "height": img["height"], "width": img["width"]})
    anns = []
    for a in d["annotations"]:
        b = dict(a)
        b["id"] = len(anns) + 1
        b["image_id"] = id_map[a["image_id"]]
        anns.append(b)
    out = {"info": {}, "licenses": [], "images": images,
           "annotations": anns, "categories": d["categories"]}
    if name_map is not None:
        for img in out["images"]:
            img["file_name"] = name_map(img["file_name"])
    with open(dst_json, "w", encoding="utf-8") as f:
        json.dump(out, f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    os.makedirs(OUT, exist_ok=True)

    for name in ("target2017", "test_shift2017"):
        os.makedirs(os.path.join(OUT, name), exist_ok=True)
    os.makedirs(os.path.join(OUT, "annotations"), exist_ok=True)

    # target domain = shifted val + test images (unlabeled)
    target_images = []
    for split in ("val2017", "test2017"):
        src_dir = os.path.join(SWDD, split)
        for fn in sorted(os.listdir(src_dir)):
            if not fn.lower().endswith(".png"):
                continue
            img = cv2.imread(os.path.join(src_dir, fn))
            cv2.imwrite(os.path.join(OUT, "target2017", fn), shift(img, rng))
            target_images.append({"id": len(target_images) + 1, "file_name": fn,
                                  "height": img.shape[0], "width": img.shape[1]})
    target_ann = {"info": {}, "licenses": [], "images": target_images,
                  "annotations": [], "categories": [
                      {"id": 1, "name": "wall"}, {"id": 2, "name": "noWall"}]}
    with open(os.path.join(OUT, "annotations", "instances_target2017.json"), "w", encoding="utf-8") as f:
        json.dump(target_ann, f)
    print("target images:", len(target_images))

    # shifted test = shifted test images with GT copied
    for fn in sorted(os.listdir(os.path.join(SWDD, "test2017"))):
        if not fn.lower().endswith(".png"):
            continue
        img = cv2.imread(os.path.join(SWDD, "test2017", fn))
        cv2.imwrite(os.path.join(OUT, "test_shift2017", fn), shift(img, rng))
    copy_ann(os.path.join(SWDD, "annotations", "instances_test2017.json"),
             os.path.join(OUT, "annotations", "instances_test_shift.json"), None)
    print("shifted test written")


if __name__ == "__main__":
    main()
