"""御来迎の内筒を下から押し上げる形（rise）の外筒と内筒を、3D の中で折って組む確かめ（omochae.fold3d.check_rise）。

本人の決定（2026-11-06）「御来迎 v12 と虎 v5 に、3D の確かめを試験として足す。」による。凍結の基準の床ではなく、
python -m omochae.fold3d の入口（つまみの形だけを組む）も変えない（rise はそこで 4 のまま。tests/test_goraigo_rise.py で見る）。
見る事は check_rise の注のとおり: 2 本の筒が閉じる・外筒の色の面が外・内筒が外筒に入る・静かな時から開いた位置までの行程。
扇が開く所は組まない（受けと蛇腹のばねで開く仕組みで、蝶番ではないので）。面は硬い板で、紙の厚み・たわみ・摩擦は入れない。
"""
import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import fold3d  # noqa: E402
from omochae.__main__ import load_source  # noqa: E402
from omochae.compose import compose  # noqa: E402
from omochae.templates import slider_fan as sf  # noqa: E402

SC = json.loads((ROOT / "examples/goraigo_v12.json").read_text(encoding="utf-8"))
V12 = {**sf.DEFAULTS, **SC["params"]}

# 1. 次の組の見本の寸法で、刷る部品（配置の後の部品）から組むと、全部通る
p, layout, fails = compose("slider_fan", SC["params"], load_source(SC["source_id"]))
assert fails == []
notes, failures = fold3d.check_rise(layout["parts"], p)
assert failures == [], [f.line() for f in failures]
heads = [n.split(":")[0] for n in notes]
assert heads == ["閉じる 1 外筒", "外向き 1 外筒", "閉じる 2 内筒", "入れる 2 内筒", "押し上げる 2 内筒"], heads
assert "10.0mm 出る" in notes[-1] and "口の高さ" in notes[-1], notes[-1]


def floors(parts, **extra):
    return [f.floor for f in fold3d.check_rise(parts, {**V12, **extra})[1]]


def parts(**extra):
    return sf.parts({**V12, **extra})


# 2. 負の対照（1 つの崩れに 1 つの床。前の操作が落ちると、それに頼る後の操作は見ない）
# 外筒を谷折りに戻すと（凡例の谷折りは刷った面がへこむ向き）、閉じるが色の面が内に入る
qs = parts()
outer = next(q for q in qs if q.key == "tube")
outer.valley, outer.mountain = outer.mountain, []
assert floors(qs) == ["3D.face"], floors(qs)
# 内筒の折り線を 1 本抜くと、閉じない（入れる・押し上げるは見ない）
qs = parts()
inner = next(q for q in qs if q.key == "pusher")
inner.valley = inner.valley[:-1]
assert floors(qs) == ["3D.close"], floors(qs)
# 内筒が外筒より大きいと、外筒に入らない（式の床 F5.slide_clearance と同じ事を、折った形の断面で見る）
assert floors(parts(pusher_side=27)) == ["3D.fit"]
assert floors(parts(pusher_side=26)) == ["3D.fit"]  # 一辺が同じ時は、すき間が 0 で入らない（紙の厚みを入れなくても落ちる）
assert floors(parts(pusher_side=25.5)) == []         # すき間 0.5 なら入る（紙の厚みの分の余りは式の床 F5.slide_clearance が見る）
# 行程: 押し上げる量が足りないと、静かな時に扇が口から出る（押し上げる量 28: 台の上の面 74＋扇 28.75 が口 102 を超える）
assert floors(parts(), push_amount=28) == ["3D.stroke"]
# 静かな時の差し込みが内筒の一辺より短い（押し上げる量 81: 差し込み 21 が一辺 22 より短い）
assert floors(parts(push_amount=81), push_amount=81) == ["3D.stroke"]
# 内筒が外筒＋10 に足りないと、開いた位置で内筒の下の端が外筒の下へ 10mm 出ない
assert floors(parts(pusher_height=111)) == ["3D.stroke"]

# 3. 型紙の部品を写しても、元の部品は変えない（試験の負の対照が、ほかの試験の部品に漏れない事の確かめ）
qs = parts()
before = copy.deepcopy([(q.key, q.valley, q.mountain) for q in qs])
fold3d.check_rise(qs, V12)
assert [(q.key, q.valley, q.mountain) for q in qs] == before
print("ok 御来迎の内筒を下から押し上げる形（rise）の 3D の確かめ")
