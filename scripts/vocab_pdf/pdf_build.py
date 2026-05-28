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

    cell_style = ParagraphStyle(
        "cell", fontName="CJK", fontSize=6, leading=7.5, wordWrap="CJK"
    )
    phonics_style = ParagraphStyle(
        "phonics", fontName=ipa_font_name, fontSize=6, leading=7.5, wordWrap="CJK"
    )
    example_style = ParagraphStyle(
        "example", fontName="CJK", fontSize=6, leading=7.5, wordWrap="CJK"
    )
    header_style = ParagraphStyle(
        "hdr", fontName="CJK", fontSize=7, leading=9, textColor=colors.white
    )

    def escape_xml(text: str) -> str:
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def P(text: str, style=cell_style) -> Paragraph:
        return Paragraph(escape_xml(text), style)

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
                P(e.english),
                P(phonics_column(e.english, include_ipa=include_ipa, allow_network=False), phonics_style),
                P(e.chinese),
                P(example_sentence(e.english, e.chinese), example_style),
                Paragraph(src_html, cell_style),
            ]
        )

    # portrait A4 usable width ~198mm: 英文 | 拼读+音标 | 中文 | 例句 | 出处
    table = Table(
        data,
        colWidths=[22 * mm, 48 * mm, 32 * mm, 68 * mm, 28 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "CJK"),
                ("FONTSIZE", (0, 0), (-1, -1), 6),
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
