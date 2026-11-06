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
# 2. 折るだけ: 部品が 1 つで、外形が長方形、中の切り込みも穴も糊代も無く、折り線が 1 本以上ある（切らずに折る）。
# 落ちる例にはどれも折り線を持たせて、落ちる理由を 1 つにする
RECT, FOLD = [(0, 0), (180, 0), (180, 260), (0, 260)], ((90, 0), (90, 260))
sheet = Part(1, "sheet", "紙", RECT, valley=[FOLD])
assert ways.fold_only([sheet]) is True
assert ways.fold_only([Part(1, "sheet", "紙", RECT, mountain=[FOLD])]) is True  # 山折りだけでも折り線がある
assert ways.fold_only([Part(1, "sheet", "紙", RECT, valley=[FOLD], cuts=[(10, 10, 5, 5)])]) is False
assert ways.fold_only([Part(1, "sheet", "紙", RECT, valley=[FOLD], holes=[(10, 10, 1)])]) is False
assert ways.fold_only([Part(1, "sheet", "紙", RECT, valley=[FOLD], round_cuts=[(10, 10, 5)])]) is False  # 丸い切り抜きも切る所
assert ways.fold_only([Part(1, "sheet", "紙", RECT, valley=[FOLD], glue=[[(0, 0), (10, 0), (10, 260), (0, 260)]])]) is False  # 糊代付きの長方形
assert ways.fold_only([Part(1, "sheet", "紙", RECT)]) is False  # 折り線の無い長方形
assert ways.fold_only([sheet, sheet]) is False
notch = Part(1, "sheet", "紙", [(0, 0), (180, 0), (180, 100), (90, 130), (180, 260), (0, 260)], valley=[FOLD])
assert ways.fold_only([notch]) is False
# 3. 一覧: 全部の雛形の全部の形に、2 つの印が付く
table = ways.table()
assert {(r["template"], r["form"]) for r in table} == {(t, str(f)) for t, m in TEMPLATES.items() for f in m.FORMS}
assert all(set(r) >= {"template", "form", "one_sheet", "fold_only", "period", "other_materials", "modern_substitutes"} for r in table)
# 紙一枚の形（main 007599a の時点）。相撲は割ピンを使うので外れる
assert {(r["template"], r["form"]) for r in table if r["one_sheet"]} >= {("popup_jar", "square"), ("popup_jar", "hex"),
                                                                          ("slide_box", "lid"), ("slide_box", "sleeve"), ("whistle", "horn")}
# 5. 当時の材料（再現の良さの別の軸・本人の言葉）: 紙のほかの材料が全部、当時あった物の語の一覧に当たる時だけ。
# 知らない物にも今の物にも付けない。油粘土は江戸の頃に無かったので、当時の材料に数えない（akihidem/utsushi#311）
assert ways.marks("pivot_counterweight", "neck")["period"] is False and "油粘土" in ways.details("pivot_counterweight", "neck")["modern_substitutes"]
assert ways.marks("whistle", "horn")["period"] is True  # 紙だけ
# 語と素材の 2 つの表は、サイト（akihidem/utsushi の tests/test_ways.py）にも同じ物を置く。片方を変える時は両方を変える
WORD_PERIOD = (("竹串", True), ("竹ひご", True), ("楊枝", True), ("つまようじ", True), ("割り箸", True), ("木綿の糸", True), ("たこ糸", True), ("細い紐", True), ("鈴", True), ("玉", True),
               ("油粘土", False), ("粘土", False), ("セロハンテープ", False), ("ビーズ", False), ("輪ゴム", False), ("割ピン", False), ("厚紙", False), ("ストロー", False))
MATERIAL_PERIOD = (("竹串（長さ 180mm）", True, []), ("木綿の糸（200mm）", True, []), ("竹串 1 本とテープ", False, ["テープ"]), ("油粘土 3g", False, ["油粘土"]),
                   ("油粘土の玉（直径 8mm）かビーズ", False, ["ビーズ", "油粘土"]), ("針金", False, []))
tpl = TEMPLATES["slider_fan"]
keep = tpl.bom, tpl.materials
try:
    for word, period in WORD_PERIOD:
        tpl.bom, tpl.materials = (lambda p: [{"name": "x", "material": "紙"}]), (lambda p, w=word: ["のり、はさみ、定規", f"{w} 1 本"])
        d = ways.details("slider_fan", "tab")
        assert d["period"] is period, (word, d)
        # 用意する物の文では OTHER の語しか拾わない。一覧の語を全部見るため、部品表の素材としても通す
        tpl.bom, tpl.materials = (lambda p, w=word: [{"name": "x", "material": f"{w} 1 本"}]), (lambda p: ["のり、はさみ、定規"])
        d = ways.details("slider_fan", "tab")
        assert d["one_sheet"] is False and d["period"] is period, (word, d)
    for material, period, modern in MATERIAL_PERIOD:
        tpl.bom, tpl.materials = (lambda p, m=material: [{"name": "x", "material": m}]), (lambda p: ["のり、はさみ、定規"])
        d = ways.details("slider_fan", "tab")
        assert d["one_sheet"] is False and d["period"] is period and d["modern_substitutes"] == modern, (material, d)
    tpl.bom, tpl.materials = (lambda p: [{"name": "x", "material": "紙（厚さ 0.15mm 前後）"}]), (lambda p: ["のり、はさみ、定規", "紙を 1 枚"])
    d = ways.details("slider_fan", "tab")
    assert d["one_sheet"] is True and d["period"] is True, d
finally:
    tpl.bom, tpl.materials = keep
assert not [r for r in ways.table() if r["period"] and r["modern_substitutes"]]  # 今の物で代えたのに当時の材料、は読み違い
# 名前はサイトと同じ。片方を変える時は両方の試験を変える
assert set(ways.details("slider_fan", "tab")) == {"one_sheet", "fold_only", "period", "other_materials", "modern_substitutes"}
sumo = next(r for r in table if r["template"] == "lever_link" and r["form"] == "sumo")
assert sumo["period"] is False and "割ピン" in "".join(sumo["modern_substitutes"]), sumo
assert all(r["period"] for r in table if r["one_sheet"])  # 紙だけなら当時の材料でもある
# 4. 入口: JSON で出す（サイトが絞り込みに使う）
r = subprocess.run([sys.executable, "-m", "omochae.ways", "--json"], cwd=ROOT, capture_output=True, text=True,
                   env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
assert r.returncode == 0 and json.loads(r.stdout) == json.loads(json.dumps(table, ensure_ascii=False)), r.stderr
# 間違った呼び方は 4（README の終了の番号。1 と 2 は使わない。ほかの口と同じ）
r = subprocess.run([sys.executable, "-m", "omochae.ways", "--nope"], cwd=ROOT, capture_output=True, text=True,
                   env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
assert r.returncode == 4, (r.returncode, r.stderr)
print("ok")
