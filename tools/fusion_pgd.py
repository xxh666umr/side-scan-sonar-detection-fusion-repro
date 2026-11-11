# -*- coding: utf-8 -*-
"""Generate PGD adversarial SSS images with clean labels (ROSAR-style retraining data)."""
import argparse
import json
import os
import sys

import cv2
import numpy as np
import torch
from torch.nn import functional as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from yolox.data.data_augment import ValTransform  # noqa: E402
from yolox.exp import get_exp  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--exp_file", required=True)
    ap.add_argument("-c", "--ckpt", required=True)
    ap.add_argument("--ann", required=True)
    ap.add_argument("--img_dir", required=True)
    ap.add_argument("--out_ann", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--tsize", type=int, default=0)
    ap.add_argument("--eps", type=float, default=8.0)
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    exp = get_exp(args.exp_file, None)
    if args.tsize:
        exp.test_size = (args.tsize, args.tsize)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = exp.get_model()
    ckpt = torch.load(args.ckpt, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"] if "model" in ckpt else ckpt)
    model.train().to(device)  # training-mode forward is needed to get the detection loss
    for p in model.parameters():
        p.requires_grad = False
    preproc = ValTransform(legacy=False)
    os.makedirs(args.out_dir, exist_ok=True)

    with open(args.ann, encoding="utf-8") as f:
        src = json.load(f)
    cat_by_id = {c["id"]: c for c in src["categories"]}
    anns_by_img = {}
    for a in src["annotations"]:
        anns_by_img.setdefault(a["image_id"], []).append(a)

    images, out_anns = [], []
    imgs = src["images"][: args.limit] if args.limit else src["images"]
    alpha = args.eps / max(args.steps, 1) * 2.5
    for n, info in enumerate(imgs):
        path = os.path.join(args.img_dir, info["file_name"])
        img = cv2.imread(path)
        if img is None:
            continue
        h, w = img.shape[:2]
        ratio = min(exp.test_size[0] / h, exp.test_size[1] / w)
        tensor, _ = preproc(img, None, exp.test_size)
        x = torch.from_numpy(tensor).unsqueeze(0).to(device).float()

        # targets in input-size pixel coords [cls, cx, cy, w, h]
        tgt = []
        for a in anns_by_img.get(info["id"], []):
            bx, by, bw, bh = a["bbox"]
            if bw <= 1 or bh <= 1:
                continue
            tgt.append([a["category_id"] - 1,
                        (bx + bw / 2) * ratio, (by + bh / 2) * ratio,
                        bw * ratio, bh * ratio])
        if not tgt:
            continue
        pad = torch.zeros((120, 5), dtype=torch.float32, device=device)
        t = torch.tensor(tgt, dtype=torch.float32, device=device)
        pad[:min(len(t), 120)] = t[:120]
        targets = pad.unsqueeze(0)
        corner = float(exp.input_size[0])  # unused placeholder

        x_adv = x + torch.empty_like(x).uniform_(-args.eps, args.eps)
        x_adv = x_adv.clamp(0, 255)
        for _ in range(args.steps):
            x_adv.requires_grad_(True)
            out = model(x_adv, targets, [info["file_name"]], exp.test_size)
            loss = out["total_loss"]
            grad = torch.autograd.grad(loss, x_adv)[0]
            x_adv = x_adv.detach() + alpha * grad.sign()
            x_adv = torch.min(torch.max(x_adv, x - args.eps), x + args.eps).clamp(0, 255)

        adv = x_adv.detach().squeeze(0).permute(1, 2, 0).cpu().numpy().astype(np.uint8)
        name = "adv_" + os.path.basename(info["file_name"])
        cv2.imwrite(os.path.join(args.out_dir, name), adv)
        new_id = len(images) + 1
        images.append({"id": new_id, "file_name": name, "height": adv.shape[0], "width": adv.shape[1]})
        for a in anns_by_img.get(info["id"], []):
            bx, by, bw, bh = a["bbox"]
            if bw <= 1 or bh <= 1:
                continue
            b = dict(a)
            b["id"] = len(out_anns) + 1
            b["image_id"] = new_id
            b["bbox"] = [bx * ratio, by * ratio, bw * ratio, bh * ratio]
            b["area"] = b["bbox"][2] * b["bbox"][3]
            out_anns.append(b)
        if (n + 1) % 20 == 0:
            print("attacked %d/%d" % (n + 1, len(imgs)), flush=True)

    out = {"info": {"description": "PGD adversarial set"}, "licenses": [],
           "images": images, "annotations": out_anns,
           "categories": src["categories"]}
    with open(args.out_ann, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print("adversarial images", len(images), "anns", len(out_anns), "->", args.out_ann)


if __name__ == "__main__":
    main()
