"""scripts/gen_journal_svg.py 斷行邏輯的回歸測試 —— cjk_wrap 與 table note 換行。

守的是 2026-08-15 修掉的兩個缺陷：
1. 純英文從單字中間硬切（asso/ciated、ti/ssue）—— 中文正常所以中文測資測不出來。
2. table 的 note 不換行 → 橫向出血（ppt-master gate 只驗直向溢出，這裡零訊號）。

本檔刻意用 importlib 直接載入腳本：本 kit 不自帶 venv／pyproject（依賴借 ppt-master），
所以測試不能依賴任何 pytest 設定或套件安裝。跑法：`python3 -m pytest tests -q`
"""

import importlib.util
import re
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "scripts" / "gen_journal_svg.py"
_spec = importlib.util.spec_from_file_location("gen_journal_svg", _SRC)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

cjk_wrap = gen.cjk_wrap
table = gen.table


def width(s):
    """與引擎同一套字寬：全形 2 單位、半形 1 單位。"""
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in s)


class TestCjkWrapEnglish:
    def test_does_not_split_inside_a_word(self):
        s = "Radioactive iodine therapy is associated with recurrent thyrotoxicosis"
        lines = cjk_wrap(s, 30)
        assert len(lines) > 1, "測資本身要真的需要換行，否則測不到東西"
        for word in s.split(" "):
            assert any(word in ln for ln in lines), f"單字「{word}」被腰斬：{lines}"

    def test_breaks_at_spaces_not_mid_word(self):
        # 窄欄（模擬表格 cell）最容易踩硬切；所有詞都必須整顆落在某一行
        s = "Mortality was not significantly different between arms"
        lines = cjk_wrap(s, 20)
        assert len(lines) > 1
        assert all(any(w in ln for ln in lines) for w in s.split(" ")), lines

    def test_hyphenated_token_kept_whole(self):
        assert cjk_wrap("COVID-19 vaccination", 40) == ["COVID-19 vaccination"]

    def test_oversized_word_still_hard_splits(self):
        # 單字本身寬過整行是唯一容許逐字元硬切的情況，否則會無限迴圈／溢出
        lines = cjk_wrap("Pneumonoultramicroscopicsilicovolcanoconiosis", 20)
        assert len(lines) > 1
        assert "".join(lines) == "Pneumonoultramicroscopicsilicovolcanoconiosis"


class TestCjkWrapInvariants:
    CASES = [
        ("純英文", "The excess mortality observed in the treatment group was not attributable to cardiovascular causes"),
        ("純中文", "本研究發現放射碘治療與較低的復發性甲狀腺毒症風險相關，且在毒性結節性甲狀腺腫患者中效果一致。"),
        ("中英混排", "COVID-19 患者的 hazard ratio 為 1.9（95% CI 1.2-3.0），統計上具顯著意義"),
        ("空字串", ""),
        ("單一空白", " "),
    ]

    def test_no_line_exceeds_units(self):
        for label, s in self.CASES:
            for units in (8, 20, 40, 76):
                for ln in cjk_wrap(s, units):
                    # 超長單字硬切後每行仍不得超寬
                    assert width(ln) <= units, f"{label} units={units} 超寬：{ln!r}"

    def test_no_characters_lost(self):
        for label, s in self.CASES:
            for units in (8, 20, 40, 76):
                joined = "".join(cjk_wrap(s, units)).replace(" ", "")
                assert joined == s.replace(" ", ""), f"{label} units={units} 掉字"

    def test_leading_space_does_not_emit_empty_line(self):
        # 空白自成 token 後，「cur 只剩空白」會被 flush 成空字串 → 版面多一條空行
        # （2026-08-15 codex review P1：cjk_wrap(" hello", 5) 曾回 ["", "hello"]）
        assert cjk_wrap(" hello", 5) == ["hello"]
        assert "" not in cjk_wrap("  Mortality was not significant", 12)

    def test_leading_space_stripped_even_when_line_fits(self):
        # 首行放得下時前導空白會併進 cur（u=0 恆滿足 u+w<=units），只 rstrip 會留一格縮排
        # （2026-08-15 codex review R3 P3，附 repro：cjk_wrap(" ab cd", 20) 曾回 [" ab cd"]）
        assert cjk_wrap(" ab cd", 20) == ["ab cd"]

    def test_fullwidth_indent_preserved(self):
        # textcard 段落用「　　」全形縮排排版，strip(" ") 只去半形，不可誤傷
        assert cjk_wrap("　　本研究發現放射碘治療有效", 40)[0].startswith("　　")

    def test_always_returns_at_least_one_line(self):
        assert cjk_wrap("", 20) == [""]


class TestTableNoteWrap:
    LONG_NOTE = (
        "Note: all comparisons were adjusted for baseline thyroid function status, age, sex and "
        "comorbidity burden; hazard ratios are reported with 95% confidence intervals throughout."
    )

    def _render(self, tmp_path, note):
        table(str(tmp_path), "01", "Baseline", ["Variable", "Group A"], [["Age", "58"]], note=note)
        svg = next(tmp_path.glob("*.svg")).read_text(encoding="utf-8")
        return re.findall(r"<text[^>]*>(.*?)</text>", svg)

    def test_long_note_is_wrapped(self, tmp_path):
        texts = self._render(tmp_path, self.LONG_NOTE)
        note_lines = [t for t in texts if "adjusted" in t or "confidence" in t]
        assert len(note_lines) >= 2, f"長 note 應該被斷成多行，實得：{note_lines}"

    def test_note_stays_inside_canvas(self, tmp_path):
        # x0=95、字寬約 19*0.52，右緣不得超過表格右界 1185
        texts = self._render(tmp_path, self.LONG_NOTE)
        for t in texts:
            if "adjusted" in t or "confidence" in t:
                assert 95 + width(t) * 19 * 0.52 <= 1185, f"note 橫向出血：{t!r}"

    def test_short_note_still_single_line(self, tmp_path):
        texts = self._render(tmp_path, "Note: n = 120")
        assert "Note: n = 120" in texts
