"""立てる姿の床（F5.stand）の式の要所と、姿と出典の組を確かめる。

なぜ組を試験で見るか: 雛形は、どの出典（--source）が選ばれたかを知らない。姿の値と出典の記録は場面が組にして渡すので、
組を間違えると、印は正しく刷られても絵と出典が食い違う。下の PAIRS は雛形の FIGURES とは別に手で書いた表で、両方が合う事を見る。
"""
import json
import math
import pathlib
import re

from shapely.geometry import Polygon

from omochae.compose import TEMPLATES, compose
from omochae.floors import check_bom
from omochae.templates import stand_figure as t

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = dict(t.DEFAULTS)
assert TEMPLATES["stand_figure"] is t, "templates/ に置けば登録される"
assert t.check_physics(P) == [] and not t.check_range(P)

# 姿と出典（コマ・頁）の組。調べの推定の名の順（担当の一覧の優先の順）。
PAIRS = {
    "inu": (16, "L"), "uma": (17, "L"), "mimizuku": (27, "L"), "kamibina": (12, "L"), "hagoita": (23, "L"),
    "tako_ji": (24, "L"), "tako_oni": (24, "L"),
    "tsuchi_usagi": (13, "L"), "tsuchi_kame": (13, "L"), "tsuchi_hato": (13, "L"),
    "shitadashi": (8, "R"), "kubi": (17, "R"), "fukumen": (11, "L"), "mino": (10, "L"), "suwari": (26, "L"),
    "kukurizaru": (30, "L"), "fushimi": (27, "R"), "miya": (9, "R"), "chigibako": (11, "R"),
    "tokkuri": (15, "L"), "suribachi": (21, "L"), "binkake": (26, "R"), "chagama": (30, "R"),
    "tawara": (22, "R"), "hamayumi": (15, "R"), "yamaneko": (18, "R"), "hebi": (20, "L"), "nobori": (31, "R"),
    "sakana": (12, "R"), "mochibana": (21, "R"), "torisao": (5, "L"), "torisao_hoso": (28, "L"), "kidachi": (5, "R"),
    "fumei_tama": (13, "R"), "fumei_tsutsu": (19, "R"),
}
assert set(PAIRS) == set(t.FIGURES) == set(t.FORMS), sorted(set(PAIRS) ^ set(t.FIGURES))
for fig, (canvas, side) in PAIRS.items():
    sid = f"NDL-1187053-R{canvas:07d}-{side}-stand_figure"
    assert t.FIGURES[fig]["source"] == sid, fig
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    assert (src["source_id"], src["canvas"], src["side"]) == (sid, canvas, side), fig
    assert src["image_url"].endswith(f"R{canvas:07d}/{src['crop_region']}/1600,/0/default.jpg"), fig
    assert src["crop_status"] == "unverified"
# 既定の姿（犬張子）と既定の出典は組
assert t.SOURCE == t.FIGURES[t.DEFAULTS["figure"]]["source"]
# 不明の 2 つは、名を作らず「不明（〜の形）」と書く
assert all(t.FIGURES[f]["title"].startswith("不明（") and t.FIGURES[f]["title"].endswith("形）") for f in ("fumei_tama", "fumei_tsutsu"))

# 場面の組: この雛形の場面は全部、姿と出典が PAIRS の組。姿ごとに正の場面が 1 本ある
scen = {}
for f in sorted((ROOT / "tests/frozen/scenarios").glob("stand_figure_*.json")):
    sc = json.loads(f.read_text(encoding="utf-8"))
    assert sc["template"] == "stand_figure", f.name
    fig = sc["params"]["figure"]
    if "F1.source" in sc["expect"]["floors"]:
        # 組の誤りを落とす負の場面だけは、わざと組でない。組でない事を確かめる
        assert sc["source_id"] != t.FIGURES[fig]["source"], f.name
        continue
    assert sc["source_id"] == t.FIGURES[fig]["source"], f"{f.name}: 姿 {fig} と出典 {sc['source_id']} が組でない"
    if sc["expect"]["rc"] == 0:
        scen[fig] = sc
assert set(scen) == set(t.FIGURES), sorted(set(t.FIGURES) - set(scen))

# 姿ごと: 外形は 1 つの多角形、勧める立て方と寸法で床に落ちず、配置まで通る。部品は部品表に載り、key は英小文字だけ
for fig, f in t.FIGURES.items():
    for stand in t.STANDS:
        p = {**P, "figure": fig, "stand": stand, **f.get("suggest", {})}
        g = t.geometry(p)
        assert g["body"].geom_type == "Polygon" and g["body"].is_valid and g["contacts"], fig
        assert abs(g["H"] - f["height"]) < 1e-6 and abs(g["body"].bounds[3] - g["H"]) < 1e-6, fig
        assert check_bom(t.bom(p), t.parts(p)) == [], (fig, stand)
        assert all(re.fullmatch(r"[a-z]+", q.key) for q in t.parts(p)), fig
    p = {**P, **scen[fig]["params"]}
    assert p["stand"] == f["stand"] and t.check_physics(p) == [], (fig, t.check_physics(p))
    _, layout, fails = compose("stand_figure", scen[fig]["params"], json.loads((ROOT / "data/sources" / f"{f['source']}.json").read_text(encoding="utf-8")))
    assert fails == [], (fig, [x.line() for x in fails])

# 裏の姿は表の左右を返した物（背中合わせに貼ると縁がそろう）
front, back = t.parts(P)[:2]
W = t.geometry(P)["W"]
assert Polygon(back.outline).symmetric_difference(Polygon([(W - x, y) for x, y in front.outline])).area < 1e-6
assert [q.key for q in t.parts({**P, "back": 0})] == ["front", "tab", "gauge"]

# 脚の三角: 付け根（姿の上、下の縁から s・後ろへ LEAN_DEG 傾く）と脚の先（床の上、奥行き c）の距離は脚の長さ、付け根の角は開きの角
e = t.easel(P)
lean = math.radians(t.LEAN_DEG)
hinge = (e["s"] * math.sin(lean), e["s"] * math.cos(lean))
foot = (e["c"], 0.0)
assert abs(math.dist(hinge, foot) - P["tab_length"]) < 1e-9
v1, v2 = (-hinge[0], -hinge[1]), (foot[0] - hinge[0], foot[1] - hinge[1])
ang = math.degrees(math.acos((v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2))))
assert abs(ang - P["tab_angle"]) < 1e-9
# 重心の奥行きは重心の高さ × sin(LEAN_DEG)
g = t.geometry(P)
assert abs(e["com"] - g["zc"] * math.sin(lean)) < 1e-9
# 後ろへ倒れる境: c − 重心の奥行き = 余白。境の少し上の脚は通り、少し下は「後ろへ倒れる」で落ちる
m = t.margin(g)
L0 = (e["com"] + m) * math.sin(math.radians(90 - t.LEAN_DEG)) / math.sin(math.radians(P["tab_angle"]))
assert t.check_physics({**P, "tab_length": L0 + 0.5}) == []
fs = t.check_physics({**P, "tab_length": L0 - 0.5})
assert [(f.floor, f.where) for f in fs] == [("F5.stand", "脚")] and "後ろへ倒れる" in fs[0].message, fs
# 余白は背が高いほど広い（同じ傾きで重心が大きく動く）
assert t.margin(t.geometry({**P, "scale": 1.4})) > m
# 開きの角が狭いと足の形が浅い（脚が同じ長さでも倒れる）
assert t.easel({**P, "tab_angle": 15})["c"] < e["c"]
# 糊代が姿の背に収まらない（犬の背より上まで届く長い脚）
fs = t.check_physics({**P, "tab_length": 70})
assert any("背に収まらない" in f.message for f in fs), fs
# 下の縁が細い物は、脚では横へ倒れる（羽子板の柄）
fs = t.check_physics({**P, "figure": "hagoita", "tab_length": 90, "tab_glue": 10})
assert any("横へ倒れる" in f.message for f in fs), fs

# 溝: 隙間 = 溝の幅 − 紙の厚み × 重ねた枚数。狭いと差せない、広いと傾きが MAX_WOBBLE を越える
B = {**P, "stand": "base"}
assert t.check_physics(B) == []
th = 2 * B["paper_thickness"]
assert t.wobble_deg({**B, "slot_width": th + t.MIN_CLEAR - 0.01}) is None
assert abs(t.wobble_deg({**B, "slot_width": th + 0.3}) - math.degrees(math.atan(0.3 / B["base_height"]))) < 1e-9
loose = th + B["base_height"] * math.tan(math.radians(t.MAX_WOBBLE)) + 0.05
assert any("ぐらつく" in f.message for f in t.check_physics({**B, "slot_width": loose}))
# 表だけ（back 0）なら紙 1 枚なので、2 枚では差せない溝にも入る
assert t.wobble_deg({**B, "slot_width": th}) is None and t.wobble_deg({**B, "back": 0, "slot_width": th}) is not None
# 舌は姿の下の縁と半分以上つながる。羽子板の柄（約 8.5mm）に既定の長い溝の舌は折れ、短い溝なら通る
assert any(f.where == "舌" for f in t.check_physics({**B, "figure": "hagoita"}))
assert t.check_physics({**B, "figure": "hagoita", "slot_length": 10}) == []
# 溝は箱の縁から SLOT_EDGE 内に収まる
assert any("縁まで" in f.message for f in t.check_physics({**B, "slot_length": B["base_length"] - 2 * t.SLOT_EDGE + 1}))
# 台が小さいと、重心が台の縁に近く倒れる
assert any(f.where == "台" for f in t.check_physics({**B, "base_depth": 15, "base_length": 30, "slot_length": 20, "scale": 1.5}))
# 舌の長さは箱の高さより短い（先が底に当たって、上へ押し上げない）
x, w, depth = t.tongue(B)
assert depth < B["base_height"] and abs(w - (B["slot_length"] - 2 * t.SLOT_END)) < 1e-9
# 台の箱の溝は上の面の真ん中、折り線は外形の中
net = t.base_net(B)
cx, cy = net.cuts[0][0] + net.cuts[0][2] / 2, net.cuts[0][1] + net.cuts[0][3] / 2
assert abs(cx - (B["base_height"] + B["base_length"] / 2)) < 1e-9 and abs(cy - (B["base_glue"] + B["base_depth"] / 2)) < 1e-9
from shapely.geometry import LineString
assert all(Polygon(net.outline).buffer(1e-6).contains(LineString([a, b])) for a, b in net.valley)
assert Polygon(net.outline).is_valid

# 範囲: back は 0 か 1、姿と立て方は一覧の値だけ
assert [f.floor for f in t.check_range({**P, "back": 0.5})] == ["F5.range"]
assert [f.floor for f in t.check_range({**P, "figure": "no_such"})] == ["F5.range"]
assert [f.floor for f in t.check_range({**P, "stand": "hang"})] == ["F5.range"]
# 形から出典を選ぶ表（SOURCES）は FIGURES の組と同じ。合わない出典は compose が F1.source で落とす
assert t.SOURCES == {k: f["source"] for k, f in t.FIGURES.items()}
_, _, fs = compose("stand_figure", {"figure": "uma", "stand": "easel"}, json.loads((ROOT / "data/sources" / f"{t.SOURCE}.json").read_text(encoding="utf-8")))
assert [f.floor for f in fs] == ["F1.source"], fs

# 倒れないかは脚の開き（足の形の奥行き c）で決まるので、開きの物差し（部品 4）を刷る。印の間は c、組み方の文も c を言う
gauge = next(q for q in t.parts(P) if q.key == "gauge")
ticks = sorted(a["pts"][0][1] for a in gauge.art if a["kind"] == "line")
assert abs((ticks[-1] - ticks[0]) - e["c"]) < 1e-9, ticks
assert any(f"{e['c']:.0f}mm" in s for s in t.steps(P)) and any("4" in s and "物差し" in s for s in t.steps(P))
assert "gauge" not in {q.key for q in t.parts(B)}
print("ok")
