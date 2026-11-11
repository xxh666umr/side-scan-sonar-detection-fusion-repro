# -*- coding: utf-8 -*-
"""Merge several COCO annotation files / image folders into one fused train set."""
import argparse
import json
import os
import shutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--out_ann", required=True)
    ap.add_argument("--src", nargs="+", required=True,
                    help="triples: ann_json img_dir prefix")
    ap.add_argument("--link", action="store_true", help="hardlink images instead of copy")
    args = ap.parse_args()

    img_out = os.path.join(args.out_dir, "train2017")
    os.makedirs(img_out, exist_ok=True)
    os.makedirs(os.path.dirname(args.out_ann), exist_ok=True)

    images, anns, cats = [], [], None
    seen = set()
    for ann_path, img_dir, prefix in zip(args.src[0::3], args.src[1::3], args.src[2::3]):
        with open(ann_path, encoding="utf-8") as f:
            d = json.load(f)
        if cats is None:
            cats = d.get("categories")
        id_map = {}
        for info in d["images"]:
            new_name = prefix + "_" + os.path.basename(info["file_name"])
            dst = os.path.join(img_out, new_name)
            if new_name not in seen:
                src_img = os.path.join(img_dir, info["file_name"])
                if args.link:
                    try:
                        os.link(src_img, dst)
                    except OSError:
                        shutil.copy2(src_img, dst)
                else:
                    shutil.copy2(src_img, dst)
                seen.add(new_name)
            new_id = len(images) + 1
            id_map[info["id"]] = new_id
            images.append({"id": new_id, "file_name": new_name,
                           "height": info.get("height", 640), "width": info.get("width", 640)})
        n = 0
        for a in d.get("annotations", []):
            b = dict(a)
            b["id"] = len(anns) + 1
            b["image_id"] = id_map[a["image_id"]]
            anns.append(b)
            n += 1
        print(prefix, "images:", len(d["images"]), "anns:", n)

    out = {"info": {}, "licenses": [], "images": images, "annotations": anns,
           "categories": cats or [{"id": 1, "name": "wall"}, {"id": 2, "name": "noWall"}]}
    with open(args.out_ann, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print("fused images", len(images), "annotations", len(anns), "->", args.out_ann)


if __name__ == "__main__":
    main()
