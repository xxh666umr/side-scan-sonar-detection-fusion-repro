# -*- coding: utf-8 -*-
"""Debug: run the YOLOX trainer step by step with stage prints."""
import argparse
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch  # noqa: E402
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import configure_module  # noqa: E402


def main():
    configure_module()
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", required=True)
    ap.add_argument("-b", type=int, default=8)
    ap.add_argument("--fp16", action="store_true")
    ap.add_argument("--epochs", type=int, default=1)
    args = ap.parse_args()

    print("[debug] exp loading", flush=True)
    exp = get_exp(args.f, None)
    exp.max_epoch = args.epochs
    print("[debug] exp", exp.exp_name, "max_epoch", exp.max_epoch, flush=True)

    class A:
        batch_size = args.b
        fp16 = args.fp16
        occupy = False
        cache = None
        logger = None
        experiment_name = exp.exp_name
        local_rank = 0
        devices = 1

    print("[debug] build trainer", flush=True)
    trainer = exp.get_trainer(A())
    print("[debug] trainer max_epoch", trainer.max_epoch, "file", trainer.file_name, flush=True)
    try:
        trainer.before_train()
        print("[debug] before_train done, iters/epoch", trainer.max_iter, flush=True)
        for epoch in range(trainer.start_epoch, trainer.max_epoch):
            trainer.epoch = epoch
            trainer.before_epoch()
            for it in range(trainer.max_iter):
                trainer.iter = it
                trainer.before_iter()
                trainer.train_one_iter()
                trainer.after_iter()
            trainer.after_epoch()
        print("[debug] training finished", flush=True)
        trainer.after_train()
    except Exception:
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
