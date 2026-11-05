"""Origami Simulator への書き出し（omochae.foldsim）。山は赤・谷は青・外形は黒で、線の数が部品と合う。

元の repo の tests/test_foldsim.py を、仮説でなく雛形と寸法から書き出す入口に合わせて写した。
足した事: 検査に落ちる寸法は書き出さず 3、刷る形の寸法が無ければ 4（python -m omochae と同じ入口の決まり）。
5 の節は、3D の中で折って組む確かめ（omochae.fold3d）。同じ「折る」の試験なのでここに置く（試験のファイルを増やすと凍結の照合の表が変わる）。
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

from omochae.__main__ import load_source
from omochae.foldsim import export
from omochae.templates import pivot_counterweight, slider_fan

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}


def check(out, tpl, params, head):
    """書いた SVG の線の数が、部品の外形・山折り・谷折りの数と合う事を見る。"""
    by_key = {q.key: q for q in tpl.parts({**tpl.DEFAULTS, **params})}
    for f in out:
        key = f.name[len(head) + 1:-len("_foldsim.svg")]
        q, svg = by_key[key], f.read_text(encoding="utf-8")
        assert svg.count("#ff0000") == len(q.mountain) and svg.count("#0000ff") == len(q.valley), key
        # 黒は外形の辺と、中を切り抜く穴の矩形の 4 辺（Origami Simulator は黒を外形と中の穴と読む）
        assert svg.count("#000000") == len(q.outline) + 4 * len(q.cuts), key
    return sorted(f.name for f in out)


# 1. 御来迎（つまみの形）。色の境で折る外筒と扇（hide_folds）も、折り線のデータで書き出す
tab = {"push_part": "tab"}
out, failures = export("slider_fan", tab, load_source(slider_fan.SOURCE), tempfile.mkdtemp())
assert not failures
assert check(out, slider_fan, tab, "slider_fan") == ["slider_fan_base_foldsim.svg", "slider_fan_fan_foldsim.svg", "slider_fan_pusher_foldsim.svg", "slider_fan_tube_foldsim.svg"]

# 2. 虎（首の形）と、名前の頭・部品の選び
neck = {"mount": "neck"}
out, failures = export("pivot_counterweight", neck, load_source(pivot_counterweight.SOURCE), tempfile.mkdtemp(), name="tiger")
assert not failures
assert check(out, pivot_counterweight, neck, "tiger") == ["tiger_body_foldsim.svg", "tiger_strip_foldsim.svg"]
out, _ = export("slider_fan", tab, load_source(slider_fan.SOURCE), tempfile.mkdtemp(), parts={"fan"})
assert [f.name for f in out] == ["slider_fan_fan_foldsim.svg"]

# 虎の首の形の胴は、前の壁の穴（cuts）を黒で書く
assert pivot_counterweight.parts({**pivot_counterweight.DEFAULTS, **neck})[0].cuts

# 3. 検査に落ちる寸法は書き出さず、前の回の同じ頭の SVG も残さない。部品を減らした回は、減らした分だけになる
d = tempfile.mkdtemp()
src = load_source(slider_fan.SOURCE)
assert len(export("slider_fan", tab, src, d)[0]) == 4
out, failures = export("slider_fan", {"push_part": "tab", "fold_height": 50}, src, d)
assert out == [] and [f.floor for f in failures] == ["F5.fan_height"] and not any(pathlib.Path(d).iterdir())
export("slider_fan", tab, src, d)
assert [f.name for f in export("slider_fan", tab, src, d, parts={"fan"})[0]] == ["slider_fan_fan_foldsim.svg"]
assert sorted(p.name for p in pathlib.Path(d).iterdir()) == ["slider_fan_fan_foldsim.svg"]
# 場面の inject も検査に渡す（python -m omochae と同じ判定）
_, failures = export("slider_fan", {}, src, tempfile.mkdtemp(), inject={"move_part": {"name": "base", "x": 10, "y": 60}})
assert "F5.overlap" in [f.floor for f in failures]
# 前の回の SVG を名前で選ぶので、部品の key は英小文字だけにしておく
import re
from omochae.compose import TEMPLATES
for tpl in TEMPLATES.values():
    for form in tpl.FORMS:
        assert all(re.fullmatch(r"[a-z]+", q.key) for q in tpl.parts({**tpl.DEFAULTS, tpl.FORM: form})), (tpl.ID, form)
# 模様に読める --name は断り、頭 a・b の SVG を消さない（形の検査は tests/test_path_confine.py。ここは消さない事を見る）
from omochae.model import ToolMissing
d = tempfile.mkdtemp()
for n in ("a", "b"):
    export("slider_fan", tab, src, d, name=n)
try:
    export("slider_fan", {"push_part": "tab", "fold_height": 50}, src, d, name="[ab]")
    raise AssertionError("模様に読める名前を通した")
except ToolMissing:
    assert len(list(pathlib.Path(d).iterdir())) == 8
# 寸法が落ちる時も、知らない部品の key を先に落とし、前の SVG を消さない
try:
    export("slider_fan", {"push_part": "tab", "fold_height": 50}, src, d, name="a", parts={"fna"})
    raise AssertionError("知らない部品を通した")
except ValueError:
    assert len(list(pathlib.Path(d).iterdir())) == 8
# 部品が作れない寸法（型の違う値）と知らない部品の key を一緒に渡しても、key を先に落とし、前の SVG を消さない
try:
    export("slider_fan", {"push_part": "tab", "fold_count": "many"}, src, d, name="a", parts={"fna"})
    raise AssertionError("知らない部品を通した")
except ValueError:
    assert len(list(pathlib.Path(d).iterdir())) == 8
# 雛形の部品でも今の形に無い物（吊る形の drop）は落とし、前の SVG を消さない
dh = tempfile.mkdtemp()
tsrc = load_source(pivot_counterweight.SOURCE)
export("pivot_counterweight", {"mount": "hang", "axle_height": 50}, tsrc, dh)
try:
    export("pivot_counterweight", {"mount": "hang", "axle_height": 50}, tsrc, dh, parts={"drop"})
    raise AssertionError("今の形に無い部品を通した")
except ValueError as e:
    assert "この形に無い部品: drop" in str(e) and len(list(pathlib.Path(dh).iterdir())) == 2
# 知らない部品の key は落とす
try:
    export("slider_fan", tab, src, tempfile.mkdtemp(), parts={"fan", "fna"})
    raise AssertionError("知らない部品を通した")
except ValueError as e:
    assert "fna" in str(e)

# 4. 入口（python -m omochae.foldsim）の終了の番号: 0 書き出した / 3 検査に落ちた / 4 書き出せない
with tempfile.TemporaryDirectory() as d:
    def cli(*args):
        return subprocess.run([sys.executable, "-m", "omochae.foldsim", *args, "--out", str(pathlib.Path(d) / "fs")], cwd=d, env=ENV, capture_output=True, text=True)

    assert cli("--scenario", str(ROOT / "examples/tiger_hang.json")).returncode == 0
    bad = pathlib.Path(d) / "bad.json"
    bad.write_text(json.dumps({"push_part": "tab", "fold_height": 50}), encoding="utf-8")
    r = cli("--params", str(bad))
    assert r.returncode == 3 and "F5.fan_height" in r.stderr, r.stderr
    noform = pathlib.Path(d) / "noform.json"
    noform.write_text(json.dumps({"axle_height": 50}), encoding="utf-8")
    r = cli("--template", "pivot_counterweight", "--params", str(noform))
    assert r.returncode == 4 and "mount が要る" in r.stderr, r.stderr
    r = cli("--scenario", str(ROOT / "examples/fan_tab.json"), "--parts", "nothing")
    assert r.returncode == 4 and "知らない部品" in r.stderr, r.stderr
    r = cli("--scenario", str(ROOT / "examples/fan_tab.json"), "--parts", "figure")
    assert r.returncode == 4 and "折りのある部品が無い" in r.stderr, r.stderr
    r = cli("--scenario", str(ROOT / "tests/frozen/scenarios/neg_overlap.json"))
    assert r.returncode == 3 and "F5.overlap" in r.stderr, r.stderr

# 5. 3D の中で折って組む（omochae.fold3d）。本人の決定で、提出の前は御来迎 つまみの形の 2 つだけを見る。
#    3D.close: 外筒（と、竹串の線の前提になる内筒）を、型紙の折り線で 90° ずつ谷折りすると角筒に閉じ、糊代が 1 面目に重なる
#    3D.skewer: 内筒の 2 つの穴を通す竹串が水平で、静かな時から押し上げ切るまで、外筒の溝の中を通る
#    狙いは式と絵のずれを見つける事なので、刷る部品を 1 か所だけ崩した負の対照で、それぞれ 1 行だけ落ちる事も見る。
import copy
import itertools

from omochae import fold3d
from omochae.compose import compose

TAB = {"push_part": "tab"}


def built(params):
    """型紙と同じ検査（compose）を通した部品（key ごと）と、既定を合わせた寸法。"""
    p, layout, failures = compose("slider_fan", params, src)
    assert not failures, [f.line() for f in failures]
    return {q.key: q for q in layout["parts"]}, p


pc, p = built(TAB)
notes, fails = fold3d.check(list(pc.values()), p)
assert not fails, [f.line() for f in fails]
# 何を確かめたかを、閉じる（外筒・内筒）・並ぶ（竹串）の順に 1 行ずつ言う。糊代の相手は帯の反対の端の 1 面目
assert [n.split()[:2] for n in notes] == [["閉じる", "1"], ["閉じる", "2"], ["並ぶ", "竹串:"]], notes
assert all("糊代は1 面目に" in n for n in notes[:2]), notes

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

A, H = p["tube_side"], p["tube_height"]


def tampered(key, fn):
    parts = copy.deepcopy(pc)
    fn(parts[key])
    return list(parts.values())


def move_fold(i, dx):
    def fn(q):
        (a, b), (c, d) = q.valley[i]
        q.valley[i] = ((a + dx, b), (c + dx, d))
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


def raise_hole(i, dy):
    def fn(q):
        x, y, r = q.holes[i]
        q.holes[i] = (x, y - dy, r)  # 頁の y は下向きなので、上げるのは引く
    return fn


def shift_hole(i, dx):
    def fn(q):
        x, y, r = q.holes[i]
        q.holes[i] = (x + dx, y, r)  # 同じ面の中で横へずらす（高さはそろったまま）
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


def set_fold(i, line):
    def fn(q):
        q.valley[i] = line
    return fn


def add_fold(x):
    def fn(q):
        q.valley.append(((x, 0), (x, H)))
    return fn


def swap_first_points(q):
    q.outline = [q.outline[1], q.outline[0]] + q.outline[2:]  # 外形が自分と交わる


NEG = [
    ("tube", move_fold(1, 300.0), "3D.close", "1 外筒", "分けていない"),  # 折り線が外形の外 → 黙って飛ばさず落とす（4 にしない）
    ("tube", set_fold(0, ((A, 0), (A, 0))), "3D.close", "1 外筒", "長さが 0"),  # 長さ 0 の折り線も 4 にしない
    ("tube", swap_first_points, "3D.close", "1 外筒", "自分と交わり"),        # 外形が自分と交わる
    ("tube", add_fold(4 * A + p["tube_glue"] / 2), "3D.close", "1 外筒", "1 面になっておらず"),  # 糊代を余計な折り線で 2 つに分ける
    ("pusher", scale_x(31 / 26), "3D.skewer", "2 内筒", "入らない"),  # 内筒の絵が外筒（一辺 30mm）より太い 31mm
    ("tube", move_fold(2, 2.0), "3D.close", "1 外筒", "継ぎ目"),    # 3 本目の折り線を 2mm ずらす → 90° ずつでは閉じない
    ("tube", widen_first(2.0), "3D.close", "1 外筒", "継ぎ目"),     # 1 面目だけ 2mm 広い → 継ぎ目が 1 面目の縁に来ない
    ("tube", lambda q: q.glue.clear(), "3D.close", "1 外筒", "糊代"),  # 糊代の印が無い → 継ぎ目を貼れない
    ("pusher", move_fold(0, 2.0), "3D.close", "2 内筒", "継ぎ目"),  # 内筒が閉じなければ、竹串の線は見ない（1 行だけ）
    ("tube", notch(dx=3.0), "3D.skewer", "竹串", "溝"),            # 溝を面の真ん中から 3mm ずらす
    ("tube", notch(narrow=1.0), "3D.skewer", "竹串", "溝"),        # 溝を竹串より細くする（幅 5mm → 3mm、竹串 4mm）
    ("tube", notch(down=5.0), "3D.skewer", "竹串", "溝"),          # 溝の上の端を 5mm 下げる → 押し上げ切る前に当たる
    ("pusher", raise_hole(1, 2.0), "3D.skewer", "竹串", "傾"),     # 片方の穴を 2mm 上げる → 竹串が傾く
    ("pusher", shift_hole(1, 2.0), "3D.skewer", "竹串", "向かい合って"),  # 片方の穴を 2mm 横へ → 竹串が面へ斜めに交わる
]
for key, fn, floor, where, word in NEG:
    fl = fold3d.check(tampered(key, fn), p)[1]
    assert [(f.floor, f.where) for f in fl] == [(floor, where)] and word in fl[0].message, (floor, where, [f.line() for f in fl])
# 崩す前の部品はそのまま通る（上の負の対照が、写し方のせいで落ちたのでない事）
assert not fold3d.check(tampered("tube", lambda q: None), p)[1]
# 閉じる確かめは、外形の始めの点（動かさない面）に依らない。糊代の面から始めても、相手は帯の反対の端の面で、継ぎ目が合う
w = 4 * A + p["tube_glue"]
tube = copy.deepcopy(pc["tube"])
k = tube.outline.index((w, 2))
tube.outline = tube.outline[k:] + tube.outline[:k]
note, fail = fold3d._close(tube, fold3d.fold(tube))
assert fail is None and "継ぎ目のずれ 0.00mm・糊代は帯の反対の端の面に 100% 重なる" in note, (note, fail)


# 入口（python -m omochae.fold3d）の終了の番号: 0 確かめて通った / 3 落ちた / 4 確かめられない
def cli3d(*args):
    return subprocess.run([sys.executable, "-m", "omochae.fold3d", *args], cwd=ROOT, env=ENV, capture_output=True, text=True)


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
    env = {**ENV, "PYTHONPATH": f"{d}{os.pathsep}{ENV['PYTHONPATH']}"}
    r = subprocess.run([sys.executable, "-m", "omochae.fold3d", "--scenario", str(ROOT / "examples/fan_tab.json")],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 4 and "確かめられない" in r.stderr and "split" in r.stderr and "Traceback" not in r.stderr, (r.returncode, r.stderr)
print("ok")
