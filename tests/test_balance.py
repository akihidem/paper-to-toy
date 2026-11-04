"""釣り合いの床（F5.balance）の式の要所を数点で確かめる。重心の向き（上か下か）は言葉で決めると間違えやすいので、ここで数える。"""
import math

from omochae.compose import TEMPLATES
from omochae.pivot_model import center, rest_tilt_deg
from omochae.templates import balance as t

Y = {**t.DEFAULTS, "kind": "yajirobe"}
O = {**t.DEFAULTS, "kind": "okiagari"}
assert TEMPLATES["balance"] is t, "templates/ に置けば登録される"
for p in (Y, O):
    assert t.check_physics(p) == [] and not t.check_range(p), t.check_physics(p)

# --- 弥次郎兵衛
# 既定の腕では、重心は支点（V の先）の下にある。紙の体（表裏 2 枚）は玉 1 つより軽い
_, z, total = center(t.yajirobe_points(Y))
assert z > t.MIN_DROP and t.yajirobe_points(Y)[0][0] < Y["ball_g"]
# 腕を下へ向けるほど重心が下がる
zs = [center(t.yajirobe_points({**Y, "arm_angle": a}))[1] for a in (20, 40, 60, 80)]
assert zs == sorted(zs), zs
# 腕を水平近くに上げると重心が支点の上に来て、F5.balance の重心で落ちる
fs = t.check_physics({**Y, "arm_angle": 15, "arm_length": 60})
assert [(f.floor, f.where) for f in fs] == [("F5.balance", "重心")], fs
# 玉が重いほど、左右の差（CLAY_TOL）での傾きは小さい（同じ差が全体の重さに対して小さくなる）
tilt = lambda p: abs(rest_tilt_deg(t.yajirobe_points(p, t.CLAY_TOL)))
assert tilt({**Y, "ball_g": 6}) < tilt(Y) < tilt({**Y, "ball_g": 1})
# 軽い玉で浅い腕だと、左右の差で傾きすぎる
fs = t.check_physics({**Y, "ball_g": 0.5, "arm_angle": 40})
assert any(f.where == "玉" and "傾く" in f.message for f in fs), fs
# 粘土の玉の大きさ: 体積 = 重さ / 密度
assert abs(4 / 3 * math.pi * t.ball_r(3) ** 3 * t.CLAY_DENSITY - 3) < 1e-9
# 支点の先の厚み: 表裏 2 枚 + 当て紙。2 枚の当て紙では薄く落ち、6 枚なら通る
assert abs(t.tip_thickness(Y) - 8 * Y["paper_thickness"]) < 1e-12
fs = t.check_physics({**Y, "tip_layers": 2})
assert [(f.floor, f.where) for f in fs] == [("F5.balance", "支点")], fs
# 当て紙は蛇腹: 枚数 − 1 本の折り線が、谷と山で交互
tip = next(q for q in t.parts(Y) if q.key == "tip")
assert len(tip.valley) + len(tip.mountain) == Y["tip_layers"] - 1 and abs(len(tip.valley) - len(tip.mountain)) <= 1
# 差し込みが長すぎると、竹串の奥が体の外に出るか左右で交わる
fs = t.check_physics({**Y, "arm_angle": 45, "arm_insert": 40})
assert any(f.where.endswith("腕") for f in fs), fs
# 台が低いと玉が机に当たる
assert any(f.where == "台" for f in t.check_physics({**Y, "stand_h": 80}))
# 表と裏は左右が逆で、重ねると外形がそろう
front, back = (q for q in t.parts(Y) if q.key in ("front", "back"))
assert sorted((round(Y["body_w"] - x, 6), round(y, 6)) for x, y in back.outline) == sorted((round(x, 6), round(y, 6)) for x, y in front.outline)

# --- 起き上がり小法師
# 粘土の欠けの体積は重さと合い、重心は欠けの中（底から欠けの高さの間）
h, zc = t.clay_cap(O)
R = O["base_r"]
assert abs(math.pi * h * h * (3 * R - h) / 3 * t.CLAY_DENSITY - O["bottom_g"]) < 1e-6 and 0 < zc < h
# 半球を満たすと、重心は底から 5R/8（中身の詰まった半球の重心）
full = {**O, "bottom_g": 2 / 3 * math.pi * R ** 3 * t.CLAY_DENSITY}
assert abs(t.clay_cap(full)[1] - 5 * R / 8) < 1e-6
# 底の粘土を増やすほど重心が下がる（紙が軽い間）
assert t.com_height({**O, "bottom_g": 6}) < t.com_height(O) < t.com_height({**O, "bottom_g": 1})
# 円錐が高く粘土が少ないと、重心が丸みの中心に近づき、F5.balance の重心で落ちる
fs = t.check_physics({**O, "cone_h": 100, "bottom_g": 1})
assert [(f.floor, f.where) for f in fs] == [("F5.balance", "重心")], fs
assert t.com_height({**O, "cone_h": 100, "bottom_g": 1}) > R * (1 - t.MIN_MARGIN)
# 粘土が多すぎると底の半分に収まらない
assert any(f.where == "粘土" for f in t.check_physics({**O, "bottom_g": 30, "base_r": 15}))
# 円錐を開いた扇の弧 ＝ 底の円周。低い円錐は半円を超えて落ちる
th, _ = t.cone_angles(O)
assert abs(th * t.slant(O) - 2 * math.pi * R) < 1e-9
assert any(f.where == "円錐" for f in t.check_physics({**O, "cone_h": 20}))
# 切れの幅は赤道で円周 / 切れの数、極で 0
assert abs(2 * t.gore_half_width(O, 0) * O["gores"] - 2 * math.pi * R) < 1e-9 and abs(t.gore_half_width(O, math.pi * R / 2)) < 1e-9

# 形ごとの部品は部品表と合い、鍵が重ならない
assert {q.key for q in t.parts(Y)} == {"front", "back", "tip"} and {q.key for q in t.parts(O)} == {"shell", "dome"}
assert {r["key"] for r in t.bom(Y)} >= {"arm", "ball", "stand"} and "weight" in {r["key"] for r in t.bom(O)}
print("ok")
