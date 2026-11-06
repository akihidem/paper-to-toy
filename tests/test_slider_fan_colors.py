"""御来迎（slider_fan）の色と筒の札を確かめる。どの形にも効く。

本人の決定（2026-11-06）「実物の写真と照らした直しは、御来迎・虎とも全部入れる。次の版へ」の色の直し（案 D）。
- 筒は白木、扇は金に寄せ、筒の 1 面目に紫の枠の札を描く（実物は「御来迎」の字の札。部品の絵に字は刷らないので形だけ）。
- どの形も色の境で折る（線を刷らない）ので、隣り合う面と板が同じ色にならない事を、全部の形で見る。
- 寸法の直し（扇を細かく小さく・筒を細長く）は、次の組の形の見本の場面で入れる（この試験ではない）。
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae.templates import slider_fan as sf  # noqa: E402

# 1. 色の境で折る部品（外筒・扇）は、隣り合う面と板の色が違う（同じ色だと折る所の目印が消える）。全部の形で見る
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

# 2. 筒の札（紫の枠）は 1 面目の内で、折り線・角の 2 本線・上と下の帯・部品の札「1 外筒」・溝・穴にかからない。寸法の範囲の端でも見る
for A in (sf.RANGES["tube_side"][0], 30, sf.RANGES["tube_side"][1]):
    for H in (sf.RANGES["tube_height"][0], 84, 120, sf.RANGES["tube_height"][1]):
        x0, y0, x1, y1 = sf.label_box(A, H)
        assert 1 <= x0 and x1 <= A - 1.2 - 1, (A, H, x0, x1)  # 左の折り線（筒の端）と、右の角の 2 本線（一辺−1.2）から 1mm 以上
        assert 4.5 + 1 <= y0 and y1 <= H - 5 - 1, (A, H, y0, y1)  # 上の帯（部品の札もここ）と下の帯から 1mm 以上
        assert y1 - y0 >= x1 - x0, (A, H, x1 - x0, y1 - y0)  # 札は縦長（太く短い筒でも横長にしない。検品の指摘）
for form in sf.PUSH_PARTS:
    p = {**sf.DEFAULTS, "push_part": form, **({"pusher_height": 84} if form in ("tube", "stick") else {})}
    tube = {q.key: q for q in sf.parts(p)}["tube"]
    x0, y0, x1, y1 = sf.label_box(p["tube_side"], p["tube_height"])
    assert all(not (x0 - r <= hx <= x1 + r and y0 - r <= hy <= y1 + r) for hx, hy, r in tube.holes), form
    assert all(cx >= x1 for cx, _, _, _ in [(c[0], c[1], c[2], c[3]) for c in tube.cuts]), form
    # 外形の切れ込み（つまみの形の溝）は 2 面目にある
    assert all(x >= p["tube_side"] or not (x0 < x < x1 and y0 < y < y1) for x, y in tube.outline), form
# 3. 範囲の上限: 筒の高さを 130 まで書ける形は、内筒も同じ高さまで書ける（内筒を下から押す形と柄の形は、内筒が筒より短いと落とす）
assert sf.RANGES["pusher_height"][1] >= sf.RANGES["tube_height"][1]
for form in ("tube", "stick"):
    tall = {**sf.DEFAULTS, "push_part": form, "tube_height": 130, "pusher_height": 130}
    assert sf.check_range(tall) == [] and not [f for f in sf.check_physics(tall) if "押し切れない" in f.message], form
print("ok 御来迎の色（白木・金）と筒の札")
