"""作り方の印（omochae.ways・#53）を確かめる。本人の決定 (c): 「紙一枚」(a) と「折るだけ」(b) を別の印で持つ。"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import ways  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from omochae.model import Part  # noqa: E402

# 1. 印は宣言でなく、部品表と部品から出す（宣言だと、部品を変えた時に印と食い違う）
assert ways.marks("slide_box", "lid") == {"one_sheet": True, "fold_only": False, "period": True}
assert ways.marks("whistle", "horn")["one_sheet"] is True
assert ways.marks("pivot_counterweight", "neck")["one_sheet"] is False  # 竹串と粘土が要る
assert ways.marks("spinner", "pinwheel")["one_sheet"] is False
# 2. 折るだけ: 部品が 1 つで、外形が長方形、中の切り込みも穴も無い（切らずに折る）
sheet = Part(1, "sheet", "紙", [(0, 0), (180, 0), (180, 260), (0, 260)], valley=[((90, 0), (90, 260))])
assert ways.fold_only([sheet]) is True
cut = Part(1, "sheet", "紙", [(0, 0), (180, 0), (180, 260), (0, 260)], cuts=[(10, 10, 5, 5)])
assert ways.fold_only([cut]) is False
assert ways.fold_only([sheet, sheet]) is False
notch = Part(1, "sheet", "紙", [(0, 0), (180, 0), (180, 100), (90, 130), (180, 260), (0, 260)])
assert ways.fold_only([notch]) is False
# 3. 一覧: 全部の雛形の全部の形に、2 つの印が付く
table = ways.table()
assert {(r["template"], r["form"]) for r in table} == {(t, str(f)) for t, m in TEMPLATES.items() for f in m.FORMS}
assert all(set(r) >= {"template", "form", "one_sheet", "fold_only", "period", "other_materials", "modern_substitutes"} for r in table)
# 紙一枚の形（main 007599a の時点）。相撲は割ピンを使うので外れる
assert {(r["template"], r["form"]) for r in table if r["one_sheet"]} >= {("popup_jar", "square"), ("popup_jar", "hex"),
                                                                          ("slide_box", "lid"), ("slide_box", "sleeve"), ("whistle", "horn")}
# 5. 当時の材料（再現の良さの別の軸・本人の言葉）: 竹と糸と粘土は当時の材料。割ピンや輪ゴムは今の物で代えた材料
assert ways.marks("pivot_counterweight", "neck")["period"] is True  # 竹串と粘土
sumo = next(r for r in table if r["template"] == "lever_link" and r["form"] == "sumo")
assert sumo["period"] is False and "割ピン" in "".join(sumo["modern_substitutes"]), sumo
assert all(r["period"] for r in table if r["one_sheet"])  # 紙だけなら当時の材料でもある
# 4. 入口: JSON で出す（サイトが絞り込みに使う）
r = subprocess.run([sys.executable, "-m", "omochae.ways", "--json"], cwd=ROOT, capture_output=True, text=True,
                   env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
assert r.returncode == 0 and json.loads(r.stdout) == json.loads(json.dumps(table, ensure_ascii=False)), r.stderr
print("ok")
