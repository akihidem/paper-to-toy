"""改善の輪（omochae.engine_loop）の札の言葉を、出す所で 1 行にして記号を無効にする事を確かめる（セキュリティの点検 2026-11-07）。
札の言葉（動きの札の結果の名・動かない側の札）は束から来る字で、長さと連絡先の形しか見ていない。そのまま出すと、
Issue の下書きの「なぜか」に改行で見出しを足せ、版ごとの数の表の列を | で崩せ、HTML の形や制御の文字（見えない文字）も生で入った。
作った人の文と同じく、1 行にして Markdown の記号・HTML の形・制御の文字を無効にする。
雛形の札（「動いた」「回らない」など）と受け入れた報告の札では、出る字が今までと同じ事も見る。"""
import copy
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import engine_loop as el  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from omochae.intake import MOVED_JA  # noqa: E402

SAMPLE = json.loads((ROOT / "examples/bundles/sample_made_up.json").read_text(encoding="utf-8"))
tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local")
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")
os.environ["OMOCHAE_REPORTS"] = str(tmp / "no-reports")
NO_LEDGER = {"versions": [], "next": []}
# 見えない文字と制御の文字は、ファイルに生で置かない（chr で作る）
ESC, RLO, LS = chr(0x1B), chr(0x202E), chr(0x2028)
COLUMNS = 9  # 版ごとの数の表の列の数


def with_label(word, moved="動いた"):
    """群 0 の動きの札を、word（動かない側）と moved（動いた側）にした束。"""
    b = copy.deepcopy(SAMPLE)
    g = b["groups"][0]
    g.update(results={moved: 1, word: 2}, moved_word=moved, not_moved_word=word)
    return b


def why_of(b):
    """その束から起きる、動きの床の案の Issue の下書きの「なぜか」の節。"""
    d = {x["key"]: x for x in el.drafts(el.groups([b]))}["motion:slider_fan:goraigo-v10"]
    doc = el.issue_draft({**d, "id": "EP-0000", "status": "draft"})
    return doc.split("## なぜか（根拠）\n")[1].split("\n## ")[0]


def row_of(b):
    """その束の版ごとの数の表の、群 0（goraigo-v10）の行。"""
    out = el.compare(el.groups([b]), NO_LEDGER)
    rows = [ln for ln in out.splitlines() if ln.startswith("| goraigo-v10")]
    assert len(rows) == 1, out
    return rows[0], out


# 1. 改行・表の区切り・HTML の形・Markdown の記号・制御の文字・見えない文字を持つ札。どれも束の入口（長さと連絡先の形）は通る
WEIRD = ("動か\n## 足した見出し", "動か|ない|x", "<img src=x>", "動か" + ESC + "[31mない", "動か" + RLO + "ない", "**太字**", "[a](b)",
         "動か" + LS + "ない", "動か\r\n- 項目")
for word in WEIRD:
    b = with_label(word)
    assert el.check_bundle(b) == [], (word, [f.line() for f in el.check_bundle(b)])
    why = why_of(b)
    # 「なぜか」の節は、前と同じ 2 行（根拠の文と、案の番号と数）。札の改行で行や見出しが増えない
    lines = why.strip("\n").split("\n")
    assert len(lines) == 2 and lines[0].startswith("- ") and lines[1].startswith("- 案の番号"), (word, why)
    assert "\n## 足した見出し" not in why and "\n- 項目" not in why
    for raw in ("<img", ESC, RLO, LS, "\r"):
        assert raw not in why, (word, raw)
    assert not re.search(r"(?<!\\)[|*\[\]]", lines[0]), (word, lines[0])  # 記号は \ で無効にしてある
    # 版ごとの数の表: 群の行は 1 行のままで、列を区切る | の数が変わらない（札の | は \| になる）
    row, out = row_of(b)
    assert len(re.findall(r"(?<!\\)\|", row)) == COLUMNS + 1, (word, row)
    for raw in ("<img", ESC, RLO, LS, "\r"):
        assert raw not in out, (word, raw)
    assert "\n## 足した見出し" not in out and "\n- 項目" not in out
# 動いた側の札も、表では同じ扱い（動いた側の札の字は「なぜか」には出ない）
row, _ = row_of(with_label("動かない", moved="動い|た"))
assert len(re.findall(r"(?<!\\)\|", row)) == COLUMNS + 1 and "動い\\|た 1" in row, row
# CLI の並べ（本物の process）でも同じ
(tmp / "b.json").write_text(json.dumps(with_label("動か\n|ない"), ensure_ascii=False), encoding="utf-8")
env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
run = lambda *a: subprocess.run([sys.executable, "-m", "omochae.engine_loop", *a], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
assert run("take", str(tmp / "b.json")).returncode == 0
r = run("compare")
rows = [ln for ln in r.stdout.splitlines() if ln.startswith("| goraigo-v10")]
assert r.returncode == 0 and len(rows) == 1 and len(re.findall(r"(?<!\\)\|", rows[0])) == COLUMNS + 1, r.stdout
motion = next(p for p in el.proposals() if p["key"] == "motion:slider_fan:goraigo-v10")
r = run("show", motion["id"])
assert r.returncode == 0 and "「動か \\|ない」の札が 2 件" in r.stdout, r.stdout

# 2. ふだんの札は、出る字が今までと同じ: 雛形の札の全部と、受け入れた報告の札（intake の MOVED_JA）
words = set(MOVED_JA.values())
for tpl in TEMPLATES.values():
    words |= set(getattr(tpl, "RESULTS", ()))
assert {"動いた", "動かない", "回らない", "わからない", "少し動いた"} <= words and len(words) >= 20, sorted(words)
for word in sorted(words):
    moved = "揺れた" if word == "動いた" else "動いた"  # 動いた側と同じ札にしない（札の数の辞書で 1 つになる）
    b = with_label(word, moved)
    assert f"は検査を通って刷られた紙で、「{word}」の札が 2 件（報告 5 件）。" in why_of(b), word
    row, _ = row_of(b)
    assert f"| {moved} 1・{word} 2 |" in row, (word, row)
# 見本の束の行と「なぜか」は、前の字のまま（tests/test_engine_loop.py の 8 と同じ行。見本だけなので v10 が今の組）
row, _ = row_of(SAMPLE)
assert row == "| goraigo-v10（今の組） | — | — | 5 件 | 動いた 2・動かない 2・わからない 1 | 手順 3: 4 回・2 人、手順 5: 1 回・1 人 | 手順 3: 1 | 20〜40（3 件） | 考え 1・工夫 5・できた後 1・レビュー 1 |", row
assert "slider_fan（刷った組 goraigo-v10）は検査を通って刷られた紙で、「動かない」の札が 2 件（報告 5 件）。" in why_of(SAMPLE)

print("OK test_engine_loop_labels")
