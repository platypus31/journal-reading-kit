# Journal Reading 簡報結構範本

> **本規格提取自三份實際院內 journal reading 成品範本**（denosumab FREEDOM / fibula flap pediatric / facet joint OA）
> + 兩份官方設計模板的共同邏輯，2026-08-12 落地。融合原則：**採用成品的章節骨架與條列式呈現（2026-08-12 拍板），
> 保留 IMRaD 完整專業要素，並修掉成品的 bug（標題溢出、拼字錯、圖用背景嵌入非 native）。**

## 提取自成品的核心邏輯（生成時必守）

1. **版面尺寸**：20 × 11.2 in（放大版 16:9，三份成品範本一致）。
2. **呈現風格＝條列式（放在大文字方塊裡）**（2026-08-12 修正，取代原段落式）：
   每張內容頁 = 標題 + **一個大文字方塊**，方塊內用**條列式 bullet** 列出講述重點（3–6 條），
   **不是整段流水敘述**。文字方塊要夠大、字要夠大（見第 10 條）。
3. **章節過場頁（Section Marker）＝全屏大寫英文章節名**：`INTRODUCTION` / `METHODS` / `RESULTS` /
   `DISCUSSION` / `CONCLUSION`（大字置中，簡約背景），每進一個 IMRaD 大段前插一張。
4. **標題全大寫、serif、大字級**（成品用 50–95pt）。🔴 **防 bug：封面與章節標題若超過 2 行就縮字級**，
   絕不讓標題壓到下方文字（fibula 那份封面就是標題 5 行壓到 presenter 資訊——不可重演）。
5. **圖表頁**：Results 段每個主要 outcome 配一張圖表頁（KM curve / forest plot / BMD 曲線 / Table）。
   🔴 圖表必須是 **native 物件或正規嵌入圖片**，不可用「背景填充」塞圖（成品的圖 python 讀不到就是這個病）。
6. **總張數 28–32**（成品 26–30），Results 段佔最大（約 35%）。
7. **設計＝取模板風格，不硬套版面**（2026-08-12 修正，推翻原 template-fill 硬套）：
   取兩份模板的**簡約風格**（白底 + 灰色流線/斜紋幾何裝飾 + serif 大寫標題），
   **但不用 ppt-master `template-fill` 硬套模板的固定版面**——模板有些頁是時序性版面（PROCESS 的 1234 編號）、
   有些裝飾圖跟 journal 內容無關，硬套會不搭。改用 **`scripts/gen_journal_svg.py`** 程式生成（矢量流線裝飾＋條列式，經 ppt-master gate/export 成 native pptx）、只借其風格，版面隨內容自由排。
   - 風格參考檔留在 `data/pptx-templates/`（primary=White Grey 流線 / fallback=Thesis 斜紋），供人工比對配色字體，**不是拿來硬填**。

8. 🔴 **語言＝英文為主（2026-08-12 demo 校準）**：內容頁**直接截取 journal 原文英文**（Methods/Results 的數據、定義、關鍵句照原文引述），
   只有 **Background 的概念解說可用中文**。**不要把整份翻成中文**（demo 全中文是錯的）。
9. 🔴 **配圖＝從 journal 抓統計圖表（2026-08-12 校準）**：Results 段必須放論文裡的**實際圖表**
   （forest plot / Kaplan-Meier / BMD 曲線 / Table），用 `scripts/extract_figures.py` 從 PDF 抽圖後插入對應頁，
   **圖文並存**，不要像 demo 那樣純文字沒圖。
10. 🔴 **字級＝內容文字要大（2026-08-12 校準）**：講述用的 body 文字別太小，一頁不塞過多字；
    寧可拆頁也要讓報告時看得清（demo 文字太小）。

---

## 封面區（2 張）

### Slide 1 — 封面
- 論文標題（英文原文，大寫，**超過 2 行就縮字級防溢出**）
- `Presenter: {報告者}`（範本格式）
- `Supervisor: {指導醫師}醫師`
- 科別、日期

### Slide 2 — 論文資訊頁
- 期刊名稱、年份、Impact Factor
- 作者（第一作者 + 通訊作者）
- 研究類型標籤（RCT / Cohort / SR / Review）
- PMID / DOI；可附論文封面截圖

---

## 導覽區（1 張）

### Slide 3 — 目錄 / CONTENT
- 大寫章節序列：INTRODUCTION → METHODS → RESULTS → DISCUSSION → CONCLUSION

---

## INTRODUCTION 前言（4–6 張）

### Section Marker — INTRODUCTION（全屏大寫過場）

### Slide — 疾病/主題概述（條列式）
- 條列 3-4 點：定義、分類、流行病學（全球 + 台灣數據）

### Slide — Pathophysiology / 機轉
- 條列重點 + 機轉圖（native 圖），30 秒能理解

### Slide — 目前治療現況 + Knowledge Gap
- 一段：現有治療指引 / 標準治療；已知什麼、還不知道什麼、為何需要這篇研究

### Slide — 關鍵概念 + 研究目的 / Hypothesis
- 不常見概念或統計名詞（non-inferiority / composite endpoint）一句話解釋
- 明確的研究問題與假說

---

## METHODS 研究方法（5–7 張）

### Section Marker — METHODS

### Slide — 研究設計概覽（條列式）
- 一段：研究類型、多/單中心、國家數、研究名稱/NCT、研究期間

### Slide — 受試者選取
- Inclusion / Exclusion Criteria（此頁**可用短 bullet**逐條列，標關鍵收案）

### Slide — 分組、盲化、介入方式
- 一段：隨機化方法、分配比例、盲化程度、分層因子
- 實驗組（藥物/劑量/頻率/療程）vs 對照組（安慰劑/標準治療），對比呈現

### Slide — Endpoints 定義
- Primary Endpoint 完整定義（中英）；Secondary / Safety Endpoints（可 bullet）

### Slide — 統計方法（+ CONSORT 時程）
- 一段：分析族群（ITT/PP）、主要分析方法、sample size、多重比較校正、中期分析

---

## RESULTS 結果（10–14 張，最大段落，佔 35%+）

### Section Marker — RESULTS

### Slide — 收案流程 (CONSORT / Flow Diagram)（native 流程圖）
- 篩選 → 排除 → 隨機化 → 各組 → 完成追蹤 → 分析，每步標人數

### Slide — 基線特徵 (Table 1)（native 表格）
- 兩組重要基線比較（年齡/性別/BMI/關鍵指標），是否 well-balanced

### Slide — Primary Outcome（概述，條列式）
- 一段：主要結果數字、效果量 + 95% CI + p-value；**大字標示是否達顯著**

### Slide — Primary Outcome（圖表頁，native 圖）
- KM curve / 主要結果圖，標註關鍵發現與軸說明

### Slide — Primary Outcome（臨床意義）
- NNT / NNH / ARR / RRR（如適用）；統計顯著 vs 臨床意義

### Slide — Secondary Outcomes（每個主要的 1 張，段落 + 對應圖）
### Slide — Subgroup Analysis（forest plot，native 圖）
### Slide — Safety / Adverse Events（段落 + 必要時 bullet 列 SAE）
### Slide — 結果摘要表（native 表格，一目了然哪些顯著）

---

## DISCUSSION 討論（4–6 張，條列式）

### Section Marker — DISCUSSION

### Slide — 主要發現摘要：1–3 句呼應假說
### Slide — 與現有文獻比較：支持的 / 矛盾的文獻與可能解釋
### Slide — 臨床意義：對台灣臨床實務的影響
### Slide — 值得討論的議題：2–3 個開放性問題（引發 journal club 討論）

---

## LIMITATIONS 研究限制（1–2 張）

### Slide — 作者提出的限制 + 我們額外發現的
- 段落或短 bullet：Selection / Measurement bias、Confounders、External validity

---

## CONCLUSION 結論（2–3 張）

### Section Marker — CONCLUSION

### Slide — Take Home Message
- 3–5 個重點，大字呈現，臨床導向（明天就能用）

### Slide — 臨床實務影響 + References
- 對查房/看診的改變，用病人聽得懂的話說一次；主要參考文獻

### Slide — THANK YOU（全屏大字，範本結尾格式）

---

## 補充頁區（Supplementary，不計入正式張數）
- 額外圖表、機制詳解、sub-analysis，備 Q&A 用，不在正式報告放映
