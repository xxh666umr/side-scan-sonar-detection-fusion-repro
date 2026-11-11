import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Evaluate YOLOX models on the SWDD video frames with the paper's OD-Metrics protocol.

Paper: Aubard et al., KD-YOLOX-ViT (arXiv 2403.09313); Table 1 was computed on the 6243
frames extracted from the 6:57 survey video using the Object Detection Metrics toolkit.
"""
import argparse
import glob
import json
import os
import sys

import cv2
import numpy as np
import torch

ODM = _os.path.join(REPO, "third_party", "object_detection_metrics")
OUT = _os.path.join(REPO, "outputs")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(ODM, "lib"))

from BoundingBox import BoundingBox  # noqa: E402
from BoundingBoxes import BoundingBoxes  # noqa: E402
from Evaluator import Evaluator, MethodAveragePrecision  # noqa: E402
from utils import BBFormat, BBType  # noqa: E402

from yolox.data.data_augment import ValTransform  # noqa: E402
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import postprocess  # noqa: E402


def load_gt(gt_dir, frames_dir):
    sizes = {}
    coco_path = os.path.join(gt_dir, "coco_format.json")
    if os.path.exists(coco_path):
        with open(coco_path, encoding="utf-8") as f:
            coco = json.load(f)
        for im in coco.get("images", []):
            sizes[os.path.splitext(os.path.basename(im["file_name"]))[0]] = (im["width"], im["height"])
    gt = {}
    for txt in glob.glob(os.path.join(gt_dir, "*.txt")):
        name = os.path.splitext(os.path.basename(txt))[0]
        W, H = sizes.get(name, (None, None))
        if W is None:
            continue
        boxes = []
        with open(txt, encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 5:
                    continue
                c, cx, cy, w, h = parts[:5]
                cx, cy, w, h = map(float, (cx, cy, w, h))
                boxes.append((int(float(c)),
                              (cx - w / 2) * W, (cy - h / 2) * H,
                              (cx + w / 2) * W, (cy + h / 2) * H))
        gt[name] = boxes
    return gt


def run_model(exp_file, ckpt, frames_dir, tsize, tag, conf=0.01, nms=0.65):
    cache = os.path.join(OUT, "video_dets_%s.json" % tag)
    if os.path.exists(cache):
        print("loading cached detections", cache, flush=True)
        with open(cache, encoding="utf-8") as f:
            raw = json.load(f)
        dets = {}
        for name, rows in raw.items():
            dets[name] = [tuple(r) for r in rows]
        return dets, len(dets)

    exp = get_exp(exp_file, None)
    exp.test_size = (tsize, tsize)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = exp.get_model()
    ckpt_obj = torch.load(ckpt, map_location=device, weights_only=False)
    model.load_state_dict(ckpt_obj["model"] if "model" in ckpt_obj else ckpt_obj)
    model.eval().to(device)
    preproc = ValTransform(legacy=False)

    dets = {}
    files = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")) +
                   glob.glob(os.path.join(frames_dir, "*.png")))
    for i, path in enumerate(files):
        name = os.path.splitext(os.path.basename(path))[0]
        img = cv2.imread(path)
        h, w = img.shape[:2]
        ratio = min(tsize / h, tsize / w)
        tensor, _ = preproc(img, None, (tsize, tsize))
        tensor = torch.from_numpy(tensor).unsqueeze(0).to(device).float()
        with torch.no_grad():
            out = model(tensor)
            out = postprocess(out, exp.num_classes, conf_thre=conf, nms_thre=nms)[0]
        rows = []
        if out is not None:
            b = out[:, :4].clone()
            b[:, 0::2] /= ratio
            b[:, 1::2] /= ratio
            arr = torch.cat([b, out[:, 4:5], out[:, 5:]], 1).cpu().numpy()
            for r in arr:
                x1, y1, x2, y2 = r[:4]
                for c in range(exp.num_classes):
                    score = float(r[4] * r[5 + c])
                    rows.append([c, score, float(x1), float(y1), float(x2), float(y2)])
        dets[name] = rows
        if (i + 1) % 1000 == 0:
            print("inferred %d/%d" % (i + 1, len(files)), flush=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(dets, f)
    return dets, len(files)


def evaluate(gt, dets, iou, method=MethodAveragePrecision.EveryPointInterpolation):
    bbs = BoundingBoxes()
    for name, boxes in gt.items():
        for c, x1, y1, x2, y2 in boxes:
            bbs.addBoundingBox(BoundingBox(name, c, x1, y1, x2, y2,
                                           format=BBFormat.XYX2Y2,
                                           bbType=BBType.GroundTruth))
    for name, rows in dets.items():
        for c, score, x1, y1, x2, y2 in rows:
            bbs.addBoundingBox(BoundingBox(name, c, x1, y1, x2, y2,
                                           format=BBFormat.XYX2Y2,
                                           bbType=BBType.Detected,
                                           classConfidence=score))
    ev = Evaluator()
    return ev.GetPascalVOCMetrics(bbs, IOUThreshold=iou, method=method)


def summarize(res):
    aps = [r["AP"] for r in res if np.isfinite(r["AP"]) and r["AP"] > -1]
    ps, rs, f1s = [], [], []
    for r in res:
        if not np.isfinite(r["AP"]) or r["AP"] <= -1:
            continue
        prec = np.asarray(r["precision"], dtype=float)
        rec = np.asarray(r["recall"], dtype=float)
        f1 = 2 * prec * rec / np.maximum(prec + rec, 1e-9)
        if len(f1) == 0 or not np.isfinite(f1).any():
            continue
        k = int(np.nanargmax(f1))
        ps.append(prec[k])
        rs.append(rec[k])
        f1s.append(f1[k])
    return {
        "AP": float(np.mean(aps)) if aps else 0.0,
        "Pr": float(np.mean(ps)) if ps else 0.0,
        "Re": float(np.mean(rs)) if rs else 0.0,
        "F1": float(np.mean(f1s)) if f1s else 0.0,
        "per_class": [{"class": r["class"], "AP": r["AP"]} for r in res],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--frames", default=_os.path.join(REPO, "data", "SWDD_video", "Images"))
    ap.add_argument("--gt", default=_os.path.join(REPO, "data", "SWDD_video", "Ground-Truth", "obj_train_data"))
    ap.add_argument("--tsize", type=int, default=416)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--method", default="every", choices=["every", "11point"])
    ap.add_argument("--out", default=os.path.join(OUT, "video_odmetrics.json"))
    args = ap.parse_args()
    method = (MethodAveragePrecision.EveryPointInterpolation if args.method == "every"
              else MethodAveragePrecision.ElevenPointInterpolation)

    print("loading GT...", flush=True)
    gt = load_gt(args.gt, args.frames)
    print("GT images:", len(gt), flush=True)
    dets, n = run_model(args.exp, args.ckpt, args.frames, args.tsize, args.tag)
    print("frames:", n, flush=True)

    s50 = summarize(evaluate(gt, dets, 0.5, method))
    aps = [summarize(evaluate(gt, dets, float(iou), method))["AP"] for iou in np.arange(0.5, 1.0, 0.05)]
    result = {
        "tag": args.tag,
        "ckpt": args.ckpt,
        "tsize": args.tsize,
        "frames": n,
        "Pr": s50["Pr"],
        "Re": s50["Re"],
        "F1": s50["F1"],
        "AP50": s50["AP"],
        "AP": float(np.mean(aps)),
        "per_class_AP50": s50["per_class"],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)

    old = []
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as f:
            old = json.load(f)
    old = [x for x in old if x.get("tag") != args.tag] + [result]
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(old, f, indent=2, ensure_ascii=False)
    print("saved", args.out, flush=True)


if __name__ == "__main__":
    main()
