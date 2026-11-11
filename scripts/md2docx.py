# -*- coding: utf-8 -*-
"""Convert the fused-reproduction report markdown to a Word document."""
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

CJK = "微软雅黑"
EN = "Segoe UI"
ACCENT = RGBColor(0x1F, 0x4E, 0x79)


def font(run, size=10.5, bold=None, color=None, mono=False):
    run.font.name = "Consolas" if mono else EN
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    rf.set(qn("w:ascii"), "Consolas" if mono else EN)
    rf.set(qn("w:hAnsi"), "Consolas" if mono else EN)
    rf.set(qn("w:eastAsia"), CJK)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def inline(par, text, size=10.5, base_bold=False):
    parts = re.split(r"(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            r = par.add_run(part[2:-2])
            font(r, size=size, bold=True)
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            r = par.add_run(part[1:-1])
            font(r, size=size - 1, mono=True)
        elif part.startswith("["):
            m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", part)
            if m:
                r = par.add_run(m.group(1))
                font(r, size=size, bold=base_bold, color=RGBColor(0x05, 0x63, 0xC1))
            else:
                r = par.add_run(part)
                font(r, size=size, bold=base_bold)
        else:
            r = par.add_run(part)
            font(r, size=size, bold=base_bold)


def table(doc, rows):
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    body = []
    for line in rows[1:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        body.append(cells)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        r = p.add_run(h.replace("**", ""))
        font(r, size=8.5, bold=True)
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "DEEAF6")
        tcPr.append(shd)
    for row in body:
        cells = t.add_row().cells
        for i, val in enumerate(row[: len(header)]):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            inline(p, val.replace("**", ""), size=8.5)
    doc.add_paragraph()


def main(md_path, out_path):
    with open(md_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2.2)
    sec.bottom_margin = Cm(2.2)
    sec.left_margin = Cm(2.2)
    sec.right_margin = Cm(2.2)
    normal = doc.styles["Normal"]
    normal.font.name = EN
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), CJK)

    i = 0
    first_heading = True
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(lines[i])
                font(r, size=8.5, mono=True)
                i += 1
            i += 1
            continue
        if line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            table(doc, block)
            continue
        if line.startswith("### "):
            p = doc.add_heading(level=3)
            r = p.add_run(line[4:])
            font(r, size=11.5, bold=True, color=RGBColor(0x2E, 0x74, 0xB5))
        elif line.startswith("## "):
            p = doc.add_heading(level=2)
            r = p.add_run(line[3:])
            font(r, size=13, bold=True, color=RGBColor(0x2E, 0x74, 0xB5))
        elif line.startswith("# "):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(8)
            r = p.add_run(line[2:])
            font(r, size=18, bold=True, color=ACCENT)
            first_heading = False
        elif line.startswith("> "):
            p = doc.add_paragraph()
            r = p.add_run(line[2:])
            font(r, size=9, color=RGBColor(0x60, 0x60, 0x60))
        elif line.startswith("| "):
            pass
        elif re.match(r"^\s*[-*] ", line):
            p = doc.add_paragraph(style="List Bullet")
            inline(p, re.sub(r"^\s*[-*] ", "", line))
        elif re.match(r"^\s*\d+\. ", line):
            p = doc.add_paragraph(style="List Number")
            inline(p, re.sub(r"^\s*\d+\. ", "", line))
        elif line.startswith("**") and line.endswith("**"):
            p = doc.add_paragraph()
            r = p.add_run(line.strip("*"))
            font(r, size=11, bold=True, color=ACCENT)
        else:
            p = doc.add_paragraph()
            p.paragraph_format.line_spacing = 1.25
            inline(p, line)
        i += 1

    doc.save(out_path)
    check = Document(out_path)
    print("paragraphs:", len(check.paragraphs), "tables:", len(check.tables))
    print("saved:", out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
