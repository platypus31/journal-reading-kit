#!/usr/bin/env python3
"""
Journal Reading Report PowerPoint Generator (Fallback)
Fallback for when the ppt-master main route is unavailable: uses python-pptx to
generate an editable .pptx directly, with no external dependency beyond python-pptx.

NOTE: this fallback consumes the older `slides.json` schema documented below, which is
NOT the same as the `content.json` schema used by the main engine (gen_journal_svg.py).

Usage:
    python3 scripts/generate_pptx.py slides.json output/jr-report.pptx

slides.json format:
{
    "title": "Journal Reading 報告標題",
    "author": "報告者",
    "department": "科別",
    "date": "2026-04-04",
    "style": "formal",  // formal | clean | teaching | competition
    "slides": [
        {
            "type": "title",
            "title": "標題",
            "subtitle": "副標題"
        },
        {
            "type": "section",
            "title": "INTRODUCTION",
            "subtitle": "前言"
        },
        {
            "type": "content",
            "title": "投影片標題",
            "bullets": ["重點一", "重點二", "重點三"],
            "section": "INTRODUCTION"
        },
        {
            "type": "two_column",
            "title": "標題",
            "left_title": "左欄標題",
            "left_bullets": ["..."],
            "right_title": "右欄標題",
            "right_bullets": ["..."],
            "section": "RESULTS"
        },
        {
            "type": "table",
            "title": "標題",
            "headers": ["欄1", "欄2", "欄3"],
            "rows": [["值1", "值2", "值3"]],
            "section": "METHODS"
        }
    ]
}
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.enum.shapes import MSO_SHAPE
except ImportError:
    print("錯誤：缺少 python-pptx 套件。請執行 pip install python-pptx 安裝。", file=sys.stderr)
    sys.exit(1)

# ── Constants ──

VALID_STYLES = ["formal", "clean", "teaching", "competition"]
VALID_SLIDE_TYPES = ["title", "section", "content", "two_column", "table"]

# ── Style definitions ──

STYLES = {
    "formal": {
        "primary": RGBColor(0x1B, 0x3A, 0x5C),      # Deep blue
        "secondary": RGBColor(0x2E, 0x86, 0xC1),     # Medium blue
        "accent": RGBColor(0x17, 0xA5, 0x89),         # Teal
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "text": RGBColor(0x2C, 0x3E, 0x50),
        "light": RGBColor(0xEB, 0xF5, 0xFB),
    },
    "clean": {
        "primary": RGBColor(0x34, 0x49, 0x5E),
        "secondary": RGBColor(0x00, 0xB8, 0x94),      # Green
        "accent": RGBColor(0xF3, 0x9C, 0x12),
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "text": RGBColor(0x2C, 0x3E, 0x50),
        "light": RGBColor(0xF0, 0xF9, 0xF4),
    },
    "teaching": {
        "primary": RGBColor(0xE6, 0x7E, 0x22),       # Orange
        "secondary": RGBColor(0x29, 0x80, 0xB9),
        "accent": RGBColor(0x27, 0xAE, 0x60),
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "text": RGBColor(0x2C, 0x3E, 0x50),
        "light": RGBColor(0xFD, 0xF2, 0xE9),
    },
    "competition": {
        "primary": RGBColor(0x1A, 0x23, 0x5B),       # Deep blue-purple
        "secondary": RGBColor(0x3D, 0x5A, 0xFE),
        "accent": RGBColor(0x00, 0xE6, 0x76),
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
        "text": RGBColor(0x1A, 0x1A, 0x2E),
        "light": RGBColor(0xE8, 0xEA, 0xF6),
    },
}

# IMRaD section labels for journal reading reports
SECTION_LABELS = {
    "INTRODUCTION": "前言 INTRODUCTION",
    "METHODS": "方法 METHODS",
    "RESULTS": "結果 RESULTS",
    "DISCUSSION": "討論 DISCUSSION",
    "CONCLUSION": "結論 CONCLUSION",
}


def add_section_indicator(slide, current_section, style_colors):
    """Add IMRaD section indicator bar on the left side."""
    sections = ["INTRODUCTION", "METHODS", "RESULTS", "DISCUSSION", "CONCLUSION"]
    bar_top = Inches(1.5)
    bar_height = Inches(0.6)
    bar_width = Inches(1.2)
    bar_left = Inches(0.15)

    for i, sec in enumerate(sections):
        top = bar_top + Emu(int(bar_height * i * 1.1))
        is_current = (sec == current_section)

        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            bar_left, top, bar_width, bar_height
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = style_colors["primary"] if is_current else style_colors["light"]
        shape.line.fill.background()

        tf = shape.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = SECTION_LABELS[sec]
        p.font.size = Pt(8)
        p.font.bold = is_current
        p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if is_current else style_colors["text"]
        p.alignment = PP_ALIGN.CENTER


def _fit_title_pt(text, base_pt, floor_pt=18):
    """依標題長度自動縮字級，防止長標題溢出壓到下方文字。

    提取自實際成品範本的防 bug 邏輯：fibula flap 那份封面標題 5 行、壓到
    presenter/supervisor 資訊上重疊。長標題逐級縮小、不低於 floor_pt。
    """
    n = len(text or "")
    size = base_pt
    for threshold in (55, 90, 125, 160):
        if n > threshold:
            size -= 5
    return max(size, floor_pt)


def create_title_slide(prs, data, style_colors):
    """Create title slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank

    # Background accent bar
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(10), Inches(1.2)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = style_colors["primary"]
    shape.line.fill.background()

    # Title
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(8.4), Inches(2))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    _title = data.get("title", "Journal Reading Report")
    p.text = _title
    p.font.size = Pt(_fit_title_pt(_title, 36))
    p.font.bold = True
    p.font.color.rgb = style_colors["primary"]

    # Author / Department / Date
    txBox2 = slide.shapes.add_textbox(Inches(0.8), Inches(4.2), Inches(8.4), Inches(1.5))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    lines = []
    if data.get("author"):
        lines.append(data["author"])
    if data.get("department"):
        lines.append(data["department"])
    if data.get("date"):
        lines.append(data["date"])
    p = tf2.paragraphs[0]
    p.text = " | ".join(lines)
    p.font.size = Pt(18)
    p.font.color.rgb = style_colors["secondary"]


def create_section_slide(prs, slide_data, style_colors):
    """Create IMRaD section divider slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Full background
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(10), Inches(7.5)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = style_colors["primary"]
    shape.line.fill.background()

    # Section title
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(2))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    _stitle = slide_data.get("title", "")
    p.text = _stitle
    p.font.size = Pt(_fit_title_pt(_stitle, 48))
    p.font.bold = True
    p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    p.alignment = PP_ALIGN.CENTER

    # Subtitle
    if slide_data.get("subtitle"):
        txBox2 = slide.shapes.add_textbox(Inches(1), Inches(4.2), Inches(8), Inches(1))
        tf2 = txBox2.text_frame
        p2 = tf2.paragraphs[0]
        p2.text = slide_data["subtitle"]
        p2.font.size = Pt(24)
        p2.font.color.rgb = style_colors["accent"]
        p2.alignment = PP_ALIGN.CENTER


def create_content_slide(prs, slide_data, style_colors):
    """Create standard content slide with bullets."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    section = slide_data.get("section")
    content_left = Inches(1.6) if section else Inches(0.8)

    # Section indicator
    if section:
        add_section_indicator(slide, section, style_colors)

    # Title bar
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(10), Inches(0.9)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = style_colors["primary"]
    shape.line.fill.background()

    txBox = slide.shapes.add_textbox(content_left, Inches(0.12), Inches(8), Inches(0.7))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = slide_data.get("title", "")
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Bullets
    bullets = slide_data.get("bullets", [])
    if bullets:
        txBox2 = slide.shapes.add_textbox(content_left, Inches(1.2), Inches(8), Inches(5.5))
        tf2 = txBox2.text_frame
        tf2.word_wrap = True

        for i, bullet in enumerate(bullets):
            if i == 0:
                p = tf2.paragraphs[0]
            else:
                p = tf2.add_paragraph()
            p.text = f"  {bullet}"
            p.font.size = Pt(16)
            p.font.color.rgb = style_colors["text"]
            p.space_after = Pt(8)
            p.level = 0


def create_two_column_slide(prs, slide_data, style_colors):
    """Create two-column comparison slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    section = slide_data.get("section")
    content_left = Inches(1.6) if section else Inches(0.5)

    if section:
        add_section_indicator(slide, section, style_colors)

    # Title bar
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(10), Inches(0.9)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = style_colors["primary"]
    shape.line.fill.background()

    txBox = slide.shapes.add_textbox(content_left, Inches(0.12), Inches(8), Inches(0.7))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = slide_data.get("title", "")
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    col_width = Inches(3.8) if section else Inches(4.2)

    # Left column
    left_box = slide.shapes.add_textbox(content_left, Inches(1.2), col_width, Inches(5.5))
    tf_l = left_box.text_frame
    tf_l.word_wrap = True
    p = tf_l.paragraphs[0]
    p.text = slide_data.get("left_title", "")
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = style_colors["secondary"]
    for bullet in slide_data.get("left_bullets", []):
        p = tf_l.add_paragraph()
        p.text = f"  {bullet}"
        p.font.size = Pt(14)
        p.font.color.rgb = style_colors["text"]
        p.space_after = Pt(6)

    # Right column
    right_left = content_left + col_width + Inches(0.3)
    right_box = slide.shapes.add_textbox(right_left, Inches(1.2), col_width, Inches(5.5))
    tf_r = right_box.text_frame
    tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = slide_data.get("right_title", "")
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = style_colors["secondary"]
    for bullet in slide_data.get("right_bullets", []):
        p = tf_r.add_paragraph()
        p.text = f"  {bullet}"
        p.font.size = Pt(14)
        p.font.color.rgb = style_colors["text"]
        p.space_after = Pt(6)


def create_table_slide(prs, slide_data, style_colors):
    """Create slide with table."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    section = slide_data.get("section")
    content_left = Inches(1.6) if section else Inches(0.5)

    if section:
        add_section_indicator(slide, section, style_colors)

    # Title bar
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(10), Inches(0.9)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = style_colors["primary"]
    shape.line.fill.background()

    txBox = slide.shapes.add_textbox(content_left, Inches(0.12), Inches(8), Inches(0.7))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = slide_data.get("title", "")
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    headers = slide_data.get("headers", [])
    rows_data = slide_data.get("rows", [])

    if not headers:
        return

    n_rows = len(rows_data) + 1
    n_cols = len(headers)
    table_width = Inches(7.5) if section else Inches(9)
    row_height = Inches(0.5)

    table_shape = slide.shapes.add_table(
        n_rows, n_cols,
        content_left, Inches(1.2),
        table_width, Emu(int(row_height * n_rows))
    )
    table = table_shape.table

    # Header row
    for j, header in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = style_colors["primary"]
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.size = Pt(12)
            paragraph.font.bold = True
            paragraph.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Data rows
    for i, row in enumerate(rows_data):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.text = str(val)
            if i % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = style_colors["light"]
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(11)
                paragraph.font.color.rgb = style_colors["text"]


def validate_data(data):
    """Validate input JSON data structure. Raises ValueError on invalid input."""
    if not isinstance(data, dict):
        raise ValueError("輸入資料必須是 JSON 物件（字典）。")

    # Required fields
    missing = []
    for field in ["title", "style", "slides"]:
        if field not in data:
            missing.append(field)
    if missing:
        raise ValueError(f"缺少必要欄位：{', '.join(missing)}。JSON 必須包含 title、style、slides。")

    # Validate style
    style = data["style"]
    if style not in VALID_STYLES:
        raise ValueError(
            f"無效的簡報風格：'{style}'。"
            f"可用的風格為：{', '.join(VALID_STYLES)}。"
        )

    # Validate slides
    slides = data["slides"]
    if not isinstance(slides, list):
        raise ValueError("'slides' 欄位必須是陣列。")
    if len(slides) == 0:
        raise ValueError("'slides' 陣列不可為空，至少需要一張投影片。")

    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            raise ValueError(f"第 {i + 1} 張投影片必須是 JSON 物件。")
        slide_type = slide.get("type")
        if slide_type is None:
            raise ValueError(f"第 {i + 1} 張投影片缺少 'type' 欄位。")
        if slide_type not in VALID_SLIDE_TYPES:
            raise ValueError(
                f"第 {i + 1} 張投影片的類型 '{slide_type}' 無效。"
                f"可用的類型為：{', '.join(VALID_SLIDE_TYPES)}。"
            )


def generate_pptx(data, output_path):
    """Generate the PowerPoint file from structured data."""
    validate_data(data)

    style_name = data.get("style", "formal")
    style_colors = STYLES.get(style_name, STYLES["formal"])

    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # Create title slide from metadata
    create_title_slide(prs, data, style_colors)

    # Create slides
    for slide_data in data.get("slides", []):
        slide_type = slide_data.get("type", "content")

        if slide_type == "title":
            create_title_slide(prs, slide_data, style_colors)
        elif slide_type == "section":
            create_section_slide(prs, slide_data, style_colors)
        elif slide_type == "content":
            create_content_slide(prs, slide_data, style_colors)
        elif slide_type == "two_column":
            create_two_column_slide(prs, slide_data, style_colors)
        elif slide_type == "table":
            create_table_slide(prs, slide_data, style_colors)
        else:
            create_content_slide(prs, slide_data, style_colors)

    prs.save(output_path)
    print(f"PowerPoint saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Journal Reading Report PowerPoint 產生器 — 將 JSON 簡報資料轉換為 .pptx 檔案",
        epilog=(
            "範例：\n"
            "  python3 scripts/generate_pptx.py slides.json output/jr-report.pptx\n\n"
            "⚠️ 本 fallback 吃舊的 slides.json schema，與主路線 gen_journal_svg.py 的\n"
            "   content.json 不通用。\n\n"
            "JSON 格式說明：\n"
            "  必要欄位：title (字串), style (formal|clean|teaching|competition), slides (陣列)\n"
            "  每張投影片的 type 可為：title, section, content, two_column, table\n"
            "  section 欄位可為：INTRODUCTION, METHODS, RESULTS, DISCUSSION, CONCLUSION"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="輸入的 JSON 檔案路徑（簡報資料）")
    parser.add_argument("output", help="輸出的 .pptx 檔案路徑")

    args = parser.parse_args()
    input_path = args.input
    output_path = args.output

    # Validate input file exists
    if not Path(input_path).is_file():
        print(f"錯誤：找不到輸入檔案 '{input_path}'。請確認路徑是否正確。", file=sys.stderr)
        sys.exit(1)

    # Load and parse JSON
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"錯誤：JSON 格式不正確。解析失敗於第 {e.lineno} 行，第 {e.colno} 欄。", file=sys.stderr)
        print(f"詳細資訊：{e.msg}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        print("錯誤：檔案編碼不正確。請確認檔案為 UTF-8 編碼。", file=sys.stderr)
        sys.exit(1)

    # Validate and generate
    try:
        generate_pptx(data, output_path)
    except ValueError as e:
        print(f"錯誤：輸入資料驗證失敗。{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"錯誤：產生簡報時發生未預期的錯誤。{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
