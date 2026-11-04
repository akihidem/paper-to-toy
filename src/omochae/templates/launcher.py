"""雛形 launcher: 紙のばね（貼り重ねた紙の腕・弓）だけで、柔らかく軽い紙の玉を飛ばす。子どもが使う物なので、安全を形の芯にする。

刷る形（form）は 2 つ。どちらも出典の図を見て起こした【解釈】で、名は推定。
- crossbow（コマ 8 左・弩か豆鉄砲。歌に 矢・玉・豆）: 赤い角筒の台（筒の中が玉の通り道）、左右の紙の腕、糸の弦、
  引き金の板。玉は紙を丸めた物。図では弓が 1 本で台を貫くが、紙では 1 本の帯を横に曲げられない（帯の幅の向きに硬い）ので、
  台の左右の壁に腕を 1 本ずつ貼る形に置き換えた。弦は左右の壁の細い溝を通って筒の中を横切り、筒の中の玉の真ん中を押す。
- bow（コマ 29 左・弓と毛玉の推定）: 少し曲げた棒に糸を張り、とげのある毛玉を糸で結んだ図。紙では、貼り重ねた紙の弓に
  糸の弦を張り、紙の房を丸めた毛玉を、弓の真ん中から糸で繋いでおく（遠くへ行かない）。
  図の毛玉が弓に結ばれている事からの【解釈】で、図の物が本当に飛ばす玩具かは分からない。

飛ばす物は柔らかく軽い紙だけ（丸めた紙・紙の房）。竹串・楊枝・豆は飛ばさない（部品表にも載せない）。

動きの見込み（F5.launch）の前提。どの値も実物では未確認:
- ばねは刷った紙の腕（弓）だけ。輪ゴムは使わない。輪ゴムの硬さは物によって桁で違い、型紙の検査で決められないため。
  弦は伸びない糸で、張らずに（たるまない程度に）結ぶ。張って結ぶと引く前から力がたまり、下の上限の見込みが崩れる。
- 硬さ k は寸法から出す: 紙 LAYERS 枚を貼り重ねた帯を片持ちの梁と見て、1 本の k₁ = 3·E·I/L³（I = 幅·(枚数·厚さ)³/12）。
  弩の腕は L = arm_len、弓は手で持つ真ん中から両端までの L = bow_span/2。どちらも梁が 2 本。
  紙の縦弾性係数 E は E_HIGH = 6GPa（ふつうの紙で言われる 2〜6GPa ほどの高い側。手元で測っていない）で数え、柔らかい紙
  なら実物の k はこれより小さい（安全の側）。紙が厚い・硬い時に越えないよう、組む前に腕の先に硬貨を下げて下がる長さを
  測り、tip_sag_min より下がらなければ使わない（steps の止めの条件）。
- ためる力の上限: 弦の真ん中を x 引く時、腕の先が下がる長さは x を越えない（糸は伸びないので）。梁 2 本にためる力は
  2·½·k₁·δ² ≦ k₁·x² ＝ ½·(2k₁)·x²。これを E = ½·k·x²（k = 2k₁）と書く。弦の角度の効き・紙のへたり・空気の抵抗は入れない。
  玉に渡る力はこの E より小さいので、E を上限の見込みに使う。
- 既定の寸法（厚さ 0.2mm・幅 9mm・腕 60mm・引き 25mm）で、弩は k ≒ 64N/m・E ≒ 20mJ、弓（170mm）は k ≒ 22N/m・E ≒ 7mJ。
- E の上限 ENERGY_CAP_MJ = 30mJ は、この雛形が選んだ余裕の値で、規格の値ではない。選んだ理由: 既定の弩で 20mJ に
  なり、紙の厚さが 1 割ほど増えるか、引く長さが 2 割ほど増えると越える所に置いて、強くしすぎた寸法を落とすため。参考に、飛ぶ物の力の
  目安として 0.08J という数を聞くが、出所も原文も確かめていない目安なので、上限の根拠にはしていない（半分より下ではある）。
  玉の速さの上限の見込みは √(2E/m)（既定で 8m/s 前後）。
- 引く長さ x が E を決めるので、引ける所の限りを紙に刷る。弩は弦の溝が根元から x + 1mm で終わり（溝の端が止め）、
  引き金の切れ込みがその x の所にある（引ける所は 1 つだけで、引く長さは変えられない）。弓は手で引くので、弓の真ん中に貼る引き止めの帯に x の所の線を刷る。
  線を越えて引けば E は上限を越えうる（紙では引くのを止められない。組み方の文で言う）。
- 玉の重さは紙の面積 × 面密度。丸めた紙の玉の直径は、紙の辺の 0.3 倍より大きくはまとまらないと見込む（推定。実物で未確認）。
- 先の太さ: 玉の直径が MIN_NOSE より細いと、目のくぼみに入りうるので落とす。毛玉も、房を広げた太さでは見ない。
  当たると房はつぶれ、芯が先になるため。毛玉の芯は弩の玉と同じ丸めた紙の玉（ball_d）で、房の帯はその玉に巻く。
  玉の大きさは型紙の玉の物差しの穴で合わせ、床の範囲は穴から GAUGE_TOL 内へ入れる（穴ちょうどの玉は決まらない）。
- 止めの条件で刷る下がりの長さは、式の値を mm の整数に切り上げる（四捨五入だと、上限を越える硬さの腕が通りうる）。
  弓は両側の梁が同じ硬さとして力を数えるので、両端を 1 つずつ測り、どちらかが足りなければ使わない。
- 穴と縁: 弦を結ぶ穴から紙の縁まで HOLE_MARGIN、引き金の切れ込みの奥と下に NOTCH_MARGIN を残す。狭いと弦に引かれて裂ける。
"""
import math

from ..model import Failure, Part

ID = "launcher"
DEFAULTS = {
    "form": "crossbow",
    # 台の角筒。長さと太さはコマ 8 の図の台の比（長さ : 太さ ≒ 8 : 1）を、玉が中を通る太さに合わせた見込み。
    "stock_length": 150, "stock_w": 20, "glue": 6,
    # 腕（弓）は紙を 4 枚に貼り重ねた帯。arm_w は 1 枚の幅（貼った後の帯の高さ）。
    "arm_len": 60, "arm_w": 9, "bow_span": 170,
    # paper_t は紙 1 枚の厚さ（mm）。ばねの硬さは厚さの 3 乗で効くので、紙を変えたら測って置き換える。
    "draw": 25, "paper_t": 0.2,
    "trigger_w": 10, "notch_depth": 4,
    "ball_paper": 64, "ball_d": 18,
    "fringe_len": 15, "tether": 400,
    # 150g/m² は厚めの紙の見込み。実物の紙を量ったら置き換える。
    "paper_gsm": 150,
}
RANGES = {
    "stock_length": (60, 185), "stock_w": (12, 30), "glue": (4, 10),
    "arm_len": (25, 70), "arm_w": (5, 14), "bow_span": (80, 185),
    "draw": (10, 60), "paper_t": (0.08, 0.5),
    "trigger_w": (6, 16), "notch_depth": (0.5, 10),
    "ball_paper": (30, 100), "ball_d": (8, 30),
    "fringe_len": (4, 25), "tether": (150, 800),
    "paper_gsm": (40, 300),
}
FORMS_ = ("crossbow", "bow")
# 刷る形を決める寸法（台で飛ばす弩か、手で持つ弓と毛玉か）。どちらも推定なので、寸法を直に渡す入口では必ず書かせる。
FORM = "form"
FORMS = FORMS_
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000008-L-launcher"
# 形ごとの出典。弩はコマ 8 左、弓と毛玉はコマ 29 左。形と合わない出典の印を刷らないため（compose が F1.source で落とす）。
SOURCES = {"crossbow": SOURCE, "bow": "NDL-1187053-R0000029-L-launcher"}

ENERGY_CAP_MJ = 30  # ためる力の上限（mJ）。前提は module の docstring
MASS_MIN, MASS_MAX = 0.1, 1.0  # 玉の重さの範囲（g）。軽すぎると速くなり、重すぎると当たった時に重い
MIN_NOSE = 15  # 玉の先の太さの下限（mm）
CRUMPLE = 0.3  # 丸めた紙の玉の直径 ÷ 紙の辺 の上限の見込み（推定）
HOLE_MARGIN = 3  # 穴・溝から紙の縁（折り線・糊代）までの見込み
NOTCH_MARGIN = 3  # 引き金の切れ込みの奥と下に残す紙の幅
NOTCH_MIN = 1.5  # 切れ込みがこれより浅いと弦が掛からない
HOLE_R = 0.8  # 弦の糸を通す穴
LAYERS = 4  # 腕と弓を貼り重ねる枚数。1 枚では柔らかすぎる（docstring の梁の見込み）
ROOT = 10  # 腕の根元の糊代の長さ。台の横の壁に貼る
FRONT = ROOT + 4  # 台の前の端から腕の根元（弦の休む所）まで
SLIT = 2  # 弦が動く溝の幅
SLOT = 1.5  # 引き金を差す切れ込みの幅
GRIP = 14  # 引き金の台の上に出るつまみの長さ
BELOW = 4  # 引き金を台の底の切れ込みに差し込む長さ。上と下の 2 点で支え、弦に引かれて倒れないように
TOOTH, TOOTH_GAP, POM_BASE, POM_TEETH = 3, 1, 6, 25  # 毛玉の房の帯（房の幅・すき間・上の帯・房の数）
POM_LEN = POM_TEETH * TOOTH + (POM_TEETH - 1) * TOOTH_GAP  # 房の帯の長さ（99mm）。刷る外形と重さの式が同じ値を使う
TETHER_OFF = 10  # 毛玉の糸の穴を弓の真ん中からずらす長さ。真ん中には引き止めの帯の糊代を貼るため
STOP_W, STOP_BASE, STOP_TAIL = 8, 8, 6  # 引き止めの帯の幅・弓に貼る糊代・線の後ろの余り
E_HIGH = 6000  # 紙の縦弾性係数の高い側の見込み（N/mm²＝6GPa）。前提は module の docstring
COIN_G = 22.5  # 腕の硬さを確かめる重り: 10 円玉 5 枚（1 枚 4.5g）
SAG_READ = 3  # 刷った物差しで読める下がりの小ささの限り（mm）
GAUGE_TOL = 0.5  # 玉の物差しの穴と、床の玉の範囲の間の余り。穴の大きさちょうどの玉は通るか通らないか決まらないため
BARREL_PLAY = (1, 4)  # 玉の直径は筒の太さよりこの範囲で細い。きついと詰まり、ゆるいと弦が玉の下を抜ける
RED, DARK, RING, BOW, PAPER, POM, INK = "#b0533a", "#6b3b2b", "#2f2a26", "#e4dac0", "#efe9da", "#e2cc8f", "#3b3a34"
TITLES = {"crossbow": "台で飛ばす弩", "bow": "弓と毛玉"}
SAFETY = "人や動物に向けない・顔の高さで飛ばさない"


def title(p):
    return TITLES[p["form"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "form": FORMS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "form":
            if v not in FORMS:
                out.append(Failure("F5.range", k, f"{v} は {FORMS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


def beam_len(p):
    """片持ちの梁 1 本の長さ（mm）。弩は腕、弓は真ん中から端まで。"""
    return p["arm_len"] if p["form"] == "crossbow" else p["bow_span"] / 2


def arm_k(p):
    """梁 1 本の先の硬さ k₁ = 3EI/L³（N/m）。E は E_HIGH（硬い側）。I は貼り重ねた帯を 1 枚の板と見る（よく貼れた時が一番硬い）。"""
    t = LAYERS * p["paper_t"]
    inertia = p["arm_w"] * t ** 3 / 12
    return 3 * E_HIGH * inertia / beam_len(p) ** 3 * 1000  # N/mm → N/m


def spring_k(p):
    """弦の真ん中を引いた時のためる力の見込みに使う k = 2k₁（N/m）。前提は module の docstring。"""
    return 2 * arm_k(p)


def tip_sag_min(p):
    """腕（弓の片側）の先に COIN_G の重りを下げた時、少なくとも下がるはずの長さ（mm）。これより下がらない腕は硬すぎて使わない。"""
    return COIN_G / 1000 * 9.8 / arm_k(p) * 1000


def energy_mj(p):
    """ためる力 ½·k·x²（mJ）。k は N/m、x は mm なので m に直す。"""
    return 0.5 * spring_k(p) * (p["draw"] / 1000) ** 2 * 1000


def _teeth():
    return POM_TEETH


def projectile_mass(p):
    """玉の重さ（g）。丸める紙の四角の面積に、弓は房の帯（芯の玉に巻く）の面積を足して、面密度を掛ける。"""
    area = p["ball_paper"] ** 2
    if p["form"] == "bow":
        area += POM_LEN * POM_BASE + _teeth() * TOOTH * p["fringe_len"]
    return area * p["paper_gsm"] * 1e-6


def nose_d(p):
    """玉の先の太さ（mm）。どちらの形も丸めた紙の玉の直径（ball_d）。毛玉の房は当たるとつぶれるので数えない。"""
    return p["ball_d"]


def speed_bound(p):
    """玉の速さの上限の見込み（m/s）。ためた力が全部玉に渡ったとした時。"""
    return math.sqrt(2 * energy_mj(p) / 1000 / (projectile_mass(p) / 1000))


def gauge_holes(p):
    """玉の物差しの 2 つの穴の直径。小さい穴は通らない（先が太い）、大きい穴は通る（弩は筒に入る。弓は芯が大きすぎない）。"""
    if p["form"] == "bow":
        return MIN_NOSE, MIN_NOSE + 6
    w = p["stock_w"]
    return max(MIN_NOSE, w - BARREL_PLAY[1]), w - BARREL_PLAY[0]


def sag_print(p):
    """止めの条件に刷る下がりの長さ（mm の整数）。切り上げて、刷った値を満たす腕が式の値も満たすようにする。"""
    return math.ceil(tip_sag_min(p) - 1e-9)


def trigger_x(p):
    """台の前の端から、引いた弦が掛かる所（引き金の前の縁）まで。"""
    return FRONT + p["draw"]


def check_physics(p):
    """F5.launch: ためる力・玉の重さ・先の太さ・穴と切れ込みの縁・弩の筒と玉の合い方を見る。前提は module の docstring。"""
    out = []
    e = energy_mj(p)
    if e > ENERGY_CAP_MJ:
        out.append(Failure("F5.launch", "ばね", f"ためる力 ½kx² = {e:.1f}mJ（k {spring_k(p):.0f}N/m・引き {p['draw']:g}mm）が {ENERGY_CAP_MJ}mJ を超える"))
    m = projectile_mass(p)
    if not MASS_MIN <= m <= MASS_MAX:
        out.append(Failure("F5.launch", "玉", f"玉の重さ {m:.2f}g が {MASS_MIN}〜{MASS_MAX}g の外"))
    if nose_d(p) < MIN_NOSE:
        out.append(Failure("F5.launch", "玉", f"玉の先の太さ {nose_d(p):g}mm が {MIN_NOSE}mm より細い"))
    if tip_sag_min(p) < SAG_READ:
        out.append(Failure("F5.launch", "ばね", f"重りで腕の先が {tip_sag_min(p):.1f}mm しか下がらず、硬すぎないかを刷った物差しで確かめられない（{SAG_READ}mm 以上）"))
    w = p["arm_w"]
    if w / 2 - HOLE_R < HOLE_MARGIN:
        where = "腕" if p["form"] == "crossbow" else "弓"
        out.append(Failure("F5.launch", where, f"弦の穴から{where}の縁まで {w / 2 - HOLE_R:.1f}mm で、引くと裂けやすい（{HOLE_MARGIN}mm 以上）"))
    d = p["ball_d"]
    if d > CRUMPLE * p["ball_paper"]:
        out.append(Failure("F5.launch", "玉", f"{p['ball_paper']:g}mm の紙では直径 {d:g}mm の玉にまとまらない（{CRUMPLE * p['ball_paper']:.1f}mm まで）"))
    # 物差しの穴の大きさちょうどの玉は、通るか通らないか決まらない。床の範囲は穴から GAUGE_TOL 内へ入れる。
    small, big = gauge_holes(p)
    lo, hi = small + GAUGE_TOL, big - GAUGE_TOL
    if not lo <= d <= hi:
        out.append(Failure("F5.launch", "玉", f"玉 {d:g}mm が物差しの穴（{small:g}・{big:g}mm）に合わない（{lo:g}〜{hi:g}mm）"))
    if p["form"] == "crossbow":
        sw, g = p["stock_w"], p["glue"]
        if p["arm_w"] > sw - 2:
            out.append(Failure("F5.launch", "腕", "腕の根元が台の横の壁に収まらない"))
        if sw / 2 - SLIT / 2 - g < HOLE_MARGIN:
            out.append(Failure("F5.launch", "弦の溝", f"弦の溝から糊代まで {sw / 2 - SLIT / 2 - g:.1f}mm で、裂けやすい（{HOLE_MARGIN}mm 以上）"))
        rear = p["stock_length"] - (trigger_x(p) + p["trigger_w"] + 1)
        if rear < HOLE_MARGIN:
            out.append(Failure("F5.launch", "引き金", f"引き金の切れ込みから台の後ろの端まで {rear:.1f}mm（{HOLE_MARGIN}mm 以上）"))
        nd = p["notch_depth"]
        if nd < NOTCH_MIN:
            out.append(Failure("F5.launch", "引き金", f"切れ込み {nd:g}mm は浅く、弦が掛からない（{NOTCH_MIN}mm 以上）"))
        if p["trigger_w"] - nd < NOTCH_MARGIN:
            out.append(Failure("F5.launch", "引き金", f"切れ込みの奥に {p['trigger_w'] - nd:g}mm しか残らず、弦に引かれて裂ける（{NOTCH_MARGIN}mm 以上）"))
    return out


def _rect(x0, y0, x1, y1, fill, inset=0.2):
    return {"kind": "poly", "pts": [(x0 + inset, y0 + inset), (x1 - inset, y0 + inset), (x1 - inset, y1 - inset), (x0 + inset, y1 - inset)], "fill": fill}


def _stock(p):
    """台の角筒の展開。上から糊代・上の面・右の壁・底・左の壁。x は台の前の端から後ろへ。
    色はコマ 8 の図の比: 前の 3 割は濃い茶（図の台の前の太い所）、後ろの端の 6% は黒い帯（図の後ろの口金）、残りは朱。"""
    L, w, g = p["stock_length"], p["stock_w"], p["glue"]
    rows = [g, g + w, g + 2 * w, g + 3 * w, g + 4 * w]
    part = Part(1, "stock", "台", [(2, 0), (L - 2, 0), (L, g), (L, rows[4]), (0, rows[4]), (0, g)], label_xy=(L * 0.45, g + 1.5), label="1 台")
    part.valley = [((0, y), (L, y)) for y in rows[:4]]
    part.glue = [[(2, 0), (L - 2, 0), (L, g), (0, g)]]
    front, ring = 0.3 * L, 0.94 * L
    for y0, y1 in zip(rows, rows[1:]):
        part.art += [_rect(0, y0, front, y1, DARK), _rect(front, y0, ring, y1, RED), _rect(ring, y0, L, y1, RING)]
    # 上の面の真ん中の筋（図の台の溝の線）。
    part.art.append({"kind": "line", "pts": [(front + 2, g + w / 2), (ring - 2, g + w / 2)], "stroke": DARK, "sw": 0.4})
    tx, d = trigger_x(p), p["draw"]
    for side in (rows[1], rows[3]):
        # 腕の根元を貼る所の印（腕の色）。弦の溝はその後ろから引き金まで。
        aw = p["arm_w"]
        part.art.append(_rect(FRONT - ROOT, side + (w - aw) / 2, FRONT, side + (w + aw) / 2, BOW, 0))
        part.cuts.append((FRONT, side + w / 2 - SLIT / 2, d + 1, SLIT))
    for face in (rows[0], rows[2]):
        # 引き金を上の面と底の 2 か所に差す切れ込み。
        part.cuts.append((tx, face + w / 2 - SLOT / 2, p["trigger_w"] + 1, SLOT))
    return part


def _laminate(number, key, name, length, p, glue_root):
    """紙を LAYERS 枚に貼り重ねる帯。幅の向きに arm_w ずつの面を、谷・山・谷と蛇腹に折り重ねる。
    谷で合わさる 1-2 枚目と 3-4 枚目は表どうし、山で合わさる 2-3 枚目は裏どうしが重なる。表の面は全部が貼る面になるので、
    表は全部糊代に刷る（絵は置かない。外に見えるのは 1 枚目と 4 枚目の裏）。裏どうしの面は刷れないので steps で言う。"""
    aw = p["arm_w"]
    H = LAYERS * aw
    part = Part(number, key, name, [(0, 0), (length, 0), (length, H), (0, H)], label_xy=(length - 4.5, 1), label=str(number))
    for k in range(1, LAYERS):
        line = ((0, k * aw), (length, k * aw))
        (part.mountain if k % 2 == 0 else part.valley).append(line)
    part.glue = [[(0, 0), (length, 0), (length, H), (0, H)]]
    if glue_root:
        part.valley.append(((ROOT, 0), (ROOT, H)))
    return part


def _arm(number, key, name, p):
    L = ROOT + p["arm_len"]
    part = _laminate(number, key, name, L, p, True)
    aw = p["arm_w"]
    # 腕の先の弦の穴。どの面も真ん中に置くと、折り重ねた時に 4 枚の穴がそろう。
    part.holes = [(L - HOLE_MARGIN - HOLE_R, k * aw + aw / 2, HOLE_R) for k in range(LAYERS)]
    return part


def _stave(p):
    L = p["bow_span"]
    part = _laminate(1, "stave", "弓", L, p, False)
    aw = p["arm_w"]
    # 両端は弦の糸、真ん中の脇は毛玉の糸。真ん中には引き止めの帯の糊代を貼るので、毛玉の穴は TETHER_OFF ずらす。
    xs = (HOLE_MARGIN + HOLE_R, L / 2 + TETHER_OFF, L - HOLE_MARGIN - HOLE_R)
    part.holes = [(x, k * aw + aw / 2, HOLE_R) for x in xs for k in range(LAYERS)]
    part.label_xy = (L / 2 + 3, 1)
    return part


def _trigger(p):
    """引き金の板。上の GRIP がつまみ、その下を台の上の面と底の切れ込みに差す。前の縁（x=0）の切れ込みに弦を掛ける。
    切れ込みは筒の太さの真ん中の高さ（弦の高さ）に来る。"""
    tw, w, nd = p["trigger_w"], p["stock_w"], p["notch_depth"]
    T = GRIP + w + BELOW
    yn = GRIP + w / 2
    pts = [(0, 0), (tw, 0), (tw, T), (0, T), (0, yn + 1), (nd, yn + 1), (nd, yn - 1), (0, yn - 1)]
    part = Part(4, "trigger", "引き金", pts, label_xy=(1, 1.5), label="4")
    # コマ 8 の図の S 字の掛け金の濃い色を、つまみに塗る。
    part.art = [_rect(0, 0, tw, GRIP - 1, DARK)]
    return part


def _ball(p):
    s = p["ball_paper"]
    part = Part(5, "ball", "玉の紙", [(0, 0), (s, 0), (s, s), (0, s)], label_xy=(1, 1.5), label="5 玉")
    part.art = [_rect(0, 0, s, s, PAPER)] + [{"kind": "poly", "pts": [(x - 1, y - 1), (x + 1, y - 1), (x + 1, y + 1), (x - 1, y + 1)], "fill": "#c9bfa6"}
                                           for x in (s * 0.3, s * 0.7) for y in (s * 0.3, s * 0.7)]
    return part


def _gauge(p):
    small, big = gauge_holes(p)
    m = HOLE_MARGIN
    W, H = m + small + m + big + m, big + 2 * m
    part = Part(6, "gauge", "玉の物差し", [(0, 0), (W, 0), (W, H), (0, H)], label_xy=(1, 0.3), label="6")
    part.holes = [(m + small / 2, H / 2, small / 2), (m + small + m + big / 2, H / 2, big / 2)]
    return part


def _drawstop(p):
    """弓の引き止めの帯。糊代を弓の真ん中の裏に貼り、帯を引く向き（後ろ）へ出す。弓の面から draw の所に線を刷り、
    毛玉と弦をその線より後ろへ引かない。紙の帯なので引くのを止める力は無く、目で見る印にとどまる。"""
    L = STOP_BASE + p["draw"] + STOP_TAIL
    part = Part(3, "drawstop", "引き止めの帯", [(0, 0), (STOP_W, 0), (STOP_W, L), (0, L)], label_xy=(0.8, STOP_BASE + 1), label="3")
    part.valley = [((0, STOP_BASE), (STOP_W, STOP_BASE))]
    part.glue = [[(0, 0), (STOP_W, 0), (STOP_W, STOP_BASE), (0, STOP_BASE)]]
    y = STOP_BASE + p["draw"]
    part.art = [_rect(0, STOP_BASE, STOP_W, y - 0.5, PAPER), _rect(0, y + 0.5, STOP_W, L, DARK),
                {"kind": "line", "pts": [(0.3, y), (STOP_W - 0.3, y)], "stroke": INK, "sw": 0.6}]
    return part


def _pompom(p):
    """毛玉の房の帯。上の帯（POM_BASE）を芯に巻き、房を広げる。房は切り込みで分ける。"""
    n, f = _teeth(), p["fringe_len"]
    Lp = n * TOOTH + (n - 1) * TOOTH_GAP
    pts = [(0, 0), (Lp, 0)]
    for i in reversed(range(n)):
        a = i * (TOOTH + TOOTH_GAP)
        pts += [(a + TOOTH, POM_BASE + f), (a, POM_BASE + f)]
        if i:
            pts += [(a, POM_BASE), (a - TOOTH_GAP, POM_BASE)]
    part = Part(2, "pompom", "毛玉の房", pts, label_xy=(0.5, 1), label="2 毛玉")
    part.glue = [[(0, 0), (Lp, 0), (Lp, POM_BASE), (0, POM_BASE)]]
    part.art = [_rect(i * (TOOTH + TOOTH_GAP), POM_BASE, i * (TOOTH + TOOTH_GAP) + TOOTH, POM_BASE + f, POM, 0.15) for i in range(n)]
    return part


def parts(p):
    if p["form"] == "crossbow":
        return [_stock(p), _arm(2, "arma", "右の腕", p), _arm(3, "armb", "左の腕", p), _trigger(p), _ball(p), _gauge(p)]
    return [_stave(p), _pompom(p), _drawstop(p), _ball(p), _gauge(p)]


def place(by_key, page, top, gap):
    """弩: 1 段目に台、2 段目に腕 2 本、3 段目に引き金・物差し・玉の紙。弓: 1 段目に弓、2 段目に房。
    どちらも説明の列は部品の下に印字域の幅いっぱいで置く（物差しの 100mm が入るように）。"""
    x0 = page.x0
    if "stock" in by_key:
        st = by_key["stock"]
        st.x, st.y = x0, top
        y = top + st.height + gap
        a, b, ball = by_key["arma"], by_key["armb"], by_key["ball"]
        a.x, a.y = x0, y
        b.x, b.y = x0 + a.width + gap, y
        y2 = y + a.height + gap
        tr, ga = by_key["trigger"], by_key["gauge"]
        tr.x, tr.y = x0, y2
        ga.x, ga.y = x0 + tr.width + gap, y2
        ball.x, ball.y = ga.x + ga.width + gap, y2
        bottom = max(ball.y + ball.height, tr.y + tr.height, ga.y + ga.height)
    else:
        sv, pom = by_key["stave"], by_key["pompom"]
        sv.x, sv.y = x0, top
        pom.x, pom.y = x0, top + sv.height + gap
        ds = by_key["drawstop"]
        ds.x, ds.y = pom.x + pom.width + gap, pom.y
        y3 = max(pom.y + pom.height, ds.y + ds.height) + gap
        ga, ball = by_key["gauge"], by_key["ball"]
        ga.x, ga.y = x0, y3
        ball.x, ball.y = x0 + ga.width + gap, y3
        bottom = max(ga.y + ga.height, ball.y + ball.height)
    return bottom + gap, page.x1 - x0, x0


def bom(p):
    paper = f"紙（厚めの紙・{p['paper_gsm']}g/m² の見込み）"
    why = "家庭のプリンタで刷って作るため"
    if p["form"] == "crossbow":
        string = 2 * p["arm_len"] + p["stock_w"] + 40
        return [
            {"number": 1, "key": "stock", "name": "台", "qty": 1, "material": paper, "substituted": True, "original_guess": "木か竹に朱塗り（図の色からの推定）", "reason": why},
            {"number": 2, "key": "arma", "name": "右の腕", "qty": 1, "material": paper, "substituted": True, "original_guess": "竹の弓（図の白い弓からの推定）", "reason": "竹を削るのは子どもに危ないので、紙を貼り重ねたばねにするため"},
            {"number": 3, "key": "armb", "name": "左の腕", "qty": 1, "material": paper, "substituted": True, "original_guess": "竹の弓（同じ）", "reason": "同じ"},
            {"number": 4, "key": "trigger", "name": "引き金", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図の S 字の掛け金）", "reason": why},
            {"number": 5, "key": "ball", "name": "玉の紙", "qty": 1, "material": f"{paper}を丸めた玉", "substituted": True, "original_guess": "豆か玉（歌の 豆・玉 による推定）", "reason": "豆や硬い玉は当たると痛く、口に入るので、柔らかく軽い紙にするため"},
            {"number": 6, "key": "gauge", "name": "玉の物差し", "qty": 1, "material": paper, "substituted": False, "original_guess": "", "reason": ""},
            {"number": 8, "key": "string", "name": "弦", "qty": 1, "material": f"木綿の糸（{string:g}mm に切る）", "substituted": True, "original_guess": "糸（図の線による）", "reason": "家にあるため"},
        ]
    tether = p["tether"] + 30  # 結び目 2 つ分の余り
    return [
        {"number": 1, "key": "stave", "name": "弓", "qty": 1, "material": paper, "substituted": True, "original_guess": "竹か木の棒（図の曲がった棒）", "reason": "竹を削るのは子どもに危ないので、紙を貼り重ねたばねにするため"},
        {"number": 2, "key": "pompom", "name": "毛玉の房", "qty": 1, "material": paper, "substituted": True, "original_guess": "毛か糸の玉（図のとげのある玉からの推定）", "reason": "柔らかく軽い玉を刷って作るため"},
        {"number": 5, "key": "ball", "name": "芯の玉の紙", "qty": 1, "material": f"{paper}を丸めた玉", "substituted": True, "original_guess": "不明（図の毛玉の芯）", "reason": "当たって房がつぶれても先が太く柔らかいよう、芯を丸めた紙の玉にするため"},
        {"number": 6, "key": "gauge", "name": "玉の物差し", "qty": 1, "material": paper, "substituted": False, "original_guess": "", "reason": ""},
        {"number": 3, "key": "drawstop", "name": "引き止めの帯", "qty": 1, "material": paper, "substituted": False, "original_guess": "", "reason": ""},
        {"number": 7, "key": "string", "name": "弦", "qty": 1, "material": f"木綿の糸（{p['bow_span'] + 40:g}mm に切る）", "substituted": True, "original_guess": "糸（図の線による）", "reason": "伸びない糸にして、ばねを刷った紙の弓だけにするため（輪ゴムは硬さが決まらない）"},
        {"number": 8, "key": "tether", "name": "毛玉の糸", "qty": 1, "material": f"木綿の糸（{tether:g}mm と、房を縛る 100mm）", "substituted": True, "original_guess": "糸（図の毛玉の糸）", "reason": "毛玉が遠くへ飛ばないよう弓に繋いでおくため"},
    ]


def materials(p):
    # 行の位置でなく key で引く。形によって部品表の行が違うので、位置で引くと別の行を刷る。
    by = {r["key"]: r for r in bom(p)}
    if p["form"] == "crossbow":
        return [f"{by['stock']['material']}を 1 枚", "のり、はさみ、定規（溝はカッターで大人が切る）", "穴あけ用の竹串 1 本（穴をあけるだけで、飛ばさない）", by["string"]["material"], "腕の硬さを確かめる 10 円玉 5 枚", f"飛ばすのは紙の玉だけ。{SAFETY}"]
    return [f"{by['stave']['material']}を 1 枚", "のり、はさみ、定規", "穴あけ用の竹串 1 本（穴をあけるだけで、飛ばさない）", by["string"]["material"], by["tether"]["material"], "弓の硬さを確かめる 10 円玉 5 枚", f"飛ばすのは紙の毛玉だけ。{SAFETY}"]


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる", f"約束: {SAFETY}。飛ばすのは紙の玉だけにする（竹串・楊枝・豆は飛ばさない）"]
    if p["form"] == "crossbow":
        tx = trigger_x(p)
        out += ["部品を実線で切る。1 台の細い溝と切れ込み、6 玉の物差しの穴はカッターで大人が切る",
                "2・3 腕を破線で 4 枚に蛇腹に折り重ねる。表の糊代の面と、2 枚目と 3 枚目の裏どうしも貼る（3 つの面を全部貼る）。乾いてから根元を直角に折る",
                "乾いたら、腕の先の穴を竹串の先で 4 枚とも通してあける（竹串は穴あけだけに使い、飛ばさない）",
                f"止めの条件: 腕の根元を机の端で押さえ、腕を横にして先の穴に 10 円玉 5 枚（{COIN_G:g}g）を糸で下げる。左右の腕を 1 本ずつ測る。先が {sag_print(p)}mm 以上下がらなければ、紙が硬すぎるので、その腕は使わない（刷った物差しで測る）",
                "1 台を破線で谷折りして角筒にし、糊代で貼る",
                "腕の根元を台の左右の壁の印に貼る（腕は横へ出し、先は後ろへ引ける向き）",
                "糸を右の腕の先の穴に結び、左右の溝を通して筒の中を横切らせ、左の腕の先の穴に結ぶ。張らずに、たるまない程度に結ぶ",
                "5 玉の紙を丸め、6 物差しの小さい穴を通らず大きい穴を通る大きさにする",
                "玉を台の前の口から入れ、弦の前まで転がす",
                f"弦を溝に沿って前の端から {tx:g}mm（溝の端）まで引く。溝の端より先へは引かない（引ける所はここ 1 つで、引く長さは変えない）。4 引き金を上の面と底の切れ込みに差して、前の縁の切れ込みに弦を掛ける",
                "遠くの壁か床に向け、引き金を真上に引き抜くと弦が外れて玉が出る"]
    else:
        out += ["部品を実線で切る。2 房の切り込みは、はさみで上の帯の手前まで",
                "1 弓を破線で 4 枚に蛇腹に折り重ねる。表の糊代の面と、2 枚目と 3 枚目の裏どうしも貼る（3 つの面を全部貼る）",
                "乾いたら、両端の穴と真ん中の穴（真ん中から少し横の毛玉の穴）を竹串の先で 4 枚とも通してあける（竹串は穴あけだけに使い、飛ばさない）",
                f"止めの条件: 弓の真ん中を机の端で押さえ、端の穴に 10 円玉 5 枚（{COIN_G:g}g）を糸で下げる。両端を 1 つずつ測る。どちらかの端が {sag_print(p)}mm 以上下がらなければ、紙が硬すぎるので、その弓は使わない（刷った物差しで測る）",
                f"弦の糸を両端の穴に結ぶ。張らずに、たるまない程度に結ぶ（張って結ぶと引く前から力がたまる）",
                "5 芯の玉の紙を丸め、6 物差しの小さい穴を通らず大きい穴を通る大きさにする",
                "2 房の上の帯を芯の玉に巻いて貼り、根元を糸で縛る。房を外へ広げて毛玉にする（当たると房はつぶれ、芯の玉が先になる）",
                f"毛玉の糸を {p['tether']:g}mm に切り、毛玉の根元と弓の毛玉の穴（真ん中の横）に結ぶ",
                "3 引き止めの帯の糊代を折り、弓の真ん中の裏に貼って、帯を後ろへ出す",
                f"毛玉を弦の真ん中に当て、3 引き止めの帯の黒い線（弓から {p['draw']:g}mm）まで引いて放す。線より後ろへ引かない（強くなりすぎる）。毛玉は糸の長さまでしか飛ばない"]
    if p["form"] == "crossbow":
        out.append("どこまで飛ぶか見る。引く長さは変えない（溝の端の 1 つだけ）")
    else:
        out.append("黒い線より手前の所で引く長さを変えて、どこまで飛ぶか比べる。線は越えない")
    return out


RESULTS = ("飛んだ", "飛ばない")


def measures(p):
    """飛ぶかの二択でなく、飛び方を言葉か絵で予想する（ほかの雛形と同じ形）。引く長さを変えて試せるのは、線より手前で引ける弓だけ。
    弩は引ける所が 1 つなので、引く長さを変える問いを置かない。"""
    if p["form"] == "crossbow":
        return {"predict": "引き金を抜くと、玉はどう飛ぶと思いますか（言葉か絵で）", "rows": [[("飛んだ所", 40)]]}
    return {"predict": "黒い線より手前で引く長さを変えると、毛玉の飛び方はどう変わると思いますか（言葉か絵で）", "rows": [[("引いた長さと飛んだ所", 40)]]}


def diagram(x, y, w, h, p):
    """組み上がりを上から見た絵。寸法の図ではなく、台（弓）・腕・弦・玉の並びを見せるだけ。"""
    if p["form"] == "crossbow":
        span = 2 * p["arm_len"] + p["stock_w"]
        s = min(w / span, h / p["stock_length"])
        cx = x + w / 2
        sw, L = p["stock_w"] * s, p["stock_length"] * s
        shapes = [{"kind": "rect", "x": cx - sw / 2, "y": y, "w": sw, "h": L}]
        ay = y + FRONT * s
        shapes += [{"kind": "line", "x1": cx - sw / 2, "y1": ay, "x2": cx - sw / 2 - p["arm_len"] * s, "y2": ay},
                   {"kind": "line", "x1": cx + sw / 2, "y1": ay, "x2": cx + sw / 2 + p["arm_len"] * s, "y2": ay}]
        ty = y + trigger_x(p) * s
        shapes += [{"kind": "line", "x1": cx - sw / 2 - p["arm_len"] * s, "y1": ay, "x2": cx, "y2": ty, "dash": "1,0.6"},
                   {"kind": "line", "x1": cx + sw / 2 + p["arm_len"] * s, "y1": ay, "x2": cx, "y2": ty, "dash": "1,0.6"}]
        r = p["ball_d"] / 2 * s
        shapes.append({"kind": "rect", "x": cx - r, "y": ty - 2 * r, "w": 2 * r, "h": 2 * r})
        return shapes
    s = min(w / p["bow_span"], h / (p["draw"] + 40))
    cx, by = x + w / 2, y + 4
    half = p["bow_span"] / 2 * s
    shapes = [{"kind": "line", "x1": cx - half, "y1": by + 6, "x2": cx, "y2": by}, {"kind": "line", "x1": cx, "y1": by, "x2": cx + half, "y2": by + 6}]
    dy = by + 6 + p["draw"] * s
    shapes += [{"kind": "line", "x1": cx - half, "y1": by + 6, "x2": cx, "y2": dy, "dash": "1,0.6"}, {"kind": "line", "x1": cx, "y1": dy, "x2": cx + half, "y2": by + 6, "dash": "1,0.6"}]
    r = p["fringe_len"] * s
    shapes.append({"kind": "rect", "x": cx - r, "y": dy - 2 * r, "w": 2 * r, "h": 2 * r})
    return shapes
