"""雛形 wheel_cart の床 F5.wheel の式の要所を、境目の数点で確かめる。言葉で書いた条件は向きを間違えやすいので、ここで数える。"""
from omochae.floors import check_bom
from omochae.templates import wheel_cart as w

RAT = {**w.DEFAULTS, "ride": "rat"}
STICK = {**w.DEFAULTS, "ride": "stick"}


def msgs(p):
    out = w.check_physics(p)
    assert all(f.floor == "F5.wheel" for f in out), out
    return [f.where + ":" + f.message for f in out]


# 既定の寸法はどちらの形も通り、刷る部品は全部部品表に載る
for p in (RAT, STICK):
    assert msgs(p) == [], msgs(p)
    assert check_bom(w.bom(p), w.parts(p)) == []

# 1. 床: 半径 - 軸の高さ が MIN_GROUND ちょうどなら通り、それより小さければ落ちる（両方の形）
for p in (RAT, STICK):
    a = p["axle_height"]
    assert not any("床を擦る" in m for m in msgs({**p, "wheel_r": a + w.MIN_GROUND}))
    assert any("床を擦る" in m for m in msgs({**p, "wheel_r": a + w.MIN_GROUND - 0.5}))

# 2. 側面: 鼠車のすき間、前後の車輪どうし。春駒の二股の内の幅は、車輪の厚み（重ねた枚数で増える）で決まる
assert any("側面" in m for m in msgs({**RAT, "wheel_gap": w.MIN_SIDE_GAP - 0.5}))
assert not msgs({**RAT, "wheel_gap": w.MIN_SIDE_GAP})
# 胴 70mm・前後 12mm の時、軸の間は 46mm。半径 22 で車輪 2 つ 44mm + 1.5mm が入らない
assert any("前と後ろの軸の間" in m for m in msgs({**RAT, "wheel_r": 22.5}))
assert w.wheel_thickness({**STICK, "wheel_layers": 4}) > w.wheel_thickness(STICK)
thin = {**STICK, "fork_inner": 4, "stick_t": 3}
assert not any("内の幅" in m for m in msgs({**thin, "wheel_layers": 1}))  # 0.15 + 3 <= 4
assert any("内の幅" in m for m in msgs({**thin, "wheel_layers": 4}))  # 1.35 + 3 > 4
# 車輪の上の端が割り箸の先に当たる: 腕 34 - 差し込み 4 - 軸 7 - 半径 = すき間
assert any("割り箸の先" in m for m in msgs({**STICK, "wheel_r": 22}))
assert not any("割り箸の先" in m for m in msgs({**STICK, "wheel_r": 21.5}))

# 3. 穴の余裕（軸の高さ・前後の位置・胴の上の縁・二股の腕の幅）
assert any("軸の穴" == m.split(":")[0] for m in msgs({**RAT, "axle_height": 3, "wheel_r": 6}))
assert any("前の壁" in m for m in msgs({**RAT, "inset_front": 3}))
assert any("上の縁" in m for m in msgs({**RAT, "body_height": 20, "axle_height": 17, "wheel_r": 20}))
assert any("腕の縁" in m for m in msgs({**STICK, "fork_width": 7, "stick_t": 3}))

# 4. 重心: 対称なら真ん中。車輪の重さ（芯の厚紙）が重心を軸へ引くので、片側へ寄せた軸で倒れる・倒れないが分かれる
assert abs(w.cart_com_x(RAT) - RAT["body_length"] / 2) < 1e-9
tip = {**RAT, "body_length": 80, "inset_front": 45, "inset_rear": 10, "wheel_r": 10, "rider_at": 0.25}
assert any("倒れる" in m for m in msgs(tip))
# 同じ寸法で車輪の芯を増やすと、重い車輪が重心を前の軸の内へ引き、倒れなくなる
assert w.cart_com_x({**tip, "wheel_layers": 6}) > w.cart_com_x(tip)
assert not any("倒れる" in m for m in msgs({**tip, "wheel_layers": 6}))
# 人形を前へ寄せると重心も前へ動く（向きの確かめ）
assert w.cart_com_x({**RAT, "rider_at": 0.2}) < w.cart_com_x(RAT)
# 春駒は手で持つので重心は見ない
assert not any("重心" in m for m in msgs(STICK))
print("ok")
