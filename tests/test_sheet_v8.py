"""v8 の直しが御来迎の型紙に入っている事を見る。

柄の形にも内筒の土台がある・つまみの溝は下から切り込む（くり抜かない）・蛇腹は糊代と貼る位置の印まで型紙で決める・
最初に筒を 1 つ作る順にする。どれも紙で組んで試した時に作りにくかった所を直した物。
"""
from omochae.templates.slider_fan import DEFAULTS, LEG_GLUE, leg_length, materials, parts, steps

tab = {**DEFAULTS, "push_part": "tab", "hub": "axle", "pusher_height": 15}
stick = {**DEFAULTS, "push_part": "stick", "hub": "axle", "pusher_height": 84}
rim = {**DEFAULTS, "push_part": "tube", "hub": "rim", "push_amount": 36, "pusher_height": 84, "fold_count": 18, "fold_width": 8}


def by_key(p):
    return {q.key: q for q in parts(p)}


# 1. 柄で押す形にも土台（短い内筒）がある
s = by_key(stick)
assert "pusher" in s and s["pusher"].name == "土台" and s["pusher"].height == stick["stage_height"]
assert any("土台" in x and "割り箸" in x for x in steps(stick))

# 2. 溝は下の端まで開いた切り込みで、中を切り抜く矩形は無い。カッターを要らない
t = by_key(tab)
assert t["tube"].cuts == [], "くり抜く溝を残さない"
assert len(t["tube"].outline) == 10, "外筒の輪郭に切り込みの 4 点が入る"
assert not any("カッター" in m for m in materials(tab))
assert any("下の端からはさみ" in x for x in steps(tab))

# 3. 軸で開く形の扇には、真ん中の足と糊代があり、台に貼る位置の印がある
for p in (tab, stick):
    f, b = by_key(p)["fan"], by_key(p)["base"]
    assert min(x for x, _ in f.outline) == -leg_length(p) and len(f.glue) == 1
    assert abs(min(x for x, _ in f.glue[0]) + leg_length(p)) < 1e-9 and max(x for x, _ in f.glue[0]) == -leg_length(p) + LEG_GLUE
    assert b.art, "台に足を貼る位置の印"
    assert any("足の糊代を 3 台の印に貼る" in x for x in steps(p))
# 口の台に載せる形（hub=rim）は扇の端を台に貼るので、足を足さない
assert min(x for x, _ in by_key(rim)["fan"].outline) == 0 and not by_key(rim)["base"].art

# 4. 最初に筒を 1 つ作る順
for p in (tab, stick, rim):
    st = steps(p)
    assert st[1].startswith("まず 1 外筒だけ") and "角筒にする" in st[2]
print("ok")

# 5. v9: 見える面（外筒と扇）は折り線を刷らず、絵の色の境で折る。隠れる部品は線を残す
for p in (tab, stick, rim):
    k = by_key(p)
    assert k["tube"].hide_folds and k["fan"].hide_folds
    assert not k["base"].hide_folds and ("pusher" not in k or not k["pusher"].hide_folds)
    fan = k["fan"]
    fills = [a["fill"] for a in fan.art[: int(p["fold_count"])]]
    assert all(a != b for a, b in zip(fills, fills[1:])), "隣の板は色が違う（色の境が折り目）"
    tube_grounds = [a["fill"] for a in k["tube"].art if a["kind"] == "poly" and a["pts"][0][1] == 4.5]
    assert len(set(tube_grounds)) == 2, "外筒は 1 面おきに地の色を変える"
    # 外筒は色の面を外にして角筒にするので、刷った面から見て山折り（本人の答え 2026-11-06「色がついている所が外を向くよう折った」）。
    # 谷折り（刷った面がへこむ向き）だと色が内に入る。線は刷らないので、型紙の PDF は変わらない
    assert len(k["tube"].mountain) == 4 and not k["tube"].valley, (len(k["tube"].mountain), len(k["tube"].valley))
assert any("色の境" in s for s in steps(tab))
# 組み方の文も 1 語だけ（谷折り → 山折り）替えた。それより大きく文を変える時は本人の確認を取る
assert "1 外筒を色の境で山折りし、糊代で貼って角筒にする" in steps(tab), steps(tab)
# 内筒は隠れる部品で破線を谷折りで刷るので、手順 2 は本人の決定（2026-11-06）の文。「同じように」だと山折りと読めて、刷った破線と食い違った
assert "2 内筒は破線で谷折りし、糊代で貼って角筒にする" in steps(tab) and not any("同じように角筒にする" in s for s in steps(tab)), steps(tab)
# 用意する物の道具（本人の確認 2026-11-06）: 穴があるのに竹串の行が無い形（内筒を下から押す・柄）は、穴をあける竹串を書く。
# つまみの形は竹串の行がもう有る。穴の無い形（内筒を下から押す・口の台）には書かない
for form, want in (("tab", "のり、はさみ、定規"), ("tube", "のり、はさみ、定規、竹串（穴あけ）"), ("stick", "のり、はさみ、定規、竹串（穴あけ）")):
    assert materials({**DEFAULTS, "push_part": form})[1] == want, (form, materials({**DEFAULTS, "push_part": form}))
assert materials({**DEFAULTS, "push_part": "tube", "hub": "rim"})[1] == "のり、はさみ、定規"
# 道具は部品を組まずに形の値で決める。部品から決めた答え（穴があり、竹串の行が無い）と、全部の押し方 × 中心の置き方で同じ事を見る
from omochae.templates.slider_fan import bom
for form in ("tab", "tube", "stick"):
    for hub in ("axle", "rim"):
        q = {**DEFAULTS, "push_part": form, "hub": hub}
        by_parts = any(x.holes for x in parts(q)) and not any("竹串" in r["material"] for r in bom(q))
        assert materials(q)[1].endswith("、竹串（穴あけ）") == by_parts, (form, hub, materials(q)[1])
# 柄の形の手順 2 も、手順 2 と同じ型の文（本人の確認 2026-11-06）。「同じように」だと、山折りの外筒と同じと読めた
stick_steps = steps({**DEFAULTS, "push_part": "stick"})
assert "2 土台は破線で谷折りし、糊代で貼って角筒にし、割り箸の先を下から差し込んで貼る" in stick_steps, stick_steps
print("ok v9")

# EP-0012（作成動画の札から採った案。2026-11-06）: 御来迎の次の版（今の組 goraigo-v10 は刻んだ版のまま残す）。
# 1. 開く糸を組み方の文に入れる（軸の形）。手順 11 の終わりに足す。手順 12・13 は 3D の確かめが番号を持つので、段は足さない。
#    部品表の糸は「試す時は」でなく、作る物に入れる
# 2. つまみの形の溝の下の口に、下の端から上へ切り込む向きの矢印（位置の印）を 2 本刷る（溝の左右。下の茶色の帯から地の色の所まで）。
#    「ここから切る」の字は刷れない（部品に置ける字は札の 1 つだけ。エンジンの共有の所を変えるのは提出の後）
# 3. 扇の足の帯（8 帯）を足し、足の付け根に巻いて足を強くする。部品表と手順 10 に入れる。足のある軸の形だけ
from omochae.__main__ import load_source
from omochae.compose import compose
from omochae.floors import check_art
from omochae.templates import slider_fan as sf
assert sf.step_ops(tab) == {"fold_outer": 3, "fold_inner": 5, "thread": 6, "insert": 12, "push": 13}, sf.step_ops(tab)
for p in (tab, stick, {**tab, "push_part": "tube", "pusher_height": 84}):
    st = steps(p)
    th = f"{sf.thread_mm(p):.0f}mm"
    assert any("開く糸 2 本" in x and th in x and "外筒の口の下の 2 つの穴" in x and "扇の両端の穴" in x for x in st), st
    row = next(r for r in sf.bom(p) if r["key"] == "thread")
    assert "試す時は" not in row["material"] and "開く糸 2 本" in row["material"], row
    band = by_key(p)["band"]
    assert band.label == "8 帯" and check_art([band]) == [], (band.label, check_art([band]))
    assert any(r["number"] == 8 and r["key"] == "band" for r in sf.bom(p))
    assert any("8 帯" in x and "足の付け根" in x for x in st), st
    _, layout, fails = compose("slider_fan", p, load_source(sf.SOURCE))
    assert not fails, (p["push_part"], [f.line() for f in fails])
# 足の帯は足に巻く長さ（足の幅の 2 つ分と紙の厚み、糊代）で、色の面を外にする山折り。足の無い形（rim）には無い
b = by_key(tab)["band"]
assert abs(b.width - (2 * (tab["fold_width"] + tab["paper_thickness"]) + sf.BAND_GLUE)) < 1e-9 and b.mountain and not b.valley, (b.width, b.mountain, b.valley)
assert "band" not in by_key(rim) and not any("8 帯" in x for x in steps(rim))
# 短い足（pivot_above_rim が 7 以下）は帯を足さず、部品表と手順 10 にも書かない。既定の扇（28 枚・高さ 48）では、短い足は
# 扇の開く角の検査（F5.fan_clearance）で落ちるので、検査に通る小さな扇（6 枚・幅 5・高さ 30）で見る（検品の指摘: 既定の扇では
# どの組も検査で飛ばされ、下の決まりが 1 度も回っていなかった）
short = {**tab, "fold_count": 6, "fold_width": 5, "fold_height": 30}
checked = 0
for piv in (2, 4, 7):
    q = {**short, "pivot_above_rim": piv}
    assert not sf.check_range(q) and not sf.check_physics(q), (piv, [f.line() for f in sf.check_physics(q)])
    checked += 1
    assert sf.band_width(q) is None and "band" not in by_key(q), piv
    assert not any(r["key"] == "band" for r in sf.bom(q)) and not any("8 帯" in x for x in steps(q)), piv
    assert any(x.startswith("4 扇の真ん中の足を、糊代の境の破線で折り") for x in steps(q)), steps(q)
assert checked == 3, checked
assert sf.band_width({**tab, "pivot_above_rim": 8}) == 4  # 8 から 4mm の帯（糊代より上 6mm から 2mm 残す）
# 溝の矢印: つまみの形だけ。範囲の端のつまみの幅でも、部品の内にあり、穴・折り線・糊代にかからない
seen = 0
for kw in (sf.RANGES["knob_width"][0], tab["knob_width"], sf.RANGES["knob_width"][1]):
    q = {**tab, "knob_width": kw}
    if sf.check_range(q) or sf.check_physics(q):
        continue
    seen += 1
    tube = by_key(q)["tube"]
    arrows = [a for a in tube.art if a["kind"] == "mark" and a.get("mark") == "slot"]
    assert len(arrows) == 2, (kw, len(arrows))
    H = q["tube_height"]
    for a in arrows:
        ys = [y for _, y in a["pts"]]
        assert min(ys) >= H - 12 - 1e-9 and max(ys) <= H - 0.5 + 1e-9, (kw, ys)  # 下の端の近くから、溝の口の上まで
        assert a["pts"][0][1] > a["pts"][1][1], (kw, a["pts"])  # 下の端の側から上へ向かう
    assert check_art([tube]) == [], (kw, [f.line() for f in check_art([tube])])
assert seen >= 2, seen
assert not any(a.get("mark") == "slot" for a in by_key(stick)["tube"].art)
print("ok 御来迎の次の版（開く糸・溝の矢印・足の帯）")
