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
    # 検査できない（exit 4）だけの時は、前の回の紙を消さない
    assert gen(scenario(d, "ok", {"push_part": "tab"}), out).returncode == 0
    broken = pathlib.Path(d) / "broken.json"
    broken.write_text(json.dumps({"template": "no_such", "source_id": SRC_ID, "params": {}, "inject": {}}), encoding="utf-8")
    assert gen(broken, out).returncode == 4
    left = sorted(p.name for p in pathlib.Path(d).glob("x.*"))
    assert left == ["x.pdf", "x.png", "x.svg"], f"検査できない時に前の紙が消えた: {left}"
    # 描いた後（PNG にする所）で検査できなくなっても、前の回の紙はそのまま、仮の名前の物も残さない
    import shutil
    before = {p.name: p.read_bytes() for p in pathlib.Path(d).glob("x.*")}
    fake = pathlib.Path(d) / "bin"
    fake.mkdir()
    (fake / "pdftoppm").write_text("#!/bin/sh\nexit 1\n")
    (fake / "pdftoppm").chmod(0o755)
    r = subprocess.run([PY, "-m", "omochae", "--scenario", str(scenario(d, "stick", {"push_part": "stick", "pusher_height": 84})), "--out", str(out)],
                       cwd=ROOT, env={**ENV, "PATH": f"{fake}:{os.environ['PATH']}"}, capture_output=True, text=True)
    assert r.returncode == 4, r.stderr
    after = {p.name: p.read_bytes() for p in pathlib.Path(d).glob("x*")}
    assert after == before, f"検査できない時に紙が変わった・増えた: {sorted(after)}"

# 1b. 仮の置き場は毎回別の名前。点のある --out でも揃い、たまたま同じ名前の別の出力（x-partial）を壊さない
with tempfile.TemporaryDirectory() as d:
    assert gen(scenario(d, "ok", {"push_part": "tab"}), pathlib.Path(d) / "x.v1").returncode == 0
    assert {"x.svg", "x.pdf", "x.png"} <= {p.name for p in pathlib.Path(d).iterdir()}
    assert gen(scenario(d, "ok", {"push_part": "tab"}), pathlib.Path(d) / "y-partial").returncode == 0
    keep = {p.name: p.read_bytes() for p in pathlib.Path(d).glob("y-partial.*")}
    assert gen(scenario(d, "stick", {"push_part": "stick", "pusher_height": 84}), pathlib.Path(d) / "y").returncode == 0
    assert {p.name: p.read_bytes() for p in pathlib.Path(d).glob("y-partial.*")} == keep
    assert not [p for p in pathlib.Path(d).iterdir() if p.name.startswith(".omochae-")], "仮の置き場が残った"

# 2. 線の絵が糊代を横切ったら落とす（面積でなく長さで見る）
sys.path.insert(0, str(ROOT / "src"))
from omochae.floors import check_art
from omochae.model import Part

glue = [[(30, 0), (40, 0), (40, 20), (30, 20)]]
over = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(5, 10), (38, 10)], "stroke": "#000", "sw": 0.3}])
clear = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(5, 10), (25, 10)], "stroke": "#000", "sw": 0.3}])
assert [f.floor for f in check_art([over])] == ["F5.image_box"]
assert check_art([clear]) == []
# 中心線は糊代の手前でも、刷られる太さで糊代にかかれば落とす
thick = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(29.5, 2), (29.5, 18)], "stroke": "#000", "sw": 2.0}])
thin = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(29.5, 2), (29.5, 18)], "stroke": "#000", "sw": 0.3}])
assert [f.floor for f in check_art([thick])] == ["F5.image_box"]
assert check_art([thin]) == []
# 輪郭線つきの面は、線の太さで糊代にかかれば落とす
framed = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue,
              art=[{"kind": "poly", "pts": [(5, 5), (29.5, 5), (29.5, 15), (5, 15)], "fill": "#ccc", "stroke": "#000", "sw": 2.0}])
assert [f.floor for f in check_art([framed])] == ["F5.image_box"]
# 折れ曲がる線は、SVG と同じく尖った角の先まで見る（丸い角で見ると角の先が糊代にかかるのを見逃す）
bent = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(10, 4), (28.0, 10), (10, 16)], "stroke": "#000", "sw": 1.5}])
assert [f.floor for f in check_art([bent])] == ["F5.image_box"]

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
other = [dict(r, key="other", name="別の物") if r["number"] == 5 else r for r in pc.bom(neck)]
assert [f.floor for f in check_bom(other, pc.parts(neck))] == ["F2.bom"]
twice = pc.bom(neck) + [dict(pc.bom(neck)[0])]
assert [f.floor for f in check_bom(twice, pc.parts(neck))] == ["F2.bom"]

# 4. 刷った後の印の検査は、所蔵・改変の注記・仮説の文をそのまま探す
from omochae.marks import check_pdf

source = json.loads((ROOT / "data/sources" / f"{SRC_ID}.json").read_text(encoding="utf-8"))
with tempfile.TemporaryDirectory() as d:
    out = pathlib.Path(d) / "m"
    assert gen(scenario(d, "ok", {"push_part": "tab"}), out).returncode == 0
    pdf = out.with_suffix(".pdf")
    assert check_pdf(pdf, source) == []
    other = {**source, "holding": source["holding"] + "（別の文）", "modification_note": "改変: 別の注記"}
    assert sorted(f.where for f in check_pdf(pdf, other)) == ["所蔵の文", "改変"]

# 5. 開く糸の長さは、筒の穴（口から THREAD_DEPTH 下）から測る
from omochae.fan_model import shortest_free_thread

p = {**sf.DEFAULTS, "push_part": "tab", "tube_side": 26, "pusher_side": 22, "base_side": 22, "pivot_above_rim": 2, "push_amount": 69, "fold_height": 38, "fold_count": 10}
tube = next(q for q in sf.parts(p) if q.key == "tube")
depth = tube.holes[0][1]
assert depth == sf.THREAD_DEPTH
z0 = p["pivot_above_rim"] + depth
assert abs(sf.thread_mm(p) - shortest_free_thread(p["tube_side"], sf.THREAD_RADIUS, z0 - p["push_amount"], z0)) < 1e-9
assert abs(sf.thread_mm(p) - 30.3) < 0.1, sf.thread_mm(p)

# 6. 色の境で折る扇でも、足の糊代の境の谷折り線だけは刷る（組み方の文が「糊代の境の破線で折り」と言うため）
import re
from omochae.compose import compose
from omochae.render import to_svg

for form in ({"push_part": "tab"}, {"push_part": "stick", "pusher_height": 84}):
    _, layout, failures = compose("slider_fan", form, source)
    assert not failures
    fan = next(q for q in layout["parts"] if q.key == "fan")
    assert len(fan.print_folds) == 1 and fan.print_folds[0][0][0] < 0, fan.print_folds
    dashed = re.findall(r'<path d="M([-\d.]+),([-\d.]+) L([-\d.]+),([-\d.]+)" [^>]*stroke-dasharray="2,1"', to_svg(layout))
    on_fan = [d for d in dashed if fan.x - 30 < float(d[0]) < fan.x + fan.width and fan.y <= float(d[1]) <= fan.y + fan.height]
    (x1, y1), (x2, y2) = fan.print_folds[0]
    assert [tuple(float(v) for v in d) for d in on_fan] == [(fan.x + x1, fan.y + y1, fan.x + x2, fan.y + y2)], on_fan
# 口の台の形は足が無いので、刷る折り線も無い
_, layout, _ = compose("slider_fan", {"hub": "rim", "push_amount": 36, "pusher_height": 40, "fold_count": 14, "fold_width": 8, "fold_height": 36}, source)
assert next(q for q in layout["parts"] if q.key == "fan").print_folds == []

print("ok")
