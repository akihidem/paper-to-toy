"""でんでん太鼓の床（F5.drum）の式の要所を数点で確かめる。糸の長さの窓と帯の長さは言葉で決めると間違えやすいので、ここで数える。"""
import math

from omochae.compose import TEMPLATES
from omochae.templates import twist_drum as t

P = dict(t.DEFAULTS)
assert TEMPLATES["twist_drum"] is t, "templates/ に置けば登録される"
assert t.check_physics(P) == [] and not t.check_range(P)

# 帯の長さ ＝ 円周（厚みの真ん中）＋ 継ぎ目の糊代。刷る帯の外形の長さも同じ値
band = next(q for q in t.parts(P) if q.key == "band")
c = 2 * math.pi * (P["radius"] - P["paper_thickness"] / 2)
assert abs(band.width - (c + P["seam_glue"])) < 1e-9 and abs(t.band_length(P) - band.width) < 1e-9
# 歯の間隔を全部足すと円周になる（歯が円周を余さず覆う）
n, pitch, inset = t.tab_teeth(P)
assert abs(n * pitch - c) < 1e-9 and pitch - 2 * inset > 1

# 糸の窓: 下限ちょうどの糸は、面の中心から半径の半分の所を打つ
low, high = t.cord_window(P)
assert abs(t.strike_offset({**P, "cord_length": low}) - t.STRIKE_ZONE * P["radius"]) < 1e-9
# 既定の寸法では、上限は柄に絡む側（√2·R − 玉の半径）で決まる
assert abs(high - (math.sqrt(2) * P["radius"] - P["bead_d"] / 2)) < 1e-9
# 窓の内は通り、外は F5.drum の糸で落ちる
assert t.check_physics({**P, "cord_length": (low + high) / 2}) == []
for bad in (low - 0.5, high + 0.5):
    fs = t.check_physics({**P, "cord_length": bad})
    assert [(f.floor, f.where) for f in fs] == [("F5.drum", "糸")], fs
# 玉が大きいほど絡みやすい（上限が下がる）
assert t.cord_window({**P, "bead_d": 12})[1] < high
# 奥行きの半分に届かない糸は面に届かない
assert t.strike_offset({**P, "cord_length": P["depth"] / 2}) is None

# 柄の穴は帯の幅の真ん中。縁までの余白が足りないと落ちる
fs = t.check_physics({**P, "depth": 10, "stick_d": 5})
assert any(f.where == "柄の穴" and "帯の縁" in f.message for f in fs), fs
# 柄の穴は継ぎ目の糊代に重ならない（小さい鼓に広い糊代）
fs = t.check_physics({**P, "radius": 15, "seam_glue": 12, "depth": 10, "cord_length": 12})
assert any("継ぎ目" in f.message for f in fs), fs
# 穴は帯の中、柄の穴どうしは円周の半分（向かい合う）、糸の穴は柄から 90°
pos = t.hole_positions(P)
assert abs((pos["stick"][1] - pos["stick"][0]) - c / 2) < 1e-9 and abs((pos["cord"][0] - pos["stick"][0]) - c / 4) < 1e-9

# 竹串の長さが足りないと落ちる
fs = t.check_physics({**P, "handle_length": 130})
assert any(f.where == "柄" for f in fs), fs

# 鳥の面だけ幣の房があり、部品表にも載る
assert "streamer" in {q.key for q in t.parts({**P, "face": "tori"})}
assert "streamer" not in {q.key for q in t.parts(P)}
assert {r["key"] for r in t.bom({**P, "face": "tori"})} >= {"streamer", "stick", "cord", "bead"}

# ---- 諫鼓（face=kanko）----
K = {**P, "face": "kanko"}
assert t.check_physics(K) == [], t.check_physics(K)
# 帯の長さは諫鼓の半径から出し、柱の四角い穴は帯の幅の真ん中・継ぎ目の向かいにある
kb = next(q for q in t.parts(K) if q.key == "band")
kc = 2 * math.pi * (K["k_radius"] - K["paper_thickness"] / 2)
assert abs(kb.width - (kc + K["seam_glue"])) < 1e-9 and kb.holes == [] and len(kb.cuts) == 1
x, y, w, h = kb.cuts[0]
assert abs(x + w / 2 - kc / 2) < 1e-9 and abs(y + h / 2 - (K["tab"] + K["k_length"] / 2)) < 1e-9
# 窓: 下限ちょうどで、玉の表が面に触れる（軸から玉の中心まで face_gap − 玉の半径）
low, high, dz = t.kanko_window(K)
assert abs(t.wheel_anchor(K) + low - (K["face_gap"] - K["bead_d"] / 2)) < 1e-9 and dz == 0
# 上限ちょうどで、打つ点のずれが STRIKE_ZONE·R になる
rho, g = t.wheel_anchor(K) + high, K["face_gap"] - K["bead_d"] / 2
assert abs(math.sqrt(rho * rho - g * g) - t.STRIKE_ZONE * K["k_radius"]) < 1e-9
# 花車が鼓の中心の高さからずれるほど窓が狭まり、kR を越えると無くなる
assert t.kanko_window({**K, "peg_height": K["peg_height"] + 5})[1] < high
assert t.kanko_window({**K, "peg_height": 20})[1] is None
for bad in (low - 0.5, high + 0.5):
    fs = t.check_physics({**K, "k_cord": bad})
    assert [(f.floor, f.where) for f in fs] == [("F5.drum", "糸")], fs
# 花車が面に近すぎる・軸が台から出る・壁が低くて棒の穴が取れない
assert any(f.where == "花車" for f in t.check_physics({**K, "wheel_r": 16, "face_gap": 17, "k_cord": 3}))
assert any(f.where == "軸" for f in t.check_physics({**K, "base_length": 60}))
assert any(f.where == "棒の穴" for f in t.check_physics({**K, "base_height": 10}))
# 諫鼓の部品と部品表（紙でない物も）が合う
assert {q.key for q in t.parts(K)} == {"front", "back", "band", "post", "base", "wheel"}
assert {r["key"] for r in t.bom(K)} >= {"peg", "rod", "pull", "cord", "bead"}
from omochae.floors import check_bom
assert check_bom(t.bom(K), t.parts(K)) == []
print("ok")
