#!/usr/bin/env bash
# journal-reading-kit bootstrap — 一鍵安裝依賴並自我驗證（冪等，可重複執行）
#
# 用法：
#   bash bootstrap.sh              # 安裝缺的東西 + self-check
#   bash bootstrap.sh --check-only # 只檢查不安裝
#
# 裝完後：在本目錄啟動你的 AI CLI（如 claude），輸入 /jr 開始使用。
set -u

CHECK_ONLY=0
[ "${1:-}" = "--check-only" ] && CHECK_ONLY=1

KIT_DIR="$(cd "$(dirname "$0")" && pwd)"
PPT_MASTER="${PPT_MASTER_DIR:-$HOME/ppt-master}"
PASS=0; FAIL=0; SKIP=0

say()  { printf '%s\n' "$*"; }
ok()   { PASS=$((PASS+1)); say "  ✅ $*"; }
bad()  { FAIL=$((FAIL+1)); say "  ❌ $*"; }
note() { SKIP=$((SKIP+1)); say "  ⚠️  $*"; }

say "== journal-reading-kit bootstrap =="
say ""
say "[1/3] 基本工具"
if command -v git >/dev/null 2>&1; then ok "git $(git --version | cut -d' ' -f3)"; else bad "缺 git — 請先安裝"; fi
if command -v python3 >/dev/null 2>&1; then
  PYV="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    ok "python3 ${PYV}"
  else
    bad "python3 ${PYV} 過舊 — 需 3.9+"
  fi
else
  bad "缺 python3 — 需 3.9+"
fi
if command -v node >/dev/null 2>&1; then ok "node $(node --version)（選配，論文網頁截圖用）"; else note "無 node（選配功能，核心流程不需要）"; fi

say ""
say "[2/3] ppt-master 匯出引擎（${PPT_MASTER}）— 內含 PyMuPDF/python-pptx，本 kit 不需另外 pip install"
if [ -d "${PPT_MASTER}/.git" ]; then
  ok "ppt-master 已存在"
else
  if [ "$CHECK_ONLY" = "1" ]; then
    note "ppt-master 未安裝（去掉 --check-only 重跑即可自動 clone，約 1.2GB）"
  else
    say "  ⏳ clone ppt-master（資產庫約 1.2GB，--depth 1，需數分鐘）..."
    if git clone --depth 1 https://github.com/hugohe3/ppt-master.git "${PPT_MASTER}"; then
      ok "ppt-master clone 完成"
    else
      bad "ppt-master clone 失敗（網路或磁碟空間？）"
    fi
  fi
fi
if [ -d "${PPT_MASTER}" ]; then
  if [ -x "${PPT_MASTER}/.venv/bin/python" ]; then
    ok "ppt-master venv 已存在"
  elif [ "$CHECK_ONLY" = "1" ]; then
    note "ppt-master venv 未建（去掉 --check-only 重跑即可安裝）"
  else
    REQ="${PPT_MASTER}/requirements.txt"
    [ -f "$REQ" ] || REQ="${PPT_MASTER}/skills/ppt-master/requirements.txt"
    if [ -f "$REQ" ] && python3 -m venv "${PPT_MASTER}/.venv" && \
       "${PPT_MASTER}/.venv/bin/pip" install -q --disable-pip-version-check -r "$REQ"; then
      ok "ppt-master venv 就緒"
    else
      bad "ppt-master venv 安裝失敗（requirements 位置或 pip 錯誤，見上方訊息）"
    fi
  fi
  if [ -x "${PPT_MASTER}/.venv/bin/python" ]; then
    if "${PPT_MASTER}/.venv/bin/python" -c 'import fitz, pptx' >/dev/null 2>&1; then
      ok "PyMuPDF + python-pptx 可 import（ppt-master venv）"
    else
      note "ppt-master venv 缺 fitz/pptx（抽圖與匯出會用到；重跑本腳本或手動 pip install）"
    fi
  fi
fi

say ""
say "[3/3] Self-check：用範例 content 實跑 SVG 引擎（純標準庫，系統 python3 即可）"
SELFCHECK_OUT="$(mktemp -d 2>/dev/null || echo /tmp/jr-bootstrap-$$)"
if python3 "${KIT_DIR}/scripts/gen_journal_svg.py" "${KIT_DIR}/data/example-content.json" "$SELFCHECK_OUT" >/dev/null 2>&1; then
  N="$(ls "$SELFCHECK_OUT" 2>/dev/null | grep -c '\.svg$')"
  if [ "$N" -gt 0 ]; then ok "SVG 引擎正常（範例生成 ${N} 張）"; else bad "SVG 引擎跑完但無產出"; fi
else
  bad "SVG 引擎 self-check 失敗：python3 scripts/gen_journal_svg.py data/example-content.json <outdir>"
fi
rm -rf "$SELFCHECK_OUT"

say ""
say "== 結果：✅ ${PASS} ｜ ❌ ${FAIL} ｜ ⚠️ ${SKIP} =="
if [ "$FAIL" -eq 0 ]; then
  say "🎉 就緒。下一步：在本目錄啟動你的 AI CLI（如 claude），輸入 /jr 開始。"
  exit 0
else
  say "還有 ❌ 項目要處理（見上），修完重跑本腳本即可（冪等）。"
  exit 1
fi
