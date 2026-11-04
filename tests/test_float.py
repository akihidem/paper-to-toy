"""浮き人形の床（F5.float）の式の要所を数点で確かめる。浮心・重心・BM は言葉で決めると間違えやすいので、ここで数える。"""
import math

from shapely.geometry import Polygon, box

import json
import pathlib

from omochae.compose import TEMPLATES, check_params
from omochae.templates import float as t  # module の名が float なので、組み込みの float を隠さないよう別名で読む

P = dict(t.DEFAULTS)
assert TEMPLATES["float"] is t, "templates/ に置けば登録される"
for v in t.VANES:
    assert t.check_physics({**P, "vane": v}) == [] and not t.check_range({**P, "vane": v}), v

# 質量は刷る部品の面積 × 面密度 ＋ テープ ＋ 粘土。部品の面積から数え直して合わせる
by = {q.key: q for q in t.parts(P)}
L, W, h = P["tray_length"], P["tray_width"], P["wall_height"]
paper = sum(Polygon(q.outline).area for q in by.values()) * P["paper_gsm"] / 1e6
# テープは底・壁の外側・ふちから内へ折り返す帯（TAPE_FOLD）
tape = (L * W + 2 * (L + W) * (h + t.TAPE_FOLD)) * P["tape_gsm"] / 1e6
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

# 狭く深い厚紙の舟は G が高く戻らない
deep = {**P, "tray_length": 40, "tray_width": 22, "wall_height": 35, "figure_height": 30, "leaf_radius": 10, "ballast_g": 0, "paper_gsm": 300}
fs = t.check_physics(deep)
assert [(f.floor, f.where) for f in fs] == [("F5.float", "重心")], fs
# 粘土は G を下げるが、重くなって V が増え BM ＝ I/V も下がる。粘土の厚みを実の面積から出すと、この狭い舟では GM は上がらない
# （前は粘土の重心を 3mm に決め打ちし、GM が上がると見ていた）。粘土で直すより、舟を広くする方が効く
light = {**deep, "ballast_g": 1, "clay_side": 6}
assert t.hydro(light)["KG"] < t.hydro(deep)["KG"] and t.hydro(light)["GM"] < t.hydro(deep)["GM"]
assert t.hydro({**deep, "tray_width": 30})["GM"] > t.hydro(deep)["GM"]

# 葉は底に入り、人形の足の台は葉に乗る
assert any(f.where == "葉" for f in t.check_physics({**P, "leaf_radius": 30}))
assert any(f.where == "人形" for f in t.check_physics({**P, "leaf_radius": 14}))
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
assert any(f.where == "風受け" for f in t.check_physics({**C, "tray_length": 79}))  # 端の 1mm と外へ折る歯の分で、葉に重なる
assert any(f.where == "粘土の印" for f in t.check_physics({**P, "tray_length": 60, "tray_width": 60, "leaf_radius": 29}))
# 指摘 4: 水よけ（テープかろう）は必ず貼るので、面密度 0 は範囲の外
assert [f.floor for f in t.check_range({**P, "tape_gsm": 0})] == ["F5.range"]

# 三度目の検品の指摘 1: 粘土の四角が重なるか底から出ると、実の面積は 4 × 辺² より狭く、粘土は厚くなる。重なりと収まりを見て、
# 厚みは実の面積（四角を合わせた面）から出す
narrow = {**P, "tray_width": 28, "tray_length": 100, "clay_side": 15, "leaf_radius": 12, "ballast_g": 12, "figure_height": 40}
sq = t.floor_marks(narrow)["ballast"]
real = sq[0].union(sq[1]).union(sq[2]).union(sq[3]).area
assert abs(t.clay_thickness(narrow) - narrow["ballast_g"] * 1000 / t.CLAY_DENSITY / real) < 1e-9
fs = t.check_physics(narrow)
assert {f.where for f in fs} >= {"粘土の印", "重り"}, fs
# 指摘 2: 風受けの足の歯は外へ折るので、足跡は半円の外へ歯の長さだけ広がる。広がった足跡で底・葉・粘土を見る
for c in t.floor_marks(C)["cups"]:
    assert c.area > math.pi * (t.cup_radius(C) + t.CUP_TAB) ** 2 / 2 * 0.98
    assert box(0, 0, C["tray_length"], C["tray_width"]).contains(c) and not c.intersects(t.floor_marks(C)["leaf"])
# 既定の葉では、歯の分の足跡が葉に重なる（半円だけ見ると通っていた）
assert any(f.where == "風受け" for f in t.check_physics({**C, "leaf_radius": 25}))
# 指摘 3: 人形の足の糊代（台形）は、葉の上に寝かせて貼るので、角まで葉の内に入る
assert t.foot_footprint(P).within(Polygon(t._circle(0, 0, P["leaf_radius"])))
fw = t.foot_width(P)
r_min = max(fw / 2, math.hypot(fw / 2 - 1.5, t.TAB))  # 台形の角のうち、葉の中心から一番遠い所
assert any(f.where == "人形" for f in t.check_physics({**P, "leaf_radius": math.floor(r_min * 10) / 10}))
# 小さな人形では糊代の奥行きが効く。足の幅だけ（幅 ≦ 葉の直径の 9 割）で見ると、この寸法は通っていた
small = {**P, "figure_height": 30, "leaf_radius": 8, "tray_width": 24, "tray_length": 60, "ballast_g": 0}
assert t.foot_width(small) <= 2 * 8 * 0.9 and [f.where for f in t.check_physics(small)] == ["人形"]
# 指摘 4: 水の注意は守れる形で言う（こぼしたら拭く・使った水は捨てる・中の刷った色がにじむ・出したら乾かす）
st = " ".join(t.steps(P))
assert all(k in st for k in ("拭く", "水を捨てる", "にじむ", "乾かす")) and "触らない" not in st

# 四度目の検品（/code-review・main との差分）の指摘。配置と外形は check_params（描く前の検査の全部）で見る
SRC = json.load(open(pathlib.Path(__file__).resolve().parents[1] / "data/sources/NDL-1187053-R0000028-R-float.json", encoding="utf-8"))


def floors(q):
    return sorted({e.split()[1] for e in check_params("float", q, SRC)["errors"]})


# 指摘 1: 顔の点が帽子と胴の間で外形の外に出て、高い人形（70 から）が F5.image_box で落ちていた。顔も外形に入れる
assert floors({**P, "figure_height": 70}) == [] and floors({**P, "figure_height": 90}) == ["F5.float"]
# 指摘 2: 高い風受けを葉の下に積むと説明の文に重なった。人形の段は 1 段目に置いた物の一番下から始める
assert floors({**P, "vane": "cups", "wall_height": 8, "glue": 5, "cup_width": 12, "cup_height": 60}) == []
# 指摘 3: 広い舟で葉が舟の右に入らず印字域を出た。入らない物は舟の下へ送る
wide = {**P, "tray_length": 110, "leaf_radius": 25}
assert floors(wide) == []
by_w = {q.key: q for q in t.parts(wide)}
t.place(by_w, __import__("omochae.page", fromlist=["PAGES"]).PAGES["A4"], 36, 4)
assert by_w["leaf"].y > by_w["tray"].y and by_w["leaf"].x == by_w["tray"].x and by_w["figure"].y >= by_w["leaf"].y + by_w["leaf"].height
# 指摘 4: 足の糊代の幅の全部に、折り線のすぐ上の紙がある（袴の裾を足の線まで平らに取る）
from shapely.geometry import Point
poly = Polygon(by["figure"].outline)
s_ = t._fig_scale(P)
x0, x1 = (t._FOOT[0] - t._LEFT) * s_ + t._OFF, (t._FOOT[1] - t._LEFT) * s_ + t._OFF
assert all(poly.contains(Point(x0 + (x1 - x0) * i / 40, t._feet(P) - 0.3)) for i in range(41))
# 指摘 5: 短い舟で「1 舟」のラベルが葉の印に重なった。重なる時は上の壁の左端に置き、雷文はその右から始める
short = {**P, "tray_length": 40, "clay_side": 6, "leaf_radius": 10, "figure_height": 30, "ballast_g": 1}  # 人形の足が葉に入り、粘土が薄く載る、物理の通る短い舟
tr = t.parts(short)[0]
assert tr.label_xy[1] < short["wall_height"] and tray.label_xy[1] > h  # 既定は底の印の右のまま
assert min(a["pts"][0][0] for a in tr.art if a["kind"] == "line" and a.get("stroke") == t.INK and a["pts"][0][1] < short["wall_height"]) >= tr.label_xy[0] + t.LABEL_W
assert floors(short) == []
# 指摘 6: 組み方の文で言う「ふちから内へ折り返す」テープの帯を、質量と重心に入れる（壁の上端にあるので G を上げる）
assert (2 * (L + W) * t.TAPE_FOLD * P["tape_gsm"] / 1e6, h - t.TAPE_FOLD / 2) in t.mass_points(P)
assert any(f"{t.TAPE_FOLD}mm" in s for s in t.steps(P))
# 葉より広い足の印は葉の内に留め、底に収まらない印は刷らない（F5.float が落とす寸法で、絵の検査を重ねて鳴らさない）
assert floors({**P, "tray_length": 110, "leaf_radius": 30}) == ["F5.float"]
print("ok")
