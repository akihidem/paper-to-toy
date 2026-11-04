"""引いて振れて戻る族（pull_nod）の床 F5.pull_nod の式の要所を数点で確かめる。

なぜ数えるか: 戻る向き・振れる角度・穴の余白は、直す向きを言葉で決めると間違えやすい。場面の rc だけでは、
どの式の項が効いて落ちたかが見えないので、項ごとに境目の両側を置く。
"""
import math

from omochae.floors import check_bom
from omochae.templates import pull_nod as pn

bow = {**pn.DEFAULTS, "kind": "bow"}
jaw = {**pn.DEFAULTS, "kind": "jaw"}
peck = {**pn.DEFAULTS, "kind": "peck"}


def floors(p):
    return [f for f in pn.check_physics(p) if f.floor == "F5.pull_nod"]


# 既定はどちらの形も通り、部品表と部品が合う
for p in (bow, jaw, peck):
    assert pn.check_range(p) == [] and pn.check_physics(p) == [], (p["kind"], pn.check_physics(p))
    assert check_bom(pn.bom(p), pn.parts(p)) == [], p["kind"]

# 1. 戻る力: 尾の粘土が重いほど戻るモーメントが増え、軽いと体の紙に負けて負になる
m1, fr = pn.return_moment(bow)
m2, _ = pn.return_moment({**bow, "weight_g": 4.0})
assert m2 > m1 > pn.SAFETY * fr
m0, _ = pn.return_moment({**bow, "weight_g": 0.2})
assert m0 < 0 and any("戻らない" in f.message for f in floors({**bow, "weight_g": 0.2}))
# 体を前に長くすると紙の重心が前へ出て、戻るモーメントが減る（向きの確かめ）
assert pn.return_moment({**bow, "torso_len": 70})[0] < m1
# 顎は前（口が開く向き）が戻る向き。粘土を顎の先に付けるので正
assert pn.return_moment(jaw)[0] > 0
# 摩擦の境目: 戻るモーメントが摩擦の SAFETY 倍をちょうど超えない粘土の量で落ちる
card, x_card = pn.lever(bow)[0][0]
arm = bow["tail_len"] - pn.CLAY_IN
w_edge = (-card * x_card + pn.SAFETY * pn.MU * card * pn.AXLE_R) / (arm - pn.SAFETY * pn.MU * pn.AXLE_R)
assert floors({**bow, "weight_g": round(w_edge - 0.01, 3)}) and not floors({**bow, "weight_g": round(w_edge + 0.05, 3)})

# 2. 振れる角度: bow は頭の下の縁が臼の上まで下がる角度。臼が高いと浅い
assert abs(pn.swing_deg(bow) - math.degrees(math.asin((50 - 11 - 18) / 50))) < 1e-9
assert pn.swing_deg({**bow, "stop_height": 36}) < pn.MIN_SWING and floors({**bow, "stop_height": 36})
assert pn.swing_deg({**bow, "stop_height": 45}) == 0.0  # 臼が軸より高いと振れない
# jaw はこぶまでの隙間と舌の長さ。隙間が狭いと口が少ししか開かない
# 角度の式そのものは 5a で確かめる
assert [f.where for f in floors({**jaw, "stop_gap": 2})] == ["こぶ"]

# 3. 穴の縁の余白: 柱の幅の半分 − 穴の半径 が HOLE_MARGIN を割ると落ちる。境目の両側
assert not floors({**bow, "post_width": 2 * (pn.HOLE_MARGIN + pn.AXLE_R)})
assert floors({**bow, "post_width": 2 * (pn.HOLE_MARGIN + pn.AXLE_R) - 0.2})
# 舌が短いと、軸の穴と糸の穴の間が狭くなって落ちる（隣の穴までの余白も見る）
assert any(f.where == "下顎" for f in floors({**jaw, "tab_len": 8}))
# 糸の腕は舌の長さから穴の置き場を引いた物で、引く力の見込みは腕が長いほど小さい
assert pn.jaw_string_arm(jaw) == jaw["tab_len"] - (pn.HOLE_MARGIN + pn.STRING_R + 0.5)
assert pn.pull_gf({**bow, "string_arm": 30}) < pn.pull_gf(bow)

# 4. peck（藁苞の鶏）: 傾く角度は、輪郭の頂点が苞の上の面に届く角度の最小。腹が低い（leg_h が小さい）ほど浅い
sw = [pn.bird_swing({**peck, "leg_h": h}, "cock") for h in (1, 2, 4, 10)]
assert sw == sorted(sw) and sw[0] < pn.MIN_SWING <= sw[1], sw
assert [f.where for f in floors({**peck, "leg_h": 1})] == ["奥の鶏"]  # 手前の鶏は縮めた分だけ深く傾ける（16.3°）
# 尾の先が苞の上の面にあり（静かな時の後ろの止め）、粘土は軸より後ろ＝戻る向き
b = pn.bird(peck, "cock")
assert abs(max(y for x, y in b["body"].exterior.coords) - b["H"]) < 1e-9 and b["clay"][0] > b["pivot"][0]
assert pn.bird_moment(peck, "cock")[0] > pn.bird_moment({**peck, "weight_g": 1.0}, "cock")[0] > 0
# 胸の糸の穴を前へ出しすぎると、斜めの胸の縁に近づいて落ちる
assert {f.where for f in floors({**peck, "peck_arm": 12})} == {"奥の鶏", "手前の鶏"}
# 苞が浅いと脚の帯が底に当たる
assert [f.where for f in floors({**peck, "straw_h": 14, "axle_depth": 8})] == ["藁苞"]
# 溝は傾く分だけ前へ長い。2 羽の溝は重ならない
(a0, al), (b0, bl) = pn._slots(peck)
assert al > pn.TAB_W + 2 and a0 + al < b0

# 5. レビューの指摘（2026-11-04）を押さえる
# 5a. 顎の止め: 舌の端の上の角は軸のまわりを回るので、上がる高さは sin で頭打ちになる。こぶが舌の届く高さより上なら、止めに当たらない
assert floors({**jaw, "stop_gap": 20}), "舌が届かない高さのこぶを通した"
assert [f.where for f in floors({**jaw, "stop_gap": 20})] == ["こぶ"] and "届かない" in floors({**jaw, "stop_gap": 20})[0].message
h2 = jaw["jaw_h"] / 2
rho, phi = math.hypot(jaw["tab_len"], h2), math.atan2(h2, jaw["tab_len"])
assert abs(pn.swing_deg(jaw) - math.degrees(math.asin((h2 + jaw["stop_gap"]) / rho) - phi)) < 1e-9
# 5b. こぶは 3 面と、三角の柱を閉じる糊代の 4 つ。最後の面を頭に貼る面にすると、柱が閉じない
bump = next(q for q in pn.parts(jaw) if q.key == "bump")
assert len(bump.valley) == 3 and len(bump.glue) == 1 and bump.glue[0][0][0] >= 3 * 8, (bump.valley, bump.glue)
# 5c. 串の抜け止めの粘土は、重り（式の weight_g）と別の行。同じ粘土から取ると、顎に付く量が式より減る
for p in (jaw, peck):
    keys = [r["key"] for r in pn.bom(p)]
    assert "stopclay" in keys, (p["kind"], keys)
    weight = next(r for r in pn.bom(p) if r["key"] == "weight")
    assert f"{p['weight_g']:g}g" in weight["material"]
    assert any("抜け止め" in m for m in pn.materials(p))
# 5d. 形ごとの出典
assert pn.SOURCES == {"bow": pn.SOURCE, "jaw": "NDL-1187053-R0000030-L-pull_nod", "peck": "NDL-1187053-R0000016-R-pull_nod"}

# 形ごとの部品の key は英小文字だけ、部品表の番号と合う
for p in (bow, jaw, peck):
    assert {q.number: q.key for q in pn.parts(p)} == {r["number"]: r["key"] for r in pn.bom(p) if r["number"] < 7}

print(round(pn.swing_deg(bow), 1), round(pn.swing_deg(jaw), 1), round(pn.bird_swing(peck, 'cock'), 1), round(pn.pull_gf(bow)), round(pn.pull_gf(jaw)), round(pn.pull_gf(peck)))
print("ok")
