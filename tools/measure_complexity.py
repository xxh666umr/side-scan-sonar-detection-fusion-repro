import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Measure params / FLOPs / latency of the E0 and E3 checkpoints (same architecture)."""
import os
import sys
import time

import torch

sys.path.insert(0, REPO)
from yolox.exp import get_exp  # noqa: E402

WEIGHTS = _os.path.join(REPO, "weights")
OUT = _os.path.join(REPO, "YOLOX_outputs")


def measure(exp_file, ckpt, tsize=416):
    exp = get_exp(exp_file, None)
    exp.test_size = (tsize, tsize)
    model = exp.get_model()
    ckpt_obj = torch.load(ckpt, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt_obj["model"] if "model" in ckpt_obj else ckpt_obj)
    model.eval().cuda()
    params = sum(p.numel() for p in model.parameters())
    x = torch.randn(1, 3, tsize, tsize).cuda()
    with torch.no_grad():
        for _ in range(10):
            model(x)
        torch.cuda.synchronize()
        t0 = time.time()
        n = 100
        for _ in range(n):
            model(x)
        torch.cuda.synchronize()
        ms = (time.time() - t0) * 1000 / n
    return params, ms


def main():
    cases = [
        ("E0（官方 Nano-ViT 权重）", os.path.join(WEIGHTS, "swdd-nano-ViT.pth")),
        ("E3（融合最终模型）", os.path.join(OUT, "e3_final", "best_ckpt.pth")),
        ("E1（+KD）", os.path.join(OUT, "e1_kd", "best_ckpt.pth")),
        ("E2（+DA）", os.path.join(OUT, "e2_da", "best_ckpt.pth")),
    ]
    print("%-28s %12s %12s" % ("模型", "参数量", "延迟(ms/张)"))
    for name, ckpt in cases:
        if not os.path.exists(ckpt):
            print(name, "missing", ckpt)
            continue
        p, ms = measure("exps/swdd/nano_vit.py", ckpt)
        print("%-28s %10.2f M %10.2f ms" % (name, p / 1e6, ms))


if __name__ == "__main__":
    main()
