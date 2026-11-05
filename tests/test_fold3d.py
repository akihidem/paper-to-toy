"""3D の中で折って組む確かめ（omochae.fold3d）。凍結の基準の 3D.close・3D.skewer の試験（criteria.md の行は、この 1 と 2 を指す）。

本人の決定（2026-11-05）で、御来迎 つまみの形だけを見る。
- 3D.close: 外筒（と、竹串の線の前提になる内筒）を、型紙の折り線で 90° ずつ折ると角筒に閉じ、糊代が 1 面目に重なる
- 3D.face: 見える面の部品（色の境で折る外筒）の色の面（刷った面）が、閉じた筒の外を向く（本人の答え 2026-11-06 で足した）
- 3D.skewer: 折った内筒が外筒に入り、2 つの穴が向かい合い、竹串が静かな時から押し上げ切るまで外筒の溝の中を通る
狙いは式と絵のずれを見つける事なので、刷る部品を 1 か所だけ崩した負の対照で、それぞれ 1 行だけ落ちる事を見る。
"""
import copy
import itertools
import json
import os
import pathlib
import subprocess
import sys
import tempfile

from omochae import fold3d
from omochae.__main__ import load_source
from omochae.compose import compose
from omochae.templates import slider_fan

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
src = load_source(slider_fan.SOURCE)
TAB = {"push_part": "tab"}


def built(params):
    """型紙と同じ検査（compose）を通した部品（key ごと）と、既定を合わせた寸法。"""
    p, layout, failures = compose("slider_fan", params, src)
    assert not failures, [f.line() for f in failures]
    return {q.key: q for q in layout["parts"]}, p


# 1. 正の組。既定の寸法で通り、何を確かめたかを、閉じる（外筒）・外向き（外筒）・閉じる（内筒）・並ぶ（竹串）の順に 1 行ずつ言う。
#    糊代の相手は帯の反対の端の 1 面目
pc, p = built(TAB)
notes, fails = fold3d.check(list(pc.values()), p)
assert not fails, [f.line() for f in fails]
assert [n.split()[:2] for n in notes] == [["閉じる", "1"], ["外向き", "1"], ["閉じる", "2"], ["並ぶ", "竹串:"]], notes
# 外筒は色の面を外にする山折り（見える面）。内筒は破線を刷る谷折りのまま（隠れる部品）
assert "山折り 4 本" in notes[0] and "谷折り 4 本" in notes[2] and all("糊代は1 面目に" in notes[i] for i in (0, 2)), notes

# 寸法を変えても、型紙の検査に通る組は 3D でも通る。通らない組が見つかったら、刷る紙は変えずに知らせる（今は無い）。
# 寸法は互いに縛り合う（押し上げる量・筒の高さ・内筒の長さ・溝の上の余白・扇の台の大きさ）ので、範囲の端の総当たりでは
# 型紙の検査に通る組が既定の近くの 6 組しか無かった。縛りに沿って動かした組で見る（75 組のうち 57 組が型紙の検査に通る）。
SIZES = [(28, 26), (30, 26), (30, 22), (31, 28), (32, 28)]  # (外筒の一辺, 内筒の一辺)
STROKES = [(69, 15, 84), (69, 20, 95), (75, 25, 110), (80, 15, 110), (90, 15, 110)]  # (押し上げる量, 内筒の長さ, 外筒の高さ)
passed = 0
for (side, inner_side), (amount, length, height), knob in itertools.product(SIZES, STROKES, (2, 4, 5)):
    params = {**TAB, "tube_side": side, "pusher_side": inner_side, "base_side": min(26, inner_side),
              "push_amount": amount, "pusher_height": length, "tube_height": height, "knob_width": knob}
    q, layout, failures = compose("slider_fan", params, src)
    if failures:
        continue
    fl = fold3d.check(layout["parts"], q)[1]
    assert not fl, (params, [f.line() for f in fl])
    passed += 1
assert passed >= 40, passed  # 型紙の検査に通る組が少なすぎると、この確かめが空回りする
print("ok 1")

# 2. 負の対照（刷る部品を 1 か所だけ崩す）。それぞれ 1 行だけで落ちる
A, H = p["tube_side"], p["tube_height"]


def tampered(key, fn):
    parts = copy.deepcopy(pc)
    fn(parts[key])
    return list(parts.values())


def lines_of(q):
    """部品の折り線の並び。外筒は山折り（色の面を外にする）、内筒は谷折りなので、線のある方を返す（手伝いが並びを取り違えないように）。"""
    assert bool(q.valley) != bool(q.mountain), (q.key, len(q.valley), len(q.mountain))
    return q.valley or q.mountain


def move_fold(i, dx):
    def fn(q):
        ls = lines_of(q)
        (a, b), (c, d) = ls[i]
        ls[i] = ((a + dx, b), (c + dx, d))
    return fn


def set_fold(i, line):
    def fn(q):
        lines_of(q)[i] = line
    return fn


def add_fold(x, top=0.0, bottom=0.0):
    """縦の折り線を足す。糊代は角を落としてあるので、外形の縁に届く端（上は y = top、下は y = H − bottom）を渡す。"""
    def fn(q):
        q.valley.append(((x, top), (x, H - bottom)))
    return fn


def notch(dx=0.0, down=0.0, narrow=0.0):
    """溝の切り込み（外形のうち 2 面目の中にある 4 点）を、横へ dx、上の端を下へ down、幅を両側から narrow ずつ動かす。"""
    def fn(q):
        x0, x1 = sorted({x for x, _ in q.outline if A < x < 2 * A})

        def mv(pt):
            x, y = pt
            if x not in (x0, x1):
                return pt
            return (x + dx + (narrow if x == x0 else -narrow), y + down if y < H else y)
        q.outline = [mv(pt) for pt in q.outline]
    return fn


def move_hole(i, dx=0.0, dy=0.0):
    def fn(q):
        x, y, r = q.holes[i]
        q.holes[i] = (x + dx, y - dy, r)  # 頁の y は下向きなので、上げるのは引く
    return fn


def widen_first(dx):
    def fn(q):
        q.outline = [(x - dx if x == 0 else x, y) for x, y in q.outline]  # 1 面目の切る縁（x = 0）だけを外へ出す
    return fn


def scale_x(k):
    """部品の横の寸法だけを k 倍にする（外形・折り線・糊代・穴）。絵の筒が式より太くずれた形。"""
    def fn(q):
        q.outline = [(x * k, y) for x, y in q.outline]
        q.valley = [((a * k, b), (c * k, d)) for (a, b), (c, d) in q.valley]
        q.glue = [[(x * k, y) for x, y in g] for g in q.glue]
        q.holes = [(x * k, y, r) for x, y, r in q.holes]
    return fn


def swap_first_points(q):
    q.outline = [q.outline[1], q.outline[0]] + q.outline[2:]  # 外形が自分と交わる


NEG = [
    ("tube", move_fold(1, 300.0), "3D.close", "1 外筒", "届いていない"),  # 折り線が外形の外 → 黙って飛ばさず落とす（4 にしない）
    ("tube", set_fold(1, ((A, 0), (2 * A, 0))), "3D.close", "1 外筒", "分けていない"),  # 外形の縁の上に乗る折り線は面を分けない
    ("tube", set_fold(0, ((A, 0), (A, 0))), "3D.close", "1 外筒", "長さが 0"),  # 長さ 0 の折り線も 4 にしない
    ("tube", set_fold(0, ((A, 0.5), (A, H))), "3D.close", "1 外筒", "届いていない"),  # 縁の 0.5mm 手前で止まる折り線
    ("tube", lambda q: q.mountain.append(q.mountain[0]), "3D.close", "1 外筒", "重なる"),  # 同じ所の 2 本目の折り線
    ("tube", lambda q: q.valley.append(q.mountain[0]), "3D.close", "1 外筒", "重なる"),  # 谷と山を同じ所に重ねる
    ("tube", swap_first_points, "3D.close", "1 外筒", "自分と交わり"),        # 外形が自分と交わる
    # 糊代を余計な折り線で 2 つに分ける（糊代の真ん中では、角を落とした斜めの縁が上下 1mm 内側にある）
    ("tube", add_fold(4 * A + p["tube_glue"] / 2, 1.0, 1.0), "3D.close", "1 外筒", "ちょうど重なって"),
    ("pusher", scale_x(31 / 26), "3D.skewer", "2 内筒", "入らない"),  # 内筒の絵が外筒（一辺 30mm）より太い 31mm
    # 直す前の版（外筒が谷折り）。谷折りは刷った面がへこむ向きなので、色の面が筒の内に入る（本人の答え 2026-11-06 で見つけた食い違い）
    ("tube", lambda q: (q.valley.extend(q.mountain), q.mountain.clear()), "3D.face", "1 外筒", "内を向く"),
    ("tube", move_fold(2, 2.0), "3D.close", "1 外筒", "継ぎ目"),    # 3 本目の折り線を 2mm ずらす → 90° ずつでは閉じない
    ("tube", widen_first(2.0), "3D.close", "1 外筒", "継ぎ目"),     # 1 面目だけ 2mm 広い → 継ぎ目が 1 面目の縁に来ない
    ("tube", lambda q: q.glue.clear(), "3D.close", "1 外筒", "糊代"),  # 糊代の印が無い → 継ぎ目を貼れない
    # 糊代の印が隣の面へ 5mm はみ出す（面の側だけを見ると、糊代の面は全部が糊代なので通った）
    ("tube", lambda q: q.glue.__setitem__(0, [(x - 5 if x == 4 * A else x, y) for x, y in q.glue[0]]), "3D.close", "1 外筒", "ちょうど重なって"),
    ("pusher", move_fold(0, 2.0), "3D.close", "2 内筒", "継ぎ目"),  # 内筒が閉じなければ、竹串の線は見ない（1 行だけ）
    ("tube", notch(dx=3.0), "3D.skewer", "竹串", "溝"),            # 溝を面の真ん中から 3mm ずらす
    ("tube", notch(narrow=1.0), "3D.skewer", "竹串", "溝"),        # 溝を竹串より細くする（幅 5mm → 3mm、竹串 4mm）
    ("tube", notch(down=5.0), "3D.skewer", "竹串", "溝"),          # 溝の上の端を 5mm 下げる → 押し上げ切る前に当たる
    ("pusher", move_hole(1, dy=2.0), "3D.skewer", "竹串", "傾"),   # 片方の穴を 2mm 上げる → 竹串が傾く
    ("pusher", move_hole(1, dx=2.0), "3D.skewer", "竹串", "向かい合って"),  # 片方の穴を 2mm 横へ → 竹串が面へ斜めに交わる
    ("pusher", lambda q: q.holes.__setitem__(1, q.holes[0]), "3D.skewer", "竹串", "同じ所"),  # 2 つの穴が同じ所 → 0 で割らずに落とす
]
for key, fn, floor, where, word in NEG:
    fl = fold3d.check(tampered(key, fn), p)[1]
    assert [(f.floor, f.where) for f in fl] == [(floor, where)] and word in fl[0].message, (floor, where, [f.line() for f in fl])
# 2 つの崩れが別の部品にある時は、それぞれ 1 行ずつ出る。外筒の色の面の向き（外筒は閉じる）は、内筒が閉じなくても捨てない
two = copy.deepcopy(pc)
two["tube"].valley, two["tube"].mountain = two["tube"].mountain, []
move_fold(0, 2.0)(two["pusher"])
fl = fold3d.check(list(two.values()), p)[1]
assert [(f.floor, f.where) for f in fl] == [("3D.close", "2 内筒"), ("3D.face", "1 外筒")], [f.line() for f in fl]
# 崩す前の部品はそのまま通る（上の負の対照が、写し方のせいで落ちたのでない事）
assert not fold3d.check(tampered("tube", lambda q: None), p)[1]
print("ok 2")

# 3. 閉じる確かめは、外形の始めの点（動かさない面）に依らない。糊代の面から始めても、相手は帯の反対の端の面で、継ぎ目が合う
w = 4 * A + p["tube_glue"]
tube = copy.deepcopy(pc["tube"])
k = tube.outline.index((w, 2))
tube.outline = tube.outline[k:] + tube.outline[:k]
note, fail = fold3d._close(tube, fold3d.fold(tube))
assert fail is None and "継ぎ目のずれ 0.00mm・糊代は帯の反対の端の面に 100% 重なる" in note, (note, fail)
# 限り: 隠れる部品（破線を刷る内筒）の谷と山の向きは見ない。内筒を山折りに替えても、鏡に映した形として組めて通る。
# 文は実際の折りの種類を言う（「谷折りすると」と言い切らない）
mirrored = copy.deepcopy(pc)
mirrored["pusher"].mountain, mirrored["pusher"].valley = mirrored["pusher"].valley, []
notes_m, fails_m = fold3d.check(list(mirrored.values()), p)
assert not fails_m and "山折り 4 本" in notes_m[2], (notes_m, [f.line() for f in fails_m])
print("ok 3")


# 4. 入口（python -m omochae.fold3d）の終了の番号: 0 確かめて通った / 3 落ちた / 4 確かめられない
def cli3d(*args, env=ENV):
    return subprocess.run([sys.executable, "-m", "omochae.fold3d", *args], cwd=ROOT, env=env, capture_output=True, text=True)


r = cli3d("--scenario", str(ROOT / "examples/fan_tab.json"))
assert r.returncode == 0 and "並ぶ 竹串:" in r.stdout and not r.stderr, (r.returncode, r.stdout, r.stderr)
r = cli3d("--scenario", str(ROOT / "tests/frozen/scenarios/neg_overlap.json"))
assert r.returncode == 3 and "F5.overlap" in r.stderr, r.stderr
with tempfile.TemporaryDirectory() as d:
    def params_file(name, body):
        f = pathlib.Path(d) / name
        f.write_text(json.dumps(body), encoding="utf-8")
        return str(f)

    r = cli3d("--params", params_file("bad.json", {"push_part": "tab", "fold_height": 50}))
    assert r.returncode == 3 and "F5.fan_height" in r.stderr, r.stderr
    # 形の値の打ち間違いは、まだ組めない形（4）でなく、型紙の検査の範囲の外（3）
    r = cli3d("--params", params_file("typo.json", {"push_part": "tabb"}))
    assert r.returncode == 3 and "F5.range" in r.stderr, r.stderr
    # 最小の 1 本はつまみの形だけ。型紙の検査に通るほかの形・雛形は「まだ組めない」で 4（通ったとは言わない）。
    # 柄の形は押す部品が筒の高さより短いと型紙の検査（F5.stroke）で 3 になるので、通る長さにする
    r = cli3d("--params", params_file("stick.json", {"push_part": "stick", "pusher_height": 84}))
    assert r.returncode == 4 and "まだ 3D で組めない" in r.stderr, r.stderr
    r = cli3d("--template", "pivot_counterweight", "--params", params_file("neck.json", {"mount": "neck"}))
    assert r.returncode == 4 and "まだ 3D で組めない" in r.stderr, r.stderr
    r = cli3d("--template", "nothing", "--params", params_file("tab.json", TAB))
    assert r.returncode == 4 and "知らない雛形" in r.stderr, r.stderr
    # 3D の確かめだけが使う shapely の部分（split）が読めない時も、トレースバックの 1 でなく 4（雛形は split を使わないので、
    # 型紙の読み込みの囲いでなく、fold3d の読み込みの囲いを通る）
    (pathlib.Path(d) / "sitecustomize.py").write_text("import shapely.ops\ndel shapely.ops.split\n", encoding="utf-8")
    r = cli3d("--scenario", str(ROOT / "examples/fan_tab.json"), env={**ENV, "PYTHONPATH": f"{d}{os.pathsep}{ENV['PYTHONPATH']}"})
    assert r.returncode == 4 and "確かめられない" in r.stderr and "split" in r.stderr and "Traceback" not in r.stderr, (r.returncode, r.stderr)
print("ok")
