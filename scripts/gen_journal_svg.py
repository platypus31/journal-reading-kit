#!/usr/bin/env python3
"""Journal Reading 簡報生成器 —— 程式生成「取 White Grey 風」的 SVG deck（2026-08-12 定案格式）。

風格：白底 + 灰色流線波紋裝飾 + serif 大寫標題 + 條列式大字內容 + 大寫 section 過場 + 圖表頁。
內容來源：/jr pipeline 從 journal 原文抽取（英文為主），寫成 content.json 後餵進本工具。

用法（用 ppt-master venv 跑，之後 svg_to_pptx 也用同 venv）：
    ~/ppt-master/.venv/bin/python scripts/gen_journal_svg.py <content.json> <svg_output_dir>

content.json 格式：
{
  "cover": {"title": ["行1","行2"], "presenter": "PGY.. 姓名", "supervisor": "..醫師"},
  "slides": [
    {"kind": "section",  "name": "INTRODUCTION"},
    {"kind": "content",  "title": "Background", "bullets": ["原文截取重點1", "重點2"]},
    {"kind": "figure",   "title": "Results — Key Figure", "caption": "圖說", "path": "figs/figures/p05_img12.png"}
  ]
}
🔴 內容以英文為主（從 journal 原文截取），bullet 精簡（gate 會擋過長溢出）；bullet 內用 raw & / < / >，esc() 會統一轉義。
"""
import base64
import glob
import math, os, re, sys, json

W, H = 1280, 720

def waves(cx, cy, n, spread, amp, wl, phase, flip):
    p = []
    for i in range(n):
        off = (i - n/2)*spread
        pts = [(cx+flip*(t-6)*46, cy+off+amp*math.sin((t*46)/wl+phase+i*0.14)) for t in range(13)]
        d = f"M {pts[0][0]:.0f} {pts[0][1]:.0f} " + " ".join(f"L {x:.0f} {y:.0f}" for x,y in pts[1:])
        p.append(f'<path d="{d}" fill="none" stroke="#8A9099" stroke-width="1.1" opacity="{max(0.5-i*0.006,0.12):.2f}"/>')
    return "\n".join(p)

def dots(cx, cy):
    return "\n".join(f'<circle cx="{cx+i*46:.0f}" cy="{cy}" r="13" fill="#6B7280" opacity="0.8"/>' for i in range(3))

def head():
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
            f'<rect width="{W}" height="{H}" fill="#F7F8FA"/>']

_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

def esc(s):
    s = _CTRL_RE.sub("", str(s))  # 剝除 XML 1.0 非法控制字元（PDF 抽文字常帶 \x00）
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def txt(x, y, s, size, color="#1A1A1A", weight="700", anchor="start", ls="0.5", family="Georgia, serif"):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}" letter-spacing="{ls}">{esc(s)}</text>')

def write(outdir, idx, name, body):
    open(f"{outdir}/{idx}_{name}.svg", "w", encoding="utf-8").write("\n".join(body + ['</svg>']))

def cover(outdir, idx, c):
    s = head()
    s.append(waves(180,560,22,11,42,150,0,1)); s.append(waves(1120,180,20,12,40,160,1.2,-1))
    s.append(dots(70,78)); s.append(dots(1090,660))
    y = 300
    for ln in (c.get("title") or ["Journal Reading"]):
        s.append(txt(W/2, y, ln, 52, anchor="middle", ls="1.5")); y += 62
    if c.get("presenter"):  s.append(txt(W/2, y+40, c["presenter"], 26, "#333", "700", "middle"))
    if c.get("supervisor"): s.append(txt(W/2, y+78, c["supervisor"], 26, "#333", "700", "middle"))
    write(outdir, idx, "cover", s)

def section(outdir, idx, name):
    s = head()
    s.append(waves(210,610,18,12,44,150,0,1)); s.append(waves(1080,120,16,12,40,160,1.0,-1))
    s.append(dots(1110,650))
    s.append(txt(W/2, H/2+20, name, 96, anchor="middle", ls="4"))
    write(outdir, idx, slug(name), s)  # 走 slug 防檔名含 / 崩潰＋路徑穿越（其他頁型都有走，section 曾漏）

def slug(title):
    """檔名安全化（codex P2：title 含 / 等字元會被當路徑分隔符炸掉）。"""
    return re.sub(r"[^\w\-]+", "_", str(title)[:16]).strip("_").lower() or "page"

def wrap_bullet(b, limit=62):
    """bullet 過長自動拆行（codex P2：單一 <text> 不換行會溢出版面）。"""
    b = str(b)
    if len(b) <= limit:
        return [b]
    lines, cur = [], ""
    for w in b.split(" "):
        if cur and len(cur) + 1 + len(w) > limit:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines

def cjk_wrap(s, units):
    """中文感知斷行：全形字 2 單位、半形 1 單位；連續 ASCII 視為一個詞不從中間腰斬
    （避免 COVID-19 被拆成 C/OVID-19）。詞本身超過整行寬才退回逐字元斷。"""
    tokens = re.findall(r"[\x20-\x7E]+|[^\x20-\x7E]", str(s))
    def width(t):
        return sum(2 if ord(ch) > 0x2E80 else 1 for ch in t)
    lines, cur, u = [], "", 0
    for t in tokens:
        w = width(t)
        if u + w <= units or not cur and w <= units:
            cur += t; u += w
            continue
        if w > units:  # 超長 ASCII 串：先斷行再逐字元硬切
            if cur:
                lines.append(cur); cur, u = "", 0
            for ch in t:
                cw = width(ch)
                if u + cw > units and cur:
                    lines.append(cur); cur, u = "", 0
                cur += ch; u += cw
        else:
            lines.append(cur); cur, u = t.lstrip(), width(t.lstrip())
    if cur:
        lines.append(cur)
    return lines or [""]

def _valid_image_bytes(path):
    """回傳圖檔 bytes（magic bytes 相符且非空），否則 None。擋 0-byte 檔與崩潰半成品被當好圖嵌入。"""
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception:
        return None
    if len(raw) < 8:
        return None
    if raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[:3] == b"\xff\xd8\xff":  # PNG / JPEG magic
        return raw
    return None

def _warn_overflow(kind, title, y):
    """內容畫到畫布外（H=720）時提醒——生成端零檢查，靜默溢出很難發現。"""
    if y > 700:
        sys.stderr.write(f"WARN {kind}「{title}」：內容底緣 y={y:.0f} 超出畫布 720，可能溢出（請拆頁或精簡）\n")

def png_size(path):
    """讀 PNG IHDR 寬高（figure hl 紅框定位用；非 PNG 回 None）。"""
    try:
        with open(path, "rb") as f:
            h = f.read(26)
        if h[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        import struct
        return struct.unpack(">II", h[16:24])
    except Exception:
        return None

def table(outdir, idx, title, headers, rows, widths=None, note=None):
    """表格頁（EBM v3 起）：rect 格線＋text 內文 → pptx 端為可編輯形狀與文字框。
    widths=各欄相對比例（預設均分）；cell 依欄寬自動中文斷行。"""
    s = head()
    s.append(waves(1150, 90, 12, 12, 34, 160, 0.6, -1)); s.append(dots(70, 70))
    s.append(txt(90, 120, title, 46, ls="1.2"))
    s.append('<line x1="90" y1="145" x2="1190" y2="145" stroke="#C4C9D0" stroke-width="2"/>')
    if not headers:
        raise SystemExit(f"table「{title}」：headers 不可為空")
    n = len(headers)
    rows = [(list(r) + [""] * n)[:n] for r in rows]  # 欄數對齊 headers（多截少補）
    if widths and len(widths) != n:
        raise SystemExit(f"table「{title}」：widths 長度 {len(widths)} ≠ 欄數 {n}")
    if widths and not all(isinstance(w, (int, float)) and w > 0 for w in widths):
        raise SystemExit(f"table「{title}」：widths 必須全為正數，收到 {widths}")
    x0, x1, y0 = 95, 1185, 175
    tw = x1 - x0
    ws = widths or [1] * n
    tot = sum(ws)
    colw = [tw * w / tot for w in ws]
    fs, lh, pad = 20, 26, 10
    # 預斷行（欄寬→可容單位：字寬約 fs*0.52 半形）
    def cell_lines(text, cw):
        return cjk_wrap(text, max(int((cw - 2 * pad) / (fs * 0.52)), 4))
    header_lines = [cell_lines(h, colw[i]) for i, h in enumerate(headers)]
    row_lines = [[cell_lines(c, colw[i]) for i, c in enumerate(r)] for r in rows]
    def row_h(cells):
        return max(len(c) for c in cells) * lh + 2 * pad
    y = y0
    # header
    hh = row_h(header_lines)
    cx = x0
    for i, lines in enumerate(header_lines):
        s.append(f'<rect x="{cx:.0f}" y="{y:.0f}" width="{colw[i]:.0f}" height="{hh:.0f}" fill="#3D434B" stroke="#B0B6BE" stroke-width="1"/>')
        ty = y + pad + lh - 7
        for ln in lines:
            s.append(txt(cx + pad, ty, ln, fs, "#FFFFFF", "700", ls="0.3")); ty += lh
        cx += colw[i]
    y += hh
    for cells in row_lines:
        rh = row_h(cells)
        cx = x0
        for i, lines in enumerate(cells):
            s.append(f'<rect x="{cx:.0f}" y="{y:.0f}" width="{colw[i]:.0f}" height="{rh:.0f}" fill="#FFFFFF" stroke="#B0B6BE" stroke-width="1"/>')
            ty = y + pad + lh - 7
            for ln in lines:
                s.append(txt(cx + pad, ty, ln, fs, "#1A1D21", "400", ls="0.2")); ty += lh
            cx += colw[i]
        y += rh
    if note:
        s.append(txt(x0, min(y + 34, 690), note, 19, "#8A9099", "400", ls="0.2"))
    _warn_overflow("table", title, y)
    write(outdir, idx, "t_" + slug(title), s)

def textcard(outdir, idx, title, paragraphs, quote=None, caption=None):
    """敘事文字卡頁（臨床情境／臨床回覆）：白卡框＋逐行 text → pptx 端整段可編輯。"""
    s = head()
    s.append(waves(1150, 90, 12, 12, 34, 160, 0.6, -1)); s.append(dots(70, 70))
    s.append(txt(90, 120, title, 46, ls="1.2"))
    s.append('<line x1="90" y1="145" x2="1190" y2="145" stroke="#C4C9D0" stroke-width="2"/>')
    fs, lh, units = 24, 40, 76
    blocks = [cjk_wrap("　　" + p, units) for p in paragraphs]
    qlines = cjk_wrap(quote, units - 4) if quote else []
    body_h = sum(len(b) for b in blocks) * lh + (len(blocks) - 1) * 14 + (len(qlines) * lh + 40 if qlines else 0)
    cy0 = 180
    s.append(f'<rect x="130" y="{cy0}" width="1020" height="{body_h + 56:.0f}" fill="#FFFFFF" stroke="#C4C9D0" stroke-width="1.5"/>')
    y = cy0 + 46
    for b in blocks:
        for ln in b:
            s.append(txt(170, y, ln, fs, "#1A1D21", "400", ls="0.3")); y += lh
        y += 14
    if qlines:
        qh = len(qlines) * lh + 24
        s.append(f'<rect x="170" y="{y - 6:.0f}" width="940" height="{qh:.0f}" fill="#F0F2F5"/>')
        s.append(f'<rect x="170" y="{y - 6:.0f}" width="6" height="{qh:.0f}" fill="#8A9099"/>')
        ty = y + lh - 12
        for ln in qlines:
            s.append(txt(200, ty, ln, fs, "#1A1D21", "400", ls="0.3")); ty += lh
        y += qh
    if caption:
        s.append(txt(W/2, 690, caption, 21, "#8A9099", "400", "middle"))
    _warn_overflow("textcard", title, y)
    write(outdir, idx, "tc_" + slug(title), s)

def content(outdir, idx, title, bullets):
    s = head()
    s.append(waves(1150,90,12,12,34,160,0.6,-1)); s.append(dots(70,70))
    s.append(txt(90, 120, title, 46, ls="1.2"))
    s.append('<line x1="90" y1="145" x2="1190" y2="145" stroke="#C4C9D0" stroke-width="2"/>')
    y = 225
    for b in bullets:
        lines = cjk_wrap(b, 76)  # 中文感知斷行（wrap_bullet 用 len() 對全形字寬算錯，會溢出畫布）
        s.append(f'<circle cx="108" cy="{y-9:.0f}" r="6" fill="#6B7280"/>')
        for ln in lines:
            s.append(txt(132, y, ln, 25, "#2A2A2A", "400", ls="0.2"))
            y += 38
        y += 30
    _warn_overflow("content", title, y)
    write(outdir, idx, "c_" + slug(title), s)

def figure(outdir, idx, title, caption, path=None, hl=None):
    """圖表頁：path 給了且檔案存在 → base64 內嵌實圖（codex P1 修復）；否則佔位框。"""
    s = head()
    s.append(dots(70, 70))
    s.append(txt(90, 120, title, 46, ls="1.2"))
    s.append('<line x1="90" y1="145" x2="1190" y2="145" stroke="#C4C9D0" stroke-width="2"/>')
    embedded = False
    raw = _valid_image_bytes(path)  # 驗 magic bytes（擋 0-byte／崩潰半成品／非圖片；只 isfile 會靜默嵌空圖）
    if raw is not None:
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext)
        if mime:
            b64 = base64.b64encode(raw).decode()
            s.append(f'<image x="240" y="170" width="800" height="440" '
                     f'preserveAspectRatio="xMidYMid meet" href="data:{mime};base64,{b64}"/>')
            embedded = True
            if hl:
                hl_ok = (isinstance(hl, (list, tuple)) and len(hl) == 4
                         and all(isinstance(v, (int, float)) for v in hl))
                sz = png_size(path)
                if not hl_ok:
                    sys.stderr.write(f"WARN figure「{title}」：hl 需為 4 個數字 [x0,y0,x1,y1]，已略過紅框\n")
                elif not (sz and sz[0] > 0 and sz[1] > 0):
                    sys.stderr.write(f"WARN figure「{title}」：紅框僅支援 PNG（此圖非 PNG 或讀不到尺寸），已略過\n")
                else:
                    iw, ih = sz
                    sc = min(800 / iw, 440 / ih)
                    dw, dh = iw * sc, ih * sc
                    dx, dy = 240 + (800 - dw) / 2, 170 + (440 - dh) / 2
                    rx0, ry0, rx1, ry1 = hl
                    s.append(f'<rect x="{dx + rx0 * dw:.1f}" y="{dy + ry0 * dh:.1f}" '
                             f'width="{max((rx1 - rx0) * dw, 0):.1f}" height="{max((ry1 - ry0) * dh, 0):.1f}" '
                             f'fill="none" stroke="#CC2222" stroke-width="2.5"/>')
        else:
            sys.stderr.write(f"WARN figure「{title}」：副檔名非 png/jpg（{path}），改用佔位框\n")
    elif path:
        sys.stderr.write(f"WARN figure「{title}」：圖檔缺失或無效（{path}），改用佔位框\n")
    if not embedded:
        s.append('<rect x="240" y="200" width="800" height="380" fill="#FFFFFF" stroke="#B0B6BE" stroke-width="2" stroke-dasharray="10 8"/>')
        s.append(txt(W/2, 380, "[ Journal Figure ]", 34, "#8A9099", "700", "middle"))
    s.append(txt(W/2, 655, caption, 22, "#8A9099", "400", "middle"))
    write(outdir, idx, "fig_" + slug(title), s)

VALID_KINDS = {"section", "figure", "table", "textcard", "content"}
_LIST_FIELDS = {"bullets": list, "paragraphs": list, "rows": list, "headers": list}

def validate_content(data):
    """型別守門：把「格式合法但型別錯」擋在生成前（否則字串會被逐字元迭代灌爆版面）。"""
    if not isinstance(data, dict):
        raise SystemExit("content.json 頂層必須是物件 {}")
    cov = data.get("cover")
    if cov is not None and not isinstance(cov, dict):
        raise SystemExit("cover 必須是物件")
    if cov and cov.get("title") is not None and not isinstance(cov["title"], list):
        raise SystemExit("cover.title 必須是陣列（每個元素一行）")
    slides = data.get("slides")
    if slides is None:
        slides = []
    if not isinstance(slides, list):
        raise SystemExit("slides 必須是陣列")
    for i, sl in enumerate(slides, 1):
        where = f"slides[{i}]"
        if not isinstance(sl, dict):
            raise SystemExit(f"{where} 必須是物件，收到 {type(sl).__name__}")
        k = sl.get("kind") or "content"
        if k not in VALID_KINDS:
            raise SystemExit(f"{where} kind「{sl.get('kind')}」無效，須為 {sorted(VALID_KINDS)}")
        # list 欄位：型別錯或 null 都擋（null 迭代會崩潰；明確報錯優於靜默空頁）
        for field, typ in _LIST_FIELDS.items():
            if field not in sl:
                continue
            if not isinstance(sl[field], typ):
                raise SystemExit(f"{where} 的 {field} 必須是陣列，收到 {type(sl[field]).__name__}")
            # 元素型別：rows 每列須是陣列；bullets/paragraphs/headers 每項須是純量（容器會被逐字元/取key）
            for j, el in enumerate(sl[field]):
                if field == "rows":
                    if not isinstance(el, (list, tuple)):
                        raise SystemExit(f"{where} 的 rows[{j}] 必須是陣列（一列儲存格），收到 {type(el).__name__}")
                elif not isinstance(el, (str, int, float)):
                    raise SystemExit(f"{where} 的 {field}[{j}] 必須是文字/數字，收到 {type(el).__name__}")

def build(content_path, outdir):
    try:
        with open(content_path, encoding="utf-8-sig") as f:  # utf-8-sig 容忍 BOM
            data = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"找不到 content.json：{content_path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"content.json 不是合法 JSON：{e}")
    validate_content(data)
    os.makedirs(outdir, exist_ok=True)
    for old in glob.glob(os.path.join(outdir, "[0-9]*_*.svg")):  # 只清本腳本產物（NN_*.svg），不動使用者手動放的檔
        os.remove(old)
    n = 1
    cover(outdir, f"{n:02d}", data.get("cover") or {}); n += 1
    dispatch = {"section": lambda idx, sl: section(outdir, idx, sl.get("name", "")),
                "figure": lambda idx, sl: figure(outdir, idx, sl.get("title", "Figure"), sl.get("caption", ""), sl.get("path"), sl.get("hl")),
                "table": lambda idx, sl: table(outdir, idx, sl.get("title", ""), sl.get("headers", []), sl.get("rows", []), sl.get("widths"), sl.get("note")),
                "textcard": lambda idx, sl: textcard(outdir, idx, sl.get("title", ""), sl.get("paragraphs", []), sl.get("quote"), sl.get("caption")),
                "content": lambda idx, sl: content(outdir, idx, sl.get("title", ""), sl.get("bullets", []))}
    for sl in data.get("slides", []):
        dispatch.get(sl.get("kind"), dispatch["content"])(f"{n:02d}", sl)
        n += 1
    print(f"generated {n-1} slides -> {outdir}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("用法: gen_journal_svg.py <content.json> <svg_output_dir>")
    build(sys.argv[1], sys.argv[2])
