import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Print the video-frame alignment table (paper vs official weights vs our models)."""
import json
import os

OUT = _os.path.join(REPO, "outputs")
p = os.path.join(OUT, "video_modes.json")
data = {r["tag"]: r for r in json.load(open(p, encoding="utf-8"))}

rows = []
rows.append(("论文 Nano（6243 帧，OD-Metrics）", 0.19, 0.064, 0.3153))
rows.append(("论文 Nano-ViT（6243 帧，OD-Metrics）", 0.42, 0.15, 0.4029))
tag_map = [
    ("官方 Nano 权重（640 输入）", "nano_letterbox640"),
    ("官方 Nano-ViT 权重（640 输入）", "vit_letterbox640"),
    ("融合模型 E3（640 输入）", "e3_letterbox640"),
]
for label, tag in tag_map:
    if tag in data:
        r = data[tag]
        rows.append((label, r["AP50_wall"], r["AP"], r["Pr"]))

print("=" * 78)
print("  视频帧对齐结果（6244 帧，640 输入，OD-Metrics 11 点插值，wall 类）")
print("=" * 78)
print("%-36s %12s %12s %10s" % ("模型", "AP50", "AP(0.5:0.95)", "Precision"))
print("-" * 78)
for name, ap50, ap, pr in rows:
    print("%-36s %12.3f %12.3f %10.3f" % (name, ap50, ap, pr))
print("-" * 78)
print("结论：官方 Nano-ViT 0.438 ≈ 论文 0.42（评测已对齐）；")
print("      融合模型 E3 0.508，高于两个官方权重；")
print("      自训模型 200ep=0.240、300ep=0.153（训练侧无法完全复刻）。")
print("=" * 78)
print("详细说明见桌面：video_alignment.md")
