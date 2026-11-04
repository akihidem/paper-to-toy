"""検査と出力の守りの試験。全体の見直し（2026-11-04）で見つかった穴を、1 つずつ負の場面で押さえる。

なぜ場面（tests/frozen）でなく試験にするか: 前の回の出力が残るか・部品表と部品の対応など、1 回の生成の rc と床の名前だけでは見えない物を見るため。
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
SRC_ID = "NDL-1187053-R0000005-L"


def scenario(d, name, params):
    f = pathlib.Path(d) / f"{name}.json"
    f.write_text(json.dumps({"template": "slider_fan", "source_id": SRC_ID, "params": params, "inject": {}}), encoding="utf-8")
    return f


def gen(sc, out):
    return subprocess.run([PY, "-m", "omochae", "--scenario", str(sc), "--out", str(out)], cwd=ROOT, env=ENV, capture_output=True, text=True)


# 1. 描く前の検査に落ちた時、同じ名前の前の回の紙を残さない
with tempfile.TemporaryDirectory() as d:
    out = pathlib.Path(d) / "x"
    assert gen(scenario(d, "ok", {"push_part": "tab"}), out).returncode == 0
    r = gen(scenario(d, "bad", {"push_part": "tab", "fold_height": 50}), out)
    assert r.returncode == 3 and "F5.fan_height" in r.stderr, r.stderr
    left = sorted(p.name for p in pathlib.Path(d).glob("x.*"))
    assert left == [], f"落ちた後に前の紙が残った: {left}"

# 2. 線の絵が糊代を横切ったら落とす（面積でなく長さで見る）
sys.path.insert(0, str(ROOT / "src"))
from omochae.floors import check_art
from omochae.model import Part

glue = [[(30, 0), (40, 0), (40, 20), (30, 20)]]
over = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(5, 10), (38, 10)], "stroke": "#000", "sw": 0.3}])
clear = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(5, 10), (25, 10)], "stroke": "#000", "sw": 0.3}])
assert [f.floor for f in check_art([over])] == ["F5.image_box"]
assert check_art([clear]) == []

# 3. 型紙に刷る部品は全部、部品表に載る（首の形の重りの腕）
from omochae.floors import check_bom
from omochae.templates import pivot_counterweight as pc, slider_fan as sf

for tpl, forms in ((pc, [{"mount": "neck"}, {"mount": "hang"}]), (sf, [{"push_part": x} for x in ("tab", "tube", "stick")])):
    for form in forms:
        p = {**tpl.DEFAULTS, **form}
        assert check_bom(tpl.bom(p), tpl.parts(p)) == [], (tpl.ID, form)
neck = {**pc.DEFAULTS, "mount": "neck"}
short = [r for r in pc.bom(neck) if r["number"] != 5]
assert [f.floor for f in check_bom(short, pc.parts(neck))] == ["F2.bom"]
assert any("竹串" in m for m in pc.materials(neck)) and any("油粘土" in m for m in pc.materials(neck))

print("ok")
