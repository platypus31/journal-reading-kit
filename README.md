# Journal Reading Kit

丟一篇論文，自動產出三種格式：**簡報（可編輯 PowerPoint）、口頭報告逐字稿、報告前閱讀摘要**。
適用於科內 Journal Club / Journal Reading 報告。給 AI CLI（Claude Code / Codex / Gemini CLI）使用的 skill 工具箱。

> 本工具與姊妹作 [ebm-report-kit](https://github.com/platypus31/ebm-report-kit)（EBM 5A 報告產生器）**各自獨立、互不依賴**，可單獨安裝使用。

## 流程

```
輸入論文（標題 / PMID / DOI / PDF）
    ↓
自動分析全文（Background → Methods → Results → Discussion）
    ↓
自動產出三種格式（簡報格式已定案「White Grey」風格，全自動不詢問）
    ├── 簡報（SVG → native 可編輯 .pptx）
    ├── 口頭報告逐字稿
    └── 報告前閱讀摘要
```

## 快速開始

### 一鍵安裝（推薦）

```bash
git clone https://github.com/platypus31/journal-reading-kit.git
cd journal-reading-kit
bash bootstrap.sh   # 自動檢查依賴、安裝 ppt-master（約 1.2GB）、self-check
```

全綠後直接啟動 AI CLI（如 `claude`）輸入 `/jr` 即可。`bash bootstrap.sh --check-only` 只檢查不安裝。
以下是需求細節與手動安裝步驟（bootstrap 自動做的就是這些事，想自己來才需要看）：

### 需求

- AI CLI：[Claude Code](https://docs.anthropic.com/en/docs/claude-code)、Codex CLI、Gemini CLI、Cursor 或 GitHub Copilot
  （repo 內含 `CLAUDE.md`／`AGENTS.md`／`GEMINI.md`／`.cursorrules`／`.github/copilot-instructions.md` 五份同內容設定）
- Python 3.9+（主引擎 `gen_journal_svg.py` 只用標準庫，不必額外裝套件）
- [ppt-master](https://github.com/hugohe3/ppt-master) —— **唯一必裝的外部依賴**（SVG → 可編輯 pptx 的匯出引擎，`bootstrap.sh` 會自動裝，手動裝見下）。
  抽圖用的 `PyMuPDF` 與 fallback 用的 `python-pptx` 都含在它的 venv 裡，**不需要另外 pip install**
- 論文取得走 `curl`（PubMed E-utilities + Europe PMC），**零 MCP**，不需任何額外設定
- 選配：Playwright（需 Node.js；`npx playwright install chromium`，論文網頁截圖用。本 repo 腳本全為 Python，不需要 `npm install`）

### 手動安裝（不跑 bootstrap 時）

簡報主路線（SVG → native 可編輯 pptx）與 PDF 抽圖都跑在 ppt-master 的 venv 裡，需先裝好：

```bash
git clone --depth 1 https://github.com/hugohe3/ppt-master.git ~/ppt-master
cd ~/ppt-master
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

⚠️ ppt-master 的資產庫約 1.2GB，建議照上面加 `--depth 1` 只抓最新一版。

裝在別的位置的話，設環境變數 `PPT_MASTER_DIR` 指過去即可 —— 本 repo 文件裡的指令一律以
`PPT_MASTER="${PPT_MASTER_DIR:-$HOME/ppt-master}"` 取值，沒設就用預設的 `~/ppt-master`：

```bash
export PPT_MASTER_DIR=/your/path/to/ppt-master
```

（`bootstrap.sh` 同樣認得 `PPT_MASTER_DIR`，會裝到你指定的位置。）

### 使用

```bash
git clone https://github.com/platypus31/journal-reading-kit.git
cd journal-reading-kit
claude
> /jr
```

提供論文標題、PMID、DOI 或 PDF 路徑，等待產出完成。全程自動，不會問你要哪種簡報風格。

三種產出都落在 repo 內的 `output/`（首次執行時自動建立，已 gitignore）：

```
output/jr-report.pptx          # 簡報（native 可編輯）
output/jr-script-{date}.md     # 口頭報告逐字稿
output/jr-summary-{date}.md    # 報告前閱讀摘要
```

## 三種輸出

### 簡報 (PowerPoint)
- IMRaD 結構（Introduction → Methods → Results → Discussion → Conclusion）
- Results 佔最大篇幅（35%+），含圖表逐一解說
- 附 Supplementary 補充頁（Q&A 備用）
- 定案「White Grey」格式：`scripts/gen_journal_svg.py` 程式生成 SVG → ppt-master 匯出 **native 可編輯** .pptx
- 配圖：`scripts/extract_figures.py` 從論文 PDF 抽統計圖表
- fallback 鏈（主路線不可用時）：ppt-master template-fill → python-pptx → Markdown

### 口頭報告逐字稿
- 每頁對應一張簡報
- 附語氣標注：`[強調]` `[停頓]` `[看觀眾]` `[指向圖表]`
- 時間提示，總計 22-34 分鐘

### 報告前閱讀摘要
- 1-2 頁 A4 精簡版
- 聽眾 5 分鐘看完掌握重點
- 附討論問題

## 品質檢查（自動執行）

- 統計顯著 vs 臨床意義判斷（NNT, ARD, CI 解讀）
- COI（利益衝突）評估
- Spin 偵測（結果過度詮釋）
- 外在效度檢核（台灣適用性）

## 自訂風格 / 模板

想換成自己的版型或配色，有三條路：

1. **直接在 PowerPoint 改（推薦）** —— 產出是 **native 可編輯 pptx**，不是圖片也不是唯讀檔，
   套自家佈景主題、改字型配色、調版面都跟一般簡報一樣操作。
2. **套自有 .pptx 範本** —— ppt-master 的 **Fill Native PPTX** 路線可把你的 .pptx 當母片硬套內容，
   接法見 [`docs/ppt-master-integration.md`](docs/ppt-master-integration.md) §3。
   ⚠️ 實測硬套有時版面/裝飾不搭，契合度請自行評估。
3. **改「White Grey」風格本身** —— 版面規則全寫在 `scripts/gen_journal_svg.py`（MIT，歡迎自行修改）。
   ⚠️ 目前**沒有參數化的模板系統**，換風格＝直接改該腳本的繪製邏輯。

## License

MIT
