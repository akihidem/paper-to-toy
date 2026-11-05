"""浮き人形の床（F5.float）の式の要所を数点で確かめる。浮心・重心・BM は言葉で決めると間違えやすいので、ここで数える。"""
import math

from shapely.geometry import LineString, Polygon, box

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
# 人形が壁の間に入るかを見るようになってから（五度目の検品）、GM が落ちる狭い舟では人形も壁に当たる。範囲の中を乱数で 4000 組
# 試しても、GM だけで落ちる組は無かった（人形が入る幅 29mm ほどからは、紙の舟の BM が十分に大きい）。両方で落ちる事を見る
assert {(f.floor, f.where) for f in fs} == {("F5.float", "重心"), ("F5.float", "人形")}, fs
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
# 足の印は葉の矢印と直角（葉の y の向き）。人形は舟の幅の向きに立つ（五度目の検品の指摘で向きを決めた）
fy = [y for _, y in foot["pts"]]
assert {x for x, _ in foot["pts"]} == {P["leaf_radius"]}
assert abs((min(fy) + max(fy)) / 2 - P["leaf_radius"]) < 1e-6 and abs(max(fy) - min(fy) - t.foot_width(P)) < 1e-6
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
small = {**P, "figure_height": 30, "leaf_radius": 8, "tray_width": 32, "tray_length": 60, "ballast_g": 0}
assert t.foot_width(small) <= 2 * 8 * 0.9 and [f.where for f in t.check_physics(small)] == ["人形"]
# 指摘 4: 水の注意は守れる形で言う（こぼしたら拭く・使った水は捨てる・中の刷った色がにじむ・出したら乾かす）
st = " ".join(t.steps(P))
assert all(k in st for k in ("拭く", "水を捨てる", "にじむ", "乾かす")) and "触らない" not in st

# 四度目の検品（main との差分）の指摘。配置と外形は check_params（描く前の検査の全部）で見る
SRC = json.load(open(pathlib.Path(__file__).resolve().parents[1] / "data/sources/NDL-1187053-R0000028-R-float.json", encoding="utf-8"))


def floors(q):
    return sorted({e.split()[1] for e in check_params("float", q, SRC)["errors"]})


# 指摘 1: 顔の点が帽子と胴の間で外形の外に出て、高い人形（70 から）が F5.image_box で落ちていた。顔も外形に入れる
# 高い人形は壁の間に入るよう舟を広げて見る（五度目の検品から、壁の上端より下の人形の幅を見る）
assert floors({**P, "figure_height": 70, "tray_width": 70}) == [] and floors({**P, "figure_height": 90}) == ["F5.float"]
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

# 五度目の検品の指摘 1: 人形の向きを決め、向きに沿って、壁の上端より下の人形の外形が底の内に入るか、風受けの高さより下の外形が
# 風受けの足跡に当たらないかを見る。向きは葉の矢印と舟の底の刻みで刷り、組み方の文で言う
(arrow,) = marks(leaf, "arrow")
ax = [x for x, _ in arrow["pts"]]
assert max(ax) > P["leaf_radius"] and len({round(y, 6) for _, y in arrow["pts"][:2]}) == 1  # 矢の軸は葉の +x（右）へ
(tick,) = marks(tray, "leafdir")
assert min(x for x, _ in tick["pts"]) >= h + L / 2 + P["leaf_radius"] - 1e-6  # 丸い印の右の外に刻む
st = " ".join(t.steps(C))
assert "矢印" in st and "刻み" in st and "2 の数字の側" not in st
# 人形の外形の半幅（足の真ん中から、左右の遠い方）。高さで切るので、低い所ほど狭い
assert t.figure_half_width(P, 1) < t.figure_half_width(P, P["wall_height"]) <= t.figure_half_width(P, P["figure_height"])  # 一番広いのは低い所の刃
# 人形は葉の真ん中に、矢印と直角（y）に立ち、糊代は葉の上にある。風受けは葉に重ならない所に置くので、人形の紙の面（x ＝ 底の真ん中）
# には届かない。それで人形と風受けの当たりは床にせず、その前提（風受けの足跡の x が葉の手前で終わる）をここで見る（六度目の検品の指摘）
# 4 つとも通る寸法にする（七度目の検品: 前は 1 つが物理で落ちて飛ばされていた）。広い舟の端・狭い隙間の端を入れる
edges = ({**C}, {**C, "tray_length": 110, "leaf_radius": 25}, {**C, "cup_width": 12}, {**C, "tray_length": 78, "leaf_radius": 14.5})
for q in edges:
    assert not t.check_physics(q), (q, t.check_physics(q))
    fm = t.floor_marks(q)
    cxq, rq = q["tray_length"] / 2, q["leaf_radius"]
    assert all(c.bounds[2] < cxq - rq or c.bounds[0] > cxq + rq for c in fm["cups"]), q
assert not hasattr(t, "figure_plan")
# 六度目の検品の指摘 2: 組み方の文は刷った矢印と刻みで言う（幅が長さより長い舟では「長い向き」が刷った矢印と食い違った）
assert all("長い向き" not in s for s in t.steps(C)) and all("長い向き" not in s for s in t.steps({**P, "tray_width": 80, "tray_length": 70}))
# 指摘 3: 刻みは右の風受けの足跡（外へ折る歯を含む）に入らない
(tick_c,) = marks(t.parts(C)[0], "leafdir")
tk = LineString([(x - h, y - h) for x, y in tick_c["pts"]])
assert not any(tk.intersects(c) for c in t.floor_marks(C)["cups"])
# 幅の狭い舟では、壁の上端より下の袴と刃が壁に当たる
narrowfig = {**P, "tray_width": 44}
assert t.figure_half_width(narrowfig, narrowfig["wall_height"]) > narrowfig["tray_width"] / 2 - t.WALL_GAP
assert [f.where for f in t.check_physics(narrowfig)] == ["人形"], t.check_physics(narrowfig)
# 検品が挙げた、どの向きでも壁に当たるのに通っていた寸法（負の場面 float_neg_figure と同じ）
wallhit = {**P, "tray_length": 71, "tray_width": 68, "wall_height": 23, "figure_height": 81, "leaf_radius": 22, "ballast_g": 4}
assert [f.where for f in t.check_physics(wallhit)] == ["人形"]
# 七度目の検品の指摘: 葉の向きの刻みが短すぎて刷られないのに通り、組み方の文は刻みを言っていた（風受けつき・長さ 76・葉 14.5）。
# 葉を 90° 回して貼ると、人形が風受けに 12mm ほど入る。通る寸法では必ず刻みを刷り、刷れない寸法は落とす
for L_ in (70, 74, 76, 78, 90):
    for r_ in (12, 13, 14, 14.5, 15, 16, 20):
        for v in t.VANES:
            q = {**P, "vane": v, "tray_length": L_, "leaf_radius": r_, "figure_height": 40}
            ticks = marks(t.parts(q)[0], "leafdir")
            if not t.check_physics(q):
                assert ticks and math.dist(*ticks[0]["pts"][:2]) >= t.NOTCH_MIN, q
            elif not ticks:
                assert "刻み" in " ".join(f.message for f in t.check_physics(q)), q
fs = t.check_physics({**C, "tray_length": 76, "leaf_radius": 14.5})
assert [f.where for f in fs] == ["葉の向きの刻み"], fs

# 息で傾く角（風受けつき）。壁より上の風受けの面に掛かる息の力 × 腕 ÷ (m·g·GM)。見込みの値（息の速さ・抗力係数・余裕）は 1 か所に置き、
# 作った人の報告（Issue #21）で直す。式を数え直して合わせる
fo, fb = t.blow_forces(C)
area = 2 * t.cup_radius(C) * (C["cup_height"] - C["wall_height"]) * 1e-6
qd = 0.5 * t.AIR_DENSITY * t.BREATH_V ** 2
assert abs(fo - qd * area * t.CD_CUP_OPEN) < 1e-12 and abs(fb - qd * area * t.CD_CUP_BACK) < 1e-12 and fo > fb > 0  # 口の側が強く押され、差が舟を回す
hyc = t.hydro(C)
arm = ((C["wall_height"] + C["cup_height"]) / 2 - hyc["d"] / 2) / 1000
b_c, rim_c = t.blow_heel(C)
# 既定の舟は長さ ≧ 幅なので、幅の向きの GM とふちの角は hydro の値（狭い向き）と同じ
assert abs(b_c - math.degrees((fo + fb) * arm / (hyc["m"] / 1000 * t.GRAVITY * hyc["GM"] / 1000))) < 1e-9 and abs(rim_c - hyc["heel"]) < 1e-9
assert t.blow_heel(C, hyc) == (b_c, rim_c) and 0 < b_c < 1  # 既定の舟は広く、息では 1° も傾かない
assert t.blow_forces(P) == (0.0, 0.0) and t.blow_heel(P)[0] == 0.0  # 風受けの無い形は、息を受ける面を見ない
assert t.blow_heel({**C, "cup_height": 50})[0] > b_c > t.blow_heel({**C, "cup_height": 30})[0]  # 高い風受けほど傾く
# 息は幅の向きに当たる。幅が長さより長い舟では、幅の向きの GM は hydro の GM（狭い向き＝長さ）より大きく、ふちの角は幅で出すので小さい
wide_c = {**C, "tray_width": 80, "tray_length": 70, "leaf_radius": 12, "cup_width": 14}
hw = t.hydro(wide_c)
b_w, rim_w = t.blow_heel(wide_c)
gm_w = hw["KB"] + 70 * 80 ** 3 / 12 / hw["V"] - hw["KG"]
fo_w, fb_w = t.blow_forces(wide_c)
arm_w = ((wide_c["wall_height"] + wide_c["cup_height"]) / 2 - hw["d"] / 2) / 1000
assert gm_w > hw["GM"] and abs(b_w - math.degrees((fo_w + fb_w) * arm_w / (hw["m"] / 1000 * t.GRAVITY * gm_w / 1000))) < 1e-9
assert abs(rim_w - math.degrees(math.atan2(2 * hw["f"], 80))) < 1e-9 and rim_w < hw["heel"]
# 狭い舟に高い風受けを立てると、息で傾く角（余裕 BLOW_SAFETY 倍）が、ふちが水に着く角に届く（負の場面 float_neg_blow と同じ寸法）
blow = {**C, "tray_width": 30, "wall_height": 8, "glue": 5, "figure_height": 30, "leaf_radius": 10, "cup_width": 34, "cup_height": 60, "ballast_g": 0}
fs = t.check_physics(blow)
b_b, rim_b = t.blow_heel(blow)
assert [f.where for f in fs] == ["風受け"] and fs[0].message.startswith("息（") and b_b * t.BLOW_SAFETY >= rim_b >= t.MIN_HEEL, fs
assert floors(blow) == ["F5.float"] and floors({**blow, "cup_height": 36}) == []  # 風受けを低くすると通る
# 余裕: 見込みの息では届かない（角 < ふちの角）が、余裕を掛けると届く寸法も落とす（息の速さは量っていない見込みで、力は速さの 2 乗）
edge = {**blow, "cup_height": 50}
b_e, rim_e = t.blow_heel(edge)
assert b_e < rim_e <= b_e * t.BLOW_SAFETY and [f.where for f in t.check_physics(edge)] == ["風受け"]
# 別の検査が落ちた舟には息の検査を重ねない（同じ舟に、別の直し方を 2 つ言わない）。3 つとも、重ねなければ息の検査に掛かる寸法:
# 乾舷が足りない舟・GM が足りない舟・壁の上に 4mm しか出ず息を受けない風受け
sunk = {**blow, "ballast_g": 8, "clay_side": 12}
tippy = {**C, "tray_length": 88, "tray_width": 20, "wall_height": 30, "glue": 5, "figure_height": 30, "leaf_radius": 8, "cup_width": 16, "cup_height": 57, "ballast_g": 0, "paper_gsm": 300}
low = {**C, "tray_length": 50, "tray_width": 20, "wall_height": 34, "glue": 5, "figure_height": 30, "leaf_radius": 8, "cup_width": 38, "cup_height": 38, "ballast_g": 0}
hy_s, hy_t, hy_l = t.hydro(sunk), t.hydro(tippy), t.hydro(low)
assert hy_s["f"] < t.FREEBOARD_MIN and hy_t["GM"] < t.GM_MIN <= hy_l["GM"] and min(hy_t["f"], hy_l["f"]) >= t.FREEBOARD_MIN and min(hy_t["heel"], hy_l["heel"]) >= t.MIN_HEEL
for q, where, word in ((sunk, "舟の壁", "余裕"), (tippy, "重心", "GM"), (low, "風受け", "息を受けない")):
    b_q, rim_q = t.blow_heel(q)
    assert b_q * t.BLOW_SAFETY >= rim_q, q
    fs = t.check_physics(q)
    assert any(f.where == where and word in f.message for f in fs) and not any(f.message.startswith("息（") for f in fs), fs


# 糊代の斜線は刷った面にある。斜線の面が貼る相手に当たり、組み上がった物の見える側に斜線が残らない向きに折る:
# 舟は谷折り（刷った面が内・底の印が内に要る）で、角の糊代はとなりの壁の外側へ。人形の足と風受けの歯は山折り（谷折りだと斜線が上を向いて残る）
fig_p, cup_p = by["figure"], next(q for q in t.parts(C) if q.key == "cupa")
assert fig_p.mountain and not fig_p.valley and not cup_p.valley and tray.valley and not tray.mountain
# 風受けの山折りの線は幅いっぱいの 1 本（歯ごとの 3mm の線は、山折りの刻みより短く、実線に見える）。歯の糊代の上の辺は全部その線の上
(fold_c,) = cup_p.mountain
assert fold_c == ((0, C["cup_height"]), (C["cup_width"], C["cup_height"])) and all(g[0][1] == g[1][1] == C["cup_height"] for g in cup_p.glue)
st_f = " ".join(t.steps(C))
assert "となりの壁の外側" in st_f and "内側に貼って" not in st_f and st_f.count("山折り") >= 3 and st_f.count("斜線") >= 3 and "絵は矢印と逆" in st_f
# 「短い壁」「長い向き」とは言わない（幅が長さより長い舟では、糊代の無い壁の方が長い）
assert all("短い壁" not in s_ and "長い向き" not in s_ for q in (P, C, {**C, "tray_width": 80, "tray_length": 70}) for s_ in t.steps(q))
# 雷文は、舟の内から見ると 2 枚の壁で同じ形（口が底の側・巻く向きも同じ）。壁ごとに「内から見た左右（u）とふちからの距離（v）」に直して比べる。
# 上の壁は内から見て紙の右が右、下の壁は紙の右が左。既定の舟（ラベルが底にあり、2 枚とも同じ所から始まる）で見る
fret = marks(tray, "fret")
top_f = [a["pts"] for a in fret if a["pts"][0][1] < h]
bot_f = [a["pts"] for a in fret if a["pts"][0][1] > h + W]


def seen(pts, lower):
    xs = [x for x, _ in pts]
    return [(round(max(xs) - x if lower else x - min(xs), 6), round(2 * h + W - y if lower else y, 6)) for x, y in pts]


assert len(top_f) == len(bot_f) >= 3 and all(seen(a, False) == seen(top_f[0], False) for a in top_f) and all(seen(b_, True) == seen(top_f[0], False) for b_ in bot_f)
# 口（線の始まり）は底の折り線の側、閉じた側はふちの側。ふちからの距離で見る
assert seen(top_f[0], False)[0][1] > seen(top_f[0], False)[1][1] and seen(bot_f[0], True)[0][1] > seen(bot_f[0], True)[1][1]

# どちらの形にも、浮かべた後に動かす手順が 1 つある: 風受けつきは息、風受けの無い形は水をかき回した渦（前は浮かべて見るだけだった）
play_n = [s_ for s_ in t.steps(P) if "渦" in s_]
play_c = [s_ for s_ in t.steps(C) if "息を吹き" in s_]
assert len(play_n) == 1 and len(play_c) == 1 and not any("渦" in s_ for s_ in t.steps(C)) and not any("息を吹き" in s_ for s_ in t.steps(P))
assert f"{t.STIR_TURNS} 回" in play_n[0] and t.steps(P).index(play_n[0]) == len(t.steps(P)) - 2  # 片付けの前
# 手順の数は形だけで決まる（重りを使わない寸法でも番号がずれない）。作った人の報告は手順の番号で来て、形ごとに集められるため
for q in (P, C):
    with_clay, no_clay = t.steps(q), t.steps({**q, "ballast_g": 0})
    diff = [i for i, (a_, b_) in enumerate(zip(with_clay, no_clay)) if a_ != b_]
    assert len(with_clay) == len(no_clay) and len(diff) == 1 and "油粘土" in with_clay[diff[0]] and "重りを使わない" in no_clay[diff[0]], diff
# 組み方の文は、サイトの手順の紙の左の列（144mm・字 3.6mm）で STEP_LINES_MAX 行まで。前の版は風受けつきで 20 行あり、紙からはみ出していた。
# サイトは「番号. 文」の形で刷り、同じ折り返し（textfit.wrap）を使う
from omochae.textfit import text_width, wrap
for q in (P, C, {**P, "ballast_g": 0}, {**C, "ballast_g": 0}, {**C, "ballast_g": 12.5}):
    n_lines = sum(len(wrap(f"{i}. {s_}", t.STEP_SIZE, t.STEP_COL_W)) for i, s_ in enumerate(t.steps(q), 1))
    assert n_lines <= t.STEP_LINES_MAX, (n_lines, q)

# 「試した事」の欄は 1 行で、数でなく言葉で書く（サイトの手順の紙は測る欄を外している。2 行にすると紙からはみ出す）。
# 形ごとに、動かし方（息・渦）に合わせた予想の問いと欄にする
mc, mn = t.measures(C), t.measures(P)
for m, word, other in ((mc, "息", "渦"), (mn, "渦", "息")):
    (row,) = m["rows"]
    lab = " ".join(lab_ for lab_, _ in row)
    assert word in lab and other not in lab and "水が入ったか" in lab and not any(ch.isdigit() for ch in lab + m["predict"]) and "mm" not in lab
    assert sum(text_width(lab_, t.STEP_SIZE) + 1.5 + w_ + 5 for lab_, w_ in row) <= 190 and text_width(m["predict"], t.STEP_SIZE) <= 190, row
assert "息" in mc["predict"] and "かき回す" in mn["predict"]

# 手順ごとの直しの行き先（step_targets）。作った人の報告の困り事は手順の番号で来るので、番号から当たる寸法・見込みの値・検査の所を引ける。
# 文と行き先は 1 つの並びから出す。名は実際にある物だけ
WHERES = {"舟の壁", "重心", "舟の糊代", "葉", "人形", "重り", "風受け", "粘土の印", "葉の向きの刻み"}
for q in (P, C, {**C, "ballast_g": 0}, {**P, "ballast_g": 0}):
    st_q, tg = t.steps(q), t.step_targets(q)
    assert sorted(tg) == list(range(1, len(st_q) + 1)), q
    for i, target in tg.items():
        assert set(target) == {"params", "consts", "floors"}, target
        assert all(k in t.RANGES for k in target["params"]) and all(hasattr(t, c) for c in target["consts"]) and set(target["floors"]) <= WHERES, (i, target)
tc, st_c = t.step_targets(C), t.steps(C)
blow_i, tape_i, clay_i = (next(i for i, s_ in enumerate(st_c, 1) if w in s_) for w in ("息を吹き", "透明テープ", "油粘土"))
assert "BREATH_V" in tc[blow_i]["consts"] and "tape_gsm" in tc[tape_i]["params"] and "重り" in tc[clay_i]["floors"]
assert t.step_targets({**C, "ballast_g": 0})[clay_i] == tc[clay_i]  # 重りを使わない寸法でも、同じ番号は同じ行き先
assert not any(tc[i]["params"] or tc[i]["consts"] or tc[i]["floors"] for i in (1, 2, 3, len(st_c)))  # 水の注意・物差し・片付けは組み方の文だけ
# 所の名（floors）は、check_physics が実際に出す所の名の全部。検査の所の名を変えた時にここで気づく
seen_w = set()
for q in (blow, sunk, narrowfig, deep, {**P, "glue": 30}, {**P, "leaf_radius": 35}, {**P, "ballast_g": 30}, {**C, "tray_length": 76, "leaf_radius": 14.5},
          {**P, "tray_width": 28, "tray_length": 100, "clay_side": 15, "leaf_radius": 12, "ballast_g": 12, "figure_height": 40}):
    seen_w |= {f.where for f in t.check_physics(q)}
assert seen_w == WHERES, seen_w ^ WHERES
print("ok")
