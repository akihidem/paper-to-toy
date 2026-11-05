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
print("ok v9")
