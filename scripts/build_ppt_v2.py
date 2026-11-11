import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Build a redesigned (v2) summary deck for the side-scan sonar fusion reproduction."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_ppt as b
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

NAVY, BLUE, LIGHT, PALE = b.NAVY, b.BLUE, b.LIGHT, b.PALE
GRAY, DARK, ORANGE, GREEN, WHITE = b.GRAY, b.DARK, b.ORANGE, b.GREEN, b.WHITE
TEAL = RGBColor(0x0E, 0x6B, 0x6B)
RED = b.RED
SW, SH = b.SW, b.SH

add_rect, add_text, add_table, add_chart = b.add_rect, b.add_text, b.add_table, b.add_chart


def title_v2(slide, title, page, sub=None):
    add_rect(slide, 0, 0, SW, 0.08, fill=NAVY)
    add_rect(slide, 0.55, 0.38, 0.09, 0.62, fill=BLUE)
    add_text(slide, 0.78, 0.3, 10.6, 0.72, [(title, 24, True, NAVY)],
             anchor=MSO_ANCHOR.MIDDLE, margins=(0, 0))
    if sub:
        add_text(slide, 0.8, 1.08, 11.9, 0.38, [(sub, 11.5, False, GRAY)], margins=(0, 0))
    add_text(slide, SW - 1.25, 0.42, 0.9, 0.4, [("%02d" % page, 11, True, RGBColor(0xB0, 0xC4, 0xDA))],
             align=PP_ALIGN.RIGHT, margins=(0, 0))


def footer(slide, page):
    add_rect(slide, 0.55, 7.12, SW - 1.1, 0.01, fill=RGBColor(0xD9, 0xE2, 0xEE))
    add_text(slide, 0.55, 7.16, 9.8, 0.26, [("侧扫声呐目标检测 · 三篇开源论文融合复现", 8.5, False, GRAY)],
             margins=(0, 0))
    add_text(slide, SW - 1.1, 7.16, 0.6, 0.26, [("%02d" % page, 8.5, False, GRAY)],
             align=PP_ALIGN.RIGHT, margins=(0, 0))


def new_slide(prs, title, page, sub=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    title_v2(s, title, page, sub)
    footer(s, page)
    return s


def chip(slide, x, y, w, h, head, body, color=BLUE, head_size=12, body_size=10):
    add_rect(slide, x, y, w, h, fill=PALE, line=LIGHT, radius=True)
    add_rect(slide, x, y, 0.08, h, fill=color)
    add_text(slide, x + 0.18, y + 0.08, w - 0.3, 0.35, [(head, head_size, True, color)])
    add_text(slide, x + 0.18, y + 0.42, w - 0.3, h - 0.5, [(body, body_size, False, DARK)], spacing=1.15)


def main():
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)

    # ---------------- 1 cover ----------------
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(s, 0, 0, SW, SH, fill=NAVY)
    add_rect(s, 0, 6.9, SW, 0.6, fill=RGBColor(0x16, 0x31, 0x4D))
    add_rect(s, 0.0, 0.0, SW, 0.12, fill=BLUE)
    add_text(s, 0.95, 1.55, 11.6, 0.45, [("项目总结汇报  ·  2026.11", 14, False, RGBColor(0x9F, 0xBE, 0xDA))])
    add_text(s, 0.95, 2.05, 11.8, 1.75, [
        ("侧扫声呐图像目标检测", 44, True, WHITE),
        ("三篇开源论文的融合复现与实验验证", 24, False, RGBColor(0xD6, 0xE4, 0xF2)),
    ])
    add_text(s, 0.95, 3.95, 11.6, 0.06, [("", 8, False, BLUE)])
    add_rect(s, 0.98, 4.05, 3.5, 0.05, fill=BLUE)
    chips = [("数据", "SWDD 604 / 130 / 130"), ("任务", "目标检测（2 类）"), ("指标", "P / R / mAP")]
    for i, (h, t) in enumerate(chips):
        x = 0.95 + i * 3.75
        add_rect(s, x, 4.45, 3.45, 1.15, fill=RGBColor(0x24, 0x45, 0x69), line=RGBColor(0x3C, 0x63, 0x8C))
        add_text(s, x + 0.2, 4.55, 3.05, 0.35, [(h, 11, True, RGBColor(0x8F, 0xB6, 0xDA))])
        add_text(s, x + 0.2, 4.92, 3.05, 0.5, [(t, 14, True, WHITE)])
    add_text(s, 0.95, 6.05, 11.5, 0.9, [
        ("汇报人：__________        导师：__________", 13, False, RGBColor(0xBF, 0xD4, 0xEA)),
    ])

    # ---------------- 2 agenda ----------------
    s = new_slide(prs, "汇报提纲", 2)
    agenda = [
        ("01", "任务与三篇论文", "要解决什么问题、为什么选这三篇"),
        ("02", "融合方案", "一个检测器 + 三种能力，E0→E3 训练链"),
        ("03", "实验结果", "主结果、消融趋势、对抗鲁棒性"),
        ("04", "对齐验证与结论", "与原文对齐、全量实测数据、结论与下一步"),
    ]
    for i, (num, head, body) in enumerate(agenda):
        x = 0.7 + (i % 2) * 6.15
        y = 1.55 + (i // 2) * 2.55
        add_rect(s, x, y, 5.9, 2.2, fill=PALE, line=LIGHT, radius=True)
        add_text(s, x + 0.25, y + 0.2, 1.2, 0.6, [(num, 26, True, BLUE)])
        add_text(s, x + 1.35, y + 0.32, 4.3, 0.55, [(head, 19, True, NAVY)])
        add_text(s, x + 1.35, y + 0.95, 4.3, 0.9, [(body, 11.5, False, GRAY)], spacing=1.2)

    # ---------------- 3 task & data ----------------
    s = new_slide(prs, "一、任务与数据：要解决什么问题", 3,
                  "侧扫声呐 = 用声波给海底“拍照”；目标检测 = 在图中框出目标并分类")
    items = [
        ("数据集", "SWDD 公开侧扫声呐数据集", "604 训练 / 130 验证 / 130 测试；640×640；2 类目标"),
        ("任务", "有监督目标检测", "输入声呐图像，输出边界框 + 类别（wall / noWall）"),
        ("指标", "Precision / Recall / mAP", "mAP 与阈值无关，作为主对比口径；另报 P/R"),
    ]
    for i, (h, name, desc) in enumerate(items):
        y = 1.62 + i * 1.42
        add_rect(s, 0.65, y, 7.3, 1.22, fill=PALE, line=LIGHT, radius=True)
        add_rect(s, 0.65, y, 0.1, 1.22, fill=BLUE)
        add_text(s, 0.9, y + 0.1, 1.4, 0.4, [(h, 12, True, BLUE)])
        add_text(s, 2.15, y + 0.1, 5.6, 0.4, [(name, 14, True, NAVY)])
        add_text(s, 2.15, y + 0.55, 5.6, 0.55, [(desc, 10.5, False, GRAY)])
    add_rect(s, 8.25, 1.62, 4.45, 4.2, fill=RGBColor(0xEE, 0xF6, 0xE8),
             line=RGBColor(0xC5, 0xE0, 0xB4), radius=True)
    add_text(s, 8.5, 1.75, 4.0, 0.4, [("三个难点 → 对应三篇论文", 13, True, GREEN)])
    tough = [
        ("噪声强、目标小", "→ 需要更好的检测结构与蒸馏（P1）"),
        ("标注数据少", "→ 需要无监督/伪标签自训练（P2）"),
        ("攻击与干扰下不稳", "→ 需要对抗重训练（P3）"),
    ]
    for i, (a, bt) in enumerate(tough):
        y = 2.3 + i * 1.12
        add_text(s, 8.5, y, 3.95, 0.35, [(a, 11.5, True, DARK)])
        add_text(s, 8.5, y + 0.34, 3.95, 0.6, [(bt, 10, False, GRAY)])

    # ---------------- 4 three papers ----------------
    s = new_slide(prs, "二、三篇开源论文：各补一种能力", 4,
                  "筛选标准：论文 + 代码都开源；三篇分别解决精度、少标注、鲁棒性")
    rows = [
        ["编号", "论文", "发表", "提供的角色", "开源"],
        ["P1", "KD-YOLOX-ViT", "arXiv 2024", "检测器底座 + 蒸馏", "代码 + 数据"],
        ["P2", "DCBD", "Sci Rep 2024", "少标注 + 伪标签自训练", "代码开源"],
        ["P3", "ROSAR", "arXiv 2024", "鲁棒性 + 对抗训练", "代码 + 数据"],
    ]
    add_table(s, 0.65, 1.55, 12.0, 3.2, rows, [0.9, 3.1, 2.1, 4.3, 1.6], font_size=12, header_size=12)
    add_rect(s, 0.65, 5.25, 12.0, 1.15, fill=LIGHT, radius=True)
    add_text(s, 0.9, 5.32, 11.5, 1.0, [
        ("融合思路：P1 做底座（结构 + 蒸馏） → P2 解决“标注少” → P3 解决“噪声/攻击下不稳” → 串成一个检测器。",
         13.5, True, NAVY)], anchor=MSO_ANCHOR.MIDDLE)

    # ---------------- 5 architecture ----------------
    s = new_slide(prs, "三、融合方案：一个检测器 + 三种能力", 5)
    add_rect(s, 4.5, 1.55, 4.3, 4.9, fill=LIGHT, line=BLUE, radius=True)
    add_text(s, 4.65, 1.72, 4.0, 0.4, [("统一检测器", 13.5, True, BLUE)], align=PP_ALIGN.CENTER)
    add_text(s, 4.65, 2.12, 4.0, 0.6, [("YOLOX-Nano-ViT", 24, True, NAVY)], align=PP_ALIGN.CENTER)
    add_text(s, 4.75, 2.95, 3.8, 2.6, [
        ("• 主干：CSPDarknet + ViT 层", 11.5, False, DARK),
        ("• 输出：类别 + 边界框", 11.5, False, DARK),
        ("• 参数量 0.96 M", 11.5, False, DARK),
        ("• 适合嵌入式部署", 11.5, False, DARK),
    ], spacing=1.35)
    mods = [("P1  KD 蒸馏", "教师 L-ViT 伪标签\n→ Nano-ViT 学生", 2.9, BLUE),
            ("P2  无监督域自适应", "目标域图像伪标签\n→ 自训练 + 过滤", 4.15, TEAL),
            ("P3  对抗重训练", "PGD 对抗样本\n→ 加入训练集重训", 5.4, ORANGE)]
    for name, desc, y, color in mods:
        add_rect(s, 0.55, y, 3.6, 1.05, fill=PALE, line=color, radius=True)
        add_text(s, 0.72, y + 0.07, 3.3, 0.35, [(name, 12.5, True, color)])
        add_text(s, 0.72, y + 0.42, 3.3, 0.55, [(desc, 10, False, GRAY)], spacing=1.1)
        add_text(s, 4.17, y + 0.3, 0.35, 0.4, [("→", 14, True, BLUE)])
    add_rect(s, 9.15, 1.55, 3.55, 4.9, fill=NAVY, radius=True)
    add_text(s, 9.35, 1.72, 3.2, 0.4, [("训练链（逐级加模块）", 12, True, RGBColor(0xBF, 0xD4, 0xEA))])
    steps = [("E0", "源域有标注数据（基线）"), ("E1", "+ KD 蒸馏"),
             ("E2", "+ 域自适应"), ("E3", "+ 对抗重训练（最终）")]
    for i, (tag, desc) in enumerate(steps):
        y = 2.25 + i * 1.02
        add_text(s, 9.35, y, 0.6, 0.4, [(tag, 16, True, RGBColor(0xFF, 0xC0, 0x00))])
        add_text(s, 9.95, y + 0.03, 2.6, 0.55, [(desc, 10.5, False, WHITE)], spacing=1.05)
        if i < 3:
            add_text(s, 9.35, y + 0.62, 2.9, 0.25, [("↓", 10, True, RGBColor(0x8F, 0xAA, 0xC8))])

    # ---------------- 6 experiment design ----------------
    s = new_slide(prs, "四、实验设计：三套测试 + 逐级消融", 6)
    add_text(s, 0.65, 1.45, 5.7, 0.4, [("三套测试，考察三种能力", 15, True, NAVY)])
    tests = [("清洁测试集", "原始 test split（130 张）", "基础精度", GREEN),
             ("域偏移测试集", "噪声 / 模糊 / 黑线 / 光照", "泛化能力（P2）", TEAL),
             ("PGD 攻击测试集", "ε=8/255，10 步攻击", "鲁棒性（P3）", ORANGE)]
    for i, (name, desc, tag, color) in enumerate(tests):
        y = 1.95 + i * 0.98
        add_rect(s, 0.65, y, 5.8, 0.82, fill=PALE, line=LIGHT, radius=True)
        add_rect(s, 0.65, y, 0.09, 0.82, fill=color)
        add_text(s, 0.85, y + 0.08, 3.4, 0.35, [(name, 12.5, True, DARK)])
        add_text(s, 0.85, y + 0.44, 3.6, 0.3, [(desc, 10, False, GRAY)])
        add_text(s, 4.6, y + 0.25, 1.7, 0.3, [(tag, 10.5, True, color)], align=PP_ALIGN.RIGHT)
    add_text(s, 0.65, 5.15, 5.8, 1.5, [
        ("评测口径", 13, True, BLUE),
        ("• test split：pycocotools COCO 指标，P/R 另给 0.25 / 0.5 两档", 10, False, GRAY),
        ("• 与原文对齐：6244 帧视频 + 640 输入 + OD-Metrics（11 点插值）", 10, False, GRAY),
    ], spacing=1.25)
    add_rect(s, 6.75, 1.45, 6.0, 5.35, fill=PALE, line=LIGHT, radius=True)
    add_text(s, 7.0, 1.6, 5.5, 0.4, [("逐级消融：同一数据、同一评测", 15, True, NAVY)])
    rows = [
        ["编号", "训练数据 / 方法"],
        ["E0", "源域 GT（604 张），基线"],
        ["E1", "+ 教师 L-ViT 伪标签（KD）"],
        ["E2", "+ 模拟目标域学生伪标签（DA）"],
        ["E3", "+ PGD 对抗样本（Robust，最终）"],
    ]
    add_table(s, 7.0, 2.1, 5.5, 2.75, rows, [1.0, 4.5], font_size=11, header_size=11)
    add_text(s, 7.0, 5.05, 5.5, 1.5, [
        ("为什么这样设计", 12, True, BLUE),
        ("每一步只加一个模块，才能看出 KD / DA / 对抗训练各自的贡献，而不是混在一起。", 10, False, GRAY),
    ], spacing=1.2)

    # ---------------- 7 main results ----------------
    s = new_slide(prs, "五、主结果：test split 上的 P / R / mAP", 7)
    rows = [
        ["模型", "mAP@0.5", "mAP@0.5:0.95", "Recall@0.5", "BestF1 P / R"],
        ["E0 基线", "0.2273", "0.1187", "0.7460", "0.222 / 0.601"],
        ["E1 + KD", "0.2544", "0.1431", "0.8606", "0.236 / 0.697"],
        ["E2 + DA", "0.1567", "0.0702", "0.8591", "0.154 / 0.775"],
        ["E3 + 对抗（最终）", "0.2600", "0.1537", "0.8584", "0.218 / 0.615"],
    ]
    add_table(s, 0.6, 1.5, 7.5, 3.2, rows, [2.4, 1.3, 1.5, 1.2, 1.5], font_size=11, header_size=10.5)
    add_chart(s, 8.3, 1.35, 4.5, 3.5,
              ["E0", "E1", "E2", "E3"],
              [("mAP@0.5", (0.2273, 0.2544, 0.1567, 0.2600))],
              [BLUE], title="mAP@0.5 对比", max_val=0.35)
    add_rect(s, 0.6, 5.0, 12.15, 1.65, fill=LIGHT, radius=True)
    add_text(s, 0.85, 5.1, 11.7, 1.45, [
        ("读表要点", 12.5, True, NAVY),
        ("① mAP 与阈值无关，是主对比口径：E1 提升 +11.9%，E3 最高 0.2600", 10.5, False, DARK),
        ("② P/R 随阈值变化：best-F1 点 E0 0.222/0.601 → E1 0.236/0.697 → E3 0.218/0.615，均在更高水平", 10.5, False, DARK),
        ("③ E2 下降的原因在“域自适应仍有短板”一页说明", 10.5, False, GRAY),
    ], spacing=1.15)

    # ---------------- 8 robustness ----------------
    s = new_slide(prs, "六、鲁棒性：对抗攻击下谁更稳", 8)
    add_chart(s, 0.55, 1.4, 6.1, 4.35,
              ["E0", "E1", "E2", "E3"],
              [("PGD 攻击下 mAP@0.5", (0.0492, 0.0558, 0.0239, 0.1428))],
              [ORANGE], title="PGD 攻击（ε=8/255）下 mAP@0.5", max_val=0.20)
    cards = [
        ("0.049 → 0.143", "对抗攻击下 mAP@0.5 提升约 2.9 倍", ORANGE),
        ("0.227 → 0.260", "清洁集 mAP@0.5 不降反升", BLUE),
        ("+11.9%", "KD 带来的清洁集提升", TEAL),
    ]
    for i, (num, desc, color) in enumerate(cards):
        y = 1.5 + i * 1.55
        add_rect(s, 7.0, y, 5.7, 1.3, fill=PALE, line=LIGHT, radius=True)
        add_text(s, 7.2, y + 0.12, 5.3, 0.55, [(num, 22, True, color)])
        add_text(s, 7.2, y + 0.72, 5.3, 0.5, [(desc, 11, False, DARK)])
    add_text(s, 7.0, 6.15, 5.7, 0.6, [
        ("结论：对抗重训练同时提升鲁棒性与清洁精度，是性价比最高的模块。", 10.5, True, NAVY)])

    # ---------------- 9 alignment ----------------
    s = new_slide(prs, "七、与原文对齐：关键是评测输入尺寸", 9,
                  "用论文同款 6244 帧视频 + OD-Metrics 复评，找到差异根源")
    rows = [
        ["设置", "Nano AP50", "Nano-ViT AP50"],
        ["416 letterbox（默认）", "0.314", "0.193"],
        ["416 直接拉伸", "0.093", "0.172"],
        ["640 letterbox", "0.321", "0.438"],
        ["论文（6243 帧）", "0.19", "0.42"],
    ]
    add_table(s, 0.6, 1.55, 6.2, 2.6, rows, [2.6, 1.8, 1.9], font_size=11, header_size=11)
    add_text(s, 0.6, 4.35, 6.2, 2.3, [
        ("同协议结论", 13, True, NAVY),
        ("• Nano-ViT：0.438 vs 论文 0.42（差约 4%）", 10.5, False, DARK),
        ("• Nano 的 AP 0.064 与论文完全一致", 10.5, False, DARK),
        ("• 416 输入低估约 2 倍 → 640 才是论文口径", 10.5, False, DARK),
        ("• 直接拉伸更差 → 必须保持宽高比", 10.5, False, DARK),
    ], spacing=1.3)
    cards = [
        ("评测已对齐", "官方 Nano-ViT 0.438 ≈ 论文 0.42", GREEN),
        ("训练未复刻", "自训 200ep 0.240 / 300ep 0.153，低于官方 0.438", ORANGE),
    ]
    for i, (head, body, color) in enumerate(cards):
        y = 1.55 + i * 2.2
        add_rect(s, 7.1, y, 5.6, 1.9, fill=PALE, line=color, radius=True)
        add_text(s, 7.3, y + 0.15, 5.2, 0.45, [(head, 15, True, color)])
        add_text(s, 7.3, y + 0.7, 5.2, 1.0, [(body, 11, False, DARK)], spacing=1.25)
    add_text(s, 7.1, 6.05, 5.6, 0.6, [
        ("原因：论文训练配置未公开（COCO 预训练 + 可能的 KD 初始化/低学习率）", 9.5, False, GRAY)])

    # ---------------- 10 full data table ----------------
    s = new_slide(prs, "八、补充实验：2.2GB 视频帧全量实测", 10,
                  "5 个模型 × 3 种预处理/输入 × 10 个 IoU 阈值，全部重跑")
    rows = [
        ["模型", "设置", "AP50(wall)", "AP 0.5:0.95", "Precision"],
        ["论文 Nano", "6243 帧 / OD-Metrics", "0.19", "0.064", "31.5%"],
        ["论文 Nano-ViT", "6243 帧 / OD-Metrics", "0.42", "0.15", "40.3%"],
        ["官方 Nano 权重", "416 letterbox", "0.314", "0.048", "0.453"],
        ["官方 Nano-ViT 权重", "416 letterbox", "0.193", "0.030", "0.349"],
        ["官方 Nano 权重", "640 letterbox", "0.321", "0.064", "0.435"],
        ["官方 Nano-ViT 权重", "640 letterbox", "0.438", "0.093", "0.634"],
        ["自训 Nano-ViT（200 轮）", "640 letterbox", "0.240", "0.045", "0.397"],
        ["自训 Nano-ViT（300 轮 + COCO 预训练）", "640 letterbox", "0.153", "0.027", "0.178"],
        ["融合模型 E3", "640 letterbox", "0.508", "0.102", "0.638"],
    ]
    add_table(s, 0.5, 1.5, 12.3, 4.7, rows, [3.6, 2.4, 1.5, 1.4, 1.3], font_size=10, header_size=10)
    add_text(s, 0.6, 6.35, 12.1, 0.6, [
        ("结论：官方权重 640 下基本复现论文；自训达不到官方（配置未公开）；融合模型 E3 全量实测最高。",
         11.5, True, NAVY)], align=PP_ALIGN.CENTER)

    # ---------------- 11 conclusions ----------------
    s = new_slide(prs, "九、关键结论", 11)
    items = [
        ("① KD 蒸馏有效", "清洁 test mAP@0.5 0.2273 → 0.2544（+11.9%），Recall 0.746 → 0.861"),
        ("② 对抗重训练最划算", "清洁 mAP@0.5 最高 0.2600；PGD 攻击下 0.0492 → 0.1428（约 2.9 倍）"),
        ("③ 域自适应仍有短板", "域偏移提升 +130%，但清洁集下降；需补完整 IDCC / 域判别器或联合训练"),
        ("④ 评测协议已对齐", "官方权重 640 输入 AP50 0.438 vs 论文 0.42；Nano 的 AP 完全一致"),
        ("⑤ 训练侧无法完全复刻", "自训 200ep/300ep 仅 0.240/0.153，论文训练配置未公开"),
        ("⑥ 融合模型效果最好", "同协议下 E3 AP50 0.508，高于两个官方权重"),
    ]
    for i, (head, body) in enumerate(items):
        x = 0.6 + (i % 2) * 6.2
        y = 1.55 + (i // 2) * 1.72
        add_rect(s, x, y, 5.95, 1.5, fill=PALE, line=LIGHT, radius=True)
        add_rect(s, x, y, 0.09, 1.5, fill=BLUE if i < 2 else ORANGE)
        add_text(s, x + 0.22, y + 0.12, 5.5, 0.4, [(head, 13, True, NAVY)])
        add_text(s, x + 0.22, y + 0.58, 5.5, 0.8, [(body, 10, False, GRAY)], spacing=1.2)

    # ---------------- 12 limitations & plan ----------------
    s = new_slide(prs, "十、局限与下一步", 12)
    add_text(s, 0.6, 1.45, 5.9, 0.4, [("当前局限", 15, True, ORANGE)])
    limits = [
        "评测已对齐，但训练配置未公开、无法完全复刻",
        "自训模型（200/300 轮）0.240 / 0.153，低于官方 0.438",
        "DCBD 为方法迁移，非逐行复现",
        "域偏移为人工模拟，非真实组内数据",
        "单卡 8GB，未做多种子重复实验",
    ]
    for i, t in enumerate(limits):
        y = 1.95 + i * 0.82
        add_text(s, 0.6, y, 0.3, 0.4, [("•", 13, True, ORANGE)])
        add_text(s, 0.88, y, 5.5, 0.6, [(t, 10.5, False, DARK)])
    add_text(s, 6.9, 1.45, 5.9, 0.4, [("下一步（与导师讨论）", 15, True, GREEN)])
    plans = [("训练侧对齐（可选）", "低学习率微调 / 向作者索取配置与评测脚本"),
             ("补齐域自适应", "实现 IDCC / 域判别器，或两阶段联合训练"),
             ("接入真实数据", "用组内侧扫数据替换模拟域偏移，重跑 E2/E3"),
             ("扩展实验", "多种子重复 + 更长训练预算")]
    for i, (head, body) in enumerate(plans):
        y = 1.95 + i * 1.1
        add_rect(s, 6.9, y, 5.85, 0.92, fill=RGBColor(0xEE, 0xF6, 0xE8),
                 line=RGBColor(0xC5, 0xE0, 0xB4), radius=True)
        add_text(s, 7.05, y + 0.06, 5.5, 0.32, [(head, 11.5, True, GREEN)])
        add_text(s, 7.05, y + 0.4, 5.5, 0.45, [(body, 9.5, False, GRAY)])

    # ---------------- 13 thanks ----------------
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(s, 0, 0, SW, SH, fill=NAVY)
    add_rect(s, 0, 0, SW, 0.12, fill=BLUE)
    add_text(s, 0.95, 2.6, 11.5, 1.0, [("谢谢，欢迎讨论", 40, True, WHITE)])
    add_text(s, 0.98, 3.75, 11.4, 0.6, [
        ("数据集 / 代码 / 模型权重 / 完整报告均已归档，可现场演示评估流程", 14, False, RGBColor(0xCF, 0xDD, 0xEE))])
    add_rect(s, 0.98, 4.55, 3.0, 0.05, fill=BLUE)
    add_text(s, 0.98, 4.85, 11.4, 0.9, [
        ("附：复现报告（Word）、results.json、消融表、E3 权重、对齐结果", 12, False, RGBColor(0xBF, 0xD4, 0xEA))])

    out = _os.path.join(REPO, "侧扫声呐目标检测_融合复现总结_v2.pptx")
    prs.save(out)
    check = Presentation(out)
    print("slides:", len(check.slides))
    print("saved:", out)


if __name__ == "__main__":
    main()
