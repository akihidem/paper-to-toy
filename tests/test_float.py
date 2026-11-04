"""浮き人形の床（F5.float）の式の要所を数点で確かめる。浮心・重心・BM は言葉で決めると間違えやすいので、ここで数える。"""
import math

from shapely.geometry import Polygon

from omochae.compose import TEMPLATES
from omochae.templates import float as t  # module の名が float なので、組み込みの float を隠さないよう別名で読む

P = dict(t.DEFAULTS)
assert TEMPLATES["float"] is t, "templates/ に置けば登録される"
for v in t.VANES:
    assert t.check_physics({**P, "vane": v}) == [] and not t.check_range({**P, "vane": v}), v

# 質量は刷る部品の面積 × 面密度 ＋ テープ ＋ 粘土。部品の面積から数え直して合わせる
by = {q.key: q for q in t.parts(P)}
L, W, h = P["tray_length"], P["tray_width"], P["wall_height"]
paper = sum(Polygon(q.outline).area for q in by.values()) * P["paper_gsm"] / 1e6
tape = (L * W + 2 * (L + W) * h) * P["tape_gsm"] / 1e6
hy = t.hydro(P)
assert abs(hy["m"] - (paper + tape + P["ballast_g"])) < 1e-9, hy
# 喫水 ＝ 体積 ÷ 底の面積、1g は 1000mm³
assert abs(hy["d"] - hy["m"] * 1000 / (L * W)) < 1e-9 and abs(hy["f"] - (h - hy["d"])) < 1e-9
# BM ＝ I/V（狭い向き: 長さ × 幅³ / 12）、KB ＝ d/2
assert abs(hy["BM"] - L * W ** 3 / 12 / hy["V"]) < 1e-9 and abs(hy["KB"] - hy["d"] / 2) < 1e-9
# 長さと幅を入れ替えても、倒れやすい向きで見るので BM は同じ
assert abs(t.hydro({**P, "tray_length": W, "tray_width": L})["BM"] - hy["BM"]) < 1e-9

# 人形が高いほど G が上がり、GM が下がる。重りは G を下げる
assert t.hydro({**P, "figure_height": 90})["KG"] > hy["KG"]
assert t.hydro({**P, "ballast_g": 0})["KG"] > hy["KG"]

# 重りを積むと沈み、壁が低いと余裕が足りず落ちる
# 粘土は四隅の四角を広げて 8mm より薄く載せる（厚さの床が先に鳴らないように）
heavy = {**P, "glue": 5, "ballast_g": 20, "clay_side": 20, "leaf_radius": 20}
fs = t.check_physics({**heavy, "wall_height": 8})
assert [(f.floor, f.where) for f in fs] == [("F5.float", "舟の壁")], fs
# 余裕が下限を越えても、狭い舟では少し傾いただけでふちが水に着く
q = {**heavy, "wall_height": 10}
assert t.hydro(q)["f"] >= t.FREEBOARD_MIN and t.hydro(q)["heel"] < t.MIN_HEEL
assert [f.where for f in t.check_physics(q)] == ["舟の壁"]

# 狭く深い厚紙の舟は G が高く戻らない。粘土で G を下げると GM は上がる
deep = {**P, "tray_length": 40, "tray_width": 20, "wall_height": 35, "figure_height": 34, "leaf_radius": 9, "ballast_g": 0, "paper_gsm": 300}
fs = t.check_physics(deep)
assert [(f.floor, f.where) for f in fs] == [("F5.float", "重心")], fs
assert t.hydro({**deep, "ballast_g": 4})["GM"] > t.hydro(deep)["GM"]

# 葉は底に入り、人形の足の台は葉に乗る
assert any(f.where == "葉" for f in t.check_physics({**P, "leaf_radius": 30}))
assert any(f.where == "人形" for f in t.check_physics({**P, "leaf_radius": 15}))
# 糊代が壁より広いと角が閉じない
assert any(f.where == "舟の糊代" for f in t.check_physics({**P, "wall_height": 9, "glue": 8}))

# 風受け: 半円に丸めると紙の幅が π × 半径。壁の上に出ないと落ち、底に入らないと落ちる
C = {**P, "vane": "cups"}
assert abs(t.cup_radius(C) * math.pi - C["cup_width"]) < 1e-9
assert any(f.where == "風受け" and "壁の上" in f.message for f in t.check_physics({**C, "cup_height": 25}))
assert any(f.where == "風受け" and "入らない" in f.message for f in t.check_physics({**C, "cup_width": 40}))
# 風受けは cups の形だけにあり、部品表にも載る。部品表の番号と key が刷る部品と合う
assert {"cupa", "cupb"} <= set(by_c := {q.key for q in t.parts(C)}) and "cupa" not in by
rows = {r["number"]: r["key"] for r in t.bom(C)}
assert all(rows[q.number] == q.key for q in t.parts(C)) and {"tape", "ballast"} <= set(rows.values())

# 組み方の文は水の注意を先に言い、紙が濡れると弱る事を言う
assert t.steps(P)[0] == "水を使う時は大人と一緒に・紙は濡れると弱る"
assert "吸水を入れない" in t.__doc__

# 式は人形が舟の真ん中に立ち、粘土が四隅に同じだけ載る（G が舟の真ん中の上にある）と見る。貼る所を紙に刷らないと、
# 作る人がずらして貼り、式の見込みと違う物ができる。印は舟と葉の絵に刷り、組み方の文で言う。
def marks(q, kind):
    return [a for a in q.art if a.get("mark") == kind]


tray, leaf = by["tray"], by["leaf"]
cx, cy = h + L / 2, h + W / 2  # 舟の展開図の底の真ん中
(ring,) = marks(tray, "leaf")
xs, ys = [x for x, _ in ring["pts"]], [y for _, y in ring["pts"]]
assert abs((min(xs) + max(xs)) / 2 - cx) < 0.1 and abs((min(ys) + max(ys)) / 2 - cy) < 0.1 and abs((max(xs) - min(xs)) / 2 - P["leaf_radius"]) < 0.1
clay = marks(tray, "ballast")
assert len(clay) == 4
# 四隅の印の重心の平均は底の真ん中（粘土の重心を真ん中に置く）
mx = sum(Polygon(a["pts"]).centroid.x for a in clay) / 4
my = sum(Polygon(a["pts"]).centroid.y for a in clay) / 4
assert abs(mx - cx) < 1e-6 and abs(my - cy) < 1e-6
assert not marks(t.parts({**P, "ballast_g": 0})[0], "ballast")  # 粘土を使わない時は刷らない
(foot,) = marks(leaf, "figure")
fx = [x for x, _ in foot["pts"]]
assert abs((min(fx) + max(fx)) / 2 - P["leaf_radius"]) < 1e-6 and abs(max(fx) - min(fx) - t.foot_width(P)) < 1e-6
cups = marks(t.parts(C)[0], "cups")
assert len(cups) == 2
st = " ".join(t.steps(C))
assert "葉の印" in st and "足の印" in st and "四隅の印" in st and "風受けの印" in st

# 二度目の検品の指摘 1: 粘土の重心の高さは、重さ・密度・四隅の四角の面積から出す厚みの半分。重い粘土を小さな四角に積むと
# 厚く高くなり、低い重心と見込んで通してはいけない
clay_t = P["ballast_g"] * 1000 / t.CLAY_DENSITY / (4 * P["clay_side"] ** 2)
assert abs(t.clay_thickness(P) - clay_t) < 1e-9 and (P["ballast_g"], clay_t / 2) in t.mass_points(P)
fs = t.check_physics({**P, "ballast_g": 30})
assert [(f.floor, f.where) for f in fs] == [("F5.float", "重り")], fs
# 指摘 2: 風受けの足の糊代は、半円に丸めても底に平らに貼れるよう、切り込みで歯に分ける
cup = next(q for q in t.parts(C) if q.key == "cupa")
assert len(cup.glue) >= 3 and all(Polygon(g).area < C["cup_width"] * t.TAB / 2 for g in cup.glue), cup.glue
assert any("切り込み" in s for s in t.steps(C))
# 指摘 3: 風受けの印は端から 1mm 内なので、使える長さは L − 2。葉・風受け・粘土の四角は底で重ならない
assert any(f.where == "風受け" for f in t.check_physics({**C, "tray_length": 79}))  # 2r + 4ρ = 78 ≦ 79 でも、端の 1mm で葉に重なる
assert any(f.where == "粘土の印" for f in t.check_physics({**P, "tray_length": 60, "tray_width": 60, "leaf_radius": 29}))
# 指摘 4: 水よけ（テープかろう）は必ず貼るので、面密度 0 は範囲の外
assert [f.floor for f in t.check_range({**P, "tape_gsm": 0})] == ["F5.range"]
print("ok")
