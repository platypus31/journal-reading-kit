# ppt-master 整合說明（簡報產生主路線）

> 目的：讓 journal reading 的簡報產出能貼合使用者的 .pptx 範本、產出 native 可編輯投影片。
> 內建的 `scripts/generate_pptx.py` 是 `Presentation()` 從零硬編碼、無法載入既有範本；
> [ppt-master](https://github.com/hugohe3/ppt-master)（MIT）能**載入你的 .pptx 範本當母片、產出 native 可編輯 pptx**，故設為簡報產生的**主路線**。
> （與 EBM report pipeline 共用同一個 ppt-master 獨立工具，接法一致。）

## 1. 它裝在哪、怎麼跑

- **位置**：獨立工具，裝在 `$PPT_MASTER_DIR`（未設則預設 `~/ppt-master`，**不在本 repo 內**）。安裝步驟見 README「安裝 ppt-master」。本文所有指令先取一次路徑：

  ```bash
  PPT_MASTER="${PPT_MASTER_DIR:-$HOME/ppt-master}"
  PY="$PPT_MASTER/.venv/bin/python"
  ```

  ppt-master 需自帶獨立 venv（`$PPT_MASTER/.venv`，python 3.10+）。
- 🔴 **認知：ppt-master 不是 GUI 軟體，是一個「skill」** —— 要掛在某個 AI agent（Claude Code / Cursor / GPT）下、由 AI 讀它的指令執行，有**互動確認關卡、不能全自動**。實際用法：到 `$PPT_MASTER`（預設 `~/ppt-master`）開一個 agent session，跟它說「用這個範本產這份簡報」。

## 2. 資料流（journal reading ↔ ppt-master）

本 pipeline 負責**內容**（論文解讀 → 簡報大綱 `content.json`），ppt-master 負責**把內容變漂亮 pptx**：

> 📌 schema 對照：主路線用 `content.json`（`scripts/gen_journal_svg.py` 的輸入，範例見 `data/example-content.json`）；
> `slides.json` 只是 fallback `scripts/generate_pptx.py` 的舊 schema，兩者不通用。

```
journal reading: generate-output.md → content.json（簡報大綱）
                                          │
                                          ▼
ppt-master（在 $PPT_MASTER 跑）：讀內容 + 你的 .pptx 範本 → native pptx
                                          │
                                          ▼
產出 .pptx → ~/Desktop/jr-report.pptx（或 output/）
```

逐字稿（`jr-script`）與閱讀摘要（`jr-summary`）不受影響，仍由 generate-output.md 原流程產出。

## 3. 兩條路線（依你有沒有 .pptx 範本二選一）

### A. 有設計範本（推薦，最貼合你的設計）— Fill Native PPTX 路線
把你的 .pptx 範本當「投影片庫」，複製版面、把 journal 內容填進 slot（純 OOXML，最保真）：
```bash
PPT_MASTER="${PPT_MASTER_DIR:-$HOME/ppt-master}"
PY="$PPT_MASTER/.venv/bin/python"
cd "$PPT_MASTER"
$PY skills/ppt-master/scripts/template_fill_pptx.py analyze <你的範本.pptx> -o analysis/lib.json
# 再由 AI 依 content.json 內容規劃 fill plan → apply 產出
```
更簡單：在 `$PPT_MASTER` 開 Claude Code session，說「用 `<範本>.pptx` 產這份 journal club 簡報，內容在這」，貼上 `content.json`，讓 AI 讀 `skills/ppt-master/SKILL.md` 走 Fill Native PPTX route。

### B. 沒有範本 — Generate PPTX 路線（AI 設計）
在 `$PPT_MASTER` 開 agent session，餵簡報大綱 + 選定風格（A 經典/B 視覺/C 精簡），讀 `SKILL.md` 走 Generate route（AI 手寫 SVG → native pptx）。有範本時優先走 A。

## 4. Fallback 關係

`ppt-master（主路線）` → `Canva MCP` → `scripts/generate_pptx.py`（陽春 python-pptx）→ `Google Slides` → `Markdown`。
`generate_pptx.py` 保留為 fallback，不再另加載入範本功能（與 ppt-master template-fill 重複）。

## 5. 更新 ppt-master

```bash
PPT_MASTER="${PPT_MASTER_DIR:-$HOME/ppt-master}"
cd "$PPT_MASTER" && git pull && .venv/bin/pip install -r requirements.txt
```
