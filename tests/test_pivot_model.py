"""振り子の式の向きを数点で確かめる。言葉で書いた直す向きは間違えやすいので、ここで数える。"""
from omochae.pivot_model import center, period_s, rest_tilt_deg
from omochae.templates.pivot_counterweight import DEFAULTS, check_physics, mass_points

base = [(0.1, 20, 0), (3.0, 0, 20)]
far = [(0.1, 20, 0), (3.0, 0, 40)]
assert period_s(far) > period_s(base), "重りが軸から遠いほど周期が長い"
heavy = [(0.1, 20, 0), (6.0, 0, 20)]
assert abs(period_s(heavy) - period_s(base)) < 0.01, "重りの量は周期をほぼ変えない"
assert period_s([(3.0, 0, -5)]) is None, "軸より上では揺れない"
assert rest_tilt_deg([(0.1, 20, 0), (3.0, 0, 20)]) < 2
# 紙の頭は重りより桁で軽いので、後ろの腕の重りで釣り合わせると大きく傾く
seesaw = dict(DEFAULTS, weight_behind=28, weight_below_axle=5, weight_g=1.0)
assert any("傾く" in f.message for f in check_physics(seesaw))
assert mass_points(DEFAULTS)[0][0] < 0.2 and not check_physics(DEFAULTS)
print(round(period_s(mass_points(DEFAULTS)), 2))

# EP-0011（作成動画の札から採った案。2026-11-06）: 首の形の 5 重りの腕に下の穴（重りの位置）と点の丸を足し、腕は試してから貼る順にした。
# - 下の穴は、軸の穴から weight_below_axle 下（釣り合いの式の重りの位置）。点の丸（位置の印）で囲む。粘土はこの穴の所に付ける
# - 糸で玉を下げる形は、玉（粘土 weight_g の球）の下が胴の底から 3mm 以上離れる寸法の時だけ、組み方の文と部品表に出す。
#   釣り合いの式は変えない: 糸で下げた玉の重さは、糸を通した穴にかかる（玉の所ではない）。糸の長さは、玉が底に当たるかだけに効く
# - 組み方の文: 腕は帯に仮に留め、頭の傾きを見て位置を決めてから貼る（手順の数と番号は変えない）
import math

from omochae.__main__ import load_source
from omochae.compose import compose
from omochae.floors import check_art
from omochae.templates import pivot_counterweight as pc
from shapely.geometry import Polygon
neck = dict(DEFAULTS, mount="neck")
seen = hangable = 0
for wba in (pc.RANGES["weight_below_axle"][0], 5, 12, 20, DEFAULTS["weight_below_axle"], 40, pc.RANGES["weight_below_axle"][1]):
    for wg in (pc.RANGES["weight_g"][0], 1.0, DEFAULTS["weight_g"], pc.RANGES["weight_g"][1]):
        for ax in (30, DEFAULTS["axle_height"], 50):
            q = dict(neck, weight_below_axle=wba, weight_g=wg, axle_height=ax)
            if pc.check_range(q) or check_physics(q):
                continue  # 検査で落ちる寸法は刷らない
            seen += 1
            drop = next(x for x in pc.parts(q) if x.key == "drop")
            (ax_x, ax_y, _), (hx, hy, hr) = drop.holes[0], drop.holes[1]
            assert hx == ax_x and abs((hy - ax_y) - wba) < 1e-9, (q, drop.holes)  # 軸の穴の真下、weight_below_axle の所
            ring = [a for a in drop.art if a["kind"] == "mark" and a.get("mark") == "weight"]
            assert len(ring) == 1 and math.dist(tuple(Polygon(ring[0]["pts"]).centroid.coords[0]), (hx, hy)) < 0.05, (q, ring)
            assert check_art([drop]) == [], (q, [f.line() for f in check_art([drop])])
            assert mass_points(q)[-1] == (wg, -q["weight_behind"], wba), "釣り合いの式の重りの位置は変えない"
            st, mat = pc.steps(q), pc.materials(q)
            L = pc.hang_thread_mm(q)
            if L is None:
                assert not any("糸" in s for s in st) and not any("糸" in m for m in mat), (q, st, mat)
            else:
                hangable += 1
                r = pc.clay_r(wg)
                assert wba + L + 2 * r <= q["axle_height"] - 3 + 1e-9, (q, L, r)  # 下げた玉の下が底から 3mm 以上
                assert any("糸" in s and f"{L:.0f}mm" in s for s in st) and any(f"{L:.0f}mm" in m for m in mat), (q, st, mat)
            assert any("下の穴（点の丸）の所に粘土" in s and "仮に留め" in s for s in st), st
            assert any("頭の傾きを見て" in s and "貼る" in s for s in st), st
assert seen >= 10 and hangable >= 1, (seen, hangable)
_, layout, fails = compose("pivot_counterweight", neck, load_source(pc.SOURCE))
assert not fails, [f.line() for f in fails]
assert any("位置の印" in x.text for x in layout["texts"]), "凡例に位置の印の行が無い"
print("ok 重りの腕の下の穴と試してから貼る順")
