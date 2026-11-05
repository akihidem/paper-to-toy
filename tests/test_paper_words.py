"""用意する物と部品表の紙の書き方の決まり（omochae.paper_words・本人の指示 2026-11-05「ルールで徹底して」）を確かめる。

紙の行は 4 つの名前（コピー用紙くらい・画用紙くらい・画用紙より厚い・空き箱の厚紙）のどれかで始め、g/m²・mm の厚さ・「見込み」を書かない。
必須 2 種の雛形（slider_fan・pivot_counterweight）は、刷った絵を変えないため今の字のまま外す（元の repo の直しと同じ線）。
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import ways  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from omochae.paper_words import BANNED, BOARD, COPY, DRAWING, NAMES, THICK, paper_name  # noqa: E402

REQUIRED = {"slider_fan", "pivot_counterweight"}  # 必須 2 種の雛形。外すのはここだけ
# 紙の行の見分け: 用意する物か部品表の材料で、紙そのものを名指しする行（紙用の割ピン・紙やすり・紙の玉などは紙の行でない）
PAPER_LINE = re.compile(r"^(紙(?!用|やすり)|厚紙|薄い紙|厚めの紙|空き箱|コピー用紙|画用紙)")

# 1. 名前の選び方: 重さがあれば重さ、無ければ厚さ。4 つの名前の外は返さない
assert paper_name(gsm=80) == COPY and paper_name(gsm=150) == DRAWING and paper_name(gsm=250) == THICK
assert paper_name(thickness=0.09) == COPY and paper_name(thickness=0.15) == DRAWING and paper_name(thickness=0.3) == THICK
assert paper_name(thickness=1.0) == BOARD
assert paper_name(gsm=150, thickness=1.0) == DRAWING  # 重さが勝つ
assert all(BANNED.search(n) is None for n in NAMES)


def lines(tid, p):
    tpl = TEMPLATES[tid]
    return [str(m) for m in tpl.materials(p)] + [str(r.get("material", "")) for r in tpl.bom(p)]


# 2. 全部の雛形の全部の形（必須 2 種を外す）で、紙の行が決まりどおり。芯や厚紙を使う寸法も見る
cases = []
for tid, tpl in sorted(TEMPLATES.items()):
    if tid in REQUIRED:
        continue
    for f in tpl.FORMS:
        p = ways._params(tpl, f)
        cases.append((tid, str(f), p))
        if "wheel_layers" in tpl.DEFAULTS:  # 車輪の芯（空き箱の厚紙）が出る寸法
            cases.append((tid, str(f), {**p, "wheel_layers": 3}))
bad = []
for tid, f, p in cases:
    ls = lines(tid, p)
    for s in ls:
        if PAPER_LINE.match(s) and (not s.startswith(NAMES) or BANNED.search(s)):
            bad.append((tid, f, s[:60]))
        if re.search(r"#[0-9a-fA-F]{6}", s):  # 色の番号が字に混ざらない（名前のぶつかりで色が刷られた事がある）
            bad.append((tid, f, s[:60]))
    assert any(s.startswith(NAMES) for s in ls), (tid, f)  # どの形も、刷る紙を 4 つの名前で言う行を持つ
assert not bad, bad[:10]
assert len({(t, f) for t, f, _ in cases}) == sum(len(t.FORMS) for k, t in TEMPLATES.items() if k not in REQUIRED)

# 3. 外すのは必須 2 種だけ（雛形が足されても、黙って外れない）
assert REQUIRED <= set(TEMPLATES)
print("ok")
