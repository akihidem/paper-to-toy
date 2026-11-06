"""御来迎の次の組（goraigo-v12）: 実物の写真と照らした直し A・C・D を確かめる。

本人の決定（2026-11-06）「実物の写真と照らした直しは、御来迎・虎とも全部入れる。次の版へ」による。
- A（扇を細かく小さく）と C（筒を細長く）は寸法なので、雛形の既定値でなく見本の場面 examples/goraigo_v12.json に置く。
  凍結の場面は既定の寸法で動くので、既定を替えると凍結の期待（rc・床・行）が崩れるため。サイトは次の組の記録にこの寸法を写す。
- D（色）は雛形に入れる。筒は白木、扇は金に寄せ、筒の 1 面目に紫の枠の札を描く。どの形も色の境で折るので、
  隣り合う面と板が同じ色にならない事を、全部の形で見る。
- B（扇の要を首の高さ）と E（下から棒で押す）は lift の仕組みを変えるので、本人が紙で lift を確かめた後に別に入れる。
"""
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae.__main__ import load_source  # noqa: E402
from omochae.compose import compose  # noqa: E402
from omochae.templates import slider_fan as sf  # noqa: E402

SC = json.loads((ROOT / "examples/goraigo_v12.json").read_text(encoding="utf-8"))
V12 = {**sf.DEFAULTS, **SC["params"]}

# 1. 寸法は実物の写真の比（目測。斜めから撮ってあるので 1〜2 割はずれる）に寄せてある。
#    折り目は 44〜52 枚・扇の半径（折りの高さ）は筒の一辺の約 1.1 倍・筒の長さは一辺の約 4 倍。形は筒を外す形（lift）
assert SC["template"] == "slider_fan" and V12["push_part"] == sf.LIFT
assert 44 <= V12["fold_count"] <= 52, V12["fold_count"]
assert abs(V12["fold_height"] / V12["tube_side"] - 1.1) <= 0.11, (V12["fold_height"], V12["tube_side"])
assert abs(V12["tube_height"] / V12["tube_side"] - 4) <= 0.4, (V12["tube_height"], V12["tube_side"])
# 既定値は変えていない（凍結の場面のため）。上の寸法は範囲の内で、検査が全部通る
assert sf.DEFAULTS["fold_count"] == 28 and sf.DEFAULTS["tube_height"] == 84 and sf.DEFAULTS["fold_height"] == 48
assert sf.check_range(V12) == [], [f.line() for f in sf.check_range(V12)]
assert sf.check_physics(V12) == [], [f.line() for f in sf.check_physics(V12)]
_, layout, fails = compose("slider_fan", SC["params"], load_source(SC["source_id"]))
assert fails == [], [f.line() for f in fails]
# 刷る口からも刷れる（A4 に収まる。扇は 46 × 5 = 230mm で右の列に縦に置く）
with tempfile.TemporaryDirectory() as d:
    r = subprocess.run([sys.executable, "-m", "omochae", "--scenario", str(ROOT / "examples/goraigo_v12.json"), "--out", f"{d}/v12"],
                       cwd=ROOT, env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert r.returncode == 0 and pathlib.Path(f"{d}/v12.pdf").exists(), r.stderr

# 2. 色の境で折る部品（外筒・扇）は、隣り合う面と板の色が違う（同じ色だと折る所の目印が消える）。全部の形で見る
for form in sf.PUSH_PARTS:
    p = {**sf.DEFAULTS, "push_part": form, **({"pusher_height": 84} if form in ("tube", "stick") else {})}
    by = {q.key: q for q in sf.parts(p)}
    A, H = p["tube_side"], p["tube_height"]
    # 面の地の色: 各面の真ん中の高さの帯（上の帯と下の帯の間）の塗り
    def ground(i):
        cx = A * (i + 0.5)
        hits = [a["fill"] for a in by["tube"].art if a["kind"] == "poly" and a["fill"] in (sf.WOOD, sf.WOOD_ALT)
                and min(x for x, _ in a["pts"]) <= cx - 3 and max(x for x, _ in a["pts"]) >= cx - 3]
        return hits[0]
    faces = [ground(i) for i in range(4)]
    assert all(faces[i] != faces[i + 1] for i in range(3)), (form, faces)
    fills = [a["fill"] for a in by["fan"].art[:int(p["fold_count"])]]
    assert all(fills[i] != fills[i + 1] for i in range(len(fills) - 1)), form
    assert set(fills) == {sf.FAN_A, sf.FAN_B} and sf.WOOD != sf.WOOD_ALT, form

# 金と白木に寄せた色: 扇は赤と緑が青より十分に強い黄の色、筒は明るい（地の明るさ 0.75 以上。前の原図の地は 0.54 と 0.64）
rgb = lambda c: tuple(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))
for c in (sf.FAN_A, sf.FAN_B):
    r_, g_, b_ = rgb(c)
    assert r_ > 0.75 and g_ > 0.6 and b_ < g_ - 0.25, c
for c in (sf.WOOD, sf.WOOD_ALT):
    assert sum(rgb(c)) / 3 >= 0.75, c

# 3. 筒の札（紫の枠）は 1 面目の内で、折り線・角の 2 本線・上と下の帯・部品の札「1 外筒」・溝・穴にかからない。寸法の範囲の端でも見る
for A in (sf.RANGES["tube_side"][0], 30, sf.RANGES["tube_side"][1]):
    for H in (sf.RANGES["tube_height"][0], 84, 120, sf.RANGES["tube_height"][1]):
        x0, y0, x1, y1 = sf.label_box(A, H)
        assert 1 <= x0 and x1 <= A - 1.2 - 1, (A, H, x0, x1)  # 左の折り線（筒の端）と、右の角の 2 本線（一辺−1.2）から 1mm 以上
        assert 4.5 + 1 <= y0 and y1 <= H - 5 - 1, (A, H, y0, y1)  # 上の帯（部品の札もここ）と下の帯から 1mm 以上
for form in sf.PUSH_PARTS:
    p = {**sf.DEFAULTS, "push_part": form, **({"pusher_height": 84} if form in ("tube", "stick") else {})}
    tube = {q.key: q for q in sf.parts(p)}["tube"]
    x0, y0, x1, y1 = sf.label_box(p["tube_side"], p["tube_height"])
    assert all(not (x0 - r <= hx <= x1 + r and y0 - r <= hy <= y1 + r) for hx, hy, r in tube.holes), form
    assert all(cx >= x1 for cx, _, _, _ in [(c[0], c[1], c[2], c[3]) for c in tube.cuts]), form
    # 外形の切れ込み（つまみの形の溝）は 2 面目にある
    assert all(x >= p["tube_side"] or not (x0 < x < x1 and y0 < y < y1) for x, y in tube.outline), form
print("ok 御来迎の次の組 v12（実物の写真の直し A・C・D）")
