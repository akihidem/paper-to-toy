"""御来迎の内筒を下から押し上げる形（push_part rise）と、次の組（goraigo-v12）の見本の寸法を確かめる。

本人の決定（2026-11-06）「筒を外す形（lift）はやめる。下から押し上げるバージョンを作る。側面のつまみのバージョンは廃止。
内筒を付ける。」と、前の決定「糸なしでやります」による。lift の糸の無い扇と受けを、内筒の上に蓋をした台に載せ、内筒を下から
指で押し上げる。見本の寸法は、実物の写真の比に A4 の 1 枚と床が許す所まで寄せた（選んだ事は slider_fan の RISE の注）。
"""
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae.__main__ import load_source  # noqa: E402
from omochae.compose import compose  # noqa: E402
from omochae.templates import slider_fan as sf  # noqa: E402

SC = json.loads((ROOT / "examples/goraigo_v12.json").read_text(encoding="utf-8"))
V12 = {**sf.DEFAULTS, **SC["params"]}
SRC = load_source(SC["source_id"])
words = lambda p: " ".join(r["material"] for r in sf.bom(p)) + " ".join(sf.materials(p)) + " ".join(sf.steps(p))

# 1. 見本の寸法: 形は rise。比は実物の写真の目測（扇の半径は筒の一辺の約 1.1 倍・像の幅は一辺の約 0.4 倍・筒の長さは一辺の約 4 倍）。
#    筒の長さは A4 の 1 枚に入る所まで（外筒と内筒を左の列に縦に積む）。1mm 長くすると刷る域から出る事も見る
assert SC["template"] == "slider_fan" and V12["push_part"] == sf.RISE
A, H = V12["tube_side"], V12["tube_height"]
assert abs(V12["fold_height"] / A - 1.1) <= 0.05 and abs(V12["figure_w"] / A - 0.4) <= 0.01, (V12["fold_height"], V12["figure_w"])
assert 3.8 <= H / A <= 4.0, H / A
assert sf.check_range(V12) == [], [f.line() for f in sf.check_range(V12)]
assert sf.check_physics(V12) == [], [f.line() for f in sf.check_physics(V12)]
assert compose("slider_fan", SC["params"], SRC)[2] == []
longer = {**SC["params"], "tube_height": H + 1, "pusher_height": V12["pusher_height"] + 1}
assert {f.floor for f in compose("slider_fan", longer, SRC)[2]} == {"F5.print_area"}
# 既定値は変えていない（凍結の場面のため）。既定の形は tab のまま
assert sf.DEFAULTS["push_part"] == "tab" and sf.DEFAULTS["tube_height"] == 84 and sf.DEFAULTS["fold_count"] == 28
with tempfile.TemporaryDirectory() as d:
    r = subprocess.run([sys.executable, "-m", "omochae", "--scenario", str(ROOT / "examples/goraigo_v12.json"), "--out", f"{d}/v12"],
                       cwd=ROOT, env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert r.returncode == 0 and pathlib.Path(f"{d}/v12.pdf").exists(), r.stderr

# 2. 部品: 1 外筒・2 内筒・3 台・4 扇・5 像・6 受け。糸・竹串・溝・つまみ・穴は無い
by = {q.key: q for q in sf.parts(V12)}
by_place = {q.key: q for q in compose("slider_fan", SC["params"], SRC)[1]["parts"]}
# 内筒は外筒より RISE_GRIP 以上長い（台が口の高さに来た開いた位置でも外筒の下へ出て、指で押し引きできる）
assert V12["pusher_height"] >= H + sf.RISE_GRIP
# 台・像・受けの段は、右の列の扇の下に置く（左の列は外筒と内筒）
assert by_place["base"].y > by_place["fan"].y + by_place["fan"].height and by_place["base"].x > by_place["tube"].x + by_place["tube"].width
assert sorted((q.number, q.key, q.label) for q in by.values()) == [
    (1, "tube", "1 外筒"), (2, "pusher", "2 内筒"), (3, "base", "3 台"), (4, "fan", "4 扇"), (5, "figure", "5"), (6, "cradle", "6 受け")]
assert all(not q.holes and not q.cuts for q in by.values()), [(q.key, q.holes, q.cuts) for q in by.values() if q.holes or q.cuts]
# 外形は 4 つの角と糊代の 2 つの角の 6 点（つまみの形は溝の切り込みで 4 点増える）
assert len(by["tube"].outline) == 6 and by["tube"].hide_folds and len(by["tube"].mountain) == 4 and not by["tube"].valley
assert len(by["pusher"].valley) == 4 and not by["pusher"].mountain and by["pusher"].height == V12["pusher_height"]  # 内筒は破線の谷折り
assert len(by["base"].mountain) == 4 and not by["base"].valley  # 台は印の面を上にして糊代を下へ折る
n, w, h = int(V12["fold_count"]), V12["fold_width"], V12["fold_height"]
assert by["fan"].outline == [(0, 0), (h, 0), (h, n * w), (0, n * w)] and not by["fan"].glue  # 足の無い長方形
c = by["cradle"]
assert len(c.valley) == 2 and len(c.glue) == 3 and abs(c.width - sf.cradle_width(V12)) < 1e-9
assert abs(c.height - (2 * sf.CRADLE_FLAP + sf.cradle_depth(V12))) < 1e-9
assert sorted((r["number"], r["key"]) for r in sf.bom(V12)) == [(1, "tube"), (2, "pusher"), (3, "base"), (4, "fan"), (5, "figure"), (6, "cradle")]
text = words(V12)
assert not any(k in text for k in ("糸", "竹串", "溝", "つまみ", "穴を")), text
# 6 受けは紙の部品なので、用意する物に「… 1 本」と書かない（6 番は前から竹串と割り箸の行の番号）
assert not any("本" in m for m in sf.materials(V12)), sf.materials(V12)

# 3. 題と組み方: 新しい形なので手順の番号は新しい。最後は、内筒を下から押し上げると扇が口から出て開き、引き下げると畳まれて筒に入る
assert sf.title(V12) == "内筒を下から押し上げる"
st = sf.steps(V12)
assert len(st) == 11 and st[0].startswith("刷った物差し"), st
assert "押し上げる" in st[-1] and "開く" in st[-1] and "引き下げる" in st[-1] and "筒に入る" in st[-1], st[-1]
assert "一緒に持つ" in st[-1] and "抜ける" in st[-1], st[-1]  # 止めは無いので、静かな時は外筒と内筒を一緒に持つ
assert any("2 内筒の上の口に差し込み" in x and "内の面に貼る" in x for x in st) and any("6 受け" in x for x in st)

# 4. 3D の確かめはつまみの形だけを組むので、この形は確かめられない（4）
r = subprocess.run([sys.executable, "-m", "omochae.fold3d", "--template", "slider_fan", "--params", json.dumps({"push_part": "rise"})],
                   cwd=ROOT, env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
assert r.returncode == 4, (r.returncode, r.stderr)

# 5. この形に効かない床は出ない（ほかの形の負の場面の寸法を v12 に足しても、足・穴・溝の床は出ない）
rise_floors = {"F5.fan_height", "F5.figure_height", "F5.stroke", "F5.slide_clearance", "F5.base_size", "F5.fan_thickness",
               "F5.figure_base", "F5.fan_clearance", "F5.fan_length", "F5.range"}
for extra in ({"pivot_above_rim": 0}, {"pivot_above_rim": 40}, {"hub": "rim"}, {"knob_width": 8}, {"stage_height": 40},
              {"fold_count": 6, "fold_width": 5, "fold_height": 40}, {"fan_length": 200}, {"paper_thickness": 1.2}):
    got = {f.floor for f in sf.check_physics({**V12, **extra}) + sf.check_range({**V12, **extra})}
    assert got <= rise_floors, (extra, got)

# 6. 落ちる寸法は、その床で落ちる（1 つの崩れに 1 つの床）
def floors(**extra):
    return [f.floor for f in sf.check_physics({**V12, **extra})]
assert floors(push_amount=30) == ["F5.fan_height"]                       # 受けの底＋扇の高さ 28.6＋2 に足りず、静かな時に扇が出る
assert floors(figure_h=30) == ["F5.figure_height"]                       # 像 30＋2 が押し上げる量 31 を超え、静かな時に像が出る
assert floors(pusher_height=111) == ["F5.stroke"]                        # 内筒が外筒＋10 に足りず、開いた位置で外筒の下に出ない
assert floors(push_amount=103) == ["F5.stroke"]                          # 押し上げる量が筒の高さを超え、静かな時に台が筒の下に出る
assert floors(push_amount=81) == ["F5.stroke"]                           # 静かな時の差し込み 21 が内筒の一辺 22 より短く、傾く
# 2 つは文を分ける（台が筒の下に出る寸法で「差し込みが負」と言わない）
msg = lambda **extra: [f.message for f in sf.check_physics({**V12, **extra})][0]
assert "台が筒の下に出る" in msg(push_amount=103) and "差し込まれず" not in msg(push_amount=103)
assert "21mm しか差し込まれず" in msg(push_amount=81)
assert floors(push_amount=80) == []                                       # 差し込み 22 なら通る（境）
assert floors(pusher_side=25, base_side=24.5) == ["F5.slide_clearance"]  # 内筒が外筒の一辺−1 より小さくない
assert floors(base_side=22) == ["F5.base_size"]                          # 台が内筒と同じ大きさで、糊代の紙 2 枚が口に入らない
assert floors(base_side=20.9) == ["F5.base_size"]                        # 台が内筒より 1mm を超えて小さく、糊代が壁に届かない
assert floors(base_side=21) == [] and floors(base_side=21.7) == []       # 境（内筒−1 と、内筒−紙 2 枚）
assert floors(fold_count=24) == ["F5.fan_clearance"]                     # 24 枚 × 4mm は 192° で、ほぼ 180° に収まらない
assert floors(figure_w=25) == ["F5.figure_base"]                         # 像の幅 25 が筒の一辺−2 を超え、筒に入らない
# 右の列の段の下に文字が重ならない: 筒が短く扇が長い寸法（段が左の列の筒より下まで来る）でも、配置の検査が通る
short = {**SC["params"], "tube_height": 70, "pusher_height": 80, "push_amount": 48, "fold_count": 35, "fold_height": 45}
assert sf.check_physics({**sf.DEFAULTS, **short}) == [], [f.line() for f in sf.check_physics({**sf.DEFAULTS, **short})]
_, lay, fs = compose("slider_fan", short, SRC)
assert fs == [], [f.line() for f in fs]
pl = {q.key: q for q in lay["parts"]}
assert pl["base"].x > pl["tube"].x + pl["tube"].width and pl["base"].y + pl["base"].height > pl["pusher"].y + pl["pusher"].height
# 既定の寸法（つまみの形の寸法）に形だけ rise を入れると床に落ちる。rise は寸法ごと書く（見本は examples/goraigo_v12.json）
assert "F5.stroke" in [f.floor for f in sf.check_physics({**sf.DEFAULTS, "push_part": sf.RISE})]
print("ok 御来迎の内筒を下から押し上げる形（rise）と次の組の見本")
