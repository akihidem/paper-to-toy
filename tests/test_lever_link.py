"""紙の棒と人形の仕掛け（F5.link）の床の式の要所を数点で確かめる。角や長さは言葉で決めると間違えやすいので、ここで数える。"""
import math

from shapely.geometry import Point, box

from omochae.compose import TEMPLATES
from omochae.floors import check_bom
from omochae.templates import lever_link as t

P = dict(t.DEFAULTS)
assert TEMPLATES["lever_link"] is t, "templates/ に置けば登録される"
# どの形も既定の寸法で床を通り、部品表に刷る部品が全部載る
for k in t.KINDS:
    q = {**P, "kind": k}
    assert not t.check_range(q) and t.check_physics(q) == [], (k, t.check_physics(q))
    assert check_bom(t.bom(q), t.parts(q)) == [], k
    assert t.SOURCES[k].startswith("NDL-1187053-R") and t.SOURCES[k].endswith("-lever_link")

# 押す形: 膝を接線の向きに押すと、角は asin(押す量 / 腕)
sumo = t.motion(P)
assert abs(sumo["input_angle"] - math.degrees(math.asin(P["travel"] / P["drive_arm"]))) < 0.15, sumo
# 腕より長く押すと死点を越える（どの角でも届かない）
assert t.push_angle((0, 0), (0, 30), (-1, 0), 31, 1) is None
fs = t.check_physics({**P, "travel": 32, "slot_len": 40})
assert [f.floor for f in fs] == ["F5.link"] and "死点" in fs[0].message, fs
# 振れが 15° に届かない押す量で落ちる（asin(s/30) < 15° は s < 7.76）
assert t.check_physics({**P, "travel": 7.9}) == []
fs = t.check_physics({**P, "travel": 7.6})
assert [f.where for f in fs] == ["B の足"], fs

# 溝: ピンの中心が動ける長さ ＝ 溝の長さ − 穴の直径。これが押し合う量より短いと落ちる
r = t.pin_r(P)
edge = P["travel"] + 2 * r
assert t.check_physics({**P, "slot_len": edge + 0.01}) == []
assert [f.where for f in t.check_physics({**P, "slot_len": edge - 0.01})] == ["溝"]

# ピンの穴の余白: 棒の幅の半分 − 穴の半径 ≧ 3。幅 10 は 3.3、幅 9.3 で 2.95 になり落ちる
m = {(n, w): v for n, w, v in t.pin_margins(t.assembly(P)[0]) if n == "細い棒"}
assert abs(min(m.values()) - (P["bar_w"] / 2 - r)) < 1e-6, m
assert any(f.where == "長い棒" for f in t.check_physics({**P, "bar_w": 9.3}))
# 同じ部品の 2 つの穴の間も紙の端と同じに見る（水車の腕が短いと、軸と手の穴の間が裂ける）
fs = t.check_physics({**P, "kind": "karakuri", "crank": 6})
assert any(f.where == "水車と手" for f in fs), fs

# 止まる物: 回す部品が割ピンの頭に当たる角。真下に 40mm 垂れた棒を回すと、真横 30mm の頭（半径 4）には 90° より前で当たる
bar = box(-3, 0, 3, 40)
hit = t.swing_hit(bar, (0, 0), 1, 120, [Point(-30, 0).buffer(t.HEAD_R)])
assert hit is not None and 60 < hit < 90, hit
assert t.swing_hit(bar, (0, 0), -1, 60, [Point(-30, 0).buffer(t.HEAD_R)]) is None  # 逆に回せば当たらない
# 梯子の板は、押すと下の端が机に当たり、そこで止まる（既定の寸法でも、押した角より机に当たる角が小さい）
big = t.motion({**P, "kind": "hashigo"})
assert big["hit_angle"] is not None and big["usable"] == big["hit_angle"] < big["input_angle"], big

# 引く形: 糸は膝が腰と穴を結ぶ線に乗るまでしか縮まない。そこで止まる角は、腰から膝と腰から穴の間の角
yk = t.motion({**P, "kind": "yakko"})
H, G = (30.0, 60.0), (52.0, 96.0)
assert yk["string_limited"] and abs(yk["input_angle"] - math.degrees(math.atan2(G[0] - H[0], G[1] - H[1]))) < 0.2, yk

# 四節: Grashof の境目。最短 + 最長 ≦ 残りの和で、最短が水車の腕
k = {**P, "kind": "karakuri"}
km = t.motion(k)
limit = km["d"] + P["drive_arm"] - km["b"]  # 水車の腕の上限
assert t.grashof(limit - 0.01, km["b"], P["drive_arm"], km["d"]) and not t.grashof(limit + 0.01, km["b"], P["drive_arm"], km["d"])
assert not t.grashof(5, 3, 10, 10)  # 最短が水車の腕でなければ 1 周回せない
fs = t.check_physics({**k, "crank": 30})
assert [f.where for f in fs] == ["四節"] and "Grashof" in fs[0].message, fs
# 1 周回る時、犬の振れはおよそ 2·asin(水車の腕 / 犬の腕)（連桿が長いので）
assert abs(km["swing"] - 2 * math.degrees(math.asin(P["crank"] / P["drive_arm"]))) < 3, km

# 板の噛み: D·cos α − t·sin α = d。厚さが無ければ acos(d/D)
assert abs(t.lock_angle(3.2, 3, 0) - math.degrees(math.acos(3 / 3.2))) < 1e-6
a = t.lock_angle(3.2, 3, 0.15)
assert abs(3.2 * math.cos(math.radians(a)) - 0.15 * math.sin(math.radians(a)) - 3) < 1e-6 and a < math.degrees(math.acos(3 / 3.2))
assert t.lock_angle(3.0, 3, 0.15) == 0.0
sv = {**P, "kind": "saru_take"}
assert [f.where for f in t.check_physics({**sv, "hole_d": 3.0})] == ["板の穴"]
assert "緩く" in t.check_physics({**sv, "hole_d": 4.0})[0].message

# 絵の札: 動く量の半分ずつ上下しても、窓の縁を 2mm 以上覆う。窓と札の余りは 15mm なので 26mm までは覆い、27mm で端が見える
eb = {**P, "kind": "ebako", "slot_len": 40}
assert t.check_physics({**eb, "travel": 26}) == []
assert any("窓から見える" in f.message for f in t.check_physics({**eb, "travel": 27}))

# 登る形は板に谷折りの耳があり、折りの書き出しの対象になる
assert all(q.valley for q in t.parts(sv) if q.key.endswith("bar"))

# 床が見る量（押す・引く量、粘土の置き場）は、紙に印を刷り、組み方の文で印を言う。印が無いと、作る人は床が見た量で動かせない
for k in ("sumo", "hashigo", "ebako"):
    q = {**P, "kind": k, "travel": 16}
    ticks = [it for pt in t.parts(q) for it in pt.art if it.get("mark") == "travel"]
    assert len(ticks) == 2 and abs(math.dist(ticks[0]["at"], ticks[1]["at"]) - 16) < 1e-6, (k, ticks)
    assert any("印" in s and "16mm" in s for s in t.steps(q)), k
for k in ("saru_take", "saru_sao"):
    q = {**P, "kind": k}
    clay = [it for pt in t.parts(q) for it in pt.art if it.get("mark") == "clay"]
    assert len(clay) == 1 and any("粘土" in s and "印" in s for s in t.steps(q)), k
assert any("印" in s and "20mm" in s for s in t.steps({**P, "kind": "yakko"}))
print("ok")
