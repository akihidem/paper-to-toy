"""虎 v7（examples/tora_v7.json）の当たりの直し。制作者の決定（2026-11-07）「虎 v6 の当たり2つ（粘土の玉が前の壁・頭の角が腕）は、
v7 で今直してください。撮影は v6 のまま。」による。

3D の JSON をサイトの試験で描いて見つかった 2 つ（v6 の寸法で、粘土の玉が前の壁へ約 1.4mm・頭の後ろの端が前の壁の 4mm 内で腕と重なる）を、
v6 の見本に 3 つの寸法だけを足して直す。次を見る:
1. v7 は v6 から 3 つだけ（首の帯 14 → 20mm・粘土の下の穴を軸の 2.5mm 後ろ（clay_back）・当たりの検査（fit_check 1））。検査を全部通る。
2. 当たりの検査（F5.pivot）: v6 の寸法に検査だけを入れると 2 つとも落ちる（文も見る）。境の両側（粘土は下の穴を 1.8 / 1.9mm 後ろ、頭は帯 18 / 19mm）。
   既定（fit_check 0）では検査しない（凍結の場面と v6 の紙を変えないため）。fit_check は選ぶ値（0 か 1）。
3. 刷る腕: 幅は 8 → 10.5mm（後ろへだけ広げる）、上の穴は前の端から 4mm のまま、下の穴は上の穴の 2.5mm 後ろ、粘土の線は穴の左右で腕を横切る。
   広い腕は帯の下に置く（文字の列を細くしない）。v6 の腕は前の所。
4. 組み方の文: v7 だけ、腕の向き（下の穴が後ろの尾の側）を言う。用意する物は v6 と同じ。揺れの式の粘土は軸の 1 + 2.5mm 後ろ。
5. 3D（omochae.assembly3d）: できあがりで、粘土の玉は前の壁（x = 0）から半径＋0.5mm 以上後ろ、頭の後ろの端は前の壁より前、頭と腕は前後に離れる。
"""
import json
import pathlib

from omochae.__main__ import load_source
from omochae.assembly3d import build
from omochae.compose import compose
from omochae.templates import pivot_counterweight as pc

ROOT = pathlib.Path(__file__).resolve().parents[1]
ex = {n: json.loads((ROOT / f"examples/{n}.json").read_text(encoding="utf-8")) for n in ("tora_v6", "tora_v7")}
v6, v7 = (dict(pc.DEFAULTS, **ex[n]["params"]) for n in ("tora_v6", "tora_v7"))
src = load_source(ex["tora_v7"]["source_id"])
lines = lambda q: [f.line() for f in pc.check_physics(q)]
r = pc.clay_r(v7["weight_g"])

# 1. v6 から 3 つだけ
assert ex["tora_v7"]["params"] == dict(ex["tora_v6"]["params"], neck_length=20, clay_back=2.5, fit_check=1)
assert pc.check_range(v7) == [] and lines(v7) == [] and not compose("pivot_counterweight", v7, src)[2]

# 2. 当たりの検査
assert lines(v6) == []  # v6 は検査しない（撮影中の紙のまま刷れる）
fit6 = lines(dict(v6, fit_check=1))
assert fit6 == [f"FAIL F5.pivot [重り] 粘土の玉（半径 {r:.1f}mm）が前の壁に当たる（玉の真ん中は前の壁の 6mm 後ろ。{r + pc.FIT_CLEAR:.1f}mm 以上後ろに）",
                f"FAIL F5.pivot [頭] 頭の後ろの端が前の壁より 4.0mm 後ろに入り、5 重りの腕に当たる（首の帯を長くするか頭を細くして、前の壁の {pc.FIT_CLEAR}mm 以上前に）"], fit6
clay_only = lambda cb: [x for x in lines(dict(v7, clay_back=cb)) if "粘土の玉" in x]
assert clay_only(1.8) and not clay_only(1.9)  # 6 + 1.8 = 7.8 < 7.86、6 + 1.9 = 7.9
head_only = lambda nl: [x for x in lines(dict(v7, neck_length=nl)) if "頭の後ろの端" in x]
assert head_only(18) and not head_only(19)  # 後ろの端 6 − 24 + 18 = 0、6 − 25 + 18 = −1
assert pc.spec()["fit_check"] == pc.FIT_CHECKS == (0, 1) and "fit_check" not in pc.RANGES
for bad in (2, 0.5, True, "1"):
    assert [f.where for f in pc.check_range(dict(v7, fit_check=bad))] == ["fit_check"], bad
assert pc.DEFAULTS["clay_back"] == 0 and pc.DEFAULTS["fit_check"] == 0

# 3. 刷る腕と置き場
drop6, drop7 = (next(x for x in pc.parts(q) if x.key == "drop") for q in (v6, v7))
assert drop6.width == pc.DROP_W and abs(drop7.width - (pc.DROP_W + 2.5)) < 1e-9
assert drop7.holes[0] == (4, 4, 1.0) and abs(drop7.holes[1][0] - 6.5) < 1e-9 and abs(drop7.holes[1][1] - (4 + v7["weight_below_axle"])) < 1e-9
marks = [a for a in drop7.art if a["kind"] == "mark" and a.get("mark") == "weight"]
assert len(marks) == 2 and marks[0]["pts"][0][0] == 0.6 and abs(marks[1]["pts"][1][0] - (drop7.width - 0.6)) < 1e-9
assert drop7.label == "5 重りの腕" and [t for t, _, _ in drop7.label_lines] == ["5 重", "り", "の", "腕"]
_, lay7, _ = compose("pivot_counterweight", v7, src)
by7 = {q.key: q for q in lay7["parts"]}
assert by7["drop"].x == by7["strip"].x and by7["drop"].y >= by7["strip"].y + by7["strip"].height  # 帯の下
_, lay6, _ = compose("pivot_counterweight", v6, load_source(ex["tora_v6"]["source_id"]))
by6 = {q.key: q for q in lay6["parts"]}
assert by6["drop"].y == by6["strip"].y and by6["drop"].x > by6["strip"].x  # v6 は前の所（帯の右の列）

# 4. 組み方の文・用意する物・揺れの式
s6, s7 = pc.steps(v6), pc.steps(v7)
diff = [(a, b) for a, b in zip(s6, s7) if a != b]
assert len(s6) == len(s7) and len(diff) == 1 and "（下の穴が後ろの尾の側に来る向きで）" in diff[0][1] and "向き" not in diff[0][0], diff
assert pc.materials(v6) == pc.materials(v7)
assert abs(pc.mass_points(v7)[2][1] + (v7["weight_behind"] + 2.5)) < 1e-12

# 5. 3D のできあがりで、当たりが無い
d = build(ROOT / "examples/tora_v7.json", commit="test")
parts = {q["key"]: q for q in d["parts"]}
last = d["steps"][-1]["poses"][-1]
M = lambda c: [[c[col * 4 + row] for col in range(4)] for row in range(4)]
ap = lambda m, q: tuple(m[i][0] * q[0] + m[i][1] * q[1] + m[i][3] for i in range(3))
xs = lambda key: [ap(M(last["parts"][key]["panels"][str(pn["id"])]), q)[0] for pn in parts[key]["panels"] for q in pn["poly"]]
clay = last["balls"]["clay"]["at"]
assert clay[0] - r >= pc.FIT_CLEAR - 1e-6, clay  # 前の壁は x = 0
assert max(xs("head")) <= -pc.FIT_CLEAR + 0.01 and max(xs("head")) < min(xs("drop")), (max(xs("head")), min(xs("drop")))
sk = last["rods"]["skewer"]["from"]
assert abs(clay[0] - (sk[0] + 2.5)) < 0.01 and abs(clay[1] - (sk[1] + v7["weight_below_axle"])) < 0.01, (clay, sk)
print("ok 虎 v7（当たりの直し: 粘土の玉と前の壁・頭の後ろの端と腕）")
