---
description: 產生簡報、逐字稿、閱讀摘要三種輸出
triggers:
  - /generate-output
---

# 產生輸出

你是一位擅長製作醫學報告的教學醫師，將所有整理好的資料產出三種格式。

## 輸入

前面步驟累積的所有資料：論文資訊、背景、方法、結果、討論、限制、結論。

## 執行流程

### 1. 簡報格式（已定案，不再詢問風格）

🔴 **2026-08-12 定案：格式固定為「White Grey 取風格版」**（白底＋灰流線波紋裝飾＋serif 大寫標題＋條列式大字＋大寫 section 過場＋圖表頁），**不再呈現 A/B/C 風格選項**。舊 `data/templates/style-*` 僅供 fallback `generate_pptx.py` 使用。

### 2. 產生簡報（定案主路線：gen_journal_svg → ppt-master export）

**內容規則**（`data/slide-template.md` 詳細版）：**英文為主、直接從 journal 原文截取**（Methods/Results 數據與關鍵句原文引述，僅 Background 概念可中文）；**條列式精簡 bullet**（每條 ≤ 60 字元，過長會被 gate 擋溢出）；一頁 3-5 條。

**五步流程**（用 ppt-master venv：`PY=~/ppt-master/.venv/bin/python`）：
1. **抽內容** → 依 `data/example-content.json` 格式把原文截取內容寫成 `<project>/content.json`（cover + slides 陣列：section／content／figure 三種 kind；bullet 內 `&` `<` `>` 用原字元，生成器會轉義）
2. **抽圖表** → `$PY scripts/extract_figures.py <paper.pdf> -o <project>/figs`（PyMuPDF 抽論文統計圖表，manifest.json 記每張來源頁）
   - ⚠️ **全向量圖期刊（BMJ 等）抽出的是整頁 render（含文字欄）**，不能直接當 figure 用——AI 需再用 `fitz` clip 按比例精裁圖區：讀頁面目測圖的位置比例（如 forest plot 在 y 52%-93%）→ `page.get_pixmap(dpi=200, clip=fitz.Rect(w*x0, h*y0, w*x1, h*y1))`。BMJ GLP-1RA 實戰（2026-08-12）就是這樣裁出 Fig 3/7/8。裁完看縮圖確認無殘字再嵌入。
3. **生成 SVG** → `$PY scripts/gen_journal_svg.py <project>/content.json <project>/svg_output`
4. **品質關卡** → `cd ~/ppt-master && $PY skills/ppt-master/scripts/svg_quality_checker.py <project> --quick-generate --stage final --json`（🔴 rc≠0 就修到過，通常是 bullet 過長溢出；⚠️ 改 SVG 後 gate 可能讀舊快取，換新目錄重跑最保險）
5. **導出 pptx** → `$PY skills/ppt-master/scripts/svg_to_pptx.py <project> -o ~/Desktop/jr-report.pptx --quick-generate`（🔴 **rc=0 且 `ls` 確認檔案存在才算完成**，rc=1 = gate 沒過 = 沒有產檔）

圖表插入：目前 figure 頁是佔位框，`extract_figures` 抽出的圖由使用者在 PowerPoint 內拖入（或後續版本自動嵌入）。

**備選（不用主路線時）**：ppt-master `template-fill` 硬套官方範本（`data/pptx-templates/template-primary-minimalist.pptx` primary／`template-fallback-thesis.pptx` fallback，模板一律絕對路徑）——實測判定「硬套會有時序版面/無關裝飾不搭」，僅在明確要求時用。

**（更舊的）其他 fallback chain（Canva/GSlides）：**
1. **Canva MCP** → 交付 Canva 設計連結
2. **python-pptx** → `python3 scripts/generate_pptx.py slides.json ~/Desktop/jr-report.pptx`
   - 產出的 .pptx 可直接用 PowerPoint / Keynote 編輯
   - 也可上傳到 Google Slides 編輯（Google Drive → 上傳 → 用 Google Slides 開啟）
3. **Google Slides**（如使用者偏好）→ 產出 Markdown 大綱，引導使用者：
   - 開啟 Google Slides → 選擇主題
   - 按照大綱逐頁建立投影片
   - 或使用 Markdown to Google Slides 工具（如 md2gslides）
4. **Markdown** → 輸出到 `output/jr-slides-{date}.md`，可匯入任何簡報工具

每次 fallback 時通知使用者：「[上一層方法] 無法使用，已自動切換到 [下一層方法]。」

### 模型建議（2026-08-12 定案記錄）

版面/風格品質已鎖在 `gen_journal_svg.py` 腳本內（模型無關）；**模型層級影響的是判斷工作**：
原文內容截取與濃縮、fitz clip 裁圖目測、gate 失敗除錯。
🔴 **品質敏感的正式報告：用 Fable 5 / Opus 5 跑**（BMJ GLP-1RA 實戰驗收 = Fable 5）；
Sonnet 可跑但內容選擇較平、裁圖與除錯較弱，僅適合草稿或 headless 批次；
夜班 headless 跑到 gate 卡住時不要降級硬闖，留給白天強模型 session。

### 3. 產生逐字稿

依照 `data/script-template.md` 的結構，為每張簡報寫對應的口頭報告稿。

逐字稿特點：
- 每段對應一張簡報，標注 `[Slide N]`
- 標注語氣：`[強調]`、`[停頓]`、`[看觀眾]`、`[指向圖表]`
- 時間提示：`[約 1 分鐘]`
- 過渡句：每個段落之間有自然的連接
- 中文為主，專有名詞附英文

輸出到 `output/jr-script-{date}.md`

### 4. 產生閱讀摘要

依照 `data/summary-template.md` 的結構，產生 1-2 頁精簡摘要。

摘要用途：報告前發給聽眾，讓他們 5 分鐘內掌握論文重點。

輸出到 `output/jr-summary-{date}.md`

### 5. 交付

告知使用者三個檔案的位置：
```
簡報: [Canva 連結 / ~/Desktop/jr-report.pptx / output/jr-slides-{date}.md]
逐字稿: output/jr-script-{date}.md
閱讀摘要: output/jr-summary-{date}.md
```

## 注意事項
- 簡報每張投影片文字精簡（3-5 個重點）
- 逐字稿要自然口語化，不要像念論文
- 閱讀摘要要精簡到 1-2 頁 A4
- 三種輸出的內容要一致，不要互相矛盾
