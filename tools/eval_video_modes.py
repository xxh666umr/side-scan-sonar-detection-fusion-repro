import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Evaluate YOLOX on video frames with alternative preprocessing modes.

Modes:
  letterbox : keep aspect ratio, pad to square (YOLOX default)
  squash    : direct resize to square (ignore aspect ratio)
"""
import argparse
import glob
import json
import os
import sys

import cv2
import numpy as np
import torch

TOOLS = os.path.join(REPO, "tools")
ODM = _os.path.join(REPO, "third_party", "object_detection_metrics")
OUT = _os.path.join(REPO, "outputs")
sys.path.insert(0, REPO)
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ODM, "lib"))

from Evaluator import MethodAveragePrecision  # noqa: E402
from eval_video_od_metrics import evaluate, load_gt, summarize  # noqa: E402
from yolox.data.data_augment import ValTransform  # noqa: E402
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import postprocess  # noqa: E402


def run_model(exp_file, ckpt, frames_dir, tsize, tag, mode, conf=0.01, nms=0.65):
    cache = os.path.join(OUT, "video_dets_%s_%s_%d.json" % (tag, mode, tsize))
    if os.path.exists(cache):
        print("loading cached", cache, flush=True)
        with open(cache, encoding="utf-8") as f:
            raw = json.load(f)
        return {k: [tuple(r) for r in v] for k, v in raw.items()}, len(raw)

    exp = get_exp(exp_file, None)
    exp.test_size = (tsize, tsize)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = exp.get_model()
    ckpt_obj = torch.load(ckpt, map_location=device, weights_only=False)
    model.load_state_dict(ckpt_obj["model"] if "model" in ckpt_obj else ckpt_obj)
    model.eval().to(device)
    preproc = ValTransform(legacy=False)

    files = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")) +
                   glob.glob(os.path.join(frames_dir, "*.png")))
    dets = {}
    for i, path in enumerate(files):
        name = os.path.splitext(os.path.basename(path))[0]
        img = cv2.imread(path)
        h, w = img.shape[:2]
        if mode == "squash":
            img_in = cv2.resize(img, (tsize, tsize))
            tensor, _ = preproc(img_in, None, (tsize, tsize))
            sx, sy = w / float(tsize), h / float(tsize)
        else:
            ratio = min(tsize / h, tsize / w)
            tensor, _ = preproc(img, None, (tsize, tsize))
            sx = sy = 1.0 / ratio
        tensor = torch.from_numpy(tensor).unsqueeze(0).to(device).float()
        with torch.no_grad():
            out = model(tensor)
            out = postprocess(out, exp.num_classes, conf_thre=conf, nms_thre=nms)[0]
        rows = []
        if out is not None:
            b = out[:, :4].clone()
            b[:, 0::2] *= sx
            b[:, 1::2] *= sy
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--tsize", type=int, default=416)
    ap.add_argument("--mode", default="squash", choices=["letterbox", "squash"])
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    gt = load_gt(_os.path.join(REPO, "data", "SWDD_video", "Ground-Truth", "obj_train_data"),
                 _os.path.join(REPO, "data", "SWDD_video", "Images"))
    dets, n = run_model(args.exp, args.ckpt,
                        _os.path.join(REPO, "data", "SWDD_video", "Images"),
                        args.tsize, args.tag, args.mode)
    method = MethodAveragePrecision.ElevenPointInterpolation
    s50 = summarize(evaluate(gt, dets, 0.5, method))
    aps = [summarize(evaluate(gt, dets, float(i), method))["AP"] for i in np.arange(0.5, 1.0, 0.05)]
    pc = {c["class"]: c["AP"] for c in s50["per_class"]}
    result = {
        "tag": args.tag, "mode": args.mode, "tsize": args.tsize, "frames": n,
        "Pr": s50["Pr"], "Re": s50["Re"], "F1": s50["F1"],
        "AP50": s50["AP"], "AP50_wall": pc.get(0), "AP": float(np.mean(aps)),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    p = os.path.join(OUT, "video_modes.json")
    old = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
    old = [x for x in old if x["tag"] != args.tag] + [result]
    json.dump(old, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("saved", p, flush=True)


if __name__ == "__main__":
    main()
