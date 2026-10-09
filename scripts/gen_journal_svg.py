#!/usr/bin/env python3
"""Journal Reading 簡報生成器 —— 程式生成「取 White Grey 風」的 SVG deck（2026-08-12 定案格式）。

風格：白底 + 灰色流線波紋裝飾 + serif 大寫標題 + 條列式大字內容 + 大寫 section 過場 + 圖表頁。
內容來源：/jr pipeline 從 journal 原文抽取（英文為主），寫成 content.json 後餵進本工具。

用法（用 ppt-master venv 跑，之後 svg_to_pptx 也用同 venv；
     ppt-master 位置取自 $PPT_MASTER_DIR，未設則預設 ~/ppt-master）：
    "${PPT_MASTER_DIR:-$HOME/ppt-master}"/.venv/bin/python scripts/gen_journal_svg.py <content.json> <svg_output_dir>

content.json 格式：
{
  "cover": {"title": ["行1","行2"], "presenter": "報告者姓名", "supervisor": "..醫師"},
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
    """中文感知斷行：全形字 2 單位、半形 1 單位。

    token 化以「空白為界」（`[\\x21-\\x7E]+` 一個英文詞、`[\\x20]+` 空白、其餘逐字元），
    所以英文只在字間斷、不從單字中腰斬（舊版把含空格的整串 ASCII 當單一 token，
    整句英文必然掉進逐字元硬切分支，產出 asso/ciated、ti/ssue 級斷詞）。
    只有「單一詞本身寬過整行」才退回逐字元硬切。"""
    tokens = re.findall(r"[\x21-\x7E]+|[\x20]+|[^\x20-\x7E]", str(s))
    def width(t):
        return sum(2 if ord(ch) > 0x2E80 else 1 for ch in t)
    lines, cur, u = [], "", 0
    def flush():
        # strip 後是空的就別塞進去：空白自成 token 後，「cur 只剩空白」是常態
        # （例：cjk_wrap(" hello", 5) 舊寫法會回 ['', 'hello'] 多一條空行印到版面上）
        # 頭尾都要去：首行放得下時前導空白會併進 cur（u=0 恆滿足），只 rstrip 會讓
        # cjk_wrap(" ab cd", 20) 回 [' ab cd'] 在版面上多一格縮排（全形空白縮排不受影響）
        nonlocal cur, u
        stripped = cur.strip(" ")
        if stripped:
            lines.append(stripped)
        cur, u = "", 0
    for t in tokens:
        w = width(t)
        if u + w <= units:
            cur += t; u += w
            continue
        if t == " " * len(t):  # 行尾放不下的空白直接丟棄（換行本身即分隔）
            if cur:
                flush()
            continue
        if w > units:  # 單一詞寬過整行（超長化學名／URL）：唯一容許逐字元硬切的情況
            if cur:
                flush()
            for ch in t:
                cw = width(ch)
                if u + cw > units and cur:
                    flush()
                cur += ch; u += cw
        else:
            flush(); cur, u = t, w
    if cur:
        flush()
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
    fs0, lh0, pad0 = 20, 26, 10
    # 2026-10-08 新增：密集表（EBM 評讀總表一題一列塞 17+ 列；效應量總表列少但每格文字長會
    # 多行折行）在預設字級下常溢出 720 畫布——不是靠拆頁（spec 規定「合併成單一頁，不另開頁」），
    # 而是試幾個遞減的縮放比例，用「實際斷行後的高度」挑第一個塞得下的（原本只用列數粗估，
    # 列少但格內文字長仍會溢出，如 8 列的效應量總表含長算式理由欄）。列數/格長都短的表
    # scale=1.0 時行為與原本完全相同。
    # codex review P2 實測：這裡曾經寫 `budget = 670 - y0` 又在迴圈內判斷 `y0 + total_h <= budget`，
    # 等於要求 `total_h <= 670 - 2*y0`——y0 被扣了兩次，原本塞得下的表會被多縮一級字級，
    # 跟「短表 scale=1.0 行為與原本完全相同」的宣稱不符。budget 改成畫布底線本身（含緩衝）。
    budget = 670  # 畫布底線 720 留足緩衝（_warn_overflow 門檻 700），避免貼邊溢出
    # note 的字級/行高是固定值（不隨 scale 縮放），但它畫在表格下方、佔掉的高度一樣要算進
    # 「塞不塞得下」的判斷——否則表格本身卡在 budget 邊緣剛好過關，note 一畫上去還是溢出
    # （2026-10-08 實測：8 列效應量總表＋長 note，表格 scale=0.85 剛好 <670，加 note 後到 742）。
    note_extra = 0
    if note:
        note_lines = cjk_wrap(note, max(int(tw / (19 * 0.52)), 8))
        note_extra = 34 + len(note_lines) * 24
    chosen = None
    for scale in (1.0, 0.85, 0.7, 0.6, 0.5, 0.42):
        # codex review P3：fs0*scale 等浮點運算會產生 8.399999999999999 這類長尾數，
        # SVG font-size 屬性雖不會因此壞掉，但 round(_, 1) 讓輸出乾淨。
        fs, lh, pad = round(fs0 * scale, 1), round(lh0 * scale, 1), round(max(pad0 * scale, 3), 1)

        def cell_lines(text, cw, _fs=fs, _pad=pad):
            return cjk_wrap(text, max(int((cw - 2 * _pad) / (_fs * 0.52)), 4))

        header_lines = [cell_lines(h, colw[i]) for i, h in enumerate(headers)]
        row_lines = [[cell_lines(c, colw[i]) for i, c in enumerate(r)] for r in rows]

        def row_h(cells, _lh=lh, _pad=pad):
            return max(len(c) for c in cells) * _lh + 2 * _pad

        total_h = row_h(header_lines) + sum(row_h(cells) for cells in row_lines)
        chosen = (fs, lh, pad, header_lines, row_lines, row_h, total_h)
        if y0 + total_h + note_extra <= budget:
            break
    else:
        # codex review P3：6 個 scale 都塞不下時直接沿用最後一次（約 8.4px，幾乎不可讀）卻沒有
        # 任何警告——下面的 `_warn_overflow("table", ...)` 只在畫完才檢查，這裡先主動提醒一次。
        sys.stderr.write(f"WARN table「{title}」：縮到最小字級（scale=0.42）仍可能溢出，考慮拆頁或精簡內容\n")
    fs, lh, pad, header_lines, row_lines, row_h, _ = chosen
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
        # note 也要斷行：單行 note 超過欄寬會橫向出血，而 gate 只驗直向溢出（橫向出血是零訊號）
        # 🔴 刻意不把 note 往上夾（舊版 min(y+34, 690)）：夾上去會壓在表格上，那是 gate 看不見的重疊；
        #    讓它照實往下畫，超出畫布由 _warn_overflow 與 ppt-master gate 的直向溢出檢查抓得到。
        nfs, nlh = 19, 24
        ny = y + 34
        for ln in cjk_wrap(note, max(int(tw / (nfs * 0.52)), 8)):
            s.append(txt(x0, ny, ln, nfs, "#8A9099", "400", ls="0.2")); ny += nlh
        y = ny  # ny 已越過最後一行基線一個 nlh＝該行底緣（同 textcard/content 的慣例）；
                # 傳基線（ny - nlh）會少算一行高，最後一行畫出畫布仍不觸發 _warn_overflow
    _warn_overflow("table", title, y)
    write(outdir, idx, "t_" + slug(title), s)

def _fc_arrow_down(x, y, color):
    """向下箭頭三角（不用 <marker>——svg_to_pptx 對 marker 轉 native 的支援沒驗證過，直接畫三角形最穩）。"""
    return f'<path d="M{x-8:.1f} {y-13:.1f} L{x+8:.1f} {y-13:.1f} L{x:.1f} {y:.1f} Z" fill="{color}"/>'

def _fc_arrow_right(x, y, color):
    return f'<path d="M{x-13:.1f} {y-8:.1f} L{x-13:.1f} {y+8:.1f} L{x:.1f} {y:.1f} Z" fill="{color}"/>'

def flowchart(outdir, idx, title, steps, excluded=None, note=None):
    """PRISMA 式由上而下篩選流程圖（EBM ACQUIRE「選文流程」頁，2026-10-09 新增）：
    steps=[{label,n,detail?}, ...] 由上到下的主線方框；excluded=[{after,n,reasons:[...]}, ...]
    在 steps[after]→steps[after+1] 的連接處往右拉出排除分支。方框／箭頭＝rect/path，
    pptx 端轉成可編輯原生形狀與文字框（與 table() 同一套做法）。數字一律由呼叫端從
    content.json 既有資料算好傳入，本函式不做任何推算，只負責畫。"""
    s = head()
    s.append(waves(1150, 90, 12, 12, 34, 160, 0.6, -1)); s.append(dots(70, 70))
    s.append(txt(90, 120, title, 46, ls="1.2"))
    s.append('<line x1="90" y1="145" x2="1190" y2="145" stroke="#C4C9D0" stroke-width="2"/>')
    if not steps:
        raise SystemExit(f"flowchart「{title}」：steps 不可為空")
    excluded = excluded or []
    exmap = {}
    for e in excluded:
        a = e.get("after")
        # codex review P3（round1 Cloudflare）：a 的型別/範圍檢查要在建立 exmap 關聯之前就擋，
        # 不要等迴圈跑到一半才發現；bool 是 int 子類別會混過 isinstance 檢查，先排除。
        if isinstance(a, bool) or not isinstance(a, int) or not (0 <= a < len(steps) - 1):
            raise SystemExit(f"flowchart「{title}」：excluded.after={a!r} 必須是 0..{len(steps)-2} 的整數")
        n_ex = e.get("n", 0)
        # codex review P2（round1 Sonnet）：flowchart() 被直接呼叫（不經 validate_content）時
        # n 可能是 None/字串，sum() 會 TypeError；這裡比照 steps 的數字檢查，給友善錯誤。
        if isinstance(n_ex, bool) or not isinstance(n_ex, (int, float)):
            raise SystemExit(f"flowchart「{title}」：excluded.n={n_ex!r} 必須是數字")
        for r in (e.get("reasons") or []):
            # codex review P2（round1 Sonnet）：reasons 元素非字串（如 dict）會被 f-string
            # 靜默印成 repr，在這裡先擋掉比在 validate_content 補更貼近實際出錯點。
            if isinstance(r, bool) or not isinstance(r, (str, int, float)):
                raise SystemExit(f"flowchart「{title}」：excluded.reasons 的元素必須是文字/數字，收到 {type(r).__name__}")
        exmap.setdefault(a, []).append(e)

    x0, box_w = 150, 480
    x1 = x0 + box_w
    xc = (x0 + x1) / 2
    y = 165
    gap = 40
    boxes = []  # (top, bottom)
    fs_label, fs_n, fs_detail = 20, 26, 15.5
    for i, st in enumerate(steps):
        label = str(st.get("label", ""))
        n = st.get("n")
        # codex review P3（round1 Sonnet）：bool 是 int 子類別，True 會混過數字檢查顯示成「n = 1」。
        if isinstance(n, bool) or not isinstance(n, (int, float)):
            raise SystemExit(f"flowchart「{title}」：steps[{i}].n 必須是數字")
        detail = st.get("detail")
        label_lines = cjk_wrap(label, 40) or [""]
        detail_lines = cjk_wrap(str(detail), 50) if detail else []
        pad = 14
        h = pad * 2 + len(label_lines) * 25 + 34 + len(detail_lines) * 20
        top, bottom = y, y + h
        s.append(f'<rect x="{x0}" y="{top:.0f}" width="{box_w}" height="{h:.0f}" rx="10" fill="#FFFFFF" stroke="#3D434B" stroke-width="2.4"/>')
        ty = top + pad + 19
        for ln in label_lines:
            s.append(txt(xc, ty, ln, fs_label, "#17293A", "700", "middle")); ty += 25
        ty += 7
        s.append(txt(xc, ty, f"n = {n:g}", fs_n, "#17293A", "700", "middle")); ty += 30
        for ln in detail_lines:
            s.append(txt(xc, ty, ln, fs_detail, "#5B6572", "400", "middle")); ty += 20
        boxes.append((top, bottom))
        y = bottom + gap
    final_y = boxes[-1][1]
    prev_excl_bottom = None  # codex review P2（round1 Sonnet）：連續 after=i,i+1 的排除框若
    # 各自只以自己的 mid_y 置中，reasons 多到框高超過 box 高＋gap 時會互相覆蓋；記住前一個
    # 排除框的底緣，下一個框頂緣不夠低就整塊下推。
    for i in range(len(steps) - 1):
        bottom_i = boxes[i][1]
        top_next = boxes[i + 1][0]
        mid_y = (bottom_i + top_next) / 2
        # 主線箭頭（有無排除分支都要畫，原本 if/else 兩份重複——codex review P3 建議抽出來一份）
        s.append(f'<path d="M{xc:.0f} {bottom_i:.0f} L{xc:.0f} {mid_y - 13:.0f}" stroke="#2B3A4A" stroke-width="3" fill="none"/>')
        s.append(_fc_arrow_down(xc, mid_y, "#2B3A4A"))
        s.append(f'<path d="M{xc:.0f} {mid_y:.0f} L{xc:.0f} {top_next:.0f}" stroke="#2B3A4A" stroke-width="3" fill="none"/>')
        exs = exmap.get(i)
        if exs:
            total_n = sum(e.get("n", 0) for e in exs)
            reason_lines = []
            for e in exs:
                for r in (e.get("reasons") or []):
                    reason_lines.extend(cjk_wrap(f"• {r}", 46))
            ex_x0, ex_w = x1 + 75, 430
            pad = 12
            eh = pad * 2 + 30 + len(reason_lines) * 19
            ey_top = max(mid_y - eh / 2, 150)
            if prev_excl_bottom is not None and ey_top < prev_excl_bottom + 8:
                ey_top = prev_excl_bottom + 8
            s.append(f'<path d="M{xc + 14:.0f} {mid_y:.0f} L{ex_x0 - 13:.0f} {mid_y:.0f}" stroke="#C0392B" stroke-width="3" fill="none"/>')
            s.append(_fc_arrow_right(ex_x0, mid_y, "#C0392B"))
            s.append(f'<rect x="{ex_x0:.0f}" y="{ey_top:.0f}" width="{ex_w}" height="{eh:.0f}" rx="8" fill="#FFF7F5" stroke="#C0392B" stroke-width="2.2"/>')
            ty = ey_top + pad + 20
            s.append(txt(ex_x0 + ex_w / 2, ty, f"Excluded, n = {total_n:g}", 19, "#C0392B", "700", "middle")); ty += 27
            for ln in reason_lines:
                s.append(txt(ex_x0 + 16, ty, ln, 14.5, "#5B2A24", "400", "start")); ty += 19
            prev_excl_bottom = ey_top + eh
            final_y = max(final_y, prev_excl_bottom)
    y = final_y + 10
    if note:
        for ln in cjk_wrap(note, 92):
            s.append(txt(x0, y + 24, ln, 16, "#8A9099", "400", ls="0.2")); y += 24
    _warn_overflow("flowchart", title, y)
    write(outdir, idx, "fc_" + slug(title), s)

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
    y0 = 225
    # 2026-10-08 新增：長 bullet（如 EBM Limitation 兩段式／台灣在地考量實查文字）在預設字級
    # 下會溢出 720 畫布——試幾個遞減的縮放比例，挑第一個能塞進畫布的；都不行就用最小字級
    # （寧可字小也不要溢出），不影響既有短 bullet 頁（scale=1.0 時行為與原本完全相同）。
    fs0, lh0, gap0, units0 = 25, 38, 30, 76
    chosen = None
    for scale in (1.0, 0.9, 0.8, 0.7, 0.6, 0.55):
        units = max(int(units0 / scale), units0)
        wrapped = [cjk_wrap(b, units) for b in bullets]
        y = y0 + sum(len(lines) * (lh0 * scale) + (gap0 * scale) for lines in wrapped)
        chosen = (scale, units, wrapped, y)
        if y <= 690:
            break
    scale, units, wrapped, _ = chosen
    # codex review P1→P2（round2，CONSENSUS 2/2）：fs0*scale 等浮點運算會產生
    # 8.399999999999999 這類長尾數；table() 已 round(_, 1)，這裡比照同步（SVG 不會因此壞掉，
    # 純粹輸出乾淨 + txt() 確認可接受 float）。
    fs, lh, gap = round(fs0 * scale, 1), round(lh0 * scale, 1), round(gap0 * scale, 1)
    y = y0
    for lines in wrapped:
        s.append(f'<circle cx="108" cy="{y - lh * 0.24:.0f}" r="{6 * scale:.1f}" fill="#6B7280"/>')
        for ln in lines:
            s.append(txt(132, y, ln, fs, "#2A2A2A", "400", ls="0.2"))
            y += lh
        y += gap
    _warn_overflow("content", title, y)
    write(outdir, idx, "c_" + slug(title), s)

def figure(outdir, idx, title, caption, path=None, hl=None, bullets=None, layout=None, notes=None):
    """圖表頁：path 給了且檔案存在 → base64 內嵌實圖（codex P1 修復）；否則佔位框。
    bullets（可選，2026-10-08 新增）：題目／判定文字列在圖片上方、同一頁（EBM APPRAISE
    「評讀題目＋原文佐證截圖」合頁用——使用者第三輪退件要求「題目列在上面、下面附截圖」，
    不要題目頁與截圖頁分開兩張）。不給 bullets 時版面與行為完全不變（零回歸風險）。
    layout（可選，2026-10-09 新增，EBM 背景機轉圖專用；使用者兩輪回饋定案：先要求並排後改
    「整頁滿版、不靠旁邊文字輔助」）：預設 None＝原本「bullets 在上、圖在下」堆疊版型（不動）；
    `"full"`＝滿版版型——不畫 bullets，只留標題與底部一行出處，圖吃掉幾乎整個內容區
    （≥80% 畫布面積，使用者原話「整頁填滿 可以直接看 不用配字體在旁邊」）；原本要給讀者看的
    英文說明改成**圖本身要畫出來的標註**（by caller：mechanism SVG 自己把每個節點/箭頭的
    英文標籤畫進去，不是這個函式的事），這個函式只負責把圖放大到滿版。
    notes（可選，2026-10-09 新增）：講者備忘稿純文字／陣列，寫進
    `<project_path>/notes/fig_<slug>.md`（ppt-master `find_notes_files()` 以檔名比對
    svg stem 自動吃進 pptx 的 speaker notes，不影響可見投影片版面）。"""
    # codex review P2/P3（三輪累積）：型別守門移到標題字級決定「之前」——bullets 是非 list 的
    # truthy 值（如字串）時，若先寫了 34 號標題才發現要忽略，標題字級與最終版面（無 bullets）會對不上。
    if bullets is not None and not isinstance(bullets, (list, tuple)):
        sys.stderr.write(f"WARN figure「{title}」：bullets 必須是陣列，收到 {type(bullets).__name__}，已忽略\n")
        bullets = None
    if layout not in (None, "full"):
        sys.stderr.write(f"WARN figure「{title}」：layout「{layout}」無效（僅支援 None/\"full\"），已忽略\n")
        layout = None
    if layout == "full" and bullets:
        sys.stderr.write(f"WARN figure「{title}」：layout=full 不畫 bullets（滿版留給圖），已忽略 bullets 參數——英文說明請改走 notes 參數\n")
        bullets = None
    s = head()
    s.append(dots(70, 70))
    s.append(txt(90, 120, title, 34 if bullets else 46, ls="1.2"))
    s.append('<line x1="90" y1="145" x2="1190" y2="145" stroke="#C4C9D0" stroke-width="2"/>')
    raw_overflow_y = None  # codex review P2：溢出警告用未夾住的真實值，夾住的 cap_y 會讓警告永遠不觸發

    if layout == "full":
        # 滿版版型：不畫 bullets，圖吃掉幾乎整個內容區（content 區約 90-1190 x 150-710；
        # 這裡取 img_w/img_h 讓面積佔比 >80%）。
        img_x, img_w = 50, 1180
        img_y0, cap_y = 160, 700
        img_h = cap_y - 20 - img_y0
    elif bullets:
        y = 180
        truncated = False
        for b in bullets:
            if y > 480:
                truncated = True
                break
            # codex review P2（第二輪）：元素非字串（None／數字／dict）會讓 cjk_wrap 炸或亂排，
            # 比照 content() 的寫法統一轉字串；None/空字串整條跳過不留空行。
            if b is None:
                continue
            b = str(b)
            if not b:
                continue
            lines = cjk_wrap(b, 84)
            for ln in lines:
                # codex review P2（第三輪）：單一 bullet 折成很多行時，外層「bullet 開頭才檢查 y」
                # 攔不住——改成逐行檢查，一超過上限就整條頁面的 bullet 繪製直接收手。
                if y > 480:
                    truncated = True
                    break
                s.append(txt(105, y, ln, 19, "#2A2A2A", "400", ls="0.2"))
                y += 27
            if truncated:
                break
            y += 5
        if truncated:
            sys.stderr.write(f"WARN figure「{title}」：bullets 太多，圖片區會被擠出畫布/與 caption 重疊，已截斷後續 bullet——內容過長，拆成兩頁或精簡文字\n")
        img_x, img_w = 240, 800
        img_y0 = max(y + 8, 170)
        img_h = max(630 - img_y0, 140)
        if img_y0 + 140 >= 630:  # codex review P2（第四輪）：被夾到下限＝圖只剩 140px 高，值得主動提醒
            sys.stderr.write(f"WARN figure「{title}」：bullets 把圖片區壓到最小高度（140px），畫面會很擠——考慮精簡文字\n")
        cap_y = min(img_y0 + img_h + 22, 695)
        raw_overflow_y = img_y0 + img_h + 42  # 未夾住：bullets 太多把圖擠出畫布時這裡會 > 720
    else:
        img_x, img_w = 240, 800
        img_y0, img_h, cap_y = 170, 440, 655
    embedded = False
    raw = _valid_image_bytes(path)  # 驗 magic bytes（擋 0-byte／崩潰半成品／非圖片；只 isfile 會靜默嵌空圖）
    if raw is not None:
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext)
        if mime:
            b64 = base64.b64encode(raw).decode()
            s.append(f'<image x="{img_x}" y="{img_y0}" width="{img_w}" height="{img_h}" '
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
                    sc = min(img_w / iw, img_h / ih)
                    dw, dh = iw * sc, ih * sc
                    dx, dy = img_x + (img_w - dw) / 2, img_y0 + (img_h - dh) / 2
                    rx0, ry0, rx1, ry1 = hl
                    s.append(f'<rect x="{dx + rx0 * dw:.1f}" y="{dy + ry0 * dh:.1f}" '
                             f'width="{max((rx1 - rx0) * dw, 0):.1f}" height="{max((ry1 - ry0) * dh, 0):.1f}" '
                             f'fill="none" stroke="#CC2222" stroke-width="2.5"/>')
        else:
            sys.stderr.write(f"WARN figure「{title}」：副檔名非 png/jpg（{path}），改用佔位框\n")
    elif path:
        sys.stderr.write(f"WARN figure「{title}」：圖檔缺失或無效（{path}），改用佔位框\n")
    if not embedded:
        # codex review P3：無 bullets 時佔位框座標要與原版完全一致（200/380/380），
        # 否則「不給 bullets 時版面與行為完全不變」的宣稱不成立（既有無圖佔位頁會跟著回歸）。
        if layout == "full":
            s.append(f'<rect x="{img_x}" y="{img_y0}" width="{img_w}" height="{img_h}" fill="#FFFFFF" stroke="#B0B6BE" stroke-width="2" stroke-dasharray="10 8"/>')
            s.append(txt(img_x + img_w / 2, img_y0 + img_h / 2, "[ Journal Figure ]", 36, "#8A9099", "700", "middle"))
        elif bullets:
            # codex review P3（第二輪）：佔位框高度跟 cap_y 連動，img_h 被夾到下限 140 時
            # 框底（img_y0+15+height）不會超出 cap_y，不會壓到下方 caption。
            # codex review P2（第三輪）：ph_h 下限 60 在極端擠壓情況仍可能讓框底超過 cap_y、
            # 與 caption 重疊；沒有足夠空間（<75px）時乾脆不畫佔位框，只留 caption——
            # 少畫一個裝飾框不影響資訊完整性，畫出去壓字才是真正的版面壞掉。
            avail = cap_y - 30 - (img_y0 + 15)
            if avail >= 75:
                ph_h = min(img_h - 30, avail)
                s.append(f'<rect x="240" y="{img_y0 + 15}" width="800" height="{ph_h}" fill="#FFFFFF" stroke="#B0B6BE" stroke-width="2" stroke-dasharray="10 8"/>')
                s.append(txt(W/2, img_y0 + ph_h/2 + 15, "[ Journal Figure ]", 34, "#8A9099", "700", "middle"))
            else:
                sys.stderr.write(f"WARN figure「{title}」：bullets 把版面擠到沒空間畫佔位框，已略過（caption 仍會畫）\n")
        else:
            s.append('<rect x="240" y="200" width="800" height="380" fill="#FFFFFF" stroke="#B0B6BE" stroke-width="2" stroke-dasharray="10 8"/>')
            s.append(txt(W/2, 380, "[ Journal Figure ]", 34, "#8A9099", "700", "middle"))
    if layout == "full":
        s.append(txt(img_x + img_w / 2, cap_y, caption, 18, "#8A9099", "400", "middle"))
    else:
        s.append(txt(W/2, cap_y, caption, 22, "#8A9099", "400", "middle"))
    # codex review P3：_warn_overflow 只在新的 bullets 路徑才呼叫（既有無 bullets 路徑維持原本
    # 「不檢查」行為不變，避免既有頁面突然冒出沒人處理過的溢出警告）；P2：用未夾住的 raw_overflow_y。
    if bullets:
        _warn_overflow("figure", title, raw_overflow_y)
    stem = "fig_" + slug(title)
    write(outdir, idx, stem, s)
    # codex review P2（2026-10-09）：outdir 是相對單層路徑（如 "svg_output"）時 dirname 會是空字串，
    # notes 跑到 CWD 下、ppt-master 找不到 → 先 abspath。沒有 notes 時要刪掉同名舊檔，
    # 否則重跑後舊講稿殘留、被吃進新 pptx。
    # review P3：只在 outdir 是慣例的 <project>/svg_output 時才寫／刪 notes，否則（如 /tmp/out）
    # 會寫進共用的 /tmp/notes/、「無 notes 就刪舊檔」還可能刪到不相干的同名檔。
    out_abs = os.path.abspath(outdir)
    notes_path = None
    if os.path.basename(out_abs) == "svg_output":
        notes_path = os.path.join(os.path.dirname(out_abs), "notes", f"{idx}_{stem}.md")
    elif notes:
        sys.stderr.write(f"WARN figure「{title}」：outdir 不是 <project>/svg_output，講者備忘稿略過不寫（ppt-master 只認 <project>/notes/）\n")
    if notes_path is None:
        pass
    elif not notes:
        try:
            if os.path.isfile(notes_path):
                os.remove(notes_path)
        except OSError as e:
            sys.stderr.write(f"WARN figure「{title}」：舊講者備忘稿刪除失敗（{e}）\n")
    if notes and notes_path:
        # 講者備忘稿（2026-10-09 新增，EBM 背景機轉圖 layout=full 用）：寫進
        # <project_path>/notes/<svg 完整檔名 stem（含 idx 前綴）>.md，project_path = outdir
        # 的上一層（outdir 慣例是 <project>/svg_output）。ppt-master 的 find_notes_files()
        # 用「檔名 stem 完全相同」比對 SVG（見該檔 docstring：notes/01_cover.md -> 01_cover.svg），
        # 只對到 "fig_xxx" 不含 idx 前綴配不上、notes 會被靜默忽略（2026-10-09 首版踩到，
        # has_notes_slide 檢查出來才發現）——svg 實際檔名是 write() 產出的 f"{idx}_{stem}.svg"，
        # notes 檔名要完全比照同一個 stem。
        try:
            os.makedirs(os.path.dirname(notes_path), exist_ok=True)
            notes_text = "\n".join(f"- {n}" for n in notes) if isinstance(notes, (list, tuple)) else str(notes)
            with open(notes_path, "w", encoding="utf-8") as f:
                f.write(notes_text)
        except OSError as e:
            sys.stderr.write(f"WARN figure「{title}」：講者備忘稿寫入失敗（{type(e).__name__}: {e}），投影片本身不受影響\n")

VALID_KINDS = {"section", "figure", "table", "textcard", "content", "flowchart"}
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
        # figure 的 layout/notes 是這次新增欄位，不在 _LIST_FIELDS 假設範圍內，獨立檢查
        # （2026-10-09 新增，EBM 背景機轉圖改滿版版型＋講者備忘稿）。
        if k == "figure":
            layout_val = sl.get("layout")
            if layout_val is not None and layout_val not in ("full",):
                raise SystemExit(f"{where} figure 的 layout 只支援 null 或 \"full\"，收到 {layout_val!r}")
            notes_val = sl.get("notes")
            if notes_val is not None and not isinstance(notes_val, (str, list)):
                raise SystemExit(f"{where} figure 的 notes 必須是文字或陣列，收到 {type(notes_val).__name__}")
            if isinstance(notes_val, list):
                for j, n in enumerate(notes_val):
                    if not isinstance(n, (str, int, float)):
                        raise SystemExit(f"{where} notes[{j}] 必須是文字/數字，收到 {type(n).__name__}")
        # flowchart 的 steps/excluded 是物件陣列（不是 _LIST_FIELDS 假設的純量陣列），獨立檢查
        # （2026-10-09 新增，EBM ACQUIRE 選文流程頁改成 PRISMA 式方框圖）。
        if k == "flowchart":
            steps = sl.get("steps")
            if not isinstance(steps, list) or not steps:
                raise SystemExit(f"{where} flowchart 的 steps 必須是非空陣列")
            for j, st in enumerate(steps):
                if not isinstance(st, dict):
                    raise SystemExit(f"{where} steps[{j}] 必須是物件 {{label,n}}")
                if not isinstance(st.get("label"), str):
                    raise SystemExit(f"{where} steps[{j}].label 必須是文字")
                # codex review P2（round2 Sonnet）：bool 是 int 子類別，這裡原本沒排除，
                # 跟 flowchart() 內部自己的檢查（已排除 bool）不一致，兩處要同步。
                n_val = st.get("n")
                if isinstance(n_val, bool) or not isinstance(n_val, (int, float)):
                    raise SystemExit(f"{where} steps[{j}].n 必須是數字")
            excl = sl.get("excluded")
            if excl is not None:
                if not isinstance(excl, list):
                    raise SystemExit(f"{where} flowchart 的 excluded 必須是陣列")
                for j, e in enumerate(excl):
                    if not isinstance(e, dict):
                        raise SystemExit(f"{where} excluded[{j}] 必須是物件 {{after,n,reasons}}")
                    after_val = e.get("after")
                    if isinstance(after_val, bool) or not isinstance(after_val, int):
                        raise SystemExit(f"{where} excluded[{j}].after 必須是整數（steps 索引，0-based）")
                    n_ex_val = e.get("n")
                    if isinstance(n_ex_val, bool) or not isinstance(n_ex_val, (int, float)):
                        raise SystemExit(f"{where} excluded[{j}].n 必須是數字")
                    if "reasons" in e:
                        if not isinstance(e["reasons"], list):
                            raise SystemExit(f"{where} excluded[{j}].reasons 必須是陣列")
                        # codex review P2（round1 Sonnet）：reasons 元素型別當時只在 flowchart()
                        # 內部檢查，validate_content 沒檢查——這裡補齊，提早在內容階段就擋掉。
                        for k2, r in enumerate(e["reasons"]):
                            if isinstance(r, bool) or not isinstance(r, (str, int, float)):
                                raise SystemExit(f"{where} excluded[{j}].reasons[{k2}] 必須是文字/數字，收到 {type(r).__name__}")

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
                "figure": lambda idx, sl: figure(outdir, idx, sl.get("title", "Figure"), sl.get("caption", ""), sl.get("path"), sl.get("hl"), sl.get("bullets"), sl.get("layout"), sl.get("notes")),
                "table": lambda idx, sl: table(outdir, idx, sl.get("title", ""), sl.get("headers", []), sl.get("rows", []), sl.get("widths"), sl.get("note")),
                "textcard": lambda idx, sl: textcard(outdir, idx, sl.get("title", ""), sl.get("paragraphs", []), sl.get("quote"), sl.get("caption")),
                "flowchart": lambda idx, sl: flowchart(outdir, idx, sl.get("title", ""), sl.get("steps", []), sl.get("excluded"), sl.get("note")),
                "content": lambda idx, sl: content(outdir, idx, sl.get("title", ""), sl.get("bullets", []))}
    for sl in data.get("slides", []):
        dispatch.get(sl.get("kind"), dispatch["content"])(f"{n:02d}", sl)
        n += 1
    print(f"generated {n-1} slides -> {outdir}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("用法: gen_journal_svg.py <content.json> <svg_output_dir>")
    build(sys.argv[1], sys.argv[2])
