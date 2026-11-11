# -*- coding: utf-8 -*-
"""Run a YOLOX model over a folder and dump COCO-format pseudo annotations."""
import argparse
import json
import os
import sys

import cv2
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from yolox.data.data_augment import ValTransform  # noqa: E402
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import postprocess  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--exp_file", required=True)
    ap.add_argument("-c", "--ckpt", required=True)
    ap.add_argument("--img_dir", required=True)
    ap.add_argument("--ann", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--nms", type=float, default=0.65)
    ap.add_argument("--tsize", type=int, default=0)
    ap.add_argument("--score_as_weight", action="store_true")
    args = ap.parse_args()

    exp = get_exp(args.exp_file, None)
    if args.tsize:
        exp.test_size = (args.tsize, args.tsize)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = exp.get_model()
    ckpt = torch.load(args.ckpt, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"] if "model" in ckpt else ckpt)
    model.eval().to(device)
    preproc = ValTransform(legacy=False)

    with open(args.ann, encoding="utf-8") as f:
        src = json.load(f)
    images = []
    anns = []
    for i, info in enumerate(src["images"]):
        img_id = i + 1
        path = os.path.join(args.img_dir, info["file_name"])
        img = cv2.imread(path)
        if img is None:
            continue
        h, w = img.shape[:2]
        ratio = min(exp.test_size[0] / h, exp.test_size[1] / w)
        tensor, _ = preproc(img, None, exp.test_size)
        tensor = torch.from_numpy(tensor).unsqueeze(0).to(device).float()
        with torch.no_grad():
            out = model(tensor)
            out = postprocess(out, exp.num_classes, conf_thre=args.conf, nms_thre=args.nms)[0]
        images.append({"id": img_id, "file_name": info["file_name"], "height": h, "width": w})
        if out is None:
            continue
        b = out[:, :4].clone()
        b[:, 0::2] /= ratio
        b[:, 1::2] /= ratio
        b[:, [0, 2]] = b[:, [0, 2]].clamp(0, w - 1)
        b[:, [1, 3]] = b[:, [1, 3]].clamp(0, h - 1)
        rows = torch.cat([b, out[:, 4:5], out[:, 5:]], 1).cpu().numpy()
        for row in rows:
            x1, y1, x2, y2 = row[:4]
            bw, bh = max(x2 - x1, 1.0), max(y2 - y1, 1.0)
            for c in range(exp.num_classes):
                score = float(row[4] * row[5 + c])
                if score < args.conf:
                    continue
                anns.append({"id": len(anns) + 1, "image_id": img_id, "category_id": c + 1,
                             "bbox": [float(x1), float(y1), float(bw), float(bh)],
                             "area": float(bw * bh), "iscrowd": 0, "score": score})
        if (i + 1) % 50 == 0:
            print("predicted %d/%d" % (i + 1, len(src["images"])), flush=True)

    out = {"info": {"description": "pseudo-labels"}, "licenses": [],
           "images": images, "annotations": anns,
           "categories": src.get("categories", [
               {"id": 1, "name": "wall"}, {"id": 2, "name": "noWall"}])}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print("images", len(images), "pseudo annotations", len(anns), "->", args.out)


if __name__ == "__main__":
    main()
