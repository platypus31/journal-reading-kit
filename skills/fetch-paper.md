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

> 🔴 **預設走 curl（NCBI E-utilities＋Europe PMC），不需任何 MCP**。若環境有 PubMed MCP 可替代這些 curl，但非必需。以下指令可直接照抄執行。

### 1. 識別論文 + 取得 Metadata（curl，零 MCP）

**PMID → metadata（標題／作者／期刊／年份／PMCID／DOI）：**
```bash
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=<PMID>&retmode=json"
```

**標題／DOI → 找 PMID：**
```bash
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term=<urlencode 的標題或 DOI>"
# 回傳 idlist[0] 即 PMID，再用上面的 esummary 取 metadata
```

**PDF 路徑：** 直接讀 PDF 取標題，再用標題 esearch 補 metadata。

整理欄位：標題／作者（第一+通訊+et al.）／期刊／年份／DOI／PMID／IF（如可查）／研究類型（RCT/Cohort/SR）。

### 2. 取得全文（curl，PMC 直連會被擋，走 Europe PMC）

```bash
# 先從 esummary 拿 PMCID（articleids 內），再抓 PDF + 全文 XML
curl -sL -A "Mozilla/5.0" "https://europepmc.org/articles/<PMCID>?pdf=render" -o paper.pdf
curl -s "https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/fullTextXML" -o fulltext.xml
# 驗證頁數（file 指令對 linearized PDF 會誤報 0 頁）：
python3 -c "import pymupdf; print(len(pymupdf.open('paper.pdf')))"
```
- 取不到全文（無 PMCID / 非 open access）→ 使用者有 PDF 就讀 PDF；都沒有 → 僅用摘要並標註限制。
- 有 PubMed MCP 的環境可改用 `mcp__*__get_full_text_article` 替代。

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
