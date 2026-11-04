"""弩・弓と毛玉の床（F5.launch）の式の要所を数点で確かめる。ためる力と玉の重さは安全を分ける量なので、言葉でなく数で見る。"""
from omochae.compose import TEMPLATES
from omochae.templates import launcher as t

P = dict(t.DEFAULTS)
B = {**P, "form": "bow"}
assert TEMPLATES["launcher"] is t, "templates/ に置けば登録される"
for p in (P, B):
    assert t.check_physics(p) == [] and not t.check_range(p), t.check_physics(p)

# ためる力 ½kx²: 40N/m・30mm は 18mJ。k を倍にすると倍、引きを倍にすると 4 倍
assert abs(t.energy_mj(P) - 18.0) < 1e-9
assert abs(t.energy_mj({**P, "spring_k": 80}) - 36.0) < 1e-9 and abs(t.energy_mj({**P, "draw": 60}) - 72.0) < 1e-9
# 上限ちょうどは通り、少しでも越えれば F5.launch のばねで落ちる（k = 2E/x²）
k_cap = 2 * t.ENERGY_CAP_MJ / 1000 / (P["draw"] / 1000) ** 2
assert t.check_physics({**P, "spring_k": k_cap - 1e-9}) == []  # 割り算の丸めの分だけ下げる
fs = t.check_physics({**P, "spring_k": k_cap + 1})
assert [(f.floor, f.where) for f in fs] == [("F5.launch", "ばね")], fs
# 弓の形も同じ上限（輪ゴムの弦でも同じ式）
assert any(f.where == "ばね" for f in t.check_physics({**B, "spring_k": 80, "draw": 40}))

# 玉の重さ ＝ 紙の面積 × 面密度。64mm 四方・150g/m² は 0.6144g
assert abs(t.projectile_mass(P) - 64 * 64 * 150e-6) < 1e-12
assert any(f.where == "玉" and "重さ" in f.message for f in t.check_physics({**P, "ball_paper": 100, "paper_gsm": 120, "ball_d": 18}))
assert any(f.where == "玉" and "重さ" in f.message for f in t.check_physics({**B, "paper_gsm": 40, "fringe_len": 8}))

# 先の太さ: 毛玉は房の長さの 2 倍。15mm より細いと落ちる
assert t.nose_d(B) == 2 * B["fringe_len"]
assert any("先の太さ" in f.message for f in t.check_physics({**B, "fringe_len": 7}))
assert not any("先の太さ" in f.message for f in t.check_physics({**B, "fringe_len": 7.5}))

# 弩の玉は、筒より 1〜4mm 細く、紙の辺の 0.3 倍まで。物差しの穴は通らない側が 15mm 以上
small, big = t.gauge_holes(P)
assert small >= t.MIN_NOSE and big == P["stock_w"] - 1 and small < P["ball_d"] < big
assert any("筒" in f.message for f in t.check_physics({**P, "ball_d": 15}))
assert any("まとまらない" in f.message for f in t.check_physics({**P, "ball_paper": 50}))

# 穴と縁: 腕の幅の半分から穴の半径を引いた残りが 3mm 未満で落ちる
assert any(f.where == "腕" for f in t.check_physics({**P, "arm_w": 7}))
assert any(f.where == "弓" for f in t.check_physics({**B, "arm_w": 7}))
# 引き金の切れ込みの奥の残り・浅すぎる切れ込み・台の後ろの端までの余り
assert any("奥に" in f.message for f in t.check_physics({**P, "notch_depth": 8}))
assert any("浅く" in f.message for f in t.check_physics({**P, "notch_depth": 1}))
assert any("後ろの端" in f.message for f in t.check_physics({**P, "stock_length": 70, "draw": 50, "spring_k": 10}))
# 弦の溝と糊代の間
assert any(f.where == "弦の溝" for f in t.check_physics({**P, "glue": 8}))

# 刷る部品の穴・切れ込みの位置が式と合う: 腕の穴は 4 枚の面の真ん中、引き金の切れ込みは筒の真ん中の高さ
arm = next(q for q in t.parts(P) if q.key == "arma")
assert [y for _, y, _ in arm.holes] == [k * P["arm_w"] + P["arm_w"] / 2 for k in range(t.LAYERS)]
trig = next(q for q in t.parts(P) if q.key == "trigger")
assert (0, t.GRIP + P["stock_w"] / 2 + 1) in trig.outline and (P["notch_depth"], t.GRIP + P["stock_w"] / 2 - 1) in trig.outline

# 形ごとの部品と部品表が合い、飛ばす物は紙だけ（竹串・楊枝・豆を部品表に載せない）
for p in (P, B):
    keys = {q.key for q in t.parts(p)}
    rows = t.bom(p)
    assert keys <= {r["key"] for r in rows}
    assert not any(w in r["material"] for r in rows for w in ("竹串", "楊枝", "豆"))
    assert any(t.SAFETY in s for s in t.steps(p))
assert sum("輪ゴム" in r["material"] for r in t.bom(B)) == 1
# 出典は形ごと（弩はコマ 8 左、弓と毛玉はコマ 29 左）。既定の出典は既定の形の物
assert getattr(t, "SOURCES", {}) == {"crossbow": "NDL-1187053-R0000008-L-launcher", "bow": "NDL-1187053-R0000029-L-launcher"} and t.SOURCE == t.SOURCES[P["form"]]
# 引く長さ x がためる力の上限を決めるので、引ける所の限りを紙に刷り、組み方の文で言う
# 弩: 弦の溝は腕の根元から x + 1mm で終わり（溝の端が止め）、引き金の切れ込みはその x の所
st = next(q for q in t.parts(P) if q.key == "stock")
assert all(c[2] == P["draw"] + 1 for c in st.cuts if c[3] == t.SLIT) and any("溝の端" in s and f"{t.trigger_x(P):g}mm" in s for s in t.steps(P))
# 弓: 引き止めの帯に、弓から x の所の線を刷る。部品表にも載り、組み方の文がその線までと言う
stop = next((q for q in t.parts(B) if q.key == "drawstop"), None)
assert stop is not None and any(it["kind"] == "line" and all(abs(y - (t.STOP_BASE + B["draw"])) < 1e-9 for _, y in it["pts"]) for it in stop.art)
assert "drawstop" in {r["key"] for r in t.bom(B)} and any("引き止めの帯" in s and "線" in s for s in t.steps(B))
# 0.08J は確かめていない目安として書くだけで、決まり（規格）の値として書かない
assert "目安" in t.__doc__ and "安全の決まり" not in t.__doc__
print("ok")
