import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Compute Precision / Recall / mAP table (advisor-facing metrics) from saved predictions."""
import json
import os

import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

OUT = _os.path.join(REPO, "outputs")
GT = _os.path.join(REPO, "datasets", "COCO", "SWDD", "annotations", "instances_test2017.json")

MODELS = [
    ("E0 基线 (Nano-ViT)", "pred_E0_clean.json", "pred_E0_clean.json.summary.json"),
    ("E1 +KD 蒸馏", "pred_E1_kd_clean.json", "pred_E1_kd_clean.json.summary.json"),
    ("E2 +域自适应", "pred_E2_da_clean.json", "pred_E2_da_clean.json.summary.json"),
    ("E3 +对抗重训练 (最终)", "pred_E3_final_clean.json", "pred_E3_final_clean.json.summary.json"),
]


def pr_at(coco, dets, conf):
    keep = [d for d in dets if d["score"] >= conf]
    if not keep:
        return 0.0, 0.0
    dt = coco.loadRes(keep)
    ev = COCOeval(coco, dt, "bbox")
    ev.params.iouThrs = np.array([0.5])
    ev.params.maxDets = [1, 10, 100]
    ev.evaluate()
    ev.accumulate()
    p = float(np.mean(ev.eval["precision"][0, :, :, 0, 2]))
    r = float(np.mean(ev.eval["recall"][0, :, 0, 2]))
    return p, r


def main():
    coco = COCO(GT)
    rows = []
    for name, pred_file, summary_file in MODELS:
        dets = json.load(open(os.path.join(OUT, pred_file), encoding="utf-8"))
        summ = json.load(open(os.path.join(OUT, summary_file), encoding="utf-8"))
        p25, r25 = pr_at(coco, dets, 0.25)
        p50, r50 = pr_at(coco, dets, 0.50)
        rows.append((name, p25, r25, p50, r50, summ["mAP50"], summ["mAP"]))

    md = ["| 模型 | Precision@0.25 | Recall@0.25 | Precision@0.5 | Recall@0.5 | mAP@0.5 | mAP@0.5:0.95 |",
          "|------|---------------|-------------|---------------|------------|---------|--------------|"]
    for r in rows:
        md.append("| %s | %.4f | %.4f | %.4f | %.4f | %.4f | %.4f |" % r)
    text = "\n".join(md)
    print(text)
    with open(os.path.join(OUT, "advisor_metrics.md"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    with open(os.path.join(OUT, "advisor_metrics.csv"), "w", encoding="utf-8") as f:
        f.write("model,precision@0.25,recall@0.25,precision@0.5,recall@0.5,mAP@0.5,mAP@0.5:0.95\n")
        for r in rows:
            f.write("%s,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n" % r)


if __name__ == "__main__":
    main()
