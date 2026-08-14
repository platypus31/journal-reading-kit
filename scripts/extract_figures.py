#!/usr/bin/env python3
"""從 journal PDF 抽出統計圖表（forest plot / KM curve / Table 圖等），供簡報配圖。

2026-08-12 校準：簡報要放論文裡的實際圖表，不能純文字。

用法（PyMuPDF 需 python3.10+，用 ppt-master 的 venv 跑）：
    ~/ppt-master/.venv/bin/python scripts/extract_figures.py <paper.pdf> -o <outdir>

行為：
- 抽出每頁嵌入的 raster 圖片，過濾掉太小的（logo/icon）。
- 同時把「含向量圖但無嵌入點陣圖」的頁 render 成整頁 PNG（forest plot 常是向量）。
- 產出 figures/ 目錄 + manifest.json（每張圖：來源頁、尺寸、路徑），供後續依 Results 內容挑圖插入。
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.stderr.write(
        "需要 PyMuPDF。請用 ppt-master 的 venv 執行：\n"
        "  ~/ppt-master/.venv/bin/python scripts/extract_figures.py <pdf> -o <outdir>\n"
    )
    sys.exit(2)

MIN_W = 220  # 過濾 icon/logo 的最小寬高（px）
MIN_H = 160


def extract(pdf_path, outdir):
    pdf_path = Path(pdf_path)
    outdir = Path(outdir)
    fig_dir = outdir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    manifest = []
    seen_xref = set()

    for pno in range(len(doc)):
        page = doc[pno]
        # 1) 嵌入的點陣圖
        raster_on_page = False
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in seen_xref:
                continue
            seen_xref.add(xref)
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.width < MIN_W or pix.height < MIN_H:
                    continue
                if pix.n >= 5:  # CMYK/alpha → 轉 RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                out = fig_dir / f"p{pno + 1:02d}_img{xref}.png"
                pix.save(out)
                manifest.append({"page": pno + 1, "type": "raster",
                                 "w": pix.width, "h": pix.height, "path": str(out)})
                raster_on_page = True
            except Exception as e:
                sys.stderr.write(f"skip xref {xref} p{pno+1}: {e}\n")

        # 2) 有向量繪圖但沒抽到點陣圖的頁 → render 整頁（forest plot / KM 常是向量）
        if not raster_on_page and page.get_drawings():
            pix = page.get_pixmap(dpi=150)
            out = fig_dir / f"p{pno + 1:02d}_pagevec.png"
            pix.save(out)
            manifest.append({"page": pno + 1, "type": "page_render_vector",
                             "w": pix.width, "h": pix.height, "path": str(out)})

    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"抽出 {len(manifest)} 張圖 → {fig_dir}")
    print(f"manifest → {outdir / 'manifest.json'}")
    return manifest


def main():
    ap = argparse.ArgumentParser(description="從 journal PDF 抽統計圖表供簡報配圖")
    ap.add_argument("pdf", help="論文 PDF 路徑")
    ap.add_argument("-o", "--output", required=True, help="輸出目錄")
    args = ap.parse_args()
    if not Path(args.pdf).is_file():
        sys.stderr.write(f"找不到 PDF：{args.pdf}\n")
        sys.exit(1)
    extract(args.pdf, args.output)


if __name__ == "__main__":
    main()
