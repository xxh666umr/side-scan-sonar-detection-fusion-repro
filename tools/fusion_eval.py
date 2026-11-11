# -*- coding: utf-8 -*-
"""Evaluate a YOLOX checkpoint on a COCO-format split and report P/R/mAP."""
import argparse
import json
import os
import sys

import numpy as np
import torch
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from yolox.data.data_augment import ValTransform  # noqa: E402
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import postprocess  # noqa: E402


def load_model(exp, ckpt_path, device):
    model = exp.get_model()
    model.eval()
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    state = ckpt["model"] if isinstance(ckpt, dict) and "model" in ckpt else ckpt
    model.load_state_dict(state)
    model.to(device)
    return model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--exp_file", required=True)
    ap.add_argument("-c", "--ckpt", required=True)
    ap.add_argument("--data_dir", required=True)
    ap.add_argument("--ann", required=True)
    ap.add_argument("--img_dir", required=True)
    ap.add_argument("--tsize", type=int, default=0)
    ap.add_argument("--conf", type=float, default=0.001)
    ap.add_argument("--nms", type=float, default=0.65)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    exp = get_exp(args.exp_file, None)
    if not os.path.isabs(args.data_dir):
        args.data_dir = os.path.abspath(args.data_dir)
    exp.data_dir = args.data_dir
    if args.tsize:
        exp.test_size = (args.tsize, args.tsize)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = load_model(exp, args.ckpt, device)
    preproc = ValTransform(legacy=False)

    coco = COCO(args.ann)
    img_ids = coco.getImgIds()
    results = []
    for n, img_id in enumerate(img_ids):
        info = coco.loadImgs([img_id])[0]
        path = os.path.join(args.img_dir, info["file_name"])
        from cv2 import imread
        img = imread(path)
        if img is None:
            raise FileNotFoundError(path)
        h, w = img.shape[:2]
        ratio = min(exp.test_size[0] / h, exp.test_size[1] / w)
        tensor, _ = preproc(img, None, exp.test_size)
        tensor = torch.from_numpy(tensor).unsqueeze(0).to(device).float()
        with torch.no_grad():
            out = model(tensor)
            out = postprocess(out, exp.num_classes, conf_thre=args.conf, nms_thre=args.nms)[0]
        if out is not None:
            b = out[:, :4].clone()
            b[:, 0::2] = b[:, 0::2] / ratio
            b[:, 1::2] = b[:, 1::2] / ratio
            for row in torch.cat([b, out[:, 4:5], out[:, 5:]], 1).cpu().numpy():
                x1, y1, x2, y2 = row[:4]
                for c in range(exp.num_classes):
                    score = float(row[4] * row[5 + c])
                    if score >= args.conf:
                        results.append({
                            "image_id": int(img_id),
                            "category_id": c + 1,
                            "bbox": [float(x1), float(y1), float(x2 - x1), float(y2 - y1)],
                            "score": score,
                        })
        if (n + 1) % 50 == 0:
            print("inferred %d/%d" % (n + 1, len(img_ids)), flush=True)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f)
        print("saved predictions", args.out)

    if not results:
        print("no detections")
        return
    dt = coco.loadRes(results)
    ev = COCOeval(coco, dt, "bbox")
    ev.evaluate()
    ev.accumulate()
    ev.summarize()
    prec = ev.eval["precision"]          # (T, R, K, A, M)
    rec = ev.eval["recall"]              # (T, R, K, A, M)
    mAP = float(np.mean(prec[:, :, :, 0, 2]))
    mAP50 = float(np.mean(prec[0, :, :, 0, 2]))
    mAP75 = float(np.mean(prec[5, :, :, 0, 2]))
    recall = float(np.mean(rec[0, :, 0, 2]))

    # precision / recall at best F1 on IoU=0.5 (paper-style OD metrics proxy)
    best_f1, best_p, best_r, best_conf = 0.0, 0.0, 0.0, 0.0
    for conf in np.arange(0.05, 0.96, 0.05):
        keep = [r for r in results if r["score"] >= conf]
        if not keep:
            continue
        dt2 = coco.loadRes(keep)
        ev2 = COCOeval(coco, dt2, "bbox")
        ev2.params.iouThrs = np.array([0.5])
        ev2.params.maxDets = [1, 10, 100]
        ev2.evaluate()
        ev2.accumulate()
        p = float(np.mean(ev2.eval["precision"][0, :, :, 0, 2]))
        r = float(np.mean(ev2.eval["recall"][0, :, 0, 2]))
        f1 = 2 * p * r / max(p + r, 1e-9)
        if f1 > best_f1:
            best_f1, best_p, best_r, best_conf = f1, p, r, float(conf)

    print("\n==== SUMMARY ====")
    print("mAP@0.5:0.95 = %.4f" % mAP)
    print("mAP@0.5      = %.4f" % mAP50)
    print("mAP@0.75     = %.4f" % mAP75)
    print("Recall@0.5   = %.4f" % recall)
    print("BestF1 P/R   = %.4f / %.4f (F1=%.4f @conf=%.2f)" % (best_p, best_r, best_f1, best_conf))
    if args.out:
        summary = {"mAP": mAP, "mAP50": mAP50, "mAP75": mAP75, "recall": recall,
                   "precision_bestF1": best_p, "recall_bestF1": best_r,
                   "f1_best": best_f1, "conf_best": best_conf,
                   "ckpt": args.ckpt, "ann": args.ann}
        with open(args.out + ".summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
