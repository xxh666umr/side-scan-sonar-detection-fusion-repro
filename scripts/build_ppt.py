import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Build the summary deck for the fused side-scan sonar detection reproduction."""
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu
from pptx.oxml.ns import qn

NAVY = RGBColor(0x1F, 0x3B, 0x5C)
BLUE = RGBColor(0x2E, 0x74, 0xB5)
LIGHT = RGBColor(0xDE, 0xEA, 0xF6)
PALE = RGBColor(0xF2, 0xF6, 0xFB)
GRAY = RGBColor(0x59, 0x59, 0x59)
DARK = RGBColor(0x26, 0x26, 0x26)
ORANGE = RGBColor(0xC5, 0x5A, 0x11)
GREEN = RGBColor(0x54, 0x82, 0x35)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
RED = RGBColor(0xC0, 0x00, 0x00)

FONT = "Microsoft YaHei"
SW, SH = 13.333, 7.5


def font(run, size=14, bold=False, color=DARK, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        rPr.append(ea)
    ea.set("typeface", FONT)


def add_rect(slide, x, y, w, h, fill=PALE, line=None, radius=False, shadow=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        try:
            shp.adjustments[0] = 0.06
        except Exception:
            pass
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = shadow
    return shp


def add_text(slide, x, y, w, h, lines, size=14, color=DARK, bold=False,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.1,
             margins=(0.05, 0.03)):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(margins[0])
    tf.margin_right = Inches(margins[0])
    tf.margin_top = Inches(margins[1])
    tf.margin_bottom = Inches(margins[1])
    if isinstance(lines, str):
        lines = [(lines, size, bold, color)]
    first = True
    for item in lines:
        text, sz, bd, cl = item if isinstance(item, tuple) else (item, size, bold, color)
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(2)
        r = p.add_run()
        r.text = text
        font(r, size=sz, bold=bd, color=cl)
    return box


def title_bar(slide, title, page=None, sub=None):
    add_rect(slide, 0, 0, SW, 0.95, fill=NAVY)
    add_rect(slide, 0, 0.95, SW, 0.05, fill=BLUE)
    add_text(slide, 0.55, 0.14, 10.8, 0.7, [(title, 26, True, WHITE)],
             anchor=MSO_ANCHOR.MIDDLE, margins=(0, 0))
    if sub:
        add_text(slide, 0.58, 1.12, 12.2, 0.4, [(sub, 12, False, GRAY)], margins=(0, 0))
    if page is not None:
        add_text(slide, SW - 1.15, 0.3, 0.8, 0.4, [("%02d" % page, 12, True, RGBColor(0xBF, 0xD4, 0xEA))],
                 align=PP_ALIGN.RIGHT, margins=(0, 0))


def add_table(slide, x, y, w, h, rows, col_w, font_size=12, header_size=12,
              header_fill=BLUE, first_col_bold=False, row_h=None):
    nrows, ncols = len(rows), len(rows[0])
    gt = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(w), Inches(h))
    table = gt.table
    total = sum(col_w)
    for i, cw in enumerate(col_w):
        table.columns[i].width = Emu(int(Inches(w) * cw / total))
    table.rows[0].height = Inches(0.55)
    for r in range(nrows):
        if r > 0 and row_h:
            table.rows[r].height = Inches(row_h)
        for c in range(ncols):
            cell = table.cell(r, c)
            cell.margin_left = Inches(0.06)
            cell.margin_right = Inches(0.06)
            cell.margin_top = Inches(0.015)
            cell.margin_bottom = Inches(0.015)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if r == 0:
                cell.fill.fore_color.rgb = header_fill
            elif r % 2 == 0:
                cell.fill.fore_color.rgb = PALE
            else:
                cell.fill.fore_color.rgb = WHITE
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if c > 0 else PP_ALIGN.LEFT
            r0 = p.add_run()
            r0.text = str(rows[r][c])
            font(r0, size=(header_size if r == 0 else font_size), bold=(r == 0 or (first_col_bold and c == 0)),
                 color=(WHITE if r == 0 else DARK))
    return table


def add_chart(slide, x, y, w, h, categories, series, colors, title=None, max_val=None, font_size=11):
    data = CategoryChartData()
    data.categories = categories
    for name, values in series:
        data.add_series(name, values)
    chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y),
                                   Inches(w), Inches(h), data).chart
    chart.has_title = bool(title)
    if title:
        chart.chart_title.text_frame.text = title
        for run in chart.chart_title.text_frame.paragraphs[0].runs:
            font(run, size=13, bold=True, color=DARK)
    chart.has_legend = len(series) > 1
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(font_size)
        chart.legend.font.name = FONT
    for i, s in enumerate(chart.series):
        s.format.fill.solid()
        s.format.fill.fore_color.rgb = colors[i]
        s.format.line.fill.background()
    plot = chart.plots[0]
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.font.size = Pt(font_size)
    dl.font.name = FONT
    dl.number_format = "0.000"
    dl.number_format_is_linked = False
    dl.position = 3  # outside end
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.tick_labels.font.size = Pt(font_size)
    chart.value_axis.tick_labels.font.name = FONT
    chart.category_axis.tick_labels.font.size = Pt(font_size + 1)
    chart.category_axis.tick_labels.font.name = FONT
    if max_val:
        chart.value_axis.maximum_scale = max_val
    chart.value_axis.minimum_scale = 0
    return chart


def main():
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    blank = prs.slide_layouts[6]

    # ---------------- 1 cover ----------------
    s = prs.slides.add_slide(blank)
    add_rect(s, 0, 0, SW, SH, fill=NAVY)
    add_rect(s, 0, 4.62, SW, 0.06, fill=BLUE)
    add_rect(s, 0.9, 1.55, 0.09, 1.55, fill=BLUE)
    add_text(s, 1.18, 1.5, 11.2, 0.5, [("课程/项目总结汇报", 16, False, RGBColor(0xBF, 0xD4, 0xEA))])
    add_text(s, 1.18, 1.95, 11.4, 1.2, [("侧扫声呐图像目标检测", 42, True, WHITE),
                                          ("三篇开源论文的融合复现与实验验证", 26, False, RGBColor(0xDD, 0xE9, 0xF5))])
    add_text(s, 1.18, 3.55, 11.4, 0.9, [
        ("数据：SWDD 侧扫声呐数据集（604 / 130 / 130 张）", 15, False, RGBColor(0xCF, 0xDD, 0xEE)),
        ("任务：目标检测    指标：Precision / Recall / mAP", 15, False, RGBColor(0xCF, 0xDD, 0xEE)),
    ])
    add_text(s, 1.18, 4.95, 11.4, 1.4, [
        ("汇报人：__________        导师：__________", 14, False, RGBColor(0xBF, 0xD4, 0xEA)),
        ("2026 年 11 月", 14, False, RGBColor(0xBF, 0xD4, 0xEA)),
    ])

    # ---------------- 2 task ----------------
    s = prs.slides.add_slide(blank)
    title_bar(s, "一、任务定义：要解决什么问题", 2)
    cards = [
        ("数据集", "侧扫声呐图像", "SWDD 公开数据集\n604 训练 / 130 验证 / 130 测试\n640×640，2 类目标"),
        ("任务", "目标检测", "在声呐图中框出目标\n并判断类别（wall / noWall）\n属于有监督检测任务"),
        ("指标", "Precision / Recall / mAP", "精确率：误报少\n召回率：漏检少\nmAP：综合指标，主对比口径"),
    ]
    for i, (tag, name, desc) in enumerate(cards):
        x = 0.62 + i * 4.09
        add_rect(s, x, 1.55, 3.75, 3.55, fill=PALE, line=LIGHT, radius=True)
        add_rect(s, x, 1.55, 3.75, 0.5, fill=BLUE, radius=False)
        add_text(s, x + 0.15, 1.6, 3.4, 0.4, [(tag, 15, True, WHITE)])
        add_text(s, x + 0.18, 2.18, 3.4, 0.6, [(name, 21, True, NAVY)])
        add_text(s, x + 0.18, 2.9, 3.4, 2.0, [(desc, 12.5, False, GRAY)], spacing=1.25)
    add_rect(s, 0.62, 5.45, 12.1, 1.1, fill=LIGHT, radius=True)
    add_text(s, 0.85, 5.55, 11.7, 0.9, [
        ("目标：找 3 篇“论文 + 代码都开源”的工作，把它们的方法融合成一个检测器，在侧扫数据上复现并给出可对比的指标。",
         14.5, True, NAVY),
    ], anchor=MSO_ANCHOR.MIDDLE)

    # ---------------- 3 papers ----------------
    s = prs.slides.add_slide(blank)
    title_bar(s, "二、选定的三篇开源论文：各提供一个能力", 3)
    rows = [
        ["论文", "发表", "提供的能力", "开源情况"],
        ["P1  KD-YOLOX-ViT\nKnowledge Distillation in YOLOX-ViT\nfor Side-Scan Sonar Object Detection",
         "arXiv 2024\nREMARO @ ETAPS", "轻量检测器 YOLOX-ViT\n+ 教师-学生知识蒸馏", "代码 + 数据\n（Apache-2.0）"],
        ["P2  DCBD\nUnsupervised underwater shipwreck\ndetection based on domain-adaptive techniques",
         "Sci Rep 2024\n（开放获取）", "无监督域自适应\n伪标签自训练 + 域内一致性", "代码开源\n数据可用"],
        ["P3  ROSAR\nAn Adversarial Re-Training Framework\nfor Robust Side-Scan Sonar Object Detection",
         "arXiv 2024\nMARIS 2025 投稿", "PGD / Patch 对抗样本\n+ 对抗重训练", "代码 + 数据\n（Zenodo）"],
    ]
    add_table(s, 0.6, 1.5, 12.15, 4.55, rows, [4.3, 2.1, 3.15, 1.85], font_size=11, header_size=12)
    add_rect(s, 0.6, 6.2, 12.15, 0.72, fill=LIGHT, radius=True)
    add_text(s, 0.8, 6.26, 11.8, 0.6, [
        ("融合思路：P1 做底座（结构+蒸馏） → P2 解决“标注少” → P3 解决“噪声/攻击下不稳”，串成一个模型。",
         13.5, True, NAVY),
    ], anchor=MSO_ANCHOR.MIDDLE)

    # ---------------- 4 architecture ----------------
    s = prs.slides.add_slide(blank)
    title_bar(s, "三、融合方案：一个检测器 + 三种能力", 4)
    add_rect(s, 4.55, 1.55, 4.2, 3.5, fill=LIGHT, line=BLUE, radius=True)
    add_text(s, 4.65, 1.7, 4.0, 0.4, [("统一检测器", 15, True, BLUE)], align=PP_ALIGN.CENTER)
    add_text(s, 4.65, 2.1, 4.0, 0.55, [("YOLOX-Nano-ViT", 22, True, NAVY)], align=PP_ALIGN.CENTER)
    add_text(s, 4.7, 2.75, 3.9, 2.1, [
        ("• 主干：CSPDarknet + ViT 层", 12.5, False, DARK),
        ("• 输出：类别 + 边界框", 12.5, False, DARK),
        ("• 参数量约 0.96 M，适合部署", 12.5, False, DARK),
    ], spacing=1.35)
    left = [
        ("P1  KD 蒸馏", "教师 L-ViT 伪标签\n→ Nano-ViT 学生", 2.55),
        ("P2  无监督域自适应", "目标域图像伪标签\n→ 自训练 + 过滤", 4.35),
    ]
    for i, (name, desc, y) in enumerate(left):
        add_rect(s, 0.55, y, 3.55, 1.2, fill=PALE, line=BLUE, radius=True)
        add_text(s, 0.7, y + 0.08, 3.25, 0.4, [(name, 14.5, True, BLUE)])
        add_text(s, 0.7, y + 0.48, 3.25, 0.65, [(desc, 11.5, False, GRAY)], spacing=1.15)
    add_rect(s, 0.55, 5.9, 3.55, 1.2, fill=PALE, line=ORANGE, radius=True)
    add_text(s, 0.7, 5.98, 3.25, 0.4, [("P3  对抗重训练", 14.5, True, ORANGE)])
    add_text(s, 0.7, 6.38, 3.25, 0.65, [("PGD 对抗样本\n→ 加入训练集重训", 11.5, False, GRAY)], spacing=1.15)
    for y in (3.15, 4.95, 6.5):
        add_rect(s, 4.12, y, 0.42, 0.06, fill=BLUE)
        add_text(s, 4.1, y - 0.28, 0.5, 0.3, [("→", 16, True, BLUE)], align=PP_ALIGN.CENTER)
    add_rect(s, 9.0, 1.55, 3.75, 5.55, fill=NAVY, radius=True)
    add_text(s, 9.2, 1.72, 3.4, 0.4, [("训练策略", 15, True, RGBColor(0xBF, 0xD4, 0xEA))])
    steps = [
        ("E0", "基线：源域有标注数据"),
        ("E1", "+ KD：教师伪标签蒸馏"),
        ("E2", "+ 域自适应：目标域自训练"),
        ("E3", "+ 对抗重训练（最终）"),
    ]
    for i, (tag, desc) in enumerate(steps):
        y = 2.2 + i * 1.12
        add_text(s, 9.2, y, 0.6, 0.4, [(tag, 17, True, RGBColor(0xFF, 0xC0, 0x00))])
        add_text(s, 9.8, y + 0.02, 2.85, 0.6, [(desc, 11.5, False, WHITE)], spacing=1.1)
        if i < 3:
            add_text(s, 9.2, y + 0.62, 3.3, 0.3, [("↓", 12, True, RGBColor(0x8F, 0xAA, 0xC8))])

    # ---------------- 5 data & protocol ----------------
    s = prs.slides.add_slide(blank)
    title_bar(s, "四、数据与评测协议", 5)
    add_text(s, 0.6, 1.45, 5.9, 0.4, [("SWDD 数据集", 18, True, NAVY)])
    kpis = [("604", "训练"), ("130", "验证"), ("130", "测试"), ("2 类", "wall / noWall")]
    for i, (num, label) in enumerate(kpis):
        x = 0.6 + i * 1.55
        add_rect(s, x, 1.95, 1.4, 1.15, fill=PALE, line=LIGHT, radius=True)
        add_text(s, x, 2.05, 1.4, 0.55, [(num, 22, True, BLUE)], align=PP_ALIGN.CENTER)
        add_text(s, x, 2.62, 1.4, 0.4, [(label, 11.5, False, GRAY)], align=PP_ALIGN.CENTER)
    add_text(s, 0.6, 3.3, 5.9, 0.5, [("640×640，COCO 标注格式；由水下沉船图像 + 公开数据整理", 12, False, GRAY)])
    add_text(s, 0.6, 4.05, 5.9, 0.4, [("三套测试，分别考察三种能力", 18, True, NAVY)])
    tests = [
        ("清洁测试集", "原始 test split（130 张）", "基础精度", GREEN),
        ("域偏移测试集", "加噪声/模糊/黑线/光照变化", "泛化能力（P2）", ORANGE),
        ("PGD 攻击测试集", "ε=8/255，10 步对抗攻击", "鲁棒性（P3）", RED),
    ]
    for i, (name, desc, tag, color) in enumerate(tests):
        y = 4.55 + i * 0.78
        add_rect(s, 0.6, y, 5.9, 0.66, fill=PALE, line=LIGHT, radius=True)
        add_rect(s, 0.6, y, 0.09, 0.66, fill=color)
        add_text(s, 0.82, y + 0.04, 2.1, 0.35, [(name, 13.5, True, DARK)])
        add_text(s, 0.82, y + 0.34, 3.9, 0.3, [(desc, 10.5, False, GRAY)])
        add_text(s, 4.85, y + 0.14, 1.55, 0.35, [(tag, 11.5, True, color)], align=PP_ALIGN.RIGHT)
    add_rect(s, 6.85, 1.45, 5.9, 5.15, fill=PALE, line=LIGHT, radius=True)
    add_text(s, 7.1, 1.6, 5.4, 0.45, [("消融实验设计（同一协议对比）", 16, True, NAVY)])
    rows = [
        ["编号", "训练数据 / 方法"],
        ["E0", "源域 GT（604 张），基线"],
        ["E1", "+ 教师 L-ViT 伪标签（KD）"],
        ["E2", "+ 模拟目标域学生伪标签（DA）"],
        ["E3", "+ PGD 对抗样本（Robust，最终）"],
    ]
    add_table(s, 7.1, 2.15, 5.4, 2.6, rows, [1.1, 4.30], font_size=11.5, header_size=12)
    add_text(s, 7.1, 4.95, 5.4, 1.4, [
        ("评测口径：", 11.5, True, BLUE),
        ("pycocotools COCO 指标（mAP@0.5、mAP@0.5:0.95、Recall@0.5）", 10.5, False, GRAY),
        ("+ 置信度扫描得 Best-F1 的 Precision / Recall；P/R 另给固定阈值 0.25 / 0.5 两档。", 10.5, False, GRAY),
        ("另：论文同款 6244 帧视频 + 640 输入，用 OD-Metrics 复评做对齐。", 10, False, BLUE),
    ], spacing=1.2)

    # ---------------- 6 main results table ----------------
    s = prs.slides.add_slide(blank)
    title_bar(s, "五、主结果：Precision / Recall / mAP（同一测试集）", 6)
    rows = [
        ["模型", "Precision\n@0.25", "Recall\n@0.25", "Precision\n@0.50", "Recall\n@0.50", "mAP@0.5", "mAP@0.5:0.95"],
        ["E0  基线（Nano-ViT）", "0.2187", "0.5700", "0.2035", "0.5040", "0.2273", "0.1187"],
        ["E1  + KD 蒸馏", "0.2111", "0.5779", "0.1889", "0.4552", "0.2544", "0.1431"],
        ["E2  + 域自适应", "0.1423", "0.6045", "0.1271", "0.4479", "0.1567", "0.0702"],
        ["E3  + 对抗重训练（最终）", "0.2024", "0.5278", "0.1865", "0.4450", "0.2600", "0.1537"],
    ]
    add_table(s, 0.6, 1.5, 12.15, 3.4, rows, [3.0, 1.35, 1.3, 1.4, 1.3, 1.35, 1.55], font_size=12.5, header_size=11.5)
    add_rect(s, 0.6, 5.1, 5.95, 1.55, fill=LIGHT, radius=True)
    add_text(s, 0.8, 5.18, 5.6, 1.4, [
        ("怎么读这张表", 13.5, True, NAVY),
        ("• mAP 与阈值无关，作为主对比口径：E1 提升，E3 最高 0.2600", 11.5, False, DARK),
        ("• P/R 随阈值变化：另给 0.25 / 0.5 两档固定阈值", 11.5, False, DARK),
    ], spacing=1.2)
    add_rect(s, 6.8, 5.1, 5.95, 1.55, fill=RGBColor(0xFF, 0xF2, 0xE6), radius=True)
    add_text(s, 7.0, 5.18, 5.6, 1.4, [
        ("Best-F1 点的 P / R（更公平的 P/R 对比）", 13.5, True, ORANGE),
        ("E0 0.222 / 0.601   →   E1 0.236 / 0.697   →   E3 0.218 / 0.615", 11.5, False, DARK),
        ("KD 与对抗重训练都提高了 P/R 的平衡点", 11.5, True, ORANGE),
    ], spacing=1.2)

    # ---------------- 7 charts ----------------
    s = prs.slides.add_slide(blank)
    title_bar(s, "六、消融趋势：每加一个模块，效果如何变化", 7)
    cats = ["E0 基线", "E1 +KD", "E2 +DA", "E3 +Robust"]
    add_chart(s, 0.55, 1.45, 6.05, 4.9, cats,
              [("mAP@0.5", (0.2273, 0.2544, 0.1567, 0.2600))],
              [BLUE], title="清洁测试集 mAP@0.5", max_val=0.35)
    add_chart(s, 6.75, 1.45, 6.05, 4.9, cats,
              [("PGD 攻击下 mAP@0.5", (0.0492, 0.0558, 0.0239, 0.1428))],
              [ORANGE], title="对抗攻击（PGD）下 mAP@0.5", max_val=0.20)
    add_text(s, 0.6, 6.45, 12.1, 0.5, [
        ("清洁精度：KD 提升 +11.9%，最终 E3 最高 0.2600；抗攻击：E3 从 0.0492 → 0.1428（约 2.9 倍）。", 12, True, NAVY),
    ], align=PP_ALIGN.CENTER)

    # ---------------- 8 consistency with papers ----------------
    s = prs.slides.add_slide(blank)
    title_bar(s, "七、与原文的一致性：结论一致，评测已对齐", 8)
    rows = [
        ["论文", "原文结论", "本次复现", "一致性"],
        ["P1 KD-YOLOX-ViT", "ViT 层：Nano AP50 0.19 →\nNano-ViT 0.42",
         "同协议重评（640）：\nNano 0.321 → Nano-ViT 0.438", "✔ 基本对齐\n（差约 4%）"],
        ["P3 ROSAR", "对抗重训练提升鲁棒性\n且精度基本不降", "PGD 下 0.049 → 0.143；\n清洁集 0.227 → 0.260", "✔ 方向一致"],
        ["P2 DCBD", "域自适应后接近全监督\n（mAP 48.6 / AP50 92.2）", "域偏移 0.008 → 0.018，\n但清洁集 0.157", "△ 仅方向一致\n（方法迁移）"],
    ]
    add_table(s, 0.6, 1.5, 12.15, 3.05, rows, [2.35, 3.55, 3.45, 2.2], font_size=11.5, header_size=12)
    add_rect(s, 0.6, 4.8, 12.15, 1.85, fill=RGBColor(0xFF, 0xF2, 0xE6), radius=True)
    add_text(s, 0.85, 4.9, 11.7, 1.65, [
        ("对齐过程发现的关键差异", 13.5, True, ORANGE),
        ("① 评测输入尺寸：416 会低估，640 才是论文口径（Nano-ViT 0.193 → 0.438）",
         11.5, False, DARK),
        ("② 类别平均/权重版本：Nano AP50 仍有差异（0.321 vs 0.19），但 AP 完全一致（0.064）",
         11.5, False, DARK),
        ("③ 训练配置未公开：自训 200ep 0.240、COCO 预训练 300ep 0.153，均达不到官方 0.438",
         11.5, False, DARK),
    ], spacing=1.2)

    # ---------------- 9 alignment findings ----------------
    s = prs.slides.add_slide(blank)
    title_bar(s, "八、与原文对齐：三个关键发现", 9)
    rows = [
        ["预处理 / 输入", "Nano AP50", "Nano-ViT AP50"],
        ["416 letterbox（默认）", "0.314", "0.193"],
        ["416 直接拉伸", "0.093", "0.172"],
        ["640 letterbox", "0.321", "0.438"],
        ["论文（6244 帧）", "0.19", "0.42"],
    ]
    add_table(s, 0.6, 1.5, 6.1, 2.75, rows, [2.55, 1.75, 1.85], font_size=12, header_size=12)
    add_text(s, 0.6, 4.45, 6.1, 1.8, [
        ("同协议结论", 13.5, True, NAVY),
        ("• Nano-ViT：0.438 vs 论文 0.42（差约 4%）", 11.5, False, DARK),
        ("• Nano 的 AP 0.064 与论文完全一致", 11.5, False, DARK),
        ("• 416 输入低估约 2 倍 → 640 才是论文口径", 11.5, False, DARK),
    ], spacing=1.3)
    findings = [
        ("① 关键差异：输入尺寸", "视频帧 1570×390，416 下目标过小；640 下 Nano-ViT 提升到 0.438", BLUE),
        ("② 必须保持宽高比", "直接拉伸到 416 明显更差（0.093），letterbox 才正确", BLUE),
        ("③ 训练侧无法完全复刻", "自训 200ep 0.240、COCO 预训练 300ep 0.153，达不到官方 0.438", ORANGE),
    ]
    for i, (head, body, color) in enumerate(findings):
        y = 1.5 + i * 1.55
        add_rect(s, 6.95, y, 5.8, 1.35,
                 fill=RGBColor(0xFF, 0xF2, 0xE6) if color == ORANGE else PALE,
                 line=LIGHT, radius=True)
        add_text(s, 7.15, y + 0.08, 5.4, 0.4, [(head, 13.5, True, color)])
        add_text(s, 7.15, y + 0.5, 5.4, 0.75, [(body, 11, False, DARK)], spacing=1.2)
    add_rect(s, 0.6, 6.45, 12.15, 0.78, fill=LIGHT, radius=True)
    add_text(s, 0.8, 6.5, 11.8, 0.68, [
        ("一句话：评测协议（640 输入）已对齐、Nano-ViT 基本复现；训练配置未公开，无法逐位复刻。",
         12, True, NAVY)], anchor=MSO_ANCHOR.MIDDLE)

    # ---------------- 9b full measured data ----------------
    s = prs.slides.add_slide(blank)
    title_bar(s, "九、补充实验：2.2GB 视频帧 + 自训模型全量实测", 10)
    rows = [
        ["模型", "设置", "AP50(wall)", "AP 0.5:0.95", "Precision"],
        ["论文 Nano", "6243 帧 / OD-Metrics", "0.19", "0.064", "31.5%"],
        ["论文 Nano-ViT", "6243 帧 / OD-Metrics", "0.42", "0.15", "40.3%"],
        ["官方 Nano 权重", "416 letterbox", "0.314", "0.048", "0.453"],
        ["官方 Nano-ViT 权重", "416 letterbox", "0.193", "0.030", "0.349"],
        ["官方 Nano 权重", "640 letterbox", "0.321", "0.064", "0.435"],
        ["官方 Nano-ViT 权重", "640 letterbox", "0.438", "0.093", "0.634"],
        ["自训 Nano-ViT（200ep）", "640 letterbox", "0.240", "0.045", "0.397"],
        ["自训 Nano-ViT（300ep，COCO 预训练）", "640 letterbox", "0.153", "0.027", "0.178"],
        ["融合模型 E3", "640 letterbox", "0.508", "0.102", "0.638"],
    ]
    add_table(s, 0.5, 1.42, 8.75, 4.85, rows, [3.2, 2.05, 1.1, 1.2, 1.1],
              font_size=10, header_size=10)
    notes = [
        ("数据规模", "视频帧共 6244 张（论文 6243），原始包 2.2GB；每帧有 YOLO 标注，共 9086 个框", BLUE),
        ("评测工具", "论文同款 OD-Metrics（Padilla 2021），11 点插值，只统计有 GT 的 wall 类", BLUE),
        ("工作量", "5 个模型 × 3 种预处理/输入 × 10 个 IoU 阈值，全部重跑", BLUE),
        ("关键结论", "640 输入才对齐：官方 Nano-ViT 0.438 ≈ 论文 0.42；E3 0.508 最高", ORANGE),
    ]
    for i, (head, body, color) in enumerate(notes):
        y = 1.45 + i * 1.27
        add_rect(s, 9.45, y, 3.4, 1.13,
                 fill=RGBColor(0xFF, 0xF2, 0xE6) if color == ORANGE else PALE,
                 line=LIGHT, radius=True)
        add_text(s, 9.6, y + 0.06, 3.1, 0.35, [(head, 12, True, color)])
        add_text(s, 9.6, y + 0.42, 3.1, 0.65, [(body, 9.5, False, DARK)], spacing=1.15)
    add_text(s, 0.5, 6.45, 12.3, 0.6, [
        ("结论：官方权重在 640 输入下基本复现论文；自训模型达不到官方水平（训练配置未公开）；融合模型 E3 全量实测最高。",
         11.5, True, NAVY)], align=PP_ALIGN.CENTER)

    # ---------------- 10 conclusions ----------------
    s = prs.slides.add_slide(blank)
    title_bar(s, "十、关键结论", 11)
    items = [
        ("① KD 蒸馏有效", "清洁 test mAP@0.5 0.2273 → 0.2544（+11.9%），Recall 0.746 → 0.861"),
        ("② 对抗重训练最划算", "清洁 mAP@0.5 最高 0.2600；PGD 攻击下 0.0492 → 0.1428（约 2.9 倍）"),
        ("③ 域自适应仍有短板", "域偏移提升 +130%，但清洁集下降；需补完整 IDCC/域判别器或联合训练"),
        ("④ 三篇可融合成一套流程", "E0→E1→E2→E3 全流程可一键复现，代码与数据均开源"),
        ("⑤ 评测协议已对齐", "官方权重 640 输入 AP50 0.438 vs 论文 0.42；训练侧公开信息无法完全复刻"),
    ]
    for i, (head, body) in enumerate(items):
        y = 1.42 + i * 1.08
        add_rect(s, 0.62, y, 12.1, 0.95, fill=PALE, line=LIGHT, radius=True)
        add_rect(s, 0.62, y, 0.1, 0.95, fill=BLUE if i < 2 else ORANGE)
        add_text(s, 0.9, y + 0.06, 3.6, 0.4, [(head, 14, True, NAVY)])
        add_text(s, 0.9, y + 0.45, 11.5, 0.45, [(body, 11.5, False, GRAY)])

    # ---------------- 10 limitations & plan ----------------
    s = prs.slides.add_slide(blank)
    title_bar(s, "十一、局限与下一步计划", 12)
    add_text(s, 0.6, 1.4, 6.0, 0.4, [("当前局限", 17, True, ORANGE)])
    limits = [
        "评测已对齐（640 输入），但训练配置未公开、无法完全复刻",
        "自训模型（200ep/300ep）仅 0.240 / 0.153，低于官方 0.438",
        "DCBD 为方法迁移，非逐行复现",
        "域偏移为人工模拟，非真实组内数据",
        "单卡 8GB，未做多种子重复实验",
    ]
    for i, t in enumerate(limits):
        y = 1.95 + i * 0.72
        add_text(s, 0.6, y, 0.3, 0.4, [("•", 14, True, ORANGE)])
        add_text(s, 0.9, y, 5.6, 0.6, [(t, 12, False, DARK)])
    add_text(s, 6.9, 1.4, 5.9, 0.4, [("下一步（下周与导师讨论）", 17, True, GREEN)])
    plans = [
        ("训练侧对齐（可选）", "低学习率微调 / 向作者索取训练配置与评测脚本"),
        ("补齐域自适应", "实现 IDCC/域判别器，或两阶段联合训练"),
        ("接入真实数据", "用组内侧扫数据替换模拟域偏移，重跑 E2/E3"),
        ("扩展实验", "多种子重复 + 更长训练预算，补充置信区间"),
    ]
    for i, (head, body) in enumerate(plans):
        y = 1.95 + i * 1.12
        add_rect(s, 6.9, y, 5.85, 0.95, fill=RGBColor(0xEE, 0xF6, 0xE8), line=RGBColor(0xC5, 0xE0, 0xB4), radius=True)
        add_text(s, 7.05, y + 0.07, 5.5, 0.35, [(head, 13, True, GREEN)])
        add_text(s, 7.05, y + 0.42, 5.5, 0.5, [(body, 10.5, False, GRAY)])

    # ---------------- 11 Q&A ----------------
    s = prs.slides.add_slide(blank)
    add_rect(s, 0, 0, SW, SH, fill=NAVY)
    add_text(s, 0.9, 2.3, 11.5, 1.0, [("谢谢，欢迎讨论", 40, True, WHITE)])
    add_text(s, 0.95, 3.55, 11.5, 0.6, [("数据集 / 代码 / 模型权重 / 完整报告均已归档，可现场演示评估流程", 15, False, RGBColor(0xCF, 0xDD, 0xEE))])
    add_rect(s, 0.95, 4.45, 2.6, 0.06, fill=BLUE)
    add_text(s, 0.95, 4.75, 11.5, 1.0, [
        ("附：复现报告（Word）、results.json、消融表、E3 权重", 13, False, RGBColor(0xBF, 0xD4, 0xEA)),
        ("2026 年 11 月", 13, False, RGBColor(0xBF, 0xD4, 0xEA)),
    ])

    out = _os.path.join(REPO, "侧扫声呐目标检测_融合复现总结.pptx")
    prs.save(out)
    check = Presentation(out)
    print("slides:", len(check.slides))
    print("saved:", out)


if __name__ == "__main__":
    main()
