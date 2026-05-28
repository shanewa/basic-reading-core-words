import random
from pathlib import Path

from .entries import WordEntry
from .examples import example_sentence
from .log import log
from .phonics import phonics_column


def find_cjk_font() -> str:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/mnt/c/Windows/Fonts/msyh.ttc",
        "/mnt/c/Windows/Fonts/simhei.ttf",
        "/mnt/c/Windows/Fonts/simsun.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return ""


def find_cjk_bold_font() -> str:
    candidates = [
        "/mnt/c/Windows/Fonts/msyhbd.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return ""


def find_ipa_font() -> str:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return ""


def build_pdf(
    entries: list[WordEntry],
    out_path: Path,
    seed: int = 42,
    *,
    include_ipa: bool = False,
) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

    rng = random.Random(seed)
    shuffled = entries[:]
    rng.shuffle(shuffled)

    font_path = find_cjk_font()
    if not font_path:
        raise SystemExit("No CJK font found. Install fonts-noto-cjk or use Windows fonts.")

    pdfmetrics.registerFont(TTFont("CJK", font_path, subfontIndex=0))

    bold_font_path = find_cjk_bold_font()
    if bold_font_path:
        pdfmetrics.registerFont(TTFont("CJKBold", bold_font_path, subfontIndex=0))
        bold_font_name = "CJKBold"
    else:
        bold_font_name = "CJK"

    ipa_font_path = find_ipa_font()
    if ipa_font_path:
        pdfmetrics.registerFont(TTFont("IPA", ipa_font_path))
        ipa_font_name = "IPA"
    else:
        ipa_font_name = "CJK"

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=6 * mm,
        rightMargin=6 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
    )

    base_font_size = 8
    header_font_size = 9

    # -- build raw text rows for measurement (before creating Paragraphs) --
    raw_header = ["英文", "音标（自然拼读）", "中文", "例句", "出处"]
    raw_rows: list[list] = []
    for e in shuffled:
        raw_rows.append([
            e.english,
            phonics_column(e.english, include_ipa=include_ipa, allow_network=False),
            e.chinese,
            example_sentence(e.english, e.chinese),
            e.sources,  # list[str]
        ])

    # -- measure max rendered string-width per column (points) --
    col_fonts = [bold_font_name, ipa_font_name, "CJK", "CJK", "CJK"]
    col_fs_delta = [0.5, 0, 0, 0, 0]  # extra pts per column on top of base

    def _measure_maxes(data_fs: float) -> list[float]:
        maxes = [0.0] * 5
        # header row at its own font size (col 0 is bold)
        for ci, text in enumerate(raw_header):
            w = pdfmetrics.stringWidth(text, col_fonts[ci], header_font_size)
            maxes[ci] = max(maxes[ci], w)
        # data rows
        for row in raw_rows:
            for ci, cell in enumerate(row):
                font = col_fonts[ci]
                fs = data_fs + col_fs_delta[ci]
                if ci == 4:  # source column: list of strings, measure longest line
                    for src in cell:
                        w = pdfmetrics.stringWidth(src, font, fs)
                        maxes[ci] = max(maxes[ci], w)
                else:
                    w = pdfmetrics.stringWidth(str(cell), font, fs)
                    maxes[ci] = max(maxes[ci], w)
        return maxes

    col_max_pts = _measure_maxes(base_font_size)

    # page geometry
    page_width_mm = 210  # A4 portrait
    margin_mm = 6 * 2    # left + right
    available_mm = page_width_mm - margin_mm
    pad_per_cell_pts = 2 + 2  # LEFTPADDING + RIGHTPADDING

    def _maxes_to_widths(maxes: list[float]) -> list[float]:
        return [(m + pad_per_cell_pts) / 72.27 * 25.4 for m in maxes]

    col_widths_mm = _maxes_to_widths(col_max_pts)
    total_mm = sum(col_widths_mm)

    data_font_size = base_font_size
    if total_mm > available_mm:
        # scale column widths down to fit; text wraps where needed
        scale = available_mm / total_mm
        for i in range(len(col_widths_mm)):
            col_widths_mm[i] *= scale
    else:
        # distribute remaining slack proportionally
        slack = available_mm - total_mm
        if slack > 0 and sum(col_max_pts) > 0:
            for i in range(len(col_widths_mm)):
                col_widths_mm[i] += slack * (col_max_pts[i] / sum(col_max_pts))

    log(
        "[pdf] measured columns: font=%dpt  widths=[%s]mm"
        % (data_font_size, ", ".join("%.1f" % w for w in col_widths_mm))
    )

    # -- Paragraph styles at the computed font size --
    cell_style = ParagraphStyle(
        "cell", fontName="CJK", fontSize=data_font_size,
        leading=data_font_size + 1.5, wordWrap="CJK",
    )
    phonics_style = ParagraphStyle(
        "phonics", fontName=ipa_font_name, fontSize=data_font_size,
        leading=data_font_size + 1.5, wordWrap="CJK",
    )
    example_style = ParagraphStyle(
        "example", fontName="CJK", fontSize=data_font_size,
        leading=data_font_size + 1.5, wordWrap="CJK",
    )
    header_style = ParagraphStyle(
        "hdr", fontName="CJK", fontSize=header_font_size,
        leading=header_font_size + 2, textColor=colors.white,
    )

    english_fs = data_font_size + 0.5
    english_style = ParagraphStyle(
        "english", fontName=bold_font_name, fontSize=english_fs,
        leading=english_fs + 1.5, wordWrap="CJK",
    )

    def escape_xml(text: str) -> str:
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def P(text: str, style=cell_style) -> Paragraph:
        return Paragraph(escape_xml(text), style)

    # -- build Paragraph table data --
    data = [
        [
            P("英文", header_style),
            P("音标（自然拼读）", header_style),
            P("中文", header_style),
            P("例句", header_style),
            P("出处", header_style),
        ]
    ]
    for e in shuffled:
        src_html = "<br/>".join(escape_xml(s) for s in e.sources)
        data.append(
            [
                P(e.english, english_style),
                P(phonics_column(e.english, include_ipa=include_ipa, allow_network=False), phonics_style),
                P(e.chinese),
                P(example_sentence(e.english, e.chinese), example_style),
                Paragraph(src_html, cell_style),
            ]
        )

    table = Table(
        data,
        colWidths=[w * mm for w in col_widths_mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "CJK"),
                ("FONTSIZE", (0, 0), (-1, -1), data_font_size),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )

    log(f"[pdf] building table ({len(shuffled)} rows)...")
    doc.build([table])
    log(f"[pdf] wrote {len(shuffled)} rows -> {out_path}")
