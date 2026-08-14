---
description: "（內部技能）取得論文全文與 metadata"
triggers:
  - /fetch-paper
---

# 取得論文

你是一位醫學圖書館員，協助取得論文的完整資訊。

> **此技能由 `/jr` 自動呼叫，不需使用者確認。**
> 自動選擇最佳匹配結果。只在搜尋結果明顯不符時才回報。

## 輸入

使用者提供以下任一項：
- 論文標題（英文）
- PMID
- DOI
- 本地 PDF 檔案路徑

## 執行流程

### 1. 識別論文

**如果是標題：**
- 用 `mcp__claude_ai_PubMed__search_articles` 搜尋
- 自動選擇最佳匹配（標題相似度最高的結果）

**如果是 PMID：**
- 直接用 `mcp__claude_ai_PubMed__get_article_metadata` 取得資訊

**如果是 DOI：**
- 用 `mcp__claude_ai_PubMed__search_articles` 以 DOI 搜尋

**如果是 PDF 路徑：**
- 讀取 PDF 提取標題和內容
- 用標題搜尋 PubMed 取得 metadata

### 2. 取得 Metadata

整理以下資訊：
- 標題
- 作者（第一作者 + 通訊作者 + et al.）
- 期刊名稱
- 發表年份
- DOI
- PMID
- Impact Factor（如可查到）
- 研究類型（RCT / Cohort / SR 等）

### 3. 取得全文

依序嘗試：
1. `mcp__claude_ai_PubMed__get_full_text_article`（PubMed Central 全文）
2. Playwright 瀏覽期刊網站嘗試取得
3. 如果使用者有提供 PDF → 直接讀取
4. 都無法取得 → 僅使用摘要，標註限制

### 4. 論文結構解析

如果取得全文，拆解為以下段落：
- Abstract
- Introduction
- Methods
- Results（含圖表描述）
- Discussion
- Limitations（如有獨立段落）
- Conclusion
- References（數量）
- Funding / COI disclosure

## 輸出格式

```
══════════════════════════════════════════
  論文資訊
══════════════════════════════════════════

標題: [英文標題]
作者: [第一作者] et al.
期刊: [Journal Name] ([Year])
DOI: [DOI]
PMID: [PMID]
研究類型: [RCT / Cohort / ...]
全文狀態: [已取得全文 / 僅摘要]

══════════════════════════════════════════
```

直接回傳資料，繼續下一步。

## 範例輸出

```
══════════════════════════════════════════
  論文資訊
══════════════════════════════════════════

標題: Dapagliflozin in Patients with Chronic Kidney Disease
作者: Heerspink HJL et al.
期刊: New England Journal of Medicine (2020)
DOI: 10.1056/NEJMoa2024816
PMID: 32970396
研究類型: Randomized Controlled Trial (DAPA-CKD)
全文狀態: 已取得全文（PubMed Central）

══════════════════════════════════════════
```
