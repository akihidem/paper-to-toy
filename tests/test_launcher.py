"""弩・弓と毛玉の床（F5.launch）の式の要所を数点で確かめる。ためる力と玉の重さは安全を分ける量なので、言葉でなく数で見る。"""
from omochae.compose import TEMPLATES
from omochae.templates import launcher as t

P = dict(t.DEFAULTS)
B = {**P, "form": "bow"}
assert TEMPLATES["launcher"] is t, "templates/ に置けば登録される"
for p in (P, B):
    assert t.check_physics(p) == [] and not t.check_range(p), t.check_physics(p)

# k は作る物の寸法から: 梁 2 本・k₁ = 3·E_HIGH·I/L³。既定の弩は 64N/m・25mm で 20mJ
k1 = 3 * t.E_HIGH * (P["arm_w"] * (t.LAYERS * P["paper_t"]) ** 3 / 12) / P["arm_len"] ** 3 * 1000
assert abs(t.spring_k(P) - 2 * k1) < 1e-9 and abs(t.energy_mj(P) - 0.5 * 2 * k1 * 0.025 ** 2 * 1000) < 1e-9
# 引きを倍にすると 4 倍、紙の厚さを倍にすると 8 倍（厚さの 3 乗）
assert abs(t.energy_mj({**P, "draw": 50}) / t.energy_mj(P) - 4) < 1e-9 and abs(t.spring_k({**P, "paper_t": 0.4}) / t.spring_k(P) - 8) < 1e-9
# 上限ちょうどの手前は通り、越えれば F5.launch のばねで落ちる（引く長さで探す: x = √(2E/k)）
x_cap = (2 * t.ENERGY_CAP_MJ / 1000 / t.spring_k(P)) ** 0.5 * 1000
assert t.check_physics({**P, "draw": x_cap - 1e-6}) == []
fs = t.check_physics({**P, "draw": x_cap + 0.5})
assert [(f.floor, f.where) for f in fs] == [("F5.launch", "ばね")], fs
# 弓の形も同じ式で、持つ所の帯の外の片側を梁にする
assert abs(t.spring_k(B) - 2 * k1 * (P["arm_len"] / ((B["bow_span"] - t.GRIP_W) / 2)) ** 3) < 1e-9
assert any(f.where == "ばね" for f in t.check_physics({**B, "paper_t": 0.35}))
# 止めの条件の下がり: 重りの力 ÷ k₁。下がりが読めないほど硬い腕は落とす
assert abs(t.tip_sag_min(P) - t.COIN_G / 1000 * 9.8 / k1 * 1000) < 1e-9
assert any("確かめられない" in f.message for f in t.check_physics({**P, "arm_len": 30, "draw": 10}))

# 玉の重さ ＝ 紙の面積 × 面密度。64mm 四方・150g/m² は 0.6144g
assert abs(t.projectile_mass(P) - 64 * 64 * 150e-6) < 1e-12
assert any(f.where == "玉" and "重さ" in f.message for f in t.check_physics({**P, "ball_paper": 100, "paper_gsm": 120, "ball_d": 18}))
# 毛玉は芯の玉の紙と房の帯を足した重さ。厚い紙では 1g を越える
assert abs(t.projectile_mass(B) - (64 * 64 + t.POM_LEN * t.POM_BASE + t.POM_TEETH * t.TOOTH * B["fringe_len"]) * 150e-6) < 1e-12
assert any(f.where == "玉" and "重さ" in f.message for f in t.check_physics({**B, "paper_gsm": 200}))

# 先の太さ: どちらの形も丸めた玉の直径。毛玉の房の長さは数えない（当たるとつぶれる）。15mm より細いと落ちる
assert t.nose_d(B) == B["ball_d"] and t.nose_d({**B, "fringe_len": 25}) == B["ball_d"]
assert any("先の太さ" in f.message for f in t.check_physics({**B, "ball_d": 14.9}))
assert not any("先の太さ" in f.message for f in t.check_physics({**B, "ball_d": 15}))

# 弩の玉は、筒より 1〜4mm 細く、紙の辺の 0.3 倍まで。物差しの穴は通らない側が 15mm 以上
small, big = t.gauge_holes(P)
assert small >= t.MIN_NOSE and big == P["stock_w"] - 1 and small < P["ball_d"] < big
assert any("物差しの穴" in f.message for f in t.check_physics({**P, "ball_d": 15}))  # 筒（太さ 20mm）に対して細すぎる
assert any("まとまらない" in f.message for f in t.check_physics({**P, "ball_paper": 50}))

# 穴と縁: 腕の幅の半分から穴の半径を引いた残りが 3mm 未満で落ちる
assert any(f.where == "腕" for f in t.check_physics({**P, "arm_w": 7}))
assert any(f.where == "弓" for f in t.check_physics({**B, "arm_w": 7}))
# 引き金の切れ込みの奥の残り・浅すぎる切れ込み・台の後ろの端までの余り
assert any("奥に" in f.message for f in t.check_physics({**P, "notch_depth": 8}))
assert any("浅く" in f.message for f in t.check_physics({**P, "notch_depth": 1}))
assert any("後ろの端" in f.message for f in t.check_physics({**P, "stock_length": 70, "draw": 50}))
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
assert not any("輪ゴム" in r["material"] for p in (P, B) for r in t.bom(p))  # ばねは刷った紙だけ
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
# 2 回目の指摘の行: 弓のばねは刷った紙だけ（輪ゴムを使わない）、弩は引ける所が 1 つで止めの条件で確かめる、
# 物差しの穴と床の範囲が合う、弓の真ん中の穴をあける、弦の糸が部品表にある、貼り重ねの 3 つの面を全部貼る、弩で引く長さを変えさせない
from shapely.geometry import Polygon
from shapely.ops import unary_union
CHECKS = {
 "H1 弓の k は作った物から": lambda: (not any("輪ゴム" in r["material"] for r in t.bom(B)) and "spring_k" not in t.DEFAULTS
     and abs(t.spring_k(B) - 2 * 3 * t.E_HIGH * (P["arm_w"] * (t.LAYERS * P["paper_t"]) ** 3 / 12) / ((B["bow_span"] - t.GRIP_W) / 2) ** 3 * 1000) < 1e-9  # 4 回目で梁を持つ所の外に改めた
     and t.energy_mj({**B, "paper_t": 0.3}) > t.energy_mj(B)),
 "H2 弩の引きは 1 つで、測って止める": lambda: (not any("引く長さを減らす" in s for s in t.steps(P))
     and any("使わない" in s and f"{t.sag_print(P)}mm" in s for s in t.steps(P))
     and any("使わない" in s and f"{t.sag_print(B)}mm" in s for s in t.steps(B))),
 "M 物差しの穴と閉じた範囲": lambda: (lambda s, b: any(f.where == "玉" for f in t.check_physics({**P, "ball_d": s}))
     and any(f.where == "玉" for f in t.check_physics({**P, "ball_d": b})) and not any("物差しの穴" in f.message for f in t.check_physics({**P, "ball_d": s + t.GAUGE_TOL})))(*t.gauge_holes(P)),
 # 4 回目で弓の真ん中の毛玉の穴をやめた（持つ所の帯の上から巻いて結ぶ）。刷る穴（両端）をあける文があるかを見る
 "M 弓の穴をあける文": lambda: any("両端の穴" in s and "あけ" in s for s in t.steps(B)) and len(next(q for q in t.parts(B) if q.key == "stave").holes) == 2 * t.LAYERS,
 "M 弓の弦の糸が部品表に": lambda: any(r["key"] == "string" and "糸" in r["material"] for r in t.bom(B)),
 "M 貼り重ねの 3 つの面": lambda: (lambda a: abs(unary_union([Polygon(g) for g in a.glue]).area - a.width * a.height) < 1e-6)(next(q for q in t.parts(P) if q.key == "arma"))
     and any("裏" in s and "貼" in s for s in t.steps(P)),
 "L 弩で引く長さを変えさせない": lambda: not any("引く長さを変えて" in s for s in t.steps(P)) and "変える" not in t.measures(P)["predict"],
}
for name, check in CHECKS.items():
    assert check(), name
# 3 回目の指摘の行: 毛玉の先は芯の玉で見る、止めの下がりは切り上げて刷る（どの寸法でも刷った値 ≧ 式の値）、
# 弓の毛玉の穴は引き止めの帯の糊代から外す、弩の腕の穴をあける文、弓は両端を測る、穴あけの竹串を用意する物に、房の長さが合う
import itertools, re
from shapely.geometry import Point
def printed_sags(p):
    return [float(x) for s in t.steps(p) if "止めの条件" in s for x in re.findall(r"([\d.]+)mm 以上下がらなければ", s)]
def sag_ok():
    for f, al, aw, pt in itertools.product(("crossbow", "bow"), (30, 50, 70), (8, 9, 12), (0.1, 0.12, 0.2, 0.3)):
        p = {**P, "form": f, "arm_len": al, "arm_w": aw, "paper_t": pt}
        got = printed_sags(p)
        if not got or min(got) < t.tip_sag_min(p):
            return False
    return True
def hole_clear():
    sv = next(q for q in t.parts(B) if q.key == "stave")
    L = B["bow_span"]
    glue = Polygon([(L / 2 - t.STOP_W / 2, 0), (L / 2 + t.STOP_W / 2, 0), (L / 2 + t.STOP_W / 2, sv.height), (L / 2 - t.STOP_W / 2, sv.height)])
    return all(not glue.intersects(Point(x, y).buffer(r)) for x, y, r in sv.holes)
CHECKS3 = {
 "H 毛玉の先は芯で見る": lambda: t.nose_d(B) == B["ball_d"] and any(f.where == "玉" for f in t.check_physics({**B, "ball_d": 12})) and t.check_physics({**B, "fringe_len": 6}) == [],
 "H 止めの下がりは切り上げて刷る": sag_ok,
 "M 弓の真ん中の穴と引き止めの糊代": hole_clear,
 "M 弩の腕の穴をあける文": lambda: any("腕の先の穴" in s and "あけ" in s for s in t.steps(P)),
 "M 弓は両側を測る": lambda: any("止めの条件" in s and "両端" in s and "どちらか" in s for s in t.steps(B)),
 "L 穴あけの竹串が用意する物に": lambda: all(any("竹串" in m and "片づけ" in m for m in t.materials(p)) for p in (P, B)),
 "L 房の長さが合う": lambda: (lambda q: abs(q.width - t.POM_LEN) < 1e-9 and abs(t.projectile_mass({**B, "ball_paper": 1e-9}) - Polygon(q.outline).area * B["paper_gsm"] * 1e-6) < 1e-6)(next(q for q in t.parts(B) if q.key == "pompom")),
}
for name, check in CHECKS3.items():
    assert check(), name
# 4 回目の指摘の行: 弓は持つ所を刷り梁はその外、弩は引いてから玉を入れる、竹串は大人があけて片づけ筒の中で弦に掛からない、
# 固く丸めた玉を落とす、弓の向けと構えと糸の長さの上限、腕は根元の折り線で押さえる、δ と x の余裕を書く
def idx(steps, *words):
    return next(i for i, s in enumerate(steps) if all(w in s for w in words))
CHECKS4 = {
 "H 弓は持つ所を刷り、梁はその外": lambda: (getattr(t, "GRIP_W", None) and t.beam_len(B) == (B["bow_span"] - t.GRIP_W) / 2
     and "grip" in {q.key for q in t.parts(B)} and "grip" in {r["key"] for r in t.bom(B)}
     and any("持つ所の帯の内だけ" in s for s in t.steps(B))
     and any(f.where == "ばね" for f in t.check_physics({**B, "bow_span": 80, "paper_t": 0.12, "arm_w": 10, "draw": 34}))),
 "H 弩は引いてから玉を入れる": lambda: idx(t.steps(P), "引き金", "弦を掛ける") < idx(t.steps(P), "玉を台の前の口から入れ"),
 "M 竹串は大人があけて片づけ、筒の中で弦に掛からない": lambda: (t.skewer_clear(P) >= 2 and any(f.where == "弦の溝" and "竹串" in f.message for f in t.check_physics({**P, "stock_w": 12, "glue": 4, "ball_d": 10, "ball_paper": 40}))
     and all(any("大人" in s and "竹串" in s and "片づけ" in s for s in t.steps(p)) for p in (P, B))
     and all(any("大人" in m and "竹串" in m for m in t.materials(p)) for p in (P, B))),
 "M 固く丸めた玉を落とす": lambda: (t.bulk_density(P) <= t.DENSITY_MAX
     and any("固" in f.message for f in t.check_physics({**P, "ball_paper": 100, "paper_gsm": 100, "ball_d": 16.5}))),
 "M 弓の向けと構え・糸の長さの上限": lambda: (any("遠くの壁か床" in s for s in t.steps(B)) and any("顔から離し" in s for s in t.steps(B))
     and any(f.where == "毛玉の糸" for f in t.check_physics({**B, "tether": t.TETHER_MAX + 1})) and t.check_physics({**B, "tether": t.TETHER_MAX}) == []),
 "L 腕は根元の折り線で押さえる": lambda: any("止めの条件" in s and "根元の折り線" in s for s in t.steps(P)),
 "L δ と x の余裕を書く": lambda: "δ ≒ x/2" in t.__doc__ and "上限" in t.__doc__,
}
for name, check in CHECKS4.items():
    assert check(), name
print("ok")
