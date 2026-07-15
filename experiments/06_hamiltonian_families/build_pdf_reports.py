#!/usr/bin/env python3
"""
build_pdf_reports.py
====================
Convierte los reportes markdown del experimento 06 a PDF con diseño tipográfico cuidado.

Uso:
    python experiments/06_hamiltonian_families/build_pdf_reports.py

Salida:
    output/reports/executive_summary.pdf
    output/reports/hasse_diagram_report.pdf
"""

import os
import re
import html
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.fonts import addMapping
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Paleta de color ─────────────────────────────────────────────────────────
C_NAVY     = colors.HexColor("#0D1B3E")
C_BLUE     = colors.HexColor("#2A4F9B")
C_ACCENT   = colors.HexColor("#4A7FD4")
C_BODY     = colors.HexColor("#1A1A2E")
C_MUTED    = colors.HexColor("#6B7FA8")
C_CODE_FG  = colors.HexColor("#1B3A70")
C_CODE_BG  = colors.HexColor("#EEF2FA")
C_TH_BG    = colors.HexColor("#0D1B3E")
C_TR_ALT   = colors.HexColor("#F2F5FC")
C_RULE     = colors.HexColor("#C0CADF")
C_QUOTE_BG = colors.HexColor("#F0F5FF")

W = A4[0]
H = A4[1]
MARGIN = 2 * cm
TEXT_W = W - 2 * MARGIN


# ── Fuentes ──────────────────────────────────────────────────────────────────
# Segoe UI tiene cobertura Unicode completa: subíndices (₁₂), ∈, →, μ, Δ, etc.
def register_fonts():
    win = "C:/Windows/Fonts"
    pairs = [
        ("SegoeUI",            "segoeui.ttf"),
        ("SegoeUI-Bold",       "segoeuib.ttf"),
        ("SegoeUI-Italic",     "segoeuii.ttf"),
        ("SegoeUI-BoldItalic", "segoeuiz.ttf"),
        ("CourierNew",         "cour.ttf"),
        ("CourierNew-Bold",    "courbd.ttf"),
    ]
    ok = set()
    for name, fname in pairs:
        path = os.path.join(win, fname)
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
            ok.add(name)

    if {"SegoeUI","SegoeUI-Bold","SegoeUI-Italic","SegoeUI-BoldItalic"} <= ok:
        addMapping("SegoeUI", 0, 0, "SegoeUI")
        addMapping("SegoeUI", 1, 0, "SegoeUI-Bold")
        addMapping("SegoeUI", 0, 1, "SegoeUI-Italic")
        addMapping("SegoeUI", 1, 1, "SegoeUI-BoldItalic")

    if {"CourierNew","CourierNew-Bold"} <= ok:
        addMapping("CourierNew", 0, 0, "CourierNew")
        addMapping("CourierNew", 1, 0, "CourierNew-Bold")


# ── Estilos ──────────────────────────────────────────────────────────────────
def make_styles():
    return {
        "h1": ParagraphStyle("h1",
            fontName="SegoeUI-Bold", fontSize=20, textColor=C_NAVY,
            spaceBefore=10, spaceAfter=8, leading=26),
        "h2": ParagraphStyle("h2",
            fontName="SegoeUI-Bold", fontSize=14, textColor=C_NAVY,
            spaceBefore=14, spaceAfter=4, leading=19),
        "h3": ParagraphStyle("h3",
            fontName="SegoeUI-Bold", fontSize=11, textColor=C_BLUE,
            spaceBefore=10, spaceAfter=3, leading=15),
        "body": ParagraphStyle("body",
            fontName="SegoeUI", fontSize=10, textColor=C_BODY,
            spaceAfter=5, leading=15),
        "meta": ParagraphStyle("meta",
            fontName="SegoeUI-Italic", fontSize=8.5, textColor=C_MUTED,
            spaceAfter=3, leading=13),
        "bullet": ParagraphStyle("bullet",
            fontName="SegoeUI", fontSize=10, textColor=C_BODY,
            spaceAfter=3, leading=15, leftIndent=14),
        "bullet2": ParagraphStyle("bullet2",
            fontName="SegoeUI", fontSize=10, textColor=C_BODY,
            spaceAfter=2, leading=14, leftIndent=28),
        "quote": ParagraphStyle("quote",
            fontName="SegoeUI-Italic", fontSize=9.5, textColor=C_CODE_FG,
            spaceAfter=4, leading=14, leftIndent=16, rightIndent=8),
        "th": ParagraphStyle("th",
            fontName="SegoeUI-Bold", fontSize=8.5, textColor=colors.white,
            leading=12, alignment=TA_CENTER),
        "td": ParagraphStyle("td",
            fontName="SegoeUI", fontSize=8.5, textColor=C_BODY,
            leading=12),
        "td_mono": ParagraphStyle("td_mono",
            fontName="CourierNew", fontSize=7.5, textColor=C_CODE_FG,
            leading=11),
    }


# ── Markup inline ─────────────────────────────────────────────────────────────
def markup(text: str) -> str:
    """Convierte markdown inline → XML de reportlab."""
    t = html.escape(text)
    t = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', t)
    t = re.sub(r'\*\*(.+?)\*\*',     r'<b>\1</b>',        t)
    t = re.sub(r'\*(.+?)\*',         r'<i>\1</i>',        t)
    t = re.sub(r'`(.+?)`',
               r'<font name="CourierNew" color="#1B3A70" size="8">\1</font>', t)
    return t


# ── Bloques de código ─────────────────────────────────────────────────────────
def build_code_block(code_lines: list) -> KeepTogether:
    text = "\n".join(code_lines)
    escaped = html.escape(text).replace("\n", "<br/>").replace(" ", "&#160;")
    para = Paragraph(
        escaped,
        ParagraphStyle("cb",
            fontName="CourierNew", fontSize=8, textColor=C_CODE_FG,
            leading=12, spaceAfter=0),
    )
    tbl = Table([[para]], colWidths=[TEXT_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_CODE_BG),
        ("BOX",           (0,0), (-1,-1), 0.6, C_ACCENT),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
    ]))
    return KeepTogether([Spacer(1,3), tbl, Spacer(1,5)])


# ── Tablas ────────────────────────────────────────────────────────────────────
def build_table(rows: list, styles: dict) -> KeepTogether:
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]

    def cell(text, is_header=False):
        raw = text.strip()
        is_code = raw.startswith("`") and raw.endswith("`")
        if is_header:
            return Paragraph(markup(raw), styles["th"])
        elif is_code:
            inner = raw[1:-1]
            return Paragraph(
                f'<font name="CourierNew" color="#1B3A70" size="7.5">{html.escape(inner)}</font>',
                styles["td"])
        else:
            return Paragraph(markup(raw), styles["td"])

    data = [[cell(c, is_header=(i == 0)) for c in row]
            for i, row in enumerate(rows)]

    col_w = TEXT_W / ncols
    tbl = Table(data, colWidths=[col_w] * ncols, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  C_TH_BG),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, C_TR_ALT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, C_RULE),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return KeepTogether([Spacer(1,3), tbl, Spacer(1,6)])


# ── Parser de markdown ────────────────────────────────────────────────────────
def _is_align_row(cells):
    return all(re.match(r'^:?-+:?$', c.strip()) for c in cells if c.strip())


def parse_md(md_text: str, styles: dict) -> list:
    lines = md_text.split("\n")
    out = []
    i = 0

    while i < len(lines):
        raw  = lines[i]
        s    = raw.strip()

        # H1
        if re.match(r'^# (?!#)', raw):
            text = raw[2:].strip()
            out.append(Paragraph(markup(text), styles["h1"]))
            out.append(HRFlowable(width="100%", thickness=2,
                                   color=C_ACCENT, spaceAfter=6))
            i += 1

        # H2
        elif re.match(r'^## (?!#)', raw):
            text = raw[3:].strip()
            out.append(Paragraph(markup(text), styles["h2"]))
            out.append(HRFlowable(width="100%", thickness=0.7,
                                   color=C_RULE, spaceAfter=3))
            i += 1

        # H3
        elif re.match(r'^### ', raw):
            text = raw[4:].strip()
            out.append(Paragraph(markup(text), styles["h3"]))
            i += 1

        # Horizontal rule
        elif re.match(r'^-{3,}\s*$', s) or re.match(r'^\*{3,}\s*$', s):
            out.append(Spacer(1, 4))
            out.append(HRFlowable(width="100%", thickness=0.5,
                                   color=C_RULE, spaceAfter=4))
            i += 1

        # Code block
        elif s.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            out.append(build_code_block(code))
            i += 1

        # Table
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip()
                         for c in lines[i].strip().strip("|").split("|")]
                if not _is_align_row(cells):
                    rows.append(cells)
                i += 1
            if rows:
                out.append(build_table(rows, styles))

        # Blockquote
        elif s.startswith(">"):
            text = s[1:].strip()
            block_lines = [text]
            i += 1
            while i < len(lines) and lines[i].strip().startswith(">"):
                block_lines.append(lines[i].strip()[1:].strip())
                i += 1
            joined = " ".join(block_lines)
            q_para = Paragraph(markup(joined), styles["quote"])
            q_tbl  = Table([[q_para]], colWidths=[TEXT_W])
            q_tbl.setStyle(TableStyle([
                ("BACKGROUND",   (0,0), (-1,-1), C_QUOTE_BG),
                ("LEFTPADDING",  (0,0), (-1,-1), 14),
                ("RIGHTPADDING", (0,0), (-1,-1), 10),
                ("TOPPADDING",   (0,0), (-1,-1), 6),
                ("BOTTOMPADDING",(0,0), (-1,-1), 6),
                ("LINEBEFORE",   (0,0), (0,-1),  3, C_ACCENT),
            ]))
            out.append(Spacer(1,3))
            out.append(q_tbl)
            out.append(Spacer(1,5))

        # Bullet list
        elif re.match(r'^(\s{0,3})[-*+] ', raw):
            indent = len(raw) - len(raw.lstrip())
            text   = re.sub(r'^\s*[-*+]\s+', '', raw)
            st     = styles["bullet2"] if indent >= 4 else styles["bullet"]
            bullet = "◦" if indent >= 4 else "•"
            out.append(Paragraph(f"{bullet}&#160;&#160;{markup(text)}", st))
            i += 1

        # Numbered list
        elif re.match(r'^\d+\.\s', s):
            num, rest = re.match(r'^(\d+)\.\s+(.*)', s).groups()
            out.append(Paragraph(
                f"<b>{num}.</b>&#160;{markup(rest)}", styles["bullet"]))
            i += 1

        # Blank line
        elif s == "":
            out.append(Spacer(1, 4))
            i += 1

        # Italic-only line (metadata)
        elif re.match(r'^\*[^*].+[^*]\*$', s):
            inner = s[1:-1]
            out.append(Paragraph(f"<i>{markup(inner)}</i>", styles["meta"]))
            i += 1

        # Normal paragraph
        else:
            if s:
                out.append(Paragraph(markup(s), styles["body"]))
            i += 1

    return out


# ── Header / footer ───────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    # Header bar
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, H - 9*mm, W, 9*mm, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, H - 9*mm, W * 0.30, 9*mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("SegoeUI-Italic", 7)
    canvas.drawString(W * 0.30 + 8, H - 6*mm,
                      "Go Ising · Experimento 06 · Familia de Hamiltonianos cúbicos")
    # Footer
    canvas.setFillColor(C_MUTED)
    canvas.setFont("SegoeUI", 7.5)
    canvas.drawString(MARGIN, 1.3*cm,
                      "Leonardo Jiménez Martínez · UNAM · 2026")
    canvas.drawRightString(W - MARGIN, 1.3*cm, f"Página {doc.page}")
    canvas.setStrokeColor(C_RULE)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 1.6*cm, W - MARGIN, 1.6*cm)
    canvas.restoreState()


# ── Conversión ────────────────────────────────────────────────────────────────
def convert(md_path: Path, pdf_path: Path, styles: dict):
    md_text = md_path.read_text(encoding="utf-8")
    flowables = parse_md(md_text, styles)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.4*cm, bottomMargin=2.2*cm,
        title=md_path.stem.replace("_", " ").title(),
        author="Leonardo Jiménez Martínez",
        subject="Go Ising · Experimento 06 · Hamiltonians cúbicos",
        creator="build_pdf_reports.py · reportlab",
    )
    doc.build(flowables, onFirstPage=on_page, onLaterPages=on_page)
    print(f"  OK  {pdf_path.name}")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    register_fonts()
    styles = make_styles()

    reports_dir = Path(__file__).parent / "output" / "reports"
    targets = [
        ("executive_summary.md",    "executive_summary.pdf"),
        ("hasse_diagram_report.md", "hasse_diagram_report.pdf"),
    ]

    for md_name, pdf_name in targets:
        md  = reports_dir / md_name
        pdf = reports_dir / pdf_name
        if not md.exists():
            print(f"  SKIP  {md_name} not found, skipping")
            continue
        convert(md, pdf, styles)
