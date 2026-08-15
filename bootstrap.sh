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
REQMISS=0   # 必裝依賴（ppt-master 及其 venv）缺失旗標——--check-only 時不報 FAIL 但不得宣告就緒
PM_BAD=0    # PPT_MASTER 路徑本身有問題（非 ppt-master repo）——不得再對該目錄動手

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
  if [ -e "${PPT_MASTER}" ]; then
    # 路徑被佔用要先判，否則 --check-only 會謊稱「重跑即可自動 clone」（實際會被擋下）
    bad "${PPT_MASTER} 已存在但不是 ppt-master 的 git repo — 請先移走或改設 PPT_MASTER_DIR 指到別處"
    PM_BAD=1
  elif [ "$CHECK_ONLY" = "1" ]; then
    note "ppt-master 未安裝（去掉 --check-only 重跑即可自動 clone，約 1.2GB）"
    REQMISS=1
  else
    say "  ⏳ clone ppt-master（資產庫約 1.2GB，--depth 1，依網速可能需數分鐘，請耐心等）..."
    if git clone --depth 1 https://github.com/hugohe3/ppt-master.git "${PPT_MASTER}"; then
      ok "ppt-master clone 完成"
    else
      bad "ppt-master clone 失敗（網路不通、磁碟空間不足，或該路徑不可寫）"
    fi
  fi
fi
if [ -d "${PPT_MASTER}" ] && [ "$PM_BAD" -eq 0 ]; then
  if [ -x "${PPT_MASTER}/.venv/bin/python" ]; then
    ok "ppt-master venv 已存在"
  elif [ "$CHECK_ONLY" = "1" ]; then
    note "ppt-master venv 未建（去掉 --check-only 重跑即可安裝）"
    REQMISS=1
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
      REQMISS=1
    fi
  fi
fi

say ""
say "[3/3] Self-check：用範例 content 實跑 SVG 引擎（純標準庫，系統 python3 即可）"
SELFCHECK_OUT="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/jr-bootstrap-$$-$RANDOM")"
mkdir -p "$SELFCHECK_OUT" 2>/dev/null || true
if python3 "${KIT_DIR}/scripts/gen_journal_svg.py" "${KIT_DIR}/data/example-content.json" "$SELFCHECK_OUT" >/dev/null 2>&1; then
  N="$(ls "$SELFCHECK_OUT" 2>/dev/null | grep -c '\.svg$')"
  if [ "$N" -gt 0 ]; then ok "SVG 引擎正常（範例生成 ${N} 張）"; else bad "SVG 引擎跑完但無產出"; fi
else
  bad "SVG 引擎 self-check 失敗：python3 scripts/gen_journal_svg.py data/example-content.json <outdir>"
fi
[ -n "$SELFCHECK_OUT" ] && [ -d "$SELFCHECK_OUT" ] && rm -rf "$SELFCHECK_OUT"

say ""
say "== 結果：✅ ${PASS} ｜ ❌ ${FAIL} ｜ ⚠️ ${SKIP} =="
if [ "$FAIL" -eq 0 ] && [ "$REQMISS" -eq 0 ]; then
  say "🎉 就緒。下一步：在本目錄啟動你的 AI CLI（如 claude），輸入 /jr 開始。"
  exit 0
elif [ "$FAIL" -eq 0 ] && [ "$REQMISS" -eq 1 ]; then
  say "⚠️  尚未就緒：必裝依賴未備妥（詳見上方 ⚠️ 訊息）—— 簡報匯出會失敗。"
  say "   若是尚未安裝，跑 \`bash bootstrap.sh\`（不加 --check-only）即可自動裝好。"
  exit 1
else
  say "還有 ❌ 項目要處理（見上），修完重跑本腳本即可（冪等）。"
  exit 1
fi
