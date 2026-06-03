import os
import platform
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Регистрируем шрифты с поддержкой кириллицы ────────────────────────────────
def _register_fonts():
    if platform.system() == 'Windows':
        fonts_dir = "C:/Windows/Fonts/"
        font_map = {
            'Regular': ('Arial',       fonts_dir + 'arial.ttf'),
            'Bold':    ('Arial-Bold',  fonts_dir + 'arialbd.ttf'),
            'Italic':  ('Arial-It',    fonts_dir + 'ariali.ttf'),
        }
    else:
        # Linux/Mac — ищем DejaVu рядом с файлом
        base = os.path.dirname(os.path.abspath(__file__))
        font_map = {
            'Regular': ('Arial',      os.path.join(base, 'DejaVuSans.ttf')),
            'Bold':    ('Arial-Bold', os.path.join(base, 'DejaVuSans-Bold.ttf')),
            'Italic':  ('Arial-It',   os.path.join(base, 'DejaVuSans.ttf')),
        }

    for key, (name, path) in font_map.items():
        try:
            pdfmetrics.registerFont(TTFont(name, path))
        except Exception as e:
            print(f"[pdf] Не удалось зарегистрировать шрифт {name}: {e}")

_register_fonts()

FONT_REG  = 'Arial'
FONT_BOLD = 'Arial-Bold'
FONT_IT   = 'Arial-It'

# ── Цвета бренда ──────────────────────────────────────────────────────────────
BRAND_BLUE = colors.HexColor('#0088CC')
DARK_TEXT  = colors.HexColor('#0F172A')
MUTED_TEXT = colors.HexColor('#64748B')
LIGHT_BG   = colors.HexColor('#F8FAFC')
BORDER     = colors.HexColor('#E2E8F0')
AMBER      = colors.HexColor('#F59E0B')
EMERALD    = colors.HexColor('#10B981')


def build_pdf(workout_result: dict, workout_id: int, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    story  = []

    # ── Стили ─────────────────────────────────────────────────────────────────
    def style(name, font=FONT_REG, size=9, color=DARK_TEXT, **kw):
        return ParagraphStyle(name, parent=styles['Normal'],
                              fontName=font, fontSize=size,
                              textColor=color, **kw)

    title_s    = style('Title',    FONT_BOLD, 22, DARK_TEXT,   spaceAfter=6,  leading=26)
    subtitle_s = style('Subtitle', FONT_REG,  10, BRAND_BLUE,  spaceAfter=16, leading=14)
    section_s  = style('Section',  FONT_BOLD, 13, DARK_TEXT,   spaceBefore=20, spaceAfter=8, leading=16)
    body_s     = style('Body',     FONT_REG,   9, MUTED_TEXT,  leading=13)
    bold_s     = style('Bold',     FONT_BOLD,  9, DARK_TEXT,   leading=13)
    small_s    = style('Small',    FONT_REG,   8, MUTED_TEXT,  leading=11)
    brand_s    = style('Brand',    FONT_REG,   9, MUTED_TEXT,  spaceAfter=12)
    footer_s   = style('Footer',   FONT_REG,   8, MUTED_TEXT,  alignment=TA_CENTER)
    amber_s    = style('Amber',    FONT_BOLD,  9, AMBER,       leading=13)
    emerald_s  = style('Emerald',  FONT_BOLD,  9, EMERALD,     leading=13)
    tip_s      = style('Tip',      FONT_REG,   9, MUTED_TEXT,  leading=13, leftIndent=8)
    muscles_s  = style('Muscles',  FONT_REG,   8, MUTED_TEXT,  leading=11, leftIndent=8, spaceBefore=2)
    extitle_s  = style('ExTitle',  FONT_BOLD, 10, DARK_TEXT,   spaceBefore=8, spaceAfter=4)

    r    = workout_result
    meta = r.get('meta', {})

    # ── Шапка ─────────────────────────────────────────────────────────────────
    story.append(Paragraph('TrainGuide — Персональный план тренировки', brand_s))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=16))
    story.append(Paragraph(r.get('title', 'План тренировки'), title_s))
    story.append(Paragraph(f'Тренировка #{workout_id}', subtitle_s))

    # ── Мета-плитки ───────────────────────────────────────────────────────────
    meta_data = [
        ['Длительность', 'Калории', 'Уровень', 'Цель', 'Место'],
        [
            f"{meta.get('duration','—')} мин",
            f"{meta.get('calories','—')} кк",
            meta.get('level','—'),
            meta.get('goal','—'),
            meta.get('location','—'),
        ]
    ]
    meta_tbl = Table(meta_data, colWidths=[3.2*cm]*5)
    meta_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  BRAND_BLUE),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  FONT_BOLD),
        ('FONTSIZE',      (0,0), (-1,0),  8),
        ('BACKGROUND',    (0,1), (-1,1),  LIGHT_BG),
        ('TEXTCOLOR',     (0,1), (-1,1),  DARK_TEXT),
        ('FONTNAME',      (0,1), (-1,1),  FONT_BOLD),
        ('FONTSIZE',      (0,1), (-1,1),  9),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',          (0,0), (-1,-1), 0.5, BORDER),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 16))

    # ── Разминка ──────────────────────────────────────────────────────────────
    warmup = r.get('warmup', [])
    if warmup:
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
        story.append(Paragraph('Разминка', section_s))
        for i, ex in enumerate(warmup, 1):
            t = Table([[
                Paragraph(f'{i}.', bold_s),
                Paragraph(ex.get('name',''), bold_s),
                Paragraph(ex.get('duration',''), amber_s),
                Paragraph(ex.get('description',''), body_s),
            ]], colWidths=[0.5*cm, 4*cm, 2.5*cm, 10*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor('#FFFBEB')),
                ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#FDE68A')),
                ('VALIGN',        (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING',    (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING',   (0,0), (-1,-1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 3))

    # ── Основные блоки ────────────────────────────────────────────────────────
    for block in r.get('blocks', []):
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
        story.append(Paragraph(block.get('name','Блок'), section_s))

        for i, ex in enumerate(block.get('exercises', []), 1):
            story.append(Paragraph(f'{i}. {ex.get("name","")}', extitle_s))

            params = Table([[
                f'{ex.get("sets","—")} подх.',
                f'{ex.get("reps","—")} повт.',
                f'Отдых: {ex.get("rest","—")}',
                f'Вес: {ex.get("weight","—")}',
            ]], colWidths=[3.5*cm]*4)
            params.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (1,-1),  colors.HexColor('#EFF6FF')),
                ('BACKGROUND',    (2,0), (-1,-1), LIGHT_BG),
                ('TEXTCOLOR',     (0,0), (1,-1),  BRAND_BLUE),
                ('TEXTCOLOR',     (2,0), (-1,-1), DARK_TEXT),
                ('FONTNAME',      (0,0), (-1,-1), FONT_BOLD),
                ('FONTSIZE',      (0,0), (-1,-1), 8),
                ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
                ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
                ('GRID',          (0,0), (-1,-1), 0.3, BORDER),
                ('TOPPADDING',    (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(params)

            if ex.get('tip'):
                story.append(Spacer(1, 3))
                story.append(Paragraph(f'* {ex["tip"]}', tip_s))

            if ex.get('muscles'):
                story.append(Paragraph(
                    '  '.join([f'• {m}' for m in ex['muscles']]),
                    muscles_s
                ))
            story.append(Spacer(1, 4))

    # ── Заминка ───────────────────────────────────────────────────────────────
    cooldown = r.get('cooldown', [])
    if cooldown:
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
        story.append(Paragraph('Заминка', section_s))
        for i, ex in enumerate(cooldown, 1):
            t = Table([[
                Paragraph(f'{i}.', bold_s),
                Paragraph(ex.get('name',''), bold_s),
                Paragraph(ex.get('duration',''), emerald_s),
                Paragraph(ex.get('description',''), body_s),
            ]], colWidths=[0.5*cm, 4*cm, 2.5*cm, 10*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor('#ECFDF5')),
                ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#A7F3D0')),
                ('VALIGN',        (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING',    (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING',   (0,0), (-1,-1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 3))

    # ── Советы ────────────────────────────────────────────────────────────────
    tips = r.get('tips', [])
    if tips:
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
        story.append(Paragraph('Советы по тренировке', section_s))
        for tip in tips:
            story.append(Paragraph(f'• {tip}', body_s))
            story.append(Spacer(1, 3))

    # ── Футер ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE))
    story.append(Paragraph(
        'Сгенерировано TrainGuide — AI-платформа персональных тренировок',
        footer_s
    ))

    doc.build(story)
    return output_path