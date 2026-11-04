"""Origami Simulator への書き出し（omochae.foldsim）。山は赤・谷は青・外形は黒で、線の数が部品と合う。

元の repo の tests/test_foldsim.py を、仮説でなく雛形と寸法から書き出す入口に合わせて写した。
足した事: 検査に落ちる寸法は書き出さず 3、刷る形の寸法が無ければ 4（python -m omochae と同じ入口の決まり）。
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
# --name は模様として読まない（[ab] で頭 a・b の SVG を消さない）
d = tempfile.mkdtemp()
for n in ("a", "b"):
    export("slider_fan", tab, src, d, name=n)
export("slider_fan", {"push_part": "tab", "fold_height": 50}, src, d, name="[ab]")
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
export("pivot_counterweight", {"mount": "hang"}, tsrc, dh)
try:
    export("pivot_counterweight", {"mount": "hang"}, tsrc, dh, parts={"drop"})
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
print("ok")
