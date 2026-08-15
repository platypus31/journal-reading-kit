<!-- OpenAI Codex CLI 設定；內容同 CLAUDE.md -->

# Journal Reading Kit

丟論文，自動產出三種格式：簡報 (PPT)、口頭報告逐字稿、報告前閱讀摘要。

## Skills

| Command | File | 類型 | 說明 |
|---------|------|------|------|
| `/jr` | `skills/jr.md` | 主入口 | 完整 journal reading 流程（唯一需要的指令） |
| `/fetch-paper` | `skills/fetch-paper.md` | 內部 | 取得論文全文與 metadata（由 /jr 自動呼叫） |
| `/background` | `skills/background.md` | 內部 | 背景知識整理（由 /jr 自動呼叫） |
| `/methods` | `skills/methods.md` | 內部 | 研究方法拆解（由 /jr 自動呼叫） |
| `/results` | `skills/results.md` | 內部 | 結果解讀 + 圖表解說（由 /jr 自動呼叫） |
| `/discussion` | `skills/discussion.md` | 內部 | 討論、限制、COI、結論（由 /jr 自動呼叫） |
| `/generate-output` | `skills/generate-output.md` | 內部 | 產生三種輸出（由 /jr 自動呼叫） |

## 使用方式

```bash
cd journal-reading-kit
claude
> /jr
```

提供論文（標題 / PMID / DOI / PDF 路徑）→ **全程全自動、不詢問任何格式選項**（簡報格式已定案「White Grey 取風格版」）。
三種產出一律落在 repo 內的 `output/`（首次執行自動建立，已 gitignore）。

## 三種輸出

1. **簡報 (PowerPoint)** — 定案格式「White Grey 取風格版」：`scripts/gen_journal_svg.py` 程式生成 SVG（英文條列式＋流線裝飾＋section 過場）→ ppt-master gate + export 成 native 可編輯 pptx；配圖 `scripts/extract_figures.py` 從論文 PDF 抽統計圖表。fallback：template-fill 硬套官方範本 → python-pptx → Markdown（詳見 `skills/generate-output.md` §2）
2. **口頭報告逐字稿** — Markdown 格式，逐頁對應簡報，標注語氣和重點
3. **報告前閱讀摘要** — 1-2 頁精簡摘要，讓聽眾 5 分鐘看完掌握論文重點

## 外部工具（零 MCP 也能跑）

- **論文取得／metadata**：內建走 PubMed E-utilities（curl）與 Europe PMC，**不需任何 MCP**
- **圖表擷取**：`scripts/extract_figures.py`（pymupdf）
- 有 PubMed／Playwright MCP 可加分，但非必需（沒有也不影響任何一步）
- **ppt-master** — 簡報產生主路線，**唯一必裝的外部依賴**（native 可編輯 pptx + 載入使用者範本，裝在 `$PPT_MASTER_DIR`，預設 `~/ppt-master`；安裝見 README，接法見 `docs/ppt-master-integration.md`）
- **WebSearch / WebFetch** — 背景知識搜尋、圖片取得（選配，缺了只影響背景補充深度）

## 語言規則

- 使用者互動：繁體中文
- 論文引用：保持英文原文
- 簡報：中文標題 + 英文數據/引用
- 逐字稿：繁體中文（附英文專有名詞）

## 專案結構

```
journal-reading-kit/
├── CLAUDE.md                  # 本檔；AGENTS.md／GEMINI.md／.cursorrules／
│                              # .github/copilot-instructions.md 為同內容的各平台複本
├── README.md
├── CONTRIBUTING.md
├── .claude/commands/jr.md     # /jr 斜線指令（轉呼叫 skills/jr.md）
├── skills/
│   ├── jr.md                  # /jr 主流程（唯一入口）
│   ├── fetch-paper.md         # （內部）取得論文（curl，零 MCP）
│   ├── background.md          # （內部）背景知識
│   ├── methods.md             # （內部）研究方法
│   ├── results.md             # （內部）結果解讀
│   ├── discussion.md          # （內部）討論與限制
│   └── generate-output.md     # （內部）產生三種輸出
├── scripts/
│   ├── gen_journal_svg.py     # 主引擎：content.json → SVG deck（White Grey）
│   ├── extract_figures.py     # 從論文 PDF 抽統計圖表
│   └── generate_pptx.py       # python-pptx fallback（吃舊 slides.json schema）
├── data/
│   ├── example-content.json           # content.json 範例＝主引擎輸入格式
│   ├── example-content-bmj-glp1ra.json # 實戰範例（BMJ GLP-1RA）
│   ├── slide-template.md      # 簡報結構範本
│   ├── script-template.md     # 逐字稿範本
│   ├── summary-template.md    # 閱讀摘要範本
│   ├── pptx-templates/        # template-fill 備選用的官方 .pptx 範本
│   └── templates/             # style-a/b/c，僅 fallback generate_pptx.py 使用
├── docs/
│   └── ppt-master-integration.md  # ppt-master 安裝後的接法詳解
└── output/                    # 三種產出落點（首次執行自動建立，已 gitignore）
```
