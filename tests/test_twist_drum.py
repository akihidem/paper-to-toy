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
assert abs(high - (math.sqrt(2) * P["radius"] - P["stick_d"] / 2 - P["bead_d"] / 2)) < 1e-9
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
assert {q.key for q in t.parts(K)} == {"front", "back", "band", "post", "base", "wheel", "rodtab", "gauge"}
assert {r["key"] for r in t.bom(K)} >= {"peg", "rod", "pull", "cord", "bead"}
from omochae.floors import check_bom
assert check_bom(t.bom(K), t.parts(K)) == []

# ---- レビューの指摘（2026-11-04）を押さえる行 ----
import re
# 1. 玉は点でない。結び目から面までの軸の向きの距離は、奥行きの半分＋玉の半径（玉の表が面に触れる時、中心は面の外に半径だけ出る）。
#    下限ちょうどの糸は、その中心の位置で半径の半分の所を打つ。既定の寸法で下限は √(13² + (9 + 4)²) ≒ 18.4mm
low, _ = t.cord_window(P)
assert abs(low - math.hypot(P["radius"] / 2, P["depth"] / 2 + P["bead_d"] / 2)) < 1e-9, low
assert t.check_physics({**P, "cord_length": 17}) != [], "玉の半径を入れると 17mm では面の真ん中に届かない"
#    諫鼓は玉が軸の側から面へ近づくので、軸から面までの距離から玉の半径を引く（向きが逆で、引くのが正しい）
assert abs(t.wheel_anchor(K) + t.kanko_window(K)[0] - (K["face_gap"] - K["bead_d"] / 2)) < 1e-9
# 2. 鳥の面: 幣の房の上の帯（STREAMER_TOP）を、胴の上に出た竹串に巻いて貼れるだけ、串を上へ出す
tori = {**P, "face": "tori"}
out_mm = [float(m) for s in t.steps(tori) for m in re.findall(r"上へ (\d+(?:\.\d+)?)mm 出す", s)]
assert out_mm and out_mm[0] >= t.STREAMER_TOP, (out_mm, t.STREAMER_TOP)
#    串を長く出す分も、竹串の長さの床で数える
need = P["handle_length"] + 2 * P["radius"] + out_mm[0]
assert any(f.where == "柄" for f in t.check_physics({**tori, "handle_length": math.floor(t.SKEWER_LEN - 2 * P["radius"] - out_mm[0]) + 1}))
# 3. 柄に絡まない条件は厳密に L + 玉の半径 < √2·R。等しい糸（柄にちょうど届く）は落とす
edge = math.sqrt(2) * P["radius"] - P["stick_d"] / 2 - P["bead_d"] / 2
assert any(f.where == "糸" for f in t.check_physics({**P, "cord_length": edge})), "柄にちょうど届く糸を通した"
# 4. 刷る形ごとの出典。既定の SOURCE は菊の面
assert t.SOURCES == {"kiku": t.SOURCE, "tori": "NDL-1187053-R0000029-L-twist_drum", "kanko": "NDL-1187053-R0000010-R-twist_drum"}
# ---- 2 回目のレビューの指摘（2026-11-04）を押さえる行 ----
def nums(text, pat):
    return [float(m) for m in re.findall(pat, text)]
# 5. 花車の高さは、式と見取り図と同じく台の上の面から測る。組み方の文の数・物差しの紙・軸の竹串の長さが同じ基準で合う
st = " ".join(t.steps(K))
assert nums(st, r"台の上の面から (\d+(?:\.\d+)?)mm") == [K["peg_height"]], st
top = nums(st, r"軸の上の端からは (\d+(?:\.\d+)?)mm 下")[0]
cut = nums(next(r for r in t.bom(K) if r["key"] == "peg")["material"], r"長さ (\d+(?:\.\d+)?)mm")[0]
assert cut == K["base_height"] + K["peg_height"] + top, (cut, top)
assert {q.key: q for q in t.parts(K)}["gauge"].height == K["peg_height"]
# 6. 柄の竹串を切る長さ ＝ 柄 ＋ 胴の直径 ＋ 胴の上。組み方の文と部品表が同じ値で、巻き紙は柄より 2mm 短い
for face in ("kiku", "tori"):
    p = {**P, "face": face}
    c = P["handle_length"] + 2 * P["radius"] + t.top_out(p)
    assert nums(" ".join(t.steps(p)), r"竹串を (\d+(?:\.\d+)?)mm に切る") == [c], face
    assert f"{c:g}mm に切る" in next(r for r in t.bom(p) if r["key"] == "stick")["material"]
    assert t.wrap_size(p)[1] == P["handle_length"] - 2
# 7. 棒の切り欠きは刷る留め具に置き換え、結ぶ所を棒の北の端からの長さで決める（押し込んだ時に軸の真横）
assert "切り欠き" not in st
assert nums(st, r"棒の北の端から (\d+(?:\.\d+)?)mm") == [t.rodtab_pos(K)] and t.rodtab_pos(K) == t.rod_north_out(K) + t.peg_pos(K) - t.TAB_W / 2
tab = {q.key: q for q in t.parts(K)}["rodtab"]
assert abs(tab.width - (t.rod_perimeter(K) + 2 * t.TAB_FLAG)) < 1e-9 and len(tab.holes) == 2
#    引ける長さで軸が 1 回も回らない寸法は落とす
assert t.pull_turns(K) >= 1 and any(f.where == "棒" for f in t.check_physics({**K, "base_length": 70}))
# ---- 3 回目のレビューの指摘（2026-11-04）を押さえる行 ----
# 8. 諫鼓で、糸が玉の半径より短いと玉が花車に重なる（窓の式だけでは通っていた寸法）
bad = {**K, "k_radius": 24, "face_gap": 10, "wheel_r": 8, "bead_d": 14, "k_cord": 3}
assert [f.where for f in t.check_physics(bad)] == ["糸"], [f.line() for f in t.check_physics(bad)]
# 9. 引き切っても棒の北の端が北の壁の穴に HOLE_MARGIN 残る。回る数はこの引ける長さで数える
#    （北に出す長さが引ける長さ＋余白か、は式そのものなので見ない。代わりに、棒が竹串の長さに収まるかを見る）
assert t.rod_length(K) <= t.SKEWER_USABLE
assert abs(t.pull_turns(K) - t.pull_travel(K) / (math.pi * K["stick_d"])) < 1e-9
assert nums(" ".join(t.steps(K)), r"北の壁から (\d+(?:\.\d+)?)mm 出す") == [round(t.rod_north_out(K))]
# 10. 柄の太さの分、絡む長さは短い（柄の表まで √2·R − 柄の半径）
assert any(f.where == "糸" for f in t.check_physics({**P, "cord_length": math.sqrt(2) * P["radius"] - P["bead_d"] / 2 - P["stick_d"] / 2 + 0.5}))
# 11. 諫鼓の窓は両端を含む。花車の高さのずれが kR ちょうどでも、下限＝上限の 1 点の糸は通る
edge = {**K, "peg_height": 47}
lo, hi, dz = t.kanko_window(edge)
assert dz == t.STRIKE_ZONE * K["k_radius"] and hi is not None and abs(hi - lo) < 1e-9
assert t.check_physics({**edge, "k_cord": lo}) == []
# ---- 4 回目のレビューの指摘（2026-11-05）を押さえる行 ----
# 12. 引く棒が竹串（SKEWER_LEN）より長くなる寸法は落とす（台が長いと、北に出す分も伸びる）
bad = {**K, "base_length": 100, "face_gap": 14, "k_cord": 5.8}
assert [f.where for f in t.check_physics(bad)] == ["棒"], [f.line() for f in t.check_physics(bad)]
# 13. 端数の出る寸法でも、刷る 3 つの数（北に出す長さ・留め具の位置・棒の長さ）は 1 つの丸めた値から出て食い違わない。
#     北に出す長さは切り上げるので、引き切っても余白が残る
odd = {**K, "base_length": 79.6, "k_length": 43}
st = " ".join(t.steps(odd))
north = nums(st, r"北の壁から (\d+(?:\.\d+)?)mm 出す")[0]
tabp = nums(st, r"棒の北の端から (\d+(?:\.\d+)?)mm")[0]
rod = nums(next(r for r in t.bom(odd) if r["key"] == "rod")["material"], r"長さ (\d+(?:\.\d+)?)mm")[0]
assert north == int(north) and north - t.pull_travel(odd) >= t.HOLE_MARGIN
assert abs(tabp - (north + t.peg_pos(odd) - t.TAB_W / 2)) < 1e-9 and abs(rod - (north + odd["base_length"] + t.ROD_GRIP)) < 1e-9
# 14. 玉が花弁の先にちょうど触れる糸も落とす（柄に絡む側と同じ厳しさ）
eq = {**K, "k_cord": K["bead_d"] / 2 + (K["wheel_r"] - t.wheel_anchor(K))}
assert any("花車に重なる" in f.message for f in t.check_physics(eq))
# ---- 5 回目のレビューの指摘（2026-11-05）を押さえる行 ----
# 15. 刷る位置は留め具の北の縁。引ける長さは、押し込んだ時の南の縁から旗が南の壁に当たるまで。北に出す分はその先に余白を残す
st = " ".join(t.steps(K))
x = nums(st, r"棒の北の端から (\d+(?:\.\d+)?)mm の所に、16 棒の留め具の北の縁")[0]
north = nums(st, r"北の壁から (\d+(?:\.\d+)?)mm 出す")[0]
assert abs(t.pull_travel(K) - (K["base_length"] - (x - north + t.TAB_W))) < 1e-9
assert north - t.pull_travel(K) >= t.HOLE_MARGIN
assert abs((x - north + t.TAB_W / 2) - t.peg_pos(K)) < 1e-9, "旗の穴（留め具の真ん中）が軸の真横に来ない"
# 16. 旗は棒の上に立ち、台の天井の下に収まる。巻いた留め具は横の軸から 1mm 以上離れる
H, d = K["base_height"], K["stick_d"]
assert H / 2 + d + t.TAB_FLAG <= H - 0.5 and t.rod_off(K) - d - 2 * K["paper_thickness"] >= 1
assert [f.where for f in t.check_physics({**K, "base_height": 13})] == ["留め具"]
# 17. 竹串のとがった先を切り落とす手順（道具・大人がする）が、どの形にもある。切り落とした分、使える長さは短い
for p in (P, {**P, "face": "tori"}, K):
    st = " ".join(t.steps(p))
    assert "とがった先" in st and "切り落とす" in st and "大人がする" in st and "ニッパー" in st, p["face"]
    assert any("ニッパー" in m for m in t.materials(p))
assert t.SKEWER_USABLE == t.SKEWER_LEN - 2 * t.SKEWER_POINT and t.stick_cut(P) <= t.SKEWER_USABLE
# 18. 柱の足の印は、黒い閉じた四角（切る線に見える）でなく、茶色のかぎの印
marks = [a for a in {q.key: q for q in t.parts(K)}["base"].art if a["kind"] == "line"]
assert len(marks) == 4 and all(a["stroke"] == t.BAND and len(a["pts"]) == 3 for a in marks)
# 19. 諫鼓の用意する物にカッターとテープ、組み方に棒を切って束ねる手順がある（長さは部品表と同じ式）
m = " ".join(t.materials(K))
assert "カッター" in m and "テープ" in m
assert nums(" ".join(t.steps(K)), r"竹串 2 本を (\d+(?:\.\d+)?)mm に切り") == [t.rod_length(K)]
print("ok")
