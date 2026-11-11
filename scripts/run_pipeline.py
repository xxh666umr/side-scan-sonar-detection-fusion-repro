import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""End-to-end fused pipeline: E0 -> KD -> DA -> Robust, with evaluation.

Run after E0 finishes (or pass --skip-e0 to reuse an existing E0 checkpoint).
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = REPO
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
WEIGHTS = os.path.join(ROOT, "weights")
OUT = os.path.join(ROOT, "outputs")
DATA = os.path.join(ROOT, "data")
COCO = os.path.join(REPO, "datasets", "COCO")
BASE = os.path.join(COCO, "SWDD")
DOMAIN = os.path.join(DATA, "SWDD_domain")
ENV = dict(os.environ)
ENV.update({
    "PYTHONPATH": REPO,
    "TMP": os.path.join(ROOT, "tmp3"),
    "TEMP": os.path.join(ROOT, "tmp3"),
    "TORCH_EXTENSIONS_DIR": os.path.join(ROOT, "torch_ext"),
    "PYTHONUNBUFFERED": "1",
})

LOG = None


def _open_log():
    global LOG
    os.makedirs(OUT, exist_ok=True)
    LOG = open(os.path.join(OUT, "pipeline.log"), "a", encoding="utf-8")


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def run(cmd, timeout=None):
    log("RUN " + " ".join('"%s"' % c if " " in c else c for c in cmd))
    p = subprocess.run(cmd, cwd=REPO, env=ENV, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError("command failed (%d): %s" % (p.returncode, cmd))
    return p.returncode


def link_dir(src, dst):
    """Create a junction (fallback: copy)."""
    if os.path.exists(dst):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    r = subprocess.run(["cmd", "/c", "mklink", "/J", dst, src], capture_output=True)
    if r.returncode != 0:
        import shutil
        shutil.copytree(src, dst)


def eval_model(exp_file, ckpt, ann, img_dir, tag, tsize):
    out = os.path.join(OUT, "pred_%s.json" % tag)
    run([PY, "tools/fusion_eval.py", "-f", exp_file, "-c", ckpt,
         "--data_dir", BASE, "--ann", ann, "--img_dir", img_dir,
         "--tsize", str(tsize), "--out", out])
    with open(out + ".summary.json", encoding="utf-8") as f:
        return json.load(f)


def train(exp_file, ckpt, data_dir, expn, epochs, out_log):
    cmd = [PY, "tools/train.py", "-f", exp_file, "-b", "8", "--fp16", "-expn", expn,
           "-o", "data_num_workers", "0", "max_epoch", str(epochs),
           "no_aug_epochs", "5", "eval_interval", "5",
           "data_dir", data_dir]
    if ckpt:
        cmd[4:4] = ["-c", ckpt]
    log("TRAIN %s -> %s (%d epochs)" % (exp_file, expn, epochs))
    with open(out_log, "w", encoding="utf-8") as f:
        p = subprocess.run(cmd, cwd=REPO, env=ENV, stdout=f, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        raise RuntimeError("training failed: %s" % expn)


def best_ckpt(expn):
    p = os.path.join(REPO, "YOLOX_outputs", expn, "best_ckpt.pth")
    if not os.path.exists(p):
        p = os.path.join(REPO, "YOLOX_outputs", expn, "last_epoch_ckpt.pth")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0_ckpt", default="")
    ap.add_argument("--e1_ckpt", default="")
    ap.add_argument("--e2_ckpt", default="")
    ap.add_argument("--stages", default="kd,da,adv")
    ap.add_argument("--epochs", type=int, default=30)
    args = ap.parse_args()

    exp_nano = "exps/swdd/nano_vit.py"
    exp_teacher = "exps/swdd/l_vit.py"
    results = {}

    e0 = args.e0_ckpt or best_ckpt("nano_vit")
    if not os.path.exists(e0):
        raise SystemExit("E0 checkpoint not found: " + e0)
    log("E0 checkpoint: " + e0)

    # ---------- KD stage ----------
    kd_ckpt = args.e1_ckpt or e0
    if "kd" in args.stages and not args.e1_ckpt:
        pseudo_t = os.path.join(OUT, "pseudo_teacher_train.json")
        if not os.path.exists(pseudo_t):
            run([PY, "tools/fusion_predict.py", "-f", exp_teacher,
                 "-c", os.path.join(WEIGHTS, "swdd-L-ViT.pth"),
                 "--img_dir", os.path.join(BASE, "train2017"),
                 "--ann", os.path.join(BASE, "annotations", "instances_train2017.json"),
                 "--out", pseudo_t, "--conf", "0.5", "--tsize", "640"])
        kd_dir = os.path.join(COCO, "SWDD_kd")
        kd_ann = os.path.join(kd_dir, "annotations", "instances_train2017.json")
        run([PY, "tools/fusion_merge.py", "--out_dir", kd_dir, "--out_ann", kd_ann,
             "--link", "--src",
             os.path.join(BASE, "annotations", "instances_train2017.json"),
             os.path.join(BASE, "train2017"), "gt",
             pseudo_t, os.path.join(BASE, "train2017"), "kdt"])
        link_dir(os.path.join(BASE, "val2017"), os.path.join(kd_dir, "val2017"))
        link_dir(os.path.join(BASE, "test2017"), os.path.join(kd_dir, "test2017"))
        for n in ("instances_val2017.json", "instances_test2017.json"):
            import shutil
            shutil.copy2(os.path.join(BASE, "annotations", n),
                         os.path.join(kd_dir, "annotations", n))
        train(exp_nano, e0, kd_dir, "e1_kd", args.epochs,
              os.path.join(OUT, "e1_train.log"))
        kd_ckpt = best_ckpt("e1_kd")
        log("E1 checkpoint: " + kd_ckpt)

    # ---------- DA stage ----------
    da_ckpt = args.e2_ckpt or kd_ckpt
    if "da" in args.stages and not args.e2_ckpt:
        pseudo_s = os.path.join(OUT, "pseudo_student_target.json")
        if not os.path.exists(pseudo_s):
            run([PY, "tools/fusion_predict.py", "-f", exp_nano, "-c", kd_ckpt,
                 "--img_dir", os.path.join(DOMAIN, "target2017"),
                 "--ann", os.path.join(DOMAIN, "annotations", "instances_target2017.json"),
                 "--out", pseudo_s, "--conf", "0.4", "--tsize", "416"])
        da_dir = os.path.join(COCO, "SWDD_da")
        da_ann = os.path.join(da_dir, "annotations", "instances_train2017.json")
        src = [os.path.join(BASE, "annotations", "instances_train2017.json"),
               os.path.join(BASE, "train2017"), "gt"]
        if os.path.exists(os.path.join(OUT, "pseudo_teacher_train.json")):
            src += [os.path.join(OUT, "pseudo_teacher_train.json"),
                    os.path.join(BASE, "train2017"), "kdt"]
        src += [pseudo_s, os.path.join(DOMAIN, "target2017"), "tgt"]
        run([PY, "tools/fusion_merge.py", "--out_dir", da_dir, "--out_ann", da_ann,
             "--link", "--src"] + src)
        link_dir(os.path.join(BASE, "val2017"), os.path.join(da_dir, "val2017"))
        link_dir(os.path.join(BASE, "test2017"), os.path.join(da_dir, "test2017"))
        import shutil
        for n in ("instances_val2017.json", "instances_test2017.json"):
            shutil.copy2(os.path.join(BASE, "annotations", n),
                         os.path.join(da_dir, "annotations", n))
        train(exp_nano, kd_ckpt, da_dir, "e2_da", args.epochs,
              os.path.join(OUT, "e2_train.log"))
        da_ckpt = best_ckpt("e2_da")
        log("E2 checkpoint: " + da_ckpt)

    # ---------- adversarial stage ----------
    adv_ckpt = da_ckpt
    if "adv" in args.stages:
        adv_ann = os.path.join(OUT, "adv_train_ann.json")
        adv_img = os.path.join(OUT, "adv_train_img")
        if not os.path.exists(adv_ann):
            run([PY, "tools/fusion_pgd.py", "-f", exp_nano, "-c", da_ckpt,
                 "--ann", os.path.join(BASE, "annotations", "instances_train2017.json"),
                 "--img_dir", os.path.join(BASE, "train2017"),
                 "--out_ann", adv_ann, "--out_dir", adv_img,
                 "--tsize", "416", "--eps", "8", "--steps", "10"])
        adv_dir = os.path.join(COCO, "SWDD_adv")
        adv_train_ann = os.path.join(adv_dir, "annotations", "instances_train2017.json")
        src = [os.path.join(BASE, "annotations", "instances_train2017.json"),
               os.path.join(BASE, "train2017"), "gt"]
        for name, img_dir, prefix in (("pseudo_teacher_train.json", os.path.join(BASE, "train2017"), "kdt"),
                                      ("pseudo_student_target.json", os.path.join(DOMAIN, "target2017"), "tgt")):
            p = os.path.join(OUT, name)
            if os.path.exists(p):
                src += [p, img_dir, prefix]
        src += [adv_ann, adv_img, "adv"]
        run([PY, "tools/fusion_merge.py", "--out_dir", adv_dir,
             "--out_ann", adv_train_ann, "--link", "--src"] + src)
        link_dir(os.path.join(BASE, "val2017"), os.path.join(adv_dir, "val2017"))
        link_dir(os.path.join(BASE, "test2017"), os.path.join(adv_dir, "test2017"))
        import shutil
        for n in ("instances_val2017.json", "instances_test2017.json"):
            shutil.copy2(os.path.join(BASE, "annotations", n),
                         os.path.join(adv_dir, "annotations", n))
        train(exp_nano, da_ckpt, adv_dir, "e3_final", args.epochs,
              os.path.join(OUT, "e3_train.log"))
        adv_ckpt = best_ckpt("e3_final")
        log("E3 checkpoint: " + adv_ckpt)

    # ---------- evaluation ----------
    models = [("E0", e0), ("E1_kd", kd_ckpt), ("E2_da", da_ckpt), ("E3_final", adv_ckpt)]
    seen = set()
    for name, ckpt in models:
        if ckpt in seen:
            continue
        seen.add(ckpt)
        log("EVAL " + name)
        clean = eval_model(exp_nano, ckpt,
                           os.path.join(BASE, "annotations", "instances_test2017.json"),
                           os.path.join(BASE, "test2017"), name + "_clean", 416)
        shift = eval_model(exp_nano, ckpt,
                           os.path.join(DOMAIN, "annotations", "instances_test_shift.json"),
                           os.path.join(DOMAIN, "test_shift2017"), name + "_shift", 416)
        # PGD test set for this model
        pgd_ann = os.path.join(OUT, "pgd_test_%s.json" % name)
        pgd_img = os.path.join(OUT, "pgd_test_img_%s" % name)
        if not os.path.exists(pgd_ann):
            run([PY, "tools/fusion_pgd.py", "-f", exp_nano, "-c", ckpt,
                 "--ann", os.path.join(BASE, "annotations", "instances_test2017.json"),
                 "--img_dir", os.path.join(BASE, "test2017"),
                 "--out_ann", pgd_ann, "--out_dir", pgd_img,
                 "--tsize", "416", "--eps", "8", "--steps", "10"])
        pgd = eval_model(exp_nano, ckpt, pgd_ann, pgd_img, name + "_pgd", 416)
        results[name] = {"clean": clean, "shift": shift, "pgd": pgd}
        with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    log("ALL DONE. results -> outputs/results.json")
    with open(os.path.join(OUT, "results.md"), "w", encoding="utf-8") as f:
        f.write("| model | clean mAP50 | clean P/R | shift mAP50 | pgd mAP50 |\n")
        f.write("|---|---|---|---|---|\n")
        for name, r in results.items():
            c = r["clean"]
            f.write("| %s | %.4f | %.3f / %.3f | %.4f | %.4f |\n" % (
                name, c["mAP50"], c["precision_bestF1"], c["recall_bestF1"],
                r["shift"]["mAP50"], r["pgd"]["mAP50"]))


if __name__ == "__main__":
    main()
