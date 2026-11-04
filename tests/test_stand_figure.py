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
P = t.filled(dict(t.DEFAULTS))
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
# 台の形は覆面の人形（勧めの値）で見る。犬張子は重心が腹の下（足の無い所）にあり、台では舌が重心の下に来ないので脚で立てる
B = t.filled({**t.DEFAULTS, "figure": "fukumen"})
assert B["stand"] == "base" and t.check_physics(B) == []
assert any("ねじれる" in f.message for f in t.check_physics(t.filled({**P, "stand": "base", "slot_length": 12})))
# 舌が 2 つの足にまたがると、足の間が舌と胴で囲まれて紙で埋まる。黙って埋めず「またぐ」で落とす。部品は落ちた寸法でも返る（check_bom が呼ぶ）
fs = t.check_physics(t.filled({**P, "stand": "base", "slot_length": 30}))
assert any(f.where == "舌" and "またがり" in f.message for f in fs), fs
front_web = next(q for q in t.parts(t.filled({**P, "stand": "base", "slot_length": 30})) if q.key == "front")
assert Polygon(front_web.outline).is_valid and not Polygon(front_web.outline).interiors
th, tp = 2 * B["paper_thickness"], B["paper_thickness"]
# 差せるかは狭く切れた側で見る: 隙間が MIN_CLEAR（毛羽 0.1mm ＋ 狭い側のずれ 2·CUT_TOL）に足りないと差せない
assert abs(t.MIN_CLEAR - (0.1 + 2 * t.CUT_TOL)) < 1e-9
assert t.wobble_deg({**B, "slot_width": th + t.MIN_CLEAR - 0.01}) is None
# 溝は手で帯を切り取れる幅（1mm 以上）で、隙間の下限は切るずれを含む。組み方は「帯を切り取る」と言う
assert t.RANGES["slot_width"][0] >= 1.0 and t.MIN_CLEAR >= 0.4
assert any("帯" in s and "切り取る" in s and "1 本の切れ目にしない" in s for s in t.steps(B))
# 表だけ（back 0）なら紙 1 枚なので、2 枚では差せない溝にも入る
narrow = th + t.MIN_CLEAR - 0.1
assert t.wobble_deg({**B, "slot_width": narrow}) is None and t.wobble_deg({**B, "back": 0, "slot_width": narrow}) is not None

# 2 つの高さで挟む前提を、展開図と舌の形から確かめる
from shapely.geometry import LineString
net = t.base_net(B)
assert len(net.cuts) == 2 and Polygon(net.outline).is_valid
assert all(Polygon(net.outline).buffer(1e-6).contains(LineString([a, b])) for a, b in net.valley)
Hb, D, g0 = B["base_height"], B["base_depth"], B["base_glue"]
Y2, Y3 = g0 + D, g0 + D + Hb
(tx, ty, tw_, th_), (bx, by, bw, bh_) = sorted(net.cuts, key=lambda c: c[1])
# 閉じると、上の面（後ろの壁の上の縁 Y2 で倒す）の奥行きは Y2 − y、底の面（後ろの壁の下の縁 Y3 から）の奥行きは y − Y3。上下の溝がそろう
assert abs((Y2 - (ty + th_ / 2)) - ((by + bh_ / 2) - Y3)) < 1e-9 and abs(tx - bx) < 1e-9 and (tw_, th_) == (bw, bh_)

# 舌の先が底の溝を抜けて机に届く事を、刷る外形から見る: 刷った舌は 箱の高さ + TONGUE_EXTRA で tongue() と同じ長さ。
# TONGUE_EXTRA > BOX_TOL なので、箱が BOX_TOL 高く折れても先が机に着き、姿の下の縁は上の面から浮く（縁が面に乗ると先が浮いて、上の溝 1 つの形になる）。
# この関係は寸法に依らないので check_physics には無く、ここで定数として見る
front = next(q for q in t.parts(B) if q.key == "front")
H = t.geometry(B)["H"]
reach = max(y for _, y in front.outline) - H  # 刷った舌の、姿の下の縁から下の長さ
assert abs(reach - (Hb + t.TONGUE_EXTRA)) < 1e-9 and abs(t.tongue(B)[2] - reach) < 1e-9, reach
assert t.TONGUE_EXTRA > t.BOX_TOL and reach > Hb + t.BOX_TOL
# 傾きの上限を、紙の厚み th の板が 2 枚の紙の溝（広く切れた幅 sw + 2·CUT_TOL。真ん中の高さ tp/2 と Hb − BOX_TOL − tp/2）を通る形から
# 数で解き、式（wobble_deg）と比べる。式を式で確かめないため
def max_tilt(z1, z2, sw, thick):
    lo, hi = 0.0, math.pi / 2 - 1e-6
    for _ in range(60):  # 板の両の面が、2 つの溝の縁の内に収まる一番大きい傾き
        a = (lo + hi) / 2
        span = thick / math.cos(a) + (z2 - z1) * math.tan(a)
        lo, hi = (a, hi) if span <= sw else (lo, a)
    return math.degrees(lo)
sw = B["slot_width"]
assert abs(max_tilt(tp / 2, Hb - t.BOX_TOL - tp / 2, sw + 2 * t.CUT_TOL, th) - t.wobble_deg(B)) < 0.1, (max_tilt(tp / 2, Hb - t.BOX_TOL - tp / 2, sw + 2 * t.CUT_TOL, th), t.wobble_deg(B))
# 上の溝 1 つだけ（紙 1 枚の厚みの間で挟む）では、ほぼ倒れる。底の溝が要る理由
assert max_tilt(0, tp, sw, th) > 45
# 緩い溝の境: 広く切れた側と低く折れた箱で MAX_WOBBLE を越える幅で落ち、少し狭い幅で通る
loose = th + (Hb - t.BOX_TOL - tp) * math.tan(math.radians(t.MAX_WOBBLE)) - 2 * t.CUT_TOL + 0.05
assert any("ぐらつく" in f.message for f in t.check_physics({**B, "slot_width": loose}))
assert t.check_physics({**B, "slot_width": loose - 0.1}) == []
# 切るずれ・折るずれを見ない時の上限の少し内（前の式なら通る幅）でも、今の式では落ちる
gap_ok = (Hb - tp) * math.tan(math.radians(t.MAX_WOBBLE)) - 0.05
assert any("ぐらつく" in f.message for f in t.check_physics({**B, "slot_width": th + gap_ok}))
# 姿だけを変えた既定（勧めの値）は、どの台の姿も、溝が広く切れて箱が低く折れた側で通る（compose の試験で 35 とも通る）
for fig, f in t.FIGURES.items():
    if f["stand"] == "base":
        assert t.wobble_deg(t.filled({**t.DEFAULTS, "figure": fig})) <= t.MAX_WOBBLE, fig
# 溝の長さの下限（RANGES）は、舌の幅（溝 − 2·SLOT_END）から両側の余白 MIN_MARGIN を引いても窓が残る長さ。
# 短いと、重心が舌の真ん中にぴたり来る姿しか横の検査を通らない。下限の溝でも、重心が真ん中に来る姿（覆面の人形）は通る
assert t.RANGES["slot_length"][0] - 2 * t.SLOT_END - 2 * t.MIN_MARGIN > 0
assert t.check_physics({**B, "slot_length": t.RANGES["slot_length"][0]}) == [], t.check_physics({**B, "slot_length": t.RANGES["slot_length"][0]})
# 倒れるかは、軸（舌の先・机の上）から測る。低い亀でも、高い箱で奥行きが浅いと落ちる（姿の下の縁から測ると通っていた）
K = t.filled({**P, "figure": "tsuchi_kame", "stand": "base", "base_depth": 15, "base_height": 30, "slot_width": 2.9})
assert any(f.where == "台" for f in t.check_physics(K)), t.check_physics(K)
# 横: 姿の下の縁は浮くので、横に支えるのは舌の幅だけ。重心が余白 MIN_MARGIN を持って舌の幅に入らないとねじれる
# 犬張子を台に: 舌は前の足の下までしか寄れず、重心（腹の下）が舌の幅の外
S = t.filled({**P, "stand": "base", "slot_length": 12})
xs, ws, _ = t.tongue(S)
assert not (xs - ws / 2 + t.MIN_MARGIN <= t.geometry(S)["cx"] <= xs + ws / 2 - t.MIN_MARGIN)
assert t.check_physics(t.filled({**t.DEFAULTS, "figure": "shitadashi"})) == []
# 余白の境: 重心がちょうど舌の端にある（余白 0）と落ちる。千木箱の既定では、重心は舌の幅の内に余白を持つ
C = t.filled({**t.DEFAULTS, "figure": "chigibako"})
xc, wc, _ = t.tongue(C)
assert xc - wc / 2 + t.MIN_MARGIN <= t.geometry(C)["cx"] <= xc + wc / 2 - t.MIN_MARGIN
# 舌は姿の下の縁と半分以上つながる。羽子板の柄（約 8.5mm）に既定の長い溝の舌は折れ、短い溝なら通る
assert any(f.where == "舌" for f in t.check_physics({**B, "figure": "hagoita", "slot_length": 30}))
assert t.check_physics(t.filled({**t.DEFAULTS, "figure": "hagoita"})) == []
# 溝は箱の縁から SLOT_EDGE 内に収まる
assert any("縁まで" in f.message for f in t.check_physics({**B, "slot_length": B["base_length"] - 2 * t.SLOT_EDGE + 1}))
# 台が小さいと、重心が台の縁に近く倒れる
assert any(f.where == "台" for f in t.check_physics({**B, "base_depth": 15, "base_length": 30, "slot_length": 20, "scale": 1.5}))
# 脚の横の位置（重心の真後ろ）を組み方で言う（裏の印が無い時）
assert any(f"左の端から {t.geometry(P)['cx']:.0f}mm" in s for s in t.steps({**P, "back": 0}))

# 範囲: back は整数の 0 か 1（true/false・1.0 はほかの寸法と同じく型で落とす）、姿と立て方は一覧の値だけ
assert [f.floor for f in t.check_range({**P, "back": 0.5})] == ["F5.range"]
assert all([f.where for f in t.check_range({**P, "back": b})] == ["back"] for b in (True, False, 1.0, 0.0, 2))
assert t.check_range({**P, "back": 0}) == [] and t.check_range({**P, "back": 1}) == []
assert [f.floor for f in t.check_range({**P, "stand": "hang"})] == ["F5.range"]
# 知らない姿は、埋まらなかった既定（stand の None）を重ねて落とさず、姿の名の誤り 1 つだけで落とす（埋める前の DEFAULTS で見る）
assert [f.where for f in t.check_range({**t.DEFAULTS, "figure": "no_such"})] == ["figure"]
# 台の糊代は壁の高さ − 1mm まで（高いと展開図で隣の糊代と重なる）。溝の傾きが通る高さ 12（紙 0.25mm で隙間を詰める）で、糊代だけを変えて見る
G = {**B, "base_height": 12, "paper_thickness": 0.25}
assert any(f.where == "台" and "収まらない" in f.message for f in t.check_physics({**G, "base_glue": 12}))
assert t.check_physics({**G, "base_glue": 11}) == [], t.check_physics({**G, "base_glue": 11})
# 狭い脚（RANGES の下限 6mm）では札を番号だけにし、札が脚からはみ出して別の検査で落ちない
narrow_src = json.loads((ROOT / "data/sources" / f"{t.SOURCE}.json").read_text(encoding="utf-8"))
_, _, fs = compose("stand_figure", {"figure": "inu", "tab_width": t.RANGES["tab_width"][0]}, narrow_src)
assert fs == [], [x.line() for x in fs]
assert next(q.label for q in t.parts({**P, "tab_width": 6}) if q.key == "tab") == "3"
assert next(q.label for q in t.parts(P) if q.key == "tab") == "3 脚"
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

# 姿だけを変えた入口（--params {"figure": X}）でも、その姿に勧める立て方と寸法が既定になって通る。書いた寸法は勝つ
for fig, f in t.FIGURES.items():
    src = json.loads((ROOT / "data/sources" / f"{f['source']}.json").read_text(encoding="utf-8"))
    p, _, fails = compose("stand_figure", {"figure": fig}, src)
    assert fails == [], (fig, [x.line() for x in fails])
    assert t.filled(p)["stand"] == f["stand"] and all(t.filled(p)[k] == v for k, v in f.get("suggest", {}).items()), fig
assert t.filled({**P, "figure": "hagoita", "slot_length": 30})["slot_length"] == 30
assert t.filled({**P, "figure": "hagoita", "stand": "easel"})["stand"] == "easel"
assert t.spec()["figures"]["hagoita"]["stand"] == "base" and t.spec()["figures"]["hagoita"]["slot_length"] == t.FIGURES["hagoita"]["suggest"]["slot_length"]

# 姿の形の覚えは上限つき（高さは連続の値なので、上限が無いと場面を回すほど増える）
assert t._shape.cache_info().maxsize is not None
print("ok")
