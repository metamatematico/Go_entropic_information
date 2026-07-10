"""
generate_book_pdf.py
====================
Genera el reporte en formato LIBRO (A5) usando reportlab Platypus.
Tipografia profesional, capitulos con portadillas, tablas de color,
figuras con pies de figura y tabla de contenidos navegable.

Salida: results/libro_entropia_go.pdf
"""

import os, sys, io, textwrap
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import FancyBboxPatch

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, CondPageBreak, HRFlowable, KeepTogether, NextPageTemplate,
    ListFlowable, ListItem,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import inch, cm, mm, pica
from reportlab.lib import colors
from reportlab.lib.colors import HexColor, black, white, gray
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas as pdfcanvas

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from compare_per_bond import (
    H_nuestro, H_alvarado, SPIN_VALS,
    all_bond_energies_nuestro, all_bond_energies_alvarado,
    bond_shannon_entropy, bond_boltzmann_entropy, bond_T_eff,
)
from analysis_patterns import PATTERNS, BOARD_SIZE
from src.go_entropy import board_from_stones

# ── Rutas ────────────────────────────────────────────────────────────────────
HERE    = str(Path(__file__).resolve().parents[2])
RESULTS = os.path.join(HERE, 'results')
OUT     = os.path.join(RESULTS, 'libro_entropia_go.pdf')

# ── Dimensiones A5 ───────────────────────────────────────────────────────────
PW, PH  = A5          # 419.53 × 595.28 pts
ML      = 2.0 * cm    # margen izquierdo
MR      = 1.5 * cm    # margen derecho
MT      = 2.2 * cm    # margen superior
MB      = 2.5 * cm    # margen inferior
TW      = PW - ML - MR   # ancho texto
FRAME_W = TW             # ancho efectivo (frame sin padding L/R)
FRAME_H = PH - MT - MB - 16  # alto efectivo (frame tiene 8pt padding T+B)
FIG_W   = FRAME_W        # figuras a ancho completo

# ── Colores ───────────────────────────────────────────────────────────────────
C_NAVY   = HexColor('#0F2044')
C_M1     = HexColor('#1D4ED8')
C_AL     = HexColor('#D97706')
C_ACC    = HexColor('#7C3AED')
C_TEXT   = HexColor('#1F2937')
C_MUTED  = HexColor('#6B7280')
C_M1_BG  = HexColor('#EFF6FF')
C_AL_BG  = HexColor('#FFFBEB')
C_KEY_BG = HexColor('#F0FDF4')
C_KEY_BD = HexColor('#86EFAC')
C_WARN   = HexColor('#FFF7ED')
C_WARN_BD= HexColor('#F59E0B')
C_RULE   = HexColor('#CBD5E1')
C_LIGHT  = HexColor('#F8F9FA')

SPIN_SYMB = {-1: 'N', 0: '.', +1: 'B'}   # en PDF: N=negro B=blanco
SPIN_DISP = {-1: '●', 0: '·', +1: '○'}
SPINS     = [-1, 0, 1]
E_COLORS  = {
    -2: HexColor('#1848c4'), -1: HexColor('#93C5FD'),
     0: HexColor('#E5E7EB'),
     1: HexColor('#FCA5A5'),  2: HexColor('#C41818'),
}


# ════════════════════════════════════════════════════════════════════════════
# ESTILOS
# ════════════════════════════════════════════════════════════════════════════

def make_styles():
    base = getSampleStyleSheet()
    def S(name, parent='Normal', **kw):
        return ParagraphStyle(name, parent=base[parent], **kw)

    return {
        # Cuerpo
        'body': S('body', fontName='Times-Roman', fontSize=9.5,
                  leading=14, textColor=C_TEXT,
                  alignment=TA_JUSTIFY, spaceAfter=6),
        'body_nb': S('body_nb', fontName='Times-Roman', fontSize=9.5,
                     leading=14, textColor=C_TEXT,
                     alignment=TA_JUSTIFY),
        # Capitulo
        'chap_num': S('chap_num', fontName='Helvetica-Bold', fontSize=11,
                      textColor=C_M1, spaceAfter=2, spaceBefore=0),
        'chap_title': S('chap_title', fontName='Helvetica-Bold', fontSize=18,
                        textColor=C_NAVY, leading=22, spaceAfter=6),
        # Secciones
        'h1': S('h1', fontName='Helvetica-Bold', fontSize=13,
                textColor=C_NAVY, spaceBefore=14, spaceAfter=5, leading=16),
        'h2': S('h2', fontName='Helvetica-Bold', fontSize=11,
                textColor=C_M1, spaceBefore=10, spaceAfter=4, leading=14),
        'h3': S('h3', fontName='Helvetica-BoldOblique', fontSize=10,
                textColor=C_TEXT, spaceBefore=7, spaceAfter=3, leading=13),
        # Figura
        'fig_caption': S('fig_caption', fontName='Times-Italic', fontSize=8,
                         textColor=C_MUTED, alignment=TA_CENTER,
                         spaceBefore=4, spaceAfter=10, leading=11),
        # Equation box
        'eq': S('eq', fontName='Courier-Bold', fontSize=9.5,
                textColor=C_NAVY, alignment=TA_CENTER,
                spaceAfter=4, leading=14),
        # Caption de caja
        'box_title': S('box_title', fontName='Helvetica-Bold', fontSize=9,
                       textColor=C_M1, spaceAfter=3, leading=12),
        'box_body': S('box_body', fontName='Times-Roman', fontSize=9,
                      textColor=C_TEXT, leading=13, spaceAfter=0),
        # Monospace
        'mono': S('mono', fontName='Courier', fontSize=8.5,
                  textColor=HexColor('#374151'), leading=12, spaceAfter=2),
        # Tabla de contenidos
        'toc1': S('toc1', fontName='Helvetica-Bold', fontSize=10,
                  textColor=C_NAVY, spaceBefore=6, spaceAfter=2, leading=14),
        'toc2': S('toc2', fontName='Times-Roman', fontSize=9,
                  textColor=C_TEXT, spaceBefore=1, spaceAfter=1,
                  leftIndent=14, leading=13),
        # Portada
        'cover_title': S('cover_title', fontName='Helvetica-Bold',
                         fontSize=22, textColor=white, alignment=TA_CENTER,
                         leading=28),
        'cover_sub': S('cover_sub', fontName='Helvetica', fontSize=11,
                       textColor=HexColor('#93C5FD'), alignment=TA_CENTER,
                       spaceAfter=6, leading=15),
        'cover_authors': S('cover_authors', fontName='Helvetica-Bold',
                           fontSize=12, textColor=white, alignment=TA_CENTER),
        # Bullet
        'bullet': S('bullet', fontName='Times-Roman', fontSize=9.5,
                    textColor=C_TEXT, leading=14, leftIndent=12,
                    firstLineIndent=-8),
    }


# ════════════════════════════════════════════════════════════════════════════
# DOCUMENTO BASE CON CABECERAS/PIES
# ════════════════════════════════════════════════════════════════════════════

class BookDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, pagesize=A5,
                                  leftMargin=ML, rightMargin=MR,
                                  topMargin=MT, bottomMargin=MB, **kw)
        self.title_text = ''
        self.chap_text  = ''

        body_frame = Frame(ML, MB, TW, PH - MT - MB, id='body',
                           leftPadding=0, rightPadding=0,
                           topPadding=8, bottomPadding=8)
        cover_frame = Frame(0, 0, PW, PH, id='cover', showBoundary=0,
                            leftPadding=0, rightPadding=0,
                            topPadding=0, bottomPadding=0)

        self.addPageTemplates([
            PageTemplate(id='cover',  frames=[cover_frame],
                         onPage=self._on_cover),
            PageTemplate(id='blank',  frames=[body_frame],
                         onPage=self._on_blank),
            PageTemplate(id='body',   frames=[body_frame],
                         onPage=self._on_body),
            PageTemplate(id='chapter',frames=[body_frame],
                         onPage=self._on_chapter),
        ])

    def afterFlowable(self, flowable):
        if hasattr(flowable, '_bookmark_chap'):
            self.chap_text = flowable._bookmark_chap
        if hasattr(flowable, '_toc_entry'):
            lvl, txt, pg = flowable._toc_entry
            self.notify('TOCEntry', (lvl, txt, self.page))

    @staticmethod
    def _on_cover(canvas, doc):
        canvas.saveState()
        # Fondo oscuro
        canvas.setFillColor(C_NAVY)
        canvas.rect(0, 0, PW, PH, fill=1, stroke=0)
        # Banda azul brillante superior
        canvas.setFillColor(C_M1)
        canvas.rect(0, PH - 3*cm, PW, 3*cm, fill=1, stroke=0)
        canvas.restoreState()

    @staticmethod
    def _on_blank(canvas, doc):
        pass

    @staticmethod
    def _on_body(canvas, doc):
        canvas.saveState()
        pg = canvas.getPageNumber()
        # Cabecera
        canvas.setStrokeColor(C_RULE)
        canvas.setLineWidth(0.5)
        canvas.line(ML, PH - MT + 6, PW - MR, PH - MT + 6)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(C_MUTED)
        if pg % 2 == 0:
            canvas.drawString(ML, PH - MT + 9, 'Análisis Entrópico del Juego de Go')
        else:
            canvas.drawRightString(PW - MR, PH - MT + 9, doc.chap_text or 'Jiménez & Mercado')
        # Pie — número de pagina
        canvas.line(ML, MB - 6, PW - MR, MB - 6)
        canvas.setFont('Times-Roman', 8)
        canvas.setFillColor(C_TEXT)
        canvas.drawCentredString(PW / 2, MB - 16, str(pg))
        canvas.restoreState()

    @staticmethod
    def _on_chapter(canvas, doc):
        canvas.saveState()
        # Banda de color al inicio de cada capitulo
        canvas.setFillColor(C_M1_BG)
        canvas.rect(0, PH - MT - 1.4*cm, PW, 1.4*cm, fill=1, stroke=0)
        canvas.setStrokeColor(C_M1)
        canvas.setLineWidth(2)
        canvas.line(0, PH - MT - 1.4*cm, PW, PH - MT - 1.4*cm)
        # Pie
        canvas.setStrokeColor(C_RULE)
        canvas.setLineWidth(0.5)
        canvas.line(ML, MB - 6, PW - MR, MB - 6)
        canvas.setFont('Times-Roman', 8)
        canvas.setFillColor(C_TEXT)
        canvas.drawCentredString(PW / 2, MB - 16, str(canvas.getPageNumber()))
        canvas.restoreState()


# ════════════════════════════════════════════════════════════════════════════
# HELPERS DE CONTENIDO
# ════════════════════════════════════════════════════════════════════════════

def P(text, style_key, S):
    return Paragraph(text, S[style_key])

def SP(n=4):
    return Spacer(1, n)

def HR(color=None, thickness=0.5):
    return HRFlowable(width='100%', thickness=thickness,
                      color=color or C_RULE, spaceAfter=6, spaceBefore=2)


def chapter_opener(num, title, S):
    """Bloque de apertura de capitulo.
    Fuerza nueva pagina SOLO si no estamos ya al principio de una."""
    p_num = Paragraph(f'Capítulo {num}', S['chap_num'])
    p_num._bookmark_chap = f'Cap. {num}: {title}'
    p_num._toc_entry = (0, f'{num}. {title}', 0)
    p_title = Paragraph(title, S['chap_title'])
    return [
        NextPageTemplate('chapter'),
        PageBreak(),          # fuerza pagina nueva con template 'chapter'
        NextPageTemplate('body'),
        SP(44),               # 1.4cm banda + 8pt topPadding del frame = ~48pt
        p_num,
        p_title,
        HR(C_M1, 2),
        SP(8),
    ]


def section(title, S, level=1):
    key = 'h1' if level == 1 else ('h2' if level == 2 else 'h3')
    p = Paragraph(title, S[key])
    if level == 1:
        p._toc_entry = (1, title, 0)
    return p


def fig(path, caption, S, width=None):
    """Figura con pie de figura, auto-escalada para caber en A5.
    No fuerza PageBreak — reportlab la coloca en nueva pagina si no cabe."""
    if not os.path.exists(path):
        return [P(f'[Figura no encontrada: {os.path.basename(path)}]',
                  'mono', S)]
    im_ref = Image(path)
    iw = im_ref.imageWidth or 1
    ih = im_ref.imageHeight or 1
    # Dejar 48pt para caption (2 lineas) + padding
    max_h = FRAME_H - 48
    w = width or FRAME_W
    h = ih * w / iw
    if h > max_h:
        h = max_h
        w = iw * h / ih
    im = Image(path, width=w, height=h)
    im.hAlign = 'CENTER'
    cap = Paragraph(caption, S['fig_caption'])
    # KeepTogether mueve figura+caption a la pagina siguiente si no caben juntos
    return [KeepTogether([SP(6), im, SP(4), cap])]


def color_box(content_items, bg_color, border_color, S, title=None):
    """Caja de color con borde. KeepTogether evita partirla entre paginas."""
    inner = []
    if title:
        inner.append(Paragraph(title, S['box_title']))
    for item in content_items:
        if isinstance(item, str):
            inner.append(Paragraph(item, S['box_body']))
        else:
            inner.append(item)
    t = Table([[inner]], colWidths=[TW - 0.3*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), bg_color),
        ('BOX',          (0, 0), (-1, -1), 1.2, border_color),
        ('TOPPADDING',   (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
        ('LEFTPADDING',  (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
    ]))
    return [KeepTogether([t, SP(6)])]


def interaction_table(H_func, S, title='', accent=C_M1):
    """Tabla 3×3 de interaccion con celdas coloreadas."""
    spins = [-1, 0, +1]
    disp  = {-1: '●', 0: '·', +1: '○'}
    e_bg  = {
        -2: HexColor('#BFDBFE'), -1: HexColor('#DBEAFE'),
         0: HexColor('#F3F4F6'),
         1: HexColor('#FEE2E2'),  2: HexColor('#FECACA'),
    }
    e_fg  = {-2: C_M1, -1: C_M1, 0: C_MUTED, 1: HexColor('#DC2626'), 2: HexColor('#B91C1C')}

    # Cabeceras
    header = ['', '● (−1)', '· (0)', '○ (+1)']
    rows   = [header]
    for s0 in spins:
        row = [Paragraph(f'<b>{disp[s0]} ({s0:+d})</b>',
                         ParagraphStyle('th', fontName='Helvetica-Bold',
                                        fontSize=9, textColor=C_NAVY,
                                        alignment=TA_CENTER))]
        for s1 in spins:
            v = int(round(H_func(s0, s1)))
            lbl = f'{v:+d}' if v != 0 else '0'
            row.append(Paragraph(
                f'<b>{lbl}</b>',
                ParagraphStyle(f'ev{v}', fontName='Helvetica-Bold',
                               fontSize=11, textColor=e_fg.get(v, black),
                               alignment=TA_CENTER)
            ))
        rows.append(row)

    cw = [TW * 0.22, TW * 0.26, TW * 0.26, TW * 0.26]
    t  = Table(rows, colWidths=cw)
    style = [
        # Header row
        ('BACKGROUND',   (0, 0), (-1, 0),  C_LIGHT),
        ('FONTNAME',     (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',     (0, 0), (-1, 0),  8.5),
        ('TEXTCOLOR',    (0, 0), (-1, 0),  C_NAVY),
        ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1),
         [HexColor('#FAFAFA'), white]),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 7),
        ('TOPPADDING',   (0, 0), (-1, -1), 7),
        ('GRID',         (0, 0), (-1, -1), 0.4, C_RULE),
        ('BOX',          (0, 0), (-1, -1), 1.2, accent),
        ('LEFTPADDING',  (0, 0), (0, -1),  8),
    ]
    # Color de celdas por valor
    for ri, s0 in enumerate(spins):
        for ci, s1 in enumerate(spins):
            v = int(round(H_func(s0, s1)))
            if v != 0:
                style.append(('BACKGROUND', (ci+1, ri+1), (ci+1, ri+1),
                               e_bg.get(v, white)))
    t.setStyle(TableStyle(style))

    elements = []
    if title:
        elements.append(Paragraph(title, S['h3']))
    elements.append(KeepTogether([t]))
    elements.append(SP(4))
    return elements


def bullet_list(items, S):
    return [ListFlowable(
        [ListItem(Paragraph(it, S['body']), bulletText='•', leftIndent=14)
         for it in items],
        bulletType='bullet', leftIndent=4,
    ), SP(4)]


def diff_table(S):
    """Tabla de diferencias estructurales M1 vs Alvarado."""
    headers = ['Propiedad', 'M1 (nuestro)', 'Alvarado', 'Impacto']
    rows = [
        ['Vacío (s=0)',      'Activo: H(0,xⱼ)=2xⱼ',  'Invisible: 0',     'M1 ve el territorio'],
        ['Simetría',         'Asimétrico',              'Simétrico',         'El orden i→j importa'],
        ['Valores posibles', '{−2,−1,0,+1,+2}',        '{−1,0,+1}',        'M1: rango mayor'],
        ['Mismo color ●●',   '−1 (atracción)',          '+1 (repulsión)',    'Signos opuestos'],
        ['S_Shannon tabla',  '1.465 nats',              '0.995 nats',       'M1: mayor entropía'],
        ['Influencia territ.','Sí captura',             'No captura',       'Diferencia conceptual'],
    ]
    cw = [TW*0.24, TW*0.24, TW*0.24, TW*0.28]
    data = []
    # Cabecera
    data.append([Paragraph(f'<b>{h}</b>',
                            ParagraphStyle('th', fontName='Helvetica-Bold',
                                           fontSize=8.5, textColor=C_NAVY,
                                           alignment=TA_CENTER))
                 for h in headers])
    for r in rows:
        data.append([Paragraph(r[0],
                                ParagraphStyle('tc0', fontName='Helvetica-Bold',
                                               fontSize=8.5, textColor=C_TEXT)),
                     Paragraph(r[1],
                                ParagraphStyle('tc1', fontName='Times-Roman',
                                               fontSize=8.5, textColor=C_M1)),
                     Paragraph(r[2],
                                ParagraphStyle('tc2', fontName='Times-Roman',
                                               fontSize=8.5, textColor=C_AL)),
                     Paragraph(r[3],
                                ParagraphStyle('tc3', fontName='Times-Italic',
                                               fontSize=8, textColor=C_MUTED))])
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0), C_LIGHT),
        ('ROWBACKGROUNDS',(0, 1),(-1,-1), [HexColor('#FAFAFA'), white]),
        ('GRID',         (0, 0), (-1,-1), 0.4, C_RULE),
        ('BOX',          (0, 0), (-1,-1), 1.0, C_NAVY),
        ('TOPPADDING',   (0, 0), (-1,-1), 6),
        ('BOTTOMPADDING',(0, 0), (-1,-1), 6),
        ('LEFTPADDING',  (0, 0), (-1,-1), 6),
        ('ALIGN',        (0, 0), (0, -1), 'LEFT'),
        ('ALIGN',        (1, 0), (-1,-1), 'CENTER'),
        ('VALIGN',       (0, 0), (-1,-1), 'MIDDLE'),
    ]))
    return [t, SP(8)]


def pattern_entropy_table(S):
    """Tabla de los 19 patrones con metricas."""
    headers = ['ID', 'Patrón', 'N', 'S_sh M1', 'S_sh AL', 'ΔS', 'T_eff M1']
    cw = [TW*0.07, TW*0.30, TW*0.05, TW*0.12, TW*0.12, TW*0.12, TW*0.12]
    data = [[Paragraph(f'<b>{h}</b>',
                        ParagraphStyle('ph', fontName='Helvetica-Bold',
                                       fontSize=7.5, textColor=C_NAVY,
                                       alignment=TA_CENTER))
             for h in headers]]
    for pid, desc, stones in PATTERNS:
        board = board_from_stones(BOARD_SIZE, stones)
        bM1 = all_bond_energies_nuestro(board)
        bAL = all_bond_energies_alvarado(board)
        Ssh_M1 = bond_shannon_entropy(bM1)
        Ssh_AL = bond_shannon_entropy(bAL)
        T = bond_T_eff(bM1)
        T_s = 'inf' if not np.isfinite(T) else f'{T:.2f}'
        ds = Ssh_M1 - Ssh_AL
        ds_col = C_M1 if ds > 0 else C_AL
        data.append([
            Paragraph(pid, ParagraphStyle('td0', fontName='Helvetica-Bold',
                                           fontSize=7.5, textColor=C_NAVY,
                                           alignment=TA_CENTER)),
            Paragraph(desc[:32], ParagraphStyle('td1', fontName='Times-Roman',
                                                 fontSize=7.5, textColor=C_TEXT)),
            Paragraph(str(len(stones)), ParagraphStyle('td2', fontName='Times-Roman',
                                                        fontSize=7.5, textColor=C_MUTED,
                                                        alignment=TA_CENTER)),
            Paragraph(f'{Ssh_M1:.3f}', ParagraphStyle('td3', fontName='Courier',
                                                        fontSize=7.5, textColor=C_M1,
                                                        alignment=TA_RIGHT)),
            Paragraph(f'{Ssh_AL:.3f}', ParagraphStyle('td4', fontName='Courier',
                                                        fontSize=7.5, textColor=C_AL,
                                                        alignment=TA_RIGHT)),
            Paragraph(f'{ds:+.3f}',   ParagraphStyle('td5', fontName='Courier-Bold',
                                                        fontSize=7.5, textColor=ds_col,
                                                        alignment=TA_RIGHT)),
            Paragraph(T_s,           ParagraphStyle('td6', fontName='Courier',
                                                     fontSize=7.5, textColor=C_MUTED,
                                                     alignment=TA_RIGHT)),
        ])
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1, 0), C_NAVY),
        ('TEXTCOLOR',     (0,0),(-1, 0), white),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [C_M1_BG, white]),
        ('GRID',          (0,0),(-1,-1), 0.3, C_RULE),
        ('BOX',           (0,0),(-1,-1), 1.2, C_M1),
        ('TOPPADDING',    (0,0),(-1,-1), 4),
        ('BOTTOMPADDING', (0,0),(-1,-1), 4),
        ('LEFTPADDING',   (0,0),(-1,-1), 4),
        ('RIGHTPADDING',  (0,0),(-1,-1), 4),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
    ]))
    return [t, SP(6)]


# ════════════════════════════════════════════════════════════════════════════
# PORTADA (pagina de titulo dibujada sobre el canvas)
# ════════════════════════════════════════════════════════════════════════════

def draw_cover(canvas, doc):
    canvas.saveState()

    # Fondo navy
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, 0, PW, PH, fill=1, stroke=0)

    # Banda superior azul
    canvas.setFillColor(C_M1)
    canvas.rect(0, PH - 2.8*cm, PW, 2.8*cm, fill=1, stroke=0)

    # Banda inferior delgada
    canvas.setFillColor(HexColor('#1E3A5F'))
    canvas.rect(0, 0, PW, 1.5*cm, fill=1, stroke=0)

    # Etiqueta superior
    canvas.setFillColor(white)
    canvas.setFont('Helvetica-Bold', 9)
    canvas.drawCentredString(PW/2, PH - 1.4*cm, 'ANÁLISIS ENTRÓPICO · ISING CLÁSICO · JUEGO DE GO')

    # Titulo principal
    canvas.setFont('Helvetica-Bold', 21)
    canvas.setFillColor(white)
    canvas.drawCentredString(PW/2, PH - 5.5*cm, 'Análisis de Información')
    canvas.drawCentredString(PW/2, PH - 7.3*cm, 'Entrópica en el')
    canvas.setFillColor(HexColor('#93C5FD'))
    canvas.drawCentredString(PW/2, PH - 9.1*cm, 'Juego de Go')

    # Subtitulo
    canvas.setFont('Helvetica', 10)
    canvas.setFillColor(HexColor('#93C5FD'))
    canvas.drawCentredString(PW/2, PH - 10.8*cm,
        'Modelo M1 vs Atomic-Go (Alvarado et al., 2019)')

    # Linea separadora
    canvas.setStrokeColor(HexColor('#334155'))
    canvas.setLineWidth(1)
    canvas.line(1.5*cm, PH - 11.8*cm, PW - 1.5*cm, PH - 11.8*cm)

    # Autores
    canvas.setFont('Helvetica-Bold', 10.5)
    canvas.setFillColor(white)
    canvas.drawCentredString(PW/2, PH - 13.2*cm,
        'Leonardo Jiménez Martínez')
    canvas.drawCentredString(PW/2, PH - 14.4*cm,
        'Mario Mercado Sánchez')
    canvas.setFont('Helvetica', 8.5)
    canvas.setFillColor(HexColor('#94A3B8'))
    canvas.drawCentredString(PW/2, PH - 15.4*cm,
        'Repositorio Ometitlan · UNAM · 2026')

    # Caja del paper
    canvas.setFillColor(HexColor('#1E3A5F'))
    canvas.roundRect(1.2*cm, PH-21.5*cm, PW-2.4*cm, 3.5*cm, 6, fill=1, stroke=0)
    canvas.setFont('Helvetica-Oblique', 8)
    canvas.setFillColor(HexColor('#93C5FD'))
    canvas.drawCentredString(PW/2, PH - 18.9*cm, 'Paper relacionado:')
    canvas.setFont('Times-Italic', 8.5)
    canvas.setFillColor(white)
    canvas.drawCentredString(PW/2, PH - 19.8*cm,
        '"Pattern Acquisition and Comparative')
    canvas.drawCentredString(PW/2, PH - 20.7*cm,
        'Analysis in the Game of Go"')
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(HexColor('#94A3B8'))
    canvas.drawCentredString(PW/2, PH - 21.4*cm,
        'Jiménez Martínez & Sesma González — Journal of Go Studies, 2025')

    # Logo / pie de portada
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(HexColor('#475569'))
    canvas.drawCentredString(PW/2, 0.6*cm, 'github.com/ometitlan/Project-Quantum-Go')

    canvas.restoreState()


# ════════════════════════════════════════════════════════════════════════════
# CONTENIDO POR CAPITULOS
# ════════════════════════════════════════════════════════════════════════════

def build_content(S):
    story = []
    R     = RESULTS

    # ── PORTADA (page 1) — dibujada por onPage, solo necesitamos un placeholder ──
    story += [Spacer(1, 1)]  # minimal: onPage dibuja todo
    story += [NextPageTemplate('blank'), PageBreak()]

    # ── REVERSO PORTADA (colofon, page 2, template 'blank') ─────────────────
    colofonH = PH - MT - MB  # altura disponible del frame body = ~462pt
    story += [
        SP(colofonH * 0.58),
        Paragraph('<b>Análisis de Información Entrópica en el Juego de Go</b>',
                  S['body']),
        Paragraph('Jiménez Martínez, L. &amp; Mercado Sánchez, M.', S['body']),
        HR(C_RULE),
        Paragraph('Repositorio: <i>github.com/ometitlan/Project-Quantum-Go</i>',
                  S['body']),
        Paragraph('Primera edición digital · Julio 2026', S['body']),
        SP(8),
        Paragraph(
            'Los modelos, análisis y código son 100% clásicos. El nombre del '
            'repositorio (Quantum-Go) es histórico y no implica computación '
            'cuántica.', S['body']),
    ]

    # ── TABLA DE CONTENIDOS ──────────────────────────────────────────────────
    story += [NextPageTemplate('body'), PageBreak()]
    story += [
        SP(12),
        Paragraph('Tabla de Contenidos', S['chap_title']),
        HR(C_M1, 2),
        SP(10),
    ]
    toc_entries = [
        (0, '1.', 'Introducción'),
        (1, '1.1', 'Contexto y motivación'),
        (1, '1.2', 'Nota metodológica: nivel de bono'),
        (0, '2.', 'Nuestro Modelo M1'),
        (1, '2.1', 'Hamiltoniano y parámetros'),
        (1, '2.2', 'Tabla de interacción y propiedades'),
        (1, '2.3', 'Mapas de energía — 19 patrones'),
        (1, '2.4', 'Dashboard termodinámico'),
        (0, '3.', 'Modelo de Referencia: Atomic-Go'),
        (1, '3.1', 'Hamiltoniano Alvarado et al. (2019)'),
        (1, '3.2', 'Tabla de interacción y propiedades'),
        (1, '3.3', 'Mapas de energía — 19 patrones'),
        (1, '3.4', 'Dashboard termodinámico'),
        (0, '4.', 'Comparación: Tabla de Interacción'),
        (0, '5.', 'Comparación: Análisis de Entropía'),
        (1, '5.1', 'Shannon, Boltzmann y T_eff'),
        (1, '5.2', 'Tabla numérica — 19 patrones'),
        (1, '5.3', 'Distribución de bonos'),
        (0, '6.', 'Hallazgos Principales'),
        (0, '7.', 'Límites del Marco Actual'),
        (0, '8.', 'Conclusiones'),
        (0, '9.', 'Referencias'),
    ]
    for lvl, num, title in toc_entries:
        style_key = 'toc1' if lvl == 0 else 'toc2'
        dot_leader = '.' * 55
        story.append(
            Paragraph(f'<b>{num}</b> &nbsp;&nbsp; {title}',
                      S[style_key])
        )

    # ══════════════════════════════════════════════════════════════════════
    # CAP. 1 — INTRODUCCION
    # ══════════════════════════════════════════════════════════════════════
    story += chapter_opener('1', 'Introducción', S)
    story.append(section('1.1  Contexto y motivación', S))
    story += [
        P('El juego de Go es uno de los problemas más estudiados en inteligencia '
          'artificial y teoría de juegos. Sobre un tablero de 19×19 intersecciones, '
          'dos jugadores alternan la colocación de piedras negras y blancas con el '
          'objetivo de controlar territorio. La complejidad combinatoria del Go '
          'supera a la del ajedrez en más de cien órdenes de magnitud, lo que lo '
          'convierte en un banco de prueba excepcional para modelos físicos y '
          'estadísticos.', 'body', S),
        P('El presente trabajo aplica el formalismo del <b>modelo de Ising clásico</b> '
          'para asignar energías de interacción a las configuraciones de piedras sobre '
          'el tablero, y estudia cómo evolucionan las medidas de entropía a lo largo '
          'de una partida y entre distintos patrones de apertura.', 'body', S),
        P('Se comparan dos interpretaciones físicas distintas del mismo problema: '
          'el <b>modelo M1</b> desarrollado por Jiménez Martínez y Mercado Sánchez '
          'en el repositorio Ometitlan, y el modelo <b>Atomic-Go</b> propuesto por '
          'Alvarado et al. (2019) como referencia bibliográfica.',
          'body', S),
        SP(4),
        section('1.2  Nota metodológica: nivel de análisis por bono', S),
        P('La comparación entre modelos se realiza al nivel de <b>bono dirigido</b>: '
          'cada par de celdas adyacentes (i→j) se evalúa como una interacción '
          'binaria independiente. Este nivel de análisis revela correctamente la '
          'asimetría de M1 y la invisibilidad del vacío en Alvarado, propiedades '
          'que quedan ocultas al agregar los 4 vecinos por celda.', 'body', S),
    ]
    story += color_box([
        'Mapeo de spins (ambos modelos):',
        '  Piedra negra (B) → s = −1',
        '  Vacío         (.) → s =  0',
        '  Piedra blanca (W) → s = +1',
        'Tablero de análisis: 9×9, esquina superior izquierda (patrones de apertura).',
    ], C_LIGHT, C_M1, S, title='Convención')

    # ══════════════════════════════════════════════════════════════════════
    # CAP. 2 — NUESTRO MODELO M1
    # ══════════════════════════════════════════════════════════════════════
    story += chapter_opener('2', 'Nuestro Modelo M1', S)
    story.append(section('2.1  Hamiltoniano y parámetros', S))
    story += color_box([
        Paragraph('<b>H(sᵢ, sⱼ) = sᵢ + 2·sⱼ − sᵢ·sⱼ² − sᵢ²·sⱼ</b>',
                  ParagraphStyle('eq2', fontName='Courier-Bold', fontSize=10.5,
                                 textColor=C_NAVY, alignment=TA_CENTER)),
    ], C_M1_BG, C_M1, S, title='Hamiltoniano M1 (bono dirigido sᵢ → sⱼ)')
    story += [
        P('Los parámetros del Hamiltoniano son: h₀ = 1 (campo en el origen), '
          'h₁ = 2 (campo en el destino), K = −1 (acoplamiento cuadrático cruzado), '
          'L = −1 (acoplamiento cuadrático cruzado inverso). Los coeficientes de '
          'distancia siguen la ley de potencia coef(d) = 1/d²:', 'body', S),
        Paragraph('coef(d=1) = 1.000   |   coef(d=2) = 0.250   |   coef(d=3) = 0.111',
                  S['mono']),
        SP(4),
        section('2.2  Tabla de interacción y propiedades', S),
    ]
    story += interaction_table(H_nuestro, S,
        title='Tabla de interacción M1: H(sᵢ, sⱼ)', accent=C_M1)
    story += bullet_list([
        '<b>Rango de valores:</b> {−2, −1, 0, +1, +2} — cinco estados posibles.',
        '<b>Asimetría:</b> H(i→j) ≠ H(j→i) para 6 de los 9 pares dirigidos.',
        '<b>Vacío activo:</b> H(0, xⱼ) = 2xⱼ ≠ 0 — la celda vacía siente a sus vecinos.',
        '<b>Mismo color:</b> H(●,●) = H(○,○) = −1 (atracción entre iguales).',
        '<b>Colores distintos:</b> H(●,○) = +1 (repulsión entre colores distintos).',
        '<b>Entropía Shannon de la tabla:</b> S = 1.465 nats.',
    ], S)
    story += color_box(
        ['El modelo M1 captura la <b>influencia territorial</b>: las intersecciones '
         'vacías adyacentes a una piedra negra reciben energía −2 (atracción), '
         'y las adyacentes a una piedra blanca reciben +2 (repulsión). '
         'Esto modela el campo de influencia que ejerce un grupo sobre el '
         'espacio circundante — concepto fundamental en la estrategia del Go.'],
        C_M1_BG, C_M1, S, title='Interpretación física')

    story.append(section('2.3  Mapas de energía — 19 patrones de apertura', S))
    story += fig(os.path.join(R, 'energy_grid_M1.png'),
        'Figura 1. Mapas de energía del Modelo M1 para los 19 patrones de '
        'apertura (Tabla I del paper). Azul = energía negativa (atracción). '
        'Rojo = energía positiva (repulsión).', S)

    story.append(section('2.4  Dashboard termodinámico', S))
    story += fig(os.path.join(R, 'dashboard_M1.png'),
        'Figura 2. Dashboard M1: mini-tableros ordenados por S_Shannon (izq. = '
        'más ordenado), dispersión T_eff vs S, y ranking completo.', S)

    # ══════════════════════════════════════════════════════════════════════
    # CAP. 3 — MODELO ALVARADO
    # ══════════════════════════════════════════════════════════════════════
    story += chapter_opener('3', 'Modelo de Referencia: Atomic-Go', S)
    story.append(section('3.1  Hamiltoniano Alvarado et al. (2019)', S))
    story += color_box([
        Paragraph('<b>H(xᵢ, xⱼ) = xᵢ · xⱼ</b>',
                  ParagraphStyle('eq3', fontName='Courier-Bold', fontSize=10.5,
                                 textColor=C_NAVY, alignment=TA_CENTER)),
    ], C_AL_BG, C_AL, S, title='Hamiltoniano Alvarado — Atomic-Go (μ = 0, wᵢⱼ = 1)')
    story += [
        P('El modelo Atomic-Go es la variante más simple del trabajo de Alvarado '
          'et al. (2019). El Hamiltoniano es el producto de spins sin campo externo '
          '(μ = 0) y pesos uniformes (w = 1). El paper describe además Generative '
          'Atomic-Go (con red bayesiana profunda) y Molecular-Go (μ = 1, Common '
          'Fate Graphs). En este análisis se implementa exclusivamente Atomic-Go.',
          'body', S),
        section('3.2  Tabla de interacción y propiedades', S),
    ]
    story += interaction_table(H_alvarado, S,
        title='Tabla de interacción Alvarado: H(xᵢ, xⱼ)', accent=C_AL)
    story += bullet_list([
        '<b>Rango de valores:</b> {−1, 0, +1} — tres estados posibles.',
        '<b>Simetría:</b> H(i→j) = H(j→i) siempre — el orden de los spins no importa.',
        '<b>Vacío invisible:</b> H(0, xⱼ) = 0 siempre — el vacío no participa.',
        '<b>Mismo color:</b> H(●,●) = H(○,○) = +1 (repulsión entre iguales).',
        '<b>Colores distintos:</b> H(●,○) = −1 (atracción entre colores distintos).',
        '<b>Entropía Shannon de la tabla:</b> S = 0.995 nats.',
    ], S)
    story += color_box(
        ['El vacío (x=0) es <b>invisible</b>: equivale a no existir en la red de '
         'interacciones. Esto implica que el modelo solo "ve" las piedras ya '
         'colocadas, ignorando el espacio libre que rodea a los grupos. '
         'El signo de la interacción mismo-color es opuesto al de M1: '
         'Alvarado asume una convención <i>antiferromagnética</i> donde '
         'el estado de mínima energía mezcla colores.'],
        C_AL_BG, C_AL, S, title='Interpretación física')

    story.append(section('3.3  Mapas de energía — 19 patrones de apertura', S))
    story += fig(os.path.join(R, 'energy_grid_alvarado.png'),
        'Figura 3. Mapas de energía del Modelo Alvarado para los 19 patrones. '
        'Notar que los patrones con piedras aisladas producen energía nula '
        '(el vacío no interactúa en este modelo).', S)

    story.append(section('3.4  Dashboard termodinámico', S))
    story += fig(os.path.join(R, 'dashboard_alvarado.png'),
        'Figura 4. Dashboard Alvarado: misma estructura que Figura 2. '
        'Muchos patrones de apertura tempranos dan S_Shannon = 0.', S)

    # ══════════════════════════════════════════════════════════════════════
    # CAP. 4 — COMPARACION TABLA DE INTERACCION
    # ══════════════════════════════════════════════════════════════════════
    story += chapter_opener('4', 'Comparación: Tabla de Interacción', S)
    story += [
        P('En este capítulo se comparan directamente las tablas de interacción '
          'de ambos modelos mediante cuatro representaciones visuales y una '
          'tabla de diferencias estructurales.', 'body', S),
        section('4.1  Diferencias estructurales clave', S),
    ]
    story += diff_table(S)
    story += fig(os.path.join(R, 'interaction_comparison.png'),
        'Figura 5. Cuatro representaciones de la tabla de interacción binaria: '
        'heatmaps 3×3 (M1, Alvarado, diferencia M1−Alvarado), gráfico de barras '
        'comparativo para los 9 pares dirigidos.', S)
    story += fig(os.path.join(R, 'bond_interaction_graph.png'),
        'Figura 6. Grafo de nodos dirigido. Flechas coloreadas por energía del bono. '
        'La asimetría de M1 es visible en las flechas de distinto grosor entre '
        'el mismo par de nodos.', S)

    # ══════════════════════════════════════════════════════════════════════
    # CAP. 5 — COMPARACION ENTROPIA
    # ══════════════════════════════════════════════════════════════════════
    story += chapter_opener('5', 'Comparación: Análisis de Entropía', S)
    story += [
        P('Se comparan cuatro métricas de entropía para los 19 patrones de apertura. '
          'Todas se calculan sobre la distribución de energías de bono del tablero '
          'completo:', 'body', S),
        P('(1) <b>S_Shannon</b> — entropía de Shannon ponderada por |E_i|, intensiva. '
          '(2) <b>S_Gibbs</b> — entropía de la distribución canónica a T_eff '
          '(Gibbs: p_b = e^{−E_b/T_eff}/Z). '
          '(3) <b>T_eff</b> = σ²(E)/|⟨E⟩|, temperatura efectiva. '
          '(4) <b>S_B = ln W</b> — entropía de Boltzmann termodinámica: cuenta '
          'el número de microestados W = N!/∏n_k! compatibles con el histograma '
          'de energías de bono observado. Extensiva, escala con N.',
          'body', S),
        section('5.1  Shannon, Gibbs y T_eff', S),
    ]
    story += fig(os.path.join(R, 'entropy_comparison.png'),
        'Figura 7. Comparación S_Shannon, S_Gibbs y T_eff. Fila 1: distribución '
        'de la tabla base (9 pares). Fila 2: S_Shannon por patrón. Fila 3: S_Gibbs '
        'y T_eff. Fila 4: diagramas de dispersión.', S)
    story += fig(os.path.join(R, 'bond_entropy_compare.png'),
        'Figura 8. Entropía de Shannon M1 (azul) vs Alvarado (naranja). '
        'M1 supera a Alvarado en 19/19 patrones. '
        'Diferencia media: 1.92 nats.', S)

    story.append(section('5.2  Tabla numérica — 19 patrones', S))
    story += pattern_entropy_table(S)
    story += [
        P('<i>Nota: ΔS_Shannon = S_sh M1 − S_sh Alvarado &gt; 0 en los 19 patrones. '
          'T_eff = ∞ indica que la media de energías es ≈ 0 (dos colores '
          'se compensan). S_Gibbs ≈ ln(N_activos) en todos los casos por la misma razón.</i>',
          'fig_caption', S),
        section('5.3  Entropía de Boltzmann  S_B = ln W', S),
        P('La entropía de Boltzmann termodinámica S_B = ln W cuenta el número de '
          'microestados W = N! / ∏ n_k! compatibles con el macroestado definido '
          'por el histograma observado de energías de bono (n_k = número de bonos '
          'con energía E_k). A diferencia de S_Gibbs, no asume equilibrio térmico '
          'ni temperatura: solo cuenta combinaciones.', 'body', S),
        P('Relación de Stirling (N grande): S_B ≈ N · H_hist donde '
          'H_hist = −Σ p_k ln p_k con p_k = n_k/N. '
          'Para N finito con algunos n_k pequeños, N·H_hist ≥ S_B '
          '(Stirling sobreestima). S_B es extensiva: escala con el número total '
          'de bonos N, mientras que S_Shannon y S_Gibbs son intensivas.',
          'body', S),
    ]
    story += fig(os.path.join(R, 'entropy_boltzmann_lnW.png'),
        'Figura 9b. Entropía de Boltzmann S_B = ln W. Fila 1: S_B por patrón '
        '(M1 > Alvarado en 19/19; Alvarado = 0 cuando no hay interacciones '
        'activas). Fila 2: verificación Stirling — S_B/N (barras) vs H_hist '
        '(puntos) deben coincidir. Fila 3: scatter M1 vs Alvarado, '
        'extensividad y tabla resumen.', S)
    story += [
        section('5.4  Distribución de energías de bono', S),
    ]
    story += fig(os.path.join(R, 'bond_distribution.png'),
        'Figura 9. Histogramas de frecuencia de valores de bono para 6 patrones '
        'representativos. Superior: M1 (5 valores, distribución rica). '
        'Inferior: Alvarado (3 valores, concentrado en 0).', S)

    # ══════════════════════════════════════════════════════════════════════
    # CAP. 6 — HALLAZGOS
    # ══════════════════════════════════════════════════════════════════════
    story += chapter_opener('6', 'Hallazgos Principales', S)

    hallazgos = [
        ('H1', C_M1, C_M1_BG,
         'M1 supera a Alvarado en entropía de Shannon (19/19 patrones)',
         'El modelo M1 asigna mayor S_Shannon a los 19 patrones, con una brecha media '
         'de 1.92 nats y correlación r = 0.83 entre modelos. Los patrones que un '
         'modelo considera complejos también lo son para el otro; la diferencia es '
         'de escala (rango de valores) y de qué interacciones se cuentan (vacío '
         'activo vs. invisible).'),
        ('H2', C_AL, C_AL_BG,
         'Signos invertidos: mismo color se atrae en M1 y se repele en Alvarado',
         'H(●,●) = −1 en M1 frente a +1 en Alvarado. Las piedras del mismo color '
         'se atraen en M1 (convención ferromagnética) y se repelen en Alvarado '
         '(antiferromagnética). Esta diferencia cualitativa cambia la interpretación '
         'física de la cohesión de un grupo.'),
        ('H3', HexColor('#15803D'), C_KEY_BG,
         'M1 captura influencia territorial; Alvarado solo captura contacto directo',
         'H(0, xⱼ) = 2xⱼ ≠ 0 en M1 hace que las celdas vacías próximas a piedras '
         'tengan energía no nula, modelando el campo territorial. En Alvarado, '
         'el vacío es energéticamente neutro — el modelo no puede representar '
         'este concepto central del Go.'),
        ('H4', C_WARN_BD, C_WARN,
         'El marco de Ising de dos colores no produce enfriamiento termodinámico',
         'T_eff = σ²(E)/|⟨E⟩| diverge durante toda la partida real analizada. '
         'La coexistencia obligatoria de negro y blanco mantiene ⟨E⟩ ≈ 0, '
         'haciendo divergir T_eff y saturar S_Gibbs ≈ ln(N_activos). '
         'El "enfriamiento" del Go existe, pero vive en la variable de '
         'ownership territorial, no en la distribución de energías de bono.'),
        ('H5', C_ACC, HexColor('#FAF5FF'),
         'Los modelos convergen al llenarse el tablero',
         'La brecha ΔS disminuye de ~1.7 nats (apertura) a ~0.8 nats (yose). '
         'Conforme el tablero se llena, la proporción de bonos piedra-piedra '
         '(evaluados de forma similar por ambos modelos) crece respecto a los '
         'bonos vacío-piedra (solo visibles para M1). Los modelos convergen '
         'en el final de partida.'),
    ]

    for code, border, bg, title, body in hallazgos:
        story += color_box(
            [Paragraph(body, S['box_body'])],
            bg, border, S, title=f'{code} — {title}')

    # ══════════════════════════════════════════════════════════════════════
    # CAP. 7 — LIMITES
    # ══════════════════════════════════════════════════════════════════════
    story += chapter_opener('7', 'Límites del Marco Actual', S)

    limites = [
        ('L1', 'T_eff no captura el enfriamiento estratégico del Go',
         'La fórmula T_eff = σ²/|⟨E⟩| diverge cuando los dos colores balancean '
         'las interacciones. Una alternativa viable sería calcular la entropía '
         'de <i>ownership</i> (a quién pertenece cada intersección), que sí '
         'debería decrecer al establecerse el territorio.'),
        ('L2', 'S_Shannon crece mecánicamente con el número de jugadas',
         'Parte del crecimiento de S_Shannon es simplemente que hay más bonos '
         'activos, no que la posición sea más compleja. Para aislar la complejidad '
         'sería necesario normalizar por log(N_bonos_activos) o calcular '
         'entropía por bono en lugar de sobre todos los bonos del tablero.'),
        ('L3', 'S_Gibbs no distingue los modelos a nivel de tabla completa',
         'Cuando T_eff → ∞, la distribución de Gibbs se vuelve uniforme y '
         'S_Gibbs → ln(N_activos). Ambos modelos convergen a S_Gibbs ≈ ln(9) '
         'sobre los 9 pares base porque sus promedios de energía son cero. '
         'S_B = ln W sí distingue: M1 da W = 10 080 microestados, '
         'Alvarado W = 756 (factores {−2,−1,0,+1,+2} vs {−1,0,+1}).'),
        ('L4', 'Solo se implementó Atomic-Go, no Molecular-Go',
         'El paper de Alvarado describe tres variantes. Molecular-Go (μ=1, CFGs, '
         'pesos tácticos) incluye evaluación de ojos, redes y escaleras, '
         'lo que cambiaría sustancialmente el espacio de energías comparado.'),
    ]

    for code, title, body in limites:
        story += color_box([body], C_WARN, C_WARN_BD, S, title=f'{code} — {title}')

    story.append(section('Trabajo futuro sugerido', S))
    story += bullet_list([
        'Calcular entropía de ownership y verificar si decrece durante la partida.',
        'Normalizar S_Shannon por log(N_bonos_activos) para comparar densidades.',
        'Implementar Molecular-Go (μ=1) e incluirlo en la comparación.',
        'Definir T_eff basada en gradiente territorial en lugar de media de energía.',
        'Extender el análisis a partidas completas de 19×19 con jugadores profesionales.',
    ], S)

    # ══════════════════════════════════════════════════════════════════════
    # CAP. 8 — CONCLUSIONES
    # ══════════════════════════════════════════════════════════════════════
    story += chapter_opener('8', 'Conclusiones', S)

    conclusiones = [
        ('C1', 'Concordancia relativa, discrepancia física',
         'La correlación r = 0.83 entre S_Shannon M1 y Alvarado indica que ambos '
         'modelos identifican correctamente qué posiciones son más ricas. Difieren '
         'en la magnitud, en qué interacciones cuentan y en el signo de las '
         'interacciones mismo-color.'),
        ('C2', 'El desacuerdo más importante: signo de la interacción mismo-color',
         'M1 asigna −1 a ●● y ○○ (atracción). Alvarado asigna +1 (repulsión). '
         'Esta diferencia implica interpretaciones físicamente opuestas sobre la '
         'cohesión de un grupo de piedras.'),
        ('C3', 'M1 captura influencia territorial; Alvarado solo contacto directo',
         'La actividad del vacío en M1 modela un efecto de campo crucial en el Go. '
         'Este efecto es invisible en Alvarado.'),
        ('C4', 'El marco de Ising de dos colores no produce enfriamiento',
         'La coexistencia de dos colores mantiene ⟨E⟩ ≈ 0 → T_eff → ∞ → '
         'S_Gibbs → ln(N_activos) durante toda la partida. '
         'S_B = ln W sí diferencia los modelos (M1: W = 10 080 en tabla base vs '
         'Alvarado: W = 756), pero tampoco decrece: más piedras = más bonos activos '
         '= más W. El "enfriamiento" del Go requiere una variable de ownership '
         'territorial, no de energía de bono.'),
        ('C5', 'Los modelos convergen en el final de partida',
         'La brecha ΔS disminuye de ~1.7 nats (apertura) a ~0.8 nats (yose). '
         'La mayor diferencia entre modelos ocurre donde el tablero tiene '
         'más espacio libre y la influencia territorial de M1 es más significativa.'),
    ]

    for code, title, body in conclusiones:
        story += [KeepTogether([
            Paragraph(f'<b>{code} — {title}</b>', S['h3']),
            Paragraph(body, S['body']),
            SP(6),
        ])]

    # ══════════════════════════════════════════════════════════════════════
    # CAP. 9 — REFERENCIAS
    # ══════════════════════════════════════════════════════════════════════
    story += chapter_opener('9', 'Referencias', S)
    refs = [
        ('[1] Alvarado, M., Rojas-Domínguez, A. & Barradas-Bautista, D. (2019). '
         '<i>Modeling the Game of Go by Ising Hamiltonian, Deep Belief Networks and '
         'Common Fate Graphs</i>. IEEE Access, 7, 120117–120127.'),
        ('[2] Jiménez Martínez, L. & Sesma González, A.A. (2025). '
         '<i>Pattern Acquisition and Comparative Analysis in the Game of Go</i>. '
         'Journal of Go Studies, Vol. 19 No. 2.'),
        ('[3] Mercado Sánchez, M. & Jiménez Martínez, L. (2026). '
         '<i>Repositorio Ometitlan: Project-Quantum-Go</i>. '
         'github.com/ometitlan/Project-Quantum-Go'),
        ('[4] Shannon, C.E. (1948). <i>A Mathematical Theory of Communication</i>. '
         'Bell System Technical Journal, 27(3), 379–423.'),
        ('[5] Boltzmann, L. (1877). <i>Über die Beziehung zwischen dem zweiten '
         'Hauptsatze der mechanischen Wärmetheorie und der '
         'Wahrscheinlichkeitsrechnung</i>. Wiener Berichte, 76, 373–435.'),
    ]
    for ref in refs:
        story.append(Paragraph(ref, S['body']))
        story.append(SP(6))

    return story


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    print(f'\nGenerando libro: {OUT}')
    S = make_styles()

    doc = BookDoc(OUT,
                  title='Análisis de Información Entrópica en el Juego de Go',
                  author='Jiménez Martínez, L. & Mercado Sánchez, M.')

    story = build_content(S)

    # La portada se dibuja via onPage del template 'cover'
    # Sobreescribimos _on_cover con nuestra funcion detallada
    for tmpl in doc.pageTemplates:
        if tmpl.id == 'cover':
            tmpl.onPage = draw_cover

    doc.multiBuild(story)

    sz = os.path.getsize(OUT) / 1024 / 1024
    print(f'Listo: {OUT}  ({sz:.1f} MB)')


if __name__ == '__main__':
    main()
