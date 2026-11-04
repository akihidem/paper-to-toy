"""雛形 launcher: 紙のばね（貼り重ねた紙の腕・弓）か輪ゴム 1 本で、柔らかく軽い紙の玉を飛ばす。子どもが使う物なので、安全を形の芯にする。

刷る形（form）は 2 つ。どちらも出典の図を見て起こした【解釈】で、名は推定。
- crossbow（コマ 8 左・弩か豆鉄砲。歌に 矢・玉・豆）: 赤い角筒の台（筒の中が玉の通り道）、左右の紙の腕、糸の弦、
  引き金の板。玉は紙を丸めた物。図では弓が 1 本で台を貫くが、紙では 1 本の帯を横に曲げられない（帯の幅の向きに硬い）ので、
  台の左右の壁に腕を 1 本ずつ貼る形に置き換えた。弦は左右の壁の細い溝を通って筒の中を横切り、筒の中の玉の真ん中を押す。
- bow（コマ 29 左・弓と毛玉の推定）: 少し曲げた棒に糸を張り、とげのある毛玉を糸で結んだ図。紙では、貼り重ねた紙の弓に
  輪ゴム 1 本を弦に張り、紙の房を丸めた毛玉を、弓の真ん中から糸で繋いでおく（遠くへ行かない）。
  図の毛玉が弓に結ばれている事からの【解釈】で、図の物が本当に飛ばす玩具かは分からない。

飛ばす物は柔らかく軽い紙だけ（丸めた紙・紙の房）。竹串・楊枝・豆は飛ばさない（部品表にも載せない）。

動きの見込み（F5.launch）の前提。どの値も実物では未確認:
- ばねの力は引いた長さに比例し（線形）、ためる力は E = ½·k·x²。k（spring_k）は「弦の真ん中を引いた時の硬さ」で、
  寸法から出さず値として受ける。測り方は steps に書く（弦の真ん中に硬貨を下げ、下がった長さで割る）。
  弦の角度による増え方・紙の腕のへたり・空気の抵抗は入れない。玉に渡る力はこの E より小さいので、E を上限の見込みに使う。
- 既定の k = 40 N/m は桁の見込み: 厚さ 0.2mm の紙 4 枚を貼り重ねた腕（幅 9mm・長さ 45mm）を、片持ちの梁
  k = 3EI/L³ ・紙の縦弾性係数 E = 3GPa の見込みで数えると 1 本 約 38 N/m。貼り重ねずに 1 枚だと 1/64 で、ほとんど飛ばない。
- E の上限 ENERGY_CAP_MJ = 30mJ。玩具の安全の決まりで、飛ぶ物の運動の力の目安に 0.08J 前後が言われる（手元で原文を
  確かめていない）。その半分より下に余裕を取った。玉の速さの上限の見込みは √(2E/m)（既定で 8m/s 前後）。
- 玉の重さは紙の面積 × 面密度。丸めた紙の玉の直径は、紙の辺の 0.3 倍より大きくはまとまらないと見込む（推定。実物で未確認）。
- 先の太さ: 玉の直径（毛玉は房の長さの 2 倍）が MIN_NOSE より細いと、目のくぼみに入りうるので落とす。
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
    "arm_len": 45, "arm_w": 9, "bow_span": 170,
    "draw": 30, "spring_k": 40,
    "trigger_w": 10, "notch_depth": 4,
    "ball_paper": 64, "ball_d": 18,
    "fringe_len": 15, "tether": 400,
    # 150g/m² は厚めの紙の見込み。実物の紙を量ったら置き換える。
    "paper_gsm": 150,
}
RANGES = {
    "stock_length": (60, 185), "stock_w": (12, 30), "glue": (4, 10),
    "arm_len": (25, 70), "arm_w": (5, 14), "bow_span": (80, 185),
    "draw": (10, 60), "spring_k": (5, 200),
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
POM_LEN, TOOTH, TOOTH_GAP, POM_BASE = 100, 3, 1, 6  # 毛玉の房の帯
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


def energy_mj(p):
    """ためる力 ½·k·x²（mJ）。k は N/m、x は mm なので m に直す。"""
    return 0.5 * p["spring_k"] * (p["draw"] / 1000) ** 2 * 1000


def _teeth():
    return int((POM_LEN + TOOTH_GAP) // (TOOTH + TOOTH_GAP))


def projectile_mass(p):
    """玉の重さ（g）。弩は丸める紙の四角、弓は房の帯の面積に面密度を掛ける。"""
    if p["form"] == "crossbow":
        area = p["ball_paper"] ** 2
    else:
        area = POM_LEN * POM_BASE + _teeth() * TOOTH * p["fringe_len"]
    return area * p["paper_gsm"] * 1e-6


def nose_d(p):
    """玉の先の太さ（mm）。弩は丸めた玉の直径（ball_d・型紙の玉の物差しで合わせる）、弓は房を広げた直径（房の長さの 2 倍。芯の太さは入れない）。"""
    return p["ball_d"] if p["form"] == "crossbow" else 2 * p["fringe_len"]


def speed_bound(p):
    """玉の速さの上限の見込み（m/s）。ためた力が全部玉に渡ったとした時。"""
    return math.sqrt(2 * energy_mj(p) / 1000 / (projectile_mass(p) / 1000))


def gauge_holes(p):
    """玉の物差しの 2 つの穴の直径。小さい穴は通らない（先が太い）、大きい穴は通る（筒に入る）。"""
    w = p["stock_w"]
    return max(MIN_NOSE, w - BARREL_PLAY[1]), w - BARREL_PLAY[0]


def trigger_x(p):
    """台の前の端から、引いた弦が掛かる所（引き金の前の縁）まで。"""
    return FRONT + p["draw"]


def check_physics(p):
    """F5.launch: ためる力・玉の重さ・先の太さ・穴と切れ込みの縁・弩の筒と玉の合い方を見る。前提は module の docstring。"""
    out = []
    e = energy_mj(p)
    if e > ENERGY_CAP_MJ:
        out.append(Failure("F5.launch", "ばね", f"ためる力 ½kx² = {e:.1f}mJ（k {p['spring_k']:g}N/m・引き {p['draw']:g}mm）が {ENERGY_CAP_MJ}mJ を超える"))
    m = projectile_mass(p)
    if not MASS_MIN <= m <= MASS_MAX:
        out.append(Failure("F5.launch", "玉", f"玉の重さ {m:.2f}g が {MASS_MIN}〜{MASS_MAX}g の外"))
    if nose_d(p) < MIN_NOSE:
        out.append(Failure("F5.launch", "玉", f"玉の先の太さ {nose_d(p):g}mm が {MIN_NOSE}mm より細い"))
    w = p["arm_w"]
    if w / 2 - HOLE_R < HOLE_MARGIN:
        where = "腕" if p["form"] == "crossbow" else "弓"
        out.append(Failure("F5.launch", where, f"弦の穴から{where}の縁まで {w / 2 - HOLE_R:.1f}mm で、引くと裂けやすい（{HOLE_MARGIN}mm 以上）"))
    if p["form"] == "crossbow":
        sw, g = p["stock_w"], p["glue"]
        d = p["ball_d"]
        if d > CRUMPLE * p["ball_paper"]:
            out.append(Failure("F5.launch", "玉", f"{p['ball_paper']:g}mm の紙では直径 {d:g}mm の玉にまとまらない（{CRUMPLE * p['ball_paper']:.1f}mm まで）"))
        lo, hi = sw - BARREL_PLAY[1], sw - BARREL_PLAY[0]
        if not lo <= d <= hi:
            out.append(Failure("F5.launch", "玉", f"玉 {d:g}mm が筒（太さ {sw:g}mm）に合わない（{lo:g}〜{hi:g}mm）"))
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
    """紙を LAYERS 枚に貼り重ねる帯。幅の向きに arm_w ずつの面を、谷・山・谷と折り重ねる。外に見える 1 枚目と 4 枚目に絵。"""
    aw = p["arm_w"]
    H = LAYERS * aw
    part = Part(number, key, name, [(0, 0), (length, 0), (length, H), (0, H)], label_xy=(length - 4.5, 1), label=str(number))
    x0 = ROOT if glue_root else 0
    for k in range(1, LAYERS):
        line = ((0, k * aw), (length, k * aw))
        (part.mountain if k % 2 == 0 else part.valley).append(line)
    # 中の 2 枚は貼り合わせる面。
    part.glue = [[(x0, aw), (length, aw), (length, 3 * aw), (x0, 3 * aw)]]
    if glue_root:
        part.valley.append(((ROOT, 0), (ROOT, H)))
        part.glue.append([(0, 0), (ROOT, 0), (ROOT, H), (0, H)])
    for k in (0, LAYERS - 1):
        part.art.append(_rect(x0, k * aw, length, (k + 1) * aw, BOW))
        part.art.append({"kind": "line", "pts": [(x0 + 1, k * aw + aw / 2), (length - 8, k * aw + aw / 2)], "stroke": DARK, "sw": 0.3})
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
    xs = (HOLE_MARGIN + HOLE_R, L / 2, L - HOLE_MARGIN - HOLE_R)  # 両端は弦（輪ゴム）、真ん中は毛玉の糸
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
    return [_stave(p), _pompom(p)]


def place(by_key, page, top, gap):
    """弩: 1 段目に台、2 段目に腕 2 本と玉の紙、腕の下に引き金と物差し。弓: 1 段目に弓、2 段目に房。
    どちらも説明の列は部品の下に印字域の幅いっぱいで置く（物差しの 100mm が入るように）。"""
    x0 = page.x0
    if "stock" in by_key:
        st = by_key["stock"]
        st.x, st.y = x0, top
        y = top + st.height + gap
        a, b, ball = by_key["arma"], by_key["armb"], by_key["ball"]
        a.x, a.y = x0, y
        b.x, b.y = x0 + a.width + gap, y
        ball.x, ball.y = b.x + b.width + gap, y
        y2 = y + a.height + gap
        tr, ga = by_key["trigger"], by_key["gauge"]
        tr.x, tr.y = x0, y2
        ga.x, ga.y = x0 + tr.width + gap, y2
        bottom = max(ball.y + ball.height, tr.y + tr.height, ga.y + ga.height)
    else:
        sv, pom = by_key["stave"], by_key["pompom"]
        sv.x, sv.y = x0, top
        pom.x, pom.y = x0, top + sv.height + gap
        bottom = pom.y + pom.height
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
        {"number": 7, "key": "band", "name": "弦", "qty": 1, "material": "輪ゴム 1 本（ふつうの太さ。切って 1 本のひもにする）", "substituted": True, "original_guess": "糸（図の線による）", "reason": "紙の弓だけでは弦を張る力が足りないため"},
        {"number": 8, "key": "tether", "name": "毛玉の糸", "qty": 1, "material": f"木綿の糸（{tether:g}mm と、房を縛る 100mm）", "substituted": True, "original_guess": "糸（図の毛玉の糸）", "reason": "毛玉が遠くへ飛ばないよう弓に繋いでおくため"},
    ]


def materials(p):
    # 行の位置でなく key で引く。形によって部品表の行が違うので、位置で引くと別の行を刷る。
    by = {r["key"]: r for r in bom(p)}
    if p["form"] == "crossbow":
        return [f"{by['stock']['material']}を 1 枚", "のり、はさみ、定規（溝はカッターで大人が切る）", by["string"]["material"], f"飛ばすのは紙の玉だけ。{SAFETY}"]
    return [f"{by['stave']['material']}を 1 枚", "のり、はさみ、定規", by["band"]["material"], by["tether"]["material"], f"飛ばすのは紙の毛玉だけ。{SAFETY}"]


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる", f"約束: {SAFETY}。飛ばすのは紙の玉だけにする（竹串・楊枝・豆は飛ばさない）"]
    if p["form"] == "crossbow":
        tx = trigger_x(p)
        out += ["部品を実線で切る。1 台の細い溝と切れ込み、6 玉の物差しの穴はカッターで大人が切る",
                "2・3 腕を破線で 4 枚に折り重ね、中の面を貼る。根元の糊代を直角に折る",
                "1 台を破線で谷折りして角筒にし、糊代で貼る",
                "腕の根元を台の左右の壁の印に貼る（腕は横へ出し、先は後ろへ引ける向き）",
                "糸を右の腕の先の穴に結び、左右の溝を通して筒の中を横切らせ、左の腕の先の穴に結ぶ。少し張る",
                "5 玉の紙を丸め、6 物差しの小さい穴を通らず大きい穴を通る大きさにする",
                f"弦の硬さを測る: 弦の真ん中に 1 円玉 10 枚（10g）を下げ、下がった長さで 98 を割ると k（N/m）。{p['spring_k']:g} より大きければ腕を短くせず、引く長さを減らす",
                "玉を台の前の口から入れ、弦の前まで転がす",
                f"弦を溝に沿って前の端から {tx:g}mm まで引き、4 引き金を上の面と底の切れ込みに差して、前の縁の切れ込みに弦を掛ける",
                "遠くの壁か床に向け、引き金を真上に引き抜くと弦が外れて玉が出る"]
    else:
        out += ["部品を実線で切る。2 房の切り込みは、はさみで上の帯の手前まで",
                "1 弓を破線で 4 枚に折り重ね、中の面を貼る。両端の穴を竹串の先であけ、少し曲げて癖をつける",
                "輪ゴム 1 本を切ってひもにし、両端を糸で弓の両端の穴に結んで張る",
                "2 房の上の帯を固く巻いて貼り、根元を糸で縛る。房を外へ広げて毛玉にする",
                f"毛玉の糸を {p['tether']:g}mm に切り、毛玉の根元と弓の真ん中の穴に結ぶ",
                f"毛玉を輪ゴムの真ん中に当て、{p['draw']:g}mm 引いて放す。毛玉は糸の長さまでしか飛ばない"]
    out.append("引く長さを変えて、どこまで飛ぶか比べる。引きすぎない（腕が折れ、紙がへたる）")
    return out


RESULTS = ("飛んだ", "飛ばない")


def measures(p):
    """飛ぶかの二択でなく、引く長さと飛び方を言葉か絵で予想する（ほかの雛形と同じ形）。"""
    return {"predict": "弦を引く長さを変えると、玉の飛び方はどう変わると思いますか（言葉か絵で）", "rows": [[("引いた長さと飛んだ所", 40)]]}


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
