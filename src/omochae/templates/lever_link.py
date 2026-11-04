"""雛形 lever_link: 平たい紙の棒と人形を割ピン（紙用の、足を開いて留める鋲）や竹串で留め、1 つの棒を動かすと人形が動く。

『江都二色』の 7 つの玩具を、刷る形（kind）で描き分ける。どれも「紙の板・棒」と「ピンの継ぎ目」でできた平たい仕掛けとして起こした。
仕掛けの読みは図からの推定で、図に書かれていない動かし方は【解釈】として各形の説明に書く。寸法はどの値も実物では未確認。
Claude が変えてよいのは RANGES の名前の値だけ。

座標の決まり: 組んだ姿（組み図）を正面から見た mm の座標で起こす。y は下向き（頁と同じ）。角度は y 下向きの座標での回転
（正の角は画面で時計回り）。刷る部品は、組み図の形を部品ごとに切り出して、部品の左上を原点に移した物。棒は長さの向きを横に寝かせて刷る。

形（kind）と仕掛けの幾何（記号は下の「動きの見込み」と同じ）:
- sumo（コマ 18 左・木偶の相撲人形）: 力士 A と力士 B。長い棒の一方の端を A の肩に丸い穴で留め、他方は B の肩のピンが棒の溝（長さ slot_len）
  に入る。B の蹴る足は腰のピン H で B に留め、H から drive_arm 下の膝のピン K に細い棒（紙の帯）を留める。
  【解釈】A を左手で持ち、細い棒を横に押すと K が H のまわりを回り、B の足が蹴り上がる。押し合うと B が溝に沿って travel だけ動く。
- saru_take（コマ 4 左・竹登り猿）: 縦の竹串（太さ pole_d）に、猿の腕と足の 2 枚の板が竹串の穴（直径 hole_d）でかかる。板の他端は
  谷折りの耳にして、猿の胴にピンで留める。竹串の中心から耳の折り目まで drive_arm。
  【解釈】猿を下から押すと板が水平に近づいて滑り、手を離すと猿の重みで板が傾いて竹串を噛む。押す・離すを繰り返して登る。
- saru_sao（コマ 20 右・竿登りの猿）: 小さな人形が板 1 枚で竹串にかかる。仕掛けは saru_take と同じで、板が 1 枚。
- ebako（コマ 6 右・糸からくり絵箱）: 窓を抜いた枠の後ろに絵の札を置き、札の左右の 2 本のピンが枠の縦の溝（長さ slot_len）を滑る。
  札の上と下の糸を枠の外へ出す。【解釈】上の糸と下の糸を交互に引くと、窓の中の女の絵が travel だけ上下する。
- karakuri（コマ 28 左・からくり台）: 門の枠（柱 2 本・梁・下の箱）が台。梁のピン O に犬（揺れる腕・長さ drive_arm）、箱の軸 A に
  水車（腕・長さ crank）を留め、斜めの棒（連桿）で犬の尾の腕と水車の手のピンを結ぶ四節の仕掛け。【解釈】横の手を回すと、犬が首を振る。
  箱の猿と石臼は箱の絵として刷る（動かさない）。
- hashigo（コマ 23 右・梯子と猿）: 猿の座る台に、梯子の形の板をピン P で留める。板の上の方、P から drive_arm の所に竹串の棒（つまみ）を差す。
  【解釈】つまみを travel だけ押し上げると、板が P のまわりに傾き、下の端が机へ下がる。
- yakko（コマ 29 右・竹乗り奴人形）: 箱を担いだ奴が竹串の先に座る。蹴る足を腰のピン H で胴に留め、H から drive_arm 下の膝 K に結んだ糸を、
  竹串に貼る胴の下の穴 G に通して下へ垂らす。【解釈】糸の輪を travel だけ引くと、膝が G へ寄って足が振れる。

動きの見込み（床 F5.link）の前提:
- ピンの穴の縁から紙の端（外形・溝・窓・ほかの穴）まで PIN_MARGIN mm 以上。狭いと、回すうちに紙が裂ける見込み（実物で未確認）。
- 割ピンの頭は全部、表の面に出る。動く部品はその面に重なって動くので、ほかの継ぎ目の頭（半径 HEAD_R）に当たると、そこで止まる。
  紙の部品どうしは層が違うので、部品の重なりでは止まらないと見る。机（hashigo の床）は止まる物に入れる。
- 押す形（sumo・hashigo）: 入力の点（膝・つまみ）を決まった向き u に travel だけ押す。入力の点はピンのまわりを半径 drive_arm で回るので、
  角 θ は (K(θ) − K(0))·u = travel を満たす最初の角（sumo は u が接線なので θ = asin(travel / drive_arm)）。どの角でも届かなければ死点を越える。
- 引く形（yakko）: 糸の長さ |K − G| が travel だけ縮む角。膝が H と G を結ぶ線に乗ると糸がそれ以上縮まず、そこで止まる。
- 動く量: 止まる物に当たる角と入力の角の小さい方が MIN_ANGLE° 以上（揺れが目に見える見込み）。滑る形は MIN_DIST mm 以上。
- 溝: 溝の長さ − ピンの穴の直径（ピンの中心が動ける長さ）≧ travel。
- 四節（karakuri）: Grashof の条件（最短 + 最長 ≦ 残りの 2 本の和）と、最短が水車の腕である事（手を 1 周回せる）。
  1 周の間の伝達角（連桿と犬の腕の間の角）が MIN_TRANSMISSION° 以上（小さいと紙のピンがきしんで回らない見込み・実物で未確認）。
- 板の噛み（saru_take・saru_sao）: 厚さ t の板の穴 D を角 α だけ傾けると、竹串に直角な向きの通り幅は D·cos α − t·sin α。
  これが竹串の太さ d になる角が噛む角 α_lock。MIN_LOCK° より小さいと水平でも滑らず、MAX_LOCK° より大きいと猿が垂れ下がって
  耳の折り目が開く見込み。摩擦は入れない（薄い板は 2 点で竹串に当たるので、ふつうの紙の摩擦で噛むと見る。実物で未確認）。
- 絵の札（ebako）: 札が上下に travel/2 ずつ動いても、窓を COVER mm 以上の余りで覆い、枠の外へ出ない。
"""
import math

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from ..model import Failure, Part

ID = "lever_link"
DEFAULTS = {
    "kind": "sumo",
    # 割ピンの足の太さの見込み 3mm（竹串も 3mm）。穴はこれより 0.4mm 大きくする。
    "pin_d": 3, "bar_w": 10,
    # ピンから押す点・揺れる腕の先までの長さ。図の人形の腿の長さの比から起こした。
    "drive_arm": 30, "travel": 20, "slot_len": 30,
    "crank": 10,
    # 竹串 3mm に、穴 3.2mm。0.2mm の遊びで噛む角が 18° 前後になる。
    "pole_d": 3, "hole_d": 3.2,
    # 0.15mm はふつうの厚めの紙の見込み。実物の紙を測ったら置き換える。
    "paper_thickness": 0.15,
}
RANGES = {
    "pin_d": (2, 5), "bar_w": (5, 20), "drive_arm": (10, 45), "travel": (2, 40), "slot_len": (10, 60),
    "crank": (5, 40), "pole_d": (2, 6), "hole_d": (2, 8), "paper_thickness": (0.05, 0.5),
}
KINDS = ("sumo", "saru_take", "saru_sao", "ebako", "karakuri", "hashigo", "yakko")
# 刷る形を決める寸法（どの玩具か）。仕掛けが形ごとに違うので、寸法を直に渡す入口では必ず書かせる。
FORM = "kind"
FORMS = KINDS
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000018-L-lever_link"
SOURCES = {
    "sumo": "NDL-1187053-R0000018-L-lever_link", "saru_take": "NDL-1187053-R0000004-L-lever_link",
    "saru_sao": "NDL-1187053-R0000020-R-lever_link", "ebako": "NDL-1187053-R0000006-R-lever_link",
    "karakuri": "NDL-1187053-R0000028-L-lever_link", "hashigo": "NDL-1187053-R0000023-R-lever_link",
    "yakko": "NDL-1187053-R0000029-R-lever_link",
}
TITLES = {"sumo": "木偶の相撲", "saru_take": "竹登りの猿", "saru_sao": "竿にすがる人形", "ebako": "糸で動く絵箱",
          "karakuri": "手回しのからくり台", "hashigo": "梯子と猿", "yakko": "竹乗りの奴"}

PIN_MARGIN = 3  # ピンの穴の縁から紙の端までの見込み。これより狭いと回すうちに裂けやすい（実物で未確認）
HEAD_R = 4  # 割ピンの頭の半径の見込み（家にある紙用の割ピンを測ったら置き換える）
MIN_ANGLE = 15  # 揺れ・蹴りが目に見える角の見込み
MIN_DIST = 8  # 滑る物が動いて見える量の見込み
MIN_TRANSMISSION = 30  # 四節の伝達角の下限の見込み
MIN_LOCK, MAX_LOCK = 3, 25  # 板の噛む角の窓の見込み
COVER = 2  # 絵の札が窓の縁を覆う余り
EAR = 14  # 登る板の耳（谷折りで胴に当てる所）の長さ
STRING_R = 0.8  # 糸を通す穴の半径
SKEWER_LEN = 180  # 家にある竹串の長さの見込み

SKIN, INK, HAIR, CLOTH, WOOD, WOOD_DARK, MONKEY, GREEN, PALE, RED, STONE = (
    "#e4d2a6", "#3b3a34", "#3a2f26", "#b5533c", "#cdb98a", "#8a6f45", "#9a6a4f", "#7d8f6e", "#ece6d6", "#b0563e", "#c9c3b2")


def title(p):
    return TITLES[p["kind"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "kind": KINDS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "kind":
            if v not in KINDS:
                out.append(Failure("F5.range", k, f"{v} は {KINDS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


# ---- 幾何の道具 ----------------------------------------------------------------------------------------------------

def pin_r(p):
    """ピンの穴の半径。ピンが回るよう、足より 0.2mm ずつ大きくする。"""
    return p["pin_d"] / 2 + 0.2


def rot(pt, pivot, deg):
    """pivot のまわりに deg 回す（y 下向きの座標。shapely.affinity.rotate と同じ向き）。"""
    a = math.radians(deg)
    x, y = pt[0] - pivot[0], pt[1] - pivot[1]
    return (pivot[0] + x * math.cos(a) - y * math.sin(a), pivot[1] + x * math.sin(a) + y * math.cos(a))


def push_angle(pivot, k0, u, s, sign, limit=170, step=0.1):
    """入力の点 k0 を向き u に s だけ押した時の角（度）。ピンのまわりに sign の向きに回し、押した向きの進みが s に届く最初の角。
    届かなければ None（入力が死点を越える）。"""
    n = 0
    while n * step <= limit:
        k = rot(k0, pivot, sign * n * step)
        if (k[0] - k0[0]) * u[0] + (k[1] - k0[1]) * u[1] >= s - 1e-9:
            return n * step
        n += 1
    return None


def pull_angle(pivot, k0, g, s, sign, step=0.1):
    """糸を穴 g へ s だけ引いた時の角（度）と、糸が張り切って止まったか。膝が pivot と g を結ぶ線に乗ると、それ以上縮まない。"""
    target = math.dist(k0, g) - s
    prev, n = math.dist(k0, g), 1
    while n * step <= 180:
        d = math.dist(rot(k0, pivot, sign * n * step), g)
        if d <= target + 1e-9:
            return n * step, False
        if d > prev:  # 縮まなくなった（膝が線を越えた）
            return (n - 1) * step, True
        prev, n = d, n + 1
    return 180.0, True


def swing_hit(poly, pivot, sign, upto, obstacles, step=0.5):
    """部品の形 poly を pivot のまわりに sign の向きへ upto° まで回し、止まる物に最初に当たる角。当たらなければ None。"""
    if not obstacles:
        return None
    n = 0
    while n * step <= upto + 1e-9:
        g = affinity.rotate(poly, sign * n * step, origin=pivot) if n else poly
        if any(g.intersects(o) for o in obstacles):
            return n * step
        n += 1
    return None


def lock_angle(hole_d, pole_d, t):
    """板の穴が竹串を噛む角（度）。D·cos α − t·sin α = d の α を二分法で解く。D ≦ d なら 0（水平でも通らない）。"""
    if hole_d <= pole_d:
        return 0.0
    lo, hi = 0.0, 89.0
    for _ in range(60):
        mid = (lo + hi) / 2
        a = math.radians(mid)
        if hole_d * math.cos(a) - t * math.sin(a) > pole_d:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def fourbar(A, O, a, b, c, R0, step=2):
    """四節の 1 周。A: 水車の軸、O: 犬のピン、a: 水車の腕、b: 連桿、c: 犬の腕。R0 は組んだ時の犬の腕の先（枝を選ぶため）。
    Returns (犬の腕の角の列（度）, 伝達角の最小（度）)。どこかで組めなければ None（手を 1 周回せない）。"""
    angles, mus, R = [], [], R0
    for i in range(0, 360, step):
        f = math.radians(i)
        C = (A[0] + a * math.cos(f), A[1] + a * math.sin(f))
        d = math.dist(C, O)
        if d > b + c or d < abs(b - c) or d == 0:
            return None
        # 2 つの円（O 半径 c と C 半径 b）の交点のうち、前の位置に近い方（連続に動く枝）。
        x = (c * c - b * b + d * d) / (2 * d)
        h = math.sqrt(max(0.0, c * c - x * x))
        ex, ey = (C[0] - O[0]) / d, (C[1] - O[1]) / d
        mx, my = O[0] + x * ex, O[1] + x * ey
        cands = [(mx - h * ey, my + h * ex), (mx + h * ey, my - h * ex)]
        R = min(cands, key=lambda q: math.dist(q, R))
        angles.append(math.degrees(math.atan2(R[1] - O[1], R[0] - O[0])))
        v1, v2 = (C[0] - R[0], C[1] - R[1]), (O[0] - R[0], O[1] - R[1])
        cos_mu = (v1[0] * v2[0] + v1[1] * v2[1]) / (b * c)
        mu = math.degrees(math.acos(max(-1.0, min(1.0, cos_mu))))
        mus.append(min(mu, 180 - mu))
    return angles, min(mus)


def grashof(a, b, c, d):
    """最短 + 最長 ≦ 残りの 2 本の和で、最短が水車の腕 a（手を 1 周回せる、crank-rocker）。"""
    ls = sorted([a, b, c, d])
    return ls[0] + ls[3] <= ls[1] + ls[2] + 1e-9 and a <= min(b, c, d)


# ---- 組み図の部品 ----------------------------------------------------------------------------------------------------
# 部品は組み図の座標で起こし、印字の座標（部品の左上が原点）へは T = (原点の x, 原点の y, 角度) で移す。

def _single(g):
    """union の結果を 1 つの多角形にする。離れた島は形の誤りなので、いちばん大きい物だけを残さず例外にする。"""
    if g.geom_type == "MultiPolygon":
        raise ValueError("部品の形が 2 つに分かれている")
    return Polygon(g.exterior.coords)


def _limb(pts, w):
    return LineString(pts).buffer(w / 2, quad_segs=4)


def _disc(c, r):
    return Point(c).buffer(r, quad_segs=8)


def _ellipse(c, rx, ry):
    return affinity.scale(Point(c).buffer(1, quad_segs=8), rx, ry)


def _art_from(shape, accents):
    """肌（形の全体）と、形の内に切り取ったアクセントの面。切る線から 0.4mm 内に収め、刷りのずれで外へ出ないようにする。"""
    inner = shape.buffer(-0.4)
    art = [{"kind": "poly", "pts": list(inner.exterior.coords)[:-1], "fill": accents[0]}]
    for geom, color in accents[1:]:
        g = geom.intersection(shape.buffer(-0.7))
        for q in getattr(g, "geoms", [g]):
            if q.geom_type == "Polygon" and not q.is_empty and q.area > 0.5:
                art.append({"kind": "poly", "pts": list(q.exterior.coords)[:-1], "fill": color})
    return art


def _figure(number, key, name, shape, base, accents, holes=(), slots=(), keepouts=(), label=None):
    """人形・枠のような部品。shape は組み図の形、holes は (x, y, r)、slots と keepouts は組み図の軸にそろった矩形 (x, y, w, h)。"""
    shape = _single(shape).simplify(0.15, preserve_topology=True)
    x0, y0 = shape.bounds[0], shape.bounds[1]
    loc = affinity.translate(shape, -x0, -y0)
    art = _art_from(loc, [base] + [(affinity.translate(g, -x0, -y0), c) for g, c in accents])
    hl = [(x - x0, y - y0, r) for x, y, r in holes]
    sl = [(x - x0, y - y0, w, h) for x, y, w, h in slots]
    ko = [(x - x0, y - y0, w, h) for x, y, w, h in keepouts]
    lx, ly = _label_spot(loc, hl, sl + ko)
    part = Part(number, key, name, [tuple(v) for v in list(loc.exterior.coords)[:-1]], label_xy=(lx, ly), label=label or str(number),
                holes=hl, cuts=sl + ko, art=art)
    return {"part": part, "T": (x0, y0, 0.0), "slots": sl, "keepouts": ko}


def _label_spot(poly, holes, rects):
    """番号を置く所。部品の内で、穴と切り抜きから離れた最初の点を下から探す（番号の字の箱 3×3.5mm が入る所）。"""
    minx, miny, maxx, maxy = poly.bounds
    avoid = unary_union([Point(x, y).buffer(r + 1) for x, y, r in holes] + [box(x, y, x + w, y + h).buffer(1) for x, y, w, h in rects]) \
        if holes or rects else None
    y = maxy - 5
    while y >= miny:
        x = minx + 1
        while x <= maxx - 4:
            b = box(x, y, x + 3.5, y + 3.6)
            if poly.buffer(-0.3).contains(b) and (avoid is None or not b.intersects(avoid)):
                return round(x, 2), round(y, 2)
            x += 1
        y -= 1
    return 1.0, 1.0


def _tick(x, y, w, h, mark):
    """床が見る量を作る人に渡す印（細い朱の矩形）。at は印の真ん中（試験が印の間の長さを測る）。
    床が押す量や粘土の置き場で通る・落ちるを決めても、紙に印が無いと作る人はその量で動かせないため。"""
    return {"kind": "poly", "pts": [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], "fill": RED, "mark": mark, "at": (x + w / 2, y + h / 2)}


def _travel_ticks(part, x0, travel):
    """棒の上に、押す量 travel だけ離した 2 本の横切る印。棒の長さの向き（印字の x）に x0 から置く。"""
    w = part.outline[2][1]
    part.art += [_tick(x0 + d - 0.4, 0.8, 0.8, w - 1.6, "travel") for d in (0.0, travel)]


def _bar(number, key, name, p0, p1, w, holes_t, slots_t=(), ext0=None, ext1=None, fold_t=None, fill=WOOD, marks=None, label=None):
    """平たい棒。p0 から p1 の向きに寝かせて刷る。holes_t は (p0 からの長さ, 半径)、slots_t は (中心の長さ, 溝の長さ, 溝の半幅)。
    ext0・ext1 は p0 の手前・p1 の先に残す紙の長さ。fold_t は谷折りの線の長さ（登る板の耳）。marks は絵の模様（stripe・rung）。"""
    L = math.dist(p0, p1)
    ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    e0, e1 = ext0 if ext0 is not None else 6, ext1 if ext1 is not None else 6
    total = e0 + L + e1
    outline = [(0, 0), (total, 0), (total, w), (0, w)]
    holes = [(e0 + t, w / 2, r) for t, r in holes_t]
    slots = [(e0 + t - sl / 2, w / 2 - hw, sl, 2 * hw) for t, sl, hw in slots_t]
    part = Part(number, key, name, outline, holes=holes, cuts=list(slots), label=label or str(number))
    # 絵は折り線をまたがないよう、折り線の両側に分けて塗る。
    spans = [(0.3, total - 0.3)] if fold_t is None else [(0.3, e0 + fold_t - 0.3), (e0 + fold_t + 0.3, total - 0.3)]
    part.art = [{"kind": "poly", "pts": [(a, 0.3), (b, 0.3), (b, w - 0.3), (a, w - 0.3)], "fill": fill} for a, b in spans]
    if marks == "stripe":  # コマ 18 の棒の斜めの刻み
        x = 5.0
        while x + 3 < total - 3:
            part.art.append({"kind": "poly", "pts": [(x, w * 0.3), (x + 1.2, w * 0.3), (x + 2.6, w * 0.7), (x + 1.4, w * 0.7)], "fill": WOOD_DARK})
            x += 6
    elif marks == "rung":  # コマ 23 の梯子の段
        x = 6.0
        while x + 1 < total - 3:
            part.art.append({"kind": "poly", "pts": [(x, 0.8), (x + 0.9, 0.8), (x + 0.9, w - 0.8), (x, w - 0.8)], "fill": WOOD_DARK})
            x += 7
    if fold_t is not None:
        part.valley = [((e0 + fold_t, 0), (e0 + fold_t, w))]
    part.label_xy = _label_spot(Polygon(outline), holes, slots)
    return {"part": part, "T": (p0[0], p0[1], ang), "e0": e0, "w": w, "slots": slots, "keepouts": []}


def to_asm(piece, pt):
    """部品の印字の座標の点を組み図の座標へ。"""
    ox, oy, ang = piece["T"]
    if "e0" in piece:
        return rot((ox + pt[0] - piece["e0"], oy + pt[1] - piece["w"] / 2), (ox, oy), ang)
    return (ox + pt[0], oy + pt[1])


def asm_poly(piece):
    return Polygon([to_asm(piece, v) for v in piece["part"].outline])


# ---- 形ごとの組み図 --------------------------------------------------------------------------------------------------

def _wrestler(cx, facing):
    """力士の形（立ち姿）。facing = 1 で右向き。コマ 18 の 2 人の力士の比（頭・胴・脚 ＝ 1 : 1.6 : 2.4）を手で取った。"""
    f = facing
    head = _disc((cx + 2 * f, 16), 9)
    knot = _disc((cx - 3 * f, 6), 3.2)
    torso = Polygon([(cx - 8, 22), (cx + 8, 22), (cx + 11, 27), (cx + 12, 60), (cx - 11, 62), (cx - 11, 27)])
    arm = _limb([(cx + 9 * f, 31), (cx + 20 * f, 39)], 8)
    return head, knot, torso, arm


def _sumo(p):
    r = pin_r(p)
    SA, SB = (24.0, 36.0), (92.0, 32.0)
    H = (86.0, 60.0)
    K = (H[0], H[1] + p["drive_arm"])
    floor_y = 112
    head, knot, torso, arm = _wrestler(24, 1)
    legs = [_limb([(18, 60), (16, 86), (14, 106)], 10), _limb([(30, 60), (32, 86), (34, 106)], 10),
            box(8, 104, 22, floor_y), box(28, 104, 42, floor_y)]
    a_shape = unary_union([head, knot, torso, arm] + legs)
    A = _figure(1, "wrestlera", "力士 A", a_shape, SKIN,
                [(box(10, 3, 40, 12), HAIR), (knot, HAIR), (box(8, 54, 42, 68), CLOTH)], holes=[(SA[0], SA[1], r)])
    head, knot, torso, arm = _wrestler(92, -1)
    stand = [_limb([(97, 60), (100, 86), (103, 106)], 10), box(96, 104, 110, floor_y), box(80, 52, 104, 66)]
    b_shape = unary_union([head, knot, torso, arm] + stand)
    B = _figure(2, "wrestlerb", "力士 B", b_shape, SKIN,
                [(box(78, 3, 106, 11), HAIR), (knot, HAIR), (box(76, 54, 106, 68), CLOTH)], holes=[(SB[0], SB[1], r), (H[0], H[1], r)])
    leg_len = 50
    leg_shape = unary_union([_limb([H, (H[0], H[1] + leg_len)], 11), _disc(H, 7), box(H[0] - 11, H[1] + leg_len - 5, H[0] + 5, H[1] + leg_len + 1)])
    leg = _figure(3, "leg", "B の蹴る足", leg_shape, SKIN, [(_disc(H, 7.5), CLOTH)], holes=[(H[0], H[1], r), (K[0], K[1], r)])
    ext = r + PIN_MARGIN + 1.5
    rod = _bar(4, "rod", "細い棒", K, (K[0] + 60, K[1]), p["bar_w"], [(0, r)], ext0=ext, ext1=4, fill=WOOD)
    # 押す量の物差し。膝の穴から 18mm の所から travel（範囲の上限 40）だけ離す。棒は膝から 60mm あるので入る。
    _travel_ticks(rod["part"], ext + 18, p["travel"])
    span = math.dist(SA, SB)
    bar = _bar(5, "bar", "長い棒", SA, SB, p["bar_w"], [(0, r)], [(span, p["slot_len"], r)], ext0=ext, ext1=p["slot_len"] / 2 + ext - r,
               fill=WOOD, marks="stripe")
    pieces = [A, B, leg, rod, bar]
    mech = {"type": "push", "mover": leg, "pivot": H, "input": K, "u": (-1.0, 0.0), "sign": 1,
            "obstacles": [_disc(SA, HEAD_R), _disc(SB, HEAD_R)], "slot": True, "out": "B の足"}
    return pieces, mech


def _climber_bar(number, key, name, p, y):
    """登る板。竹串の穴から耳の折り目まで drive_arm、耳の真ん中に胴へのピンの穴。組み図では竹串から右へ水平に出る。"""
    hr = p["hole_d"] / 2
    e0 = hr + PIN_MARGIN + 1
    return _bar(number, key, name, (0.0, y), (p["drive_arm"] + EAR / 2, y), p["bar_w"],
                [(0, hr), (p["drive_arm"] + EAR / 2, pin_r(p))], ext0=e0, ext1=EAR / 2, fold_t=p["drive_arm"], fill=WOOD_DARK)


def _saru(p, two):
    """猿の形（竹串の右にすがる横向き）。コマ 4 は胴が竹の半分ほどの幅で、腕と足の 2 か所の板で竹にかかる。コマ 20 は小さく、板は手の 1 枚。"""
    r = pin_r(p)
    off = p["drive_arm"] - 30  # 腕を長くすると、猿は竹串から離れる（板の長さで人形の置き場が決まる）
    if two:
        P1, P2 = (30.0 + off, 44.0), (30.0 + off, 68.0)
        body = _ellipse((28 + off, 56), 14, 22)
        head = _disc((16 + off, 32), 9)
        cap = _disc((16 + off, 25), 5)
        limbs = [_limb([(22 + off, 42), (4, 38)], 6), _limb([(30 + off, 72), (12, 80), (4, 78)], 7), _limb([(38 + off, 70), (50 + off, 76), (54 + off, 66)], 3.5)]
        shape = unary_union([body, head, cap] + limbs)
        fig = _figure(1, "monkey", "猿", shape, MONKEY, [(cap, CLOTH), (_disc((12 + off, 31), 4), SKIN)], holes=[(P1[0], P1[1], r), (P2[0], P2[1], r)])
        clay = (36 + off, 58)
        bars = [_climber_bar(2, "armbar", "腕の板", p, P1[1] - EAR / 2), _climber_bar(3, "legbar", "足の板", p, P2[1] - EAR / 2)]
        name = "猿"
    else:
        P1 = (30.0 + off, 50.0)
        body = _ellipse((30 + off, 56), 12, 18)
        head = _disc((24 + off, 34), 7)
        hat = Polygon([(14 + off, 32), (34 + off, 24), (30 + off, 34)])
        limbs = [_limb([(26 + off, 40), (4, 36)], 5.5), _limb([(30 + off, 70), (10, 74), (4, 70)], 6)]
        shape = unary_union([body, head, hat] + limbs)
        fig = _figure(1, "figure", "人形", shape, STONE, [(hat, WOOD), (_disc((22 + off, 35), 4), SKIN), (box(10 + off, 58, 50 + off, 76), WOOD_DARK)],
                      holes=[(P1[0], P1[1], r)])
        clay = (36 + off, 62)
        bars = [_climber_bar(2, "handbar", "手の板", p, P1[1] - EAR / 2)]
        name = "人形"
    # 粘土の置き場の印。竹串から遠い背の側に置くと、重みの腕が長くなり、板を傾けて噛ませる見込み（実物で未確認）。
    q = fig["part"]
    cx, cy = clay[0] - fig["T"][0], clay[1] - fig["T"][1]
    q.art.append({"kind": "poly", "pts": [(cx + 2.5 * math.cos(i * math.pi / 8), cy + 2.5 * math.sin(i * math.pi / 8)) for i in range(16)],
                  "fill": RED, "mark": "clay", "at": (cx, cy)})
    mech = {"type": "clamp", "out": name, "slot": False}
    return [fig] + bars, mech


def _ebako(p):
    r = pin_r(p)
    FW, FH = 90.0, 120.0
    WIN = (18.0, 30.0, 54.0, 54.0)
    CARD = (5.0, 15.0, 80.0, 84.0)
    pins = [(11.0, 57.0), (79.0, 57.0)]
    slots = [(x - r, y - p["slot_len"] / 2, 2 * r, p["slot_len"]) for x, y in pins]
    wx, wy, ww, wh = WIN
    band = [box(0.6, 0.6, FW - 0.6, wy - 0.6), box(0.6, wy + wh + 0.6, FW - 0.6, FH - 0.6),
            box(0.6, wy - 0.6, wx - 0.6, wy + wh + 0.6), box(wx + ww + 0.6, wy - 0.6, FW - 0.6, wy + wh + 0.6)]
    frame = _figure(1, "frame", "枠", box(0, 0, FW, FH), WOOD, [(g, WOOD) for g in band] + [(box(wx - 3, wy - 3, wx + ww + 3, wy - 0.8), WOOD_DARK),
                    (box(wx - 3, wy + wh + 0.8, wx + ww + 3, wy + wh + 3), WOOD_DARK)], slots=slots, keepouts=[WIN])
    # ピンの頭の真ん中が動く上と下の印。左の溝の左に、静かな位置から ±travel/2。溝の長さが足りなくても印は刷る（床が溝を落とす）。
    tx = pins[0][0] - r - 5.5
    frame["part"].art += [_tick(tx - frame["T"][0], pins[0][1] + d - 0.4 - frame["T"][1], 4, 0.8, "travel") for d in (-p["travel"] / 2, p["travel"] / 2)]
    # 札の上の絵は、窓の真ん中（静かな時）に女の立ち姿。コマ 6 の比（窓の高さの 3/4）を手で取った。
    cx, cy, cw, ch = CARD
    mx, my = wx + ww / 2, wy + wh / 2
    woman = unary_union([_disc((mx, my - 17), 4.5), Polygon([(mx - 6, my - 12), (mx + 6, my - 12), (mx + 9, my + 20), (mx - 10, my + 20)]),
                         _limb([(mx - 5, my - 9), (mx - 12, my)], 4), _limb([(mx + 5, my - 9), (mx + 11, my - 1)], 4)])
    accents = [(woman, SKIN), (_disc((mx, my - 19), 4.6).difference(box(0, my - 17, 200, 200)), HAIR),
               (box(mx - 9, my - 2, mx + 9, my + 1), CLOTH), (box(mx - 10, my + 10, mx + 9, my + 12.5), CLOTH),
               (box(wx + 2, wy + 3, wx + 30, wy + 5), RED), (box(wx + 24, wy + wh - 6, wx + ww - 2, wy + wh - 4), RED)]
    card = _figure(2, "card", "絵の札", box(cx, cy, cx + cw, cy + ch), PALE, accents,
                   holes=[(x, y, r) for x, y in pins] + [(cx + cw / 2, cy + 4, STRING_R), (cx + cw / 2, cy + ch - 4, STRING_R)])
    mech = {"type": "slide", "out": "絵の札", "slot": True, "frame": (FW, FH), "window": WIN, "card": CARD}
    return [frame, card], mech


def _karakuri(p):
    r = pin_r(p)
    O, A = (40.0, 13.0), (92.0, 115.0)
    d = math.dist(O, A)
    # 犬の腕は、組んだ時に O→A に直角（右上）へ向ける。揺れが真ん中から左右に振り分けになる見込み。
    ux, uy = (A[0] - O[0]) / d, (A[1] - O[1]) / d
    c = p["drive_arm"]
    R0 = (O[0] + c * uy, O[1] - c * ux)
    b = math.dist(R0, A)
    GATE = (14.0, 20.0, 52.0, 80.0)
    frame_shape = unary_union([box(6, 16, 14, 104), box(66, 16, 74, 104), box(0, 6, 80, 20), box(6, 100, 110, 130)])
    monkey = unary_union([_disc((40, 104), 4), _ellipse((40, 116), 7, 9)])
    frame = _figure(1, "frame", "門の枠と箱", frame_shape, WOOD,
                    [(box(6, 16, 14, 100), GREEN), (box(66, 16, 74, 100), GREEN), (monkey, MONKEY), (_ellipse((56, 112), 8, 3), STONE),
                     (box(6, 126, 110, 130), WOOD_DARK)], holes=[(O[0], O[1], r), (A[0], A[1], r)],
                    keepouts=[GATE])  # 門の口は外形の穴になるので、切り抜く矩形として刷る（部品の外形は穴を持てない）
    dog = unary_union([_ellipse((O[0], -12), 14, 7), _disc((O[0] + 14, -16), 5.5), box(O[0] - 12, -10, O[0] - 8, -2), box(O[0] + 6, -10, O[0] + 10, -2),
                       box(O[0] - 5, -8, O[0] + 5, O[1] + 6), _limb([O, R0], 10), _disc(R0, 6)])
    dogp = _figure(2, "dog", "犬", dog, PALE, [(_disc((O[0] + 16, -17), 1.2), INK), (_ellipse((O[0] - 2, -13), 5, 3), RED)],
                   holes=[(O[0], O[1], r), (R0[0], R0[1], r)])
    wr = p["crank"] + r + PIN_MARGIN + 3
    C0 = (A[0] + p["crank"], A[1])
    paddles = [Polygon([rot((A[0] + 2, A[1] - 1.2), A, k * 45), rot((A[0] + wr - 1, A[1] - 1.2), A, k * 45),
                        rot((A[0] + wr - 1, A[1] + 1.2), A, k * 45), rot((A[0] + 2, A[1] + 1.2), A, k * 45)]) for k in range(8)]
    wheel = _figure(3, "wheel", "水車と手", _disc(A, wr), WOOD, [(g, WOOD_DARK) for g in paddles], holes=[(A[0], A[1], r), (C0[0], C0[1], r)])
    ext = r + PIN_MARGIN + 1.5
    rod = _bar(4, "rod", "斜めの棒", C0, (C0[0] + b * (R0[0] - C0[0]) / math.dist(R0, C0), C0[1] + b * (R0[1] - C0[1]) / math.dist(R0, C0)),
               p["bar_w"], [(0, r), (b, r)], ext0=ext, ext1=ext)
    mech = {"type": "crank", "out": "犬", "slot": False, "O": O, "A": A, "R0": R0, "a": p["crank"], "b": b, "c": c, "d": d,
            "mover": dogp, "obstacles": [_disc(A, HEAD_R)]}
    return [frame, dogp, wheel, rod], mech


def _hashigo(p):
    r = pin_r(p)
    P = (30.0, 82.0)
    floor_y = 120.0
    ang = math.radians(28)
    u = (math.cos(ang), math.sin(ang))
    stand = unary_union([box(0, 72, 36, floor_y), _ellipse((18, 72), 18, 4), _ellipse((18, 56), 11, 13), _disc((18, 38), 8)])
    stripes = [(box(0, y, 36, y + 1), WOOD_DARK) for y in range(78, 118, 6)]
    st = _figure(1, "stand", "台と猿", stand, WOOD, stripes + [(unary_union([_ellipse((18, 56), 11, 13), _disc((18, 38), 8)]), MONKEY),
                 (_disc((18, 39), 4.5), SKIN)], holes=[(P[0], P[1], r)])
    up = p["drive_arm"] + 30
    low = 44.0  # 下の端は、傾けると机に当たる長さにする（図の板は机まで届く）。机が止める所になる
    p0 = (P[0] - up * u[0], P[1] - up * u[1])
    slat = _bar(2, "slat", "梯子の板", p0, P, p["bar_w"], [(up - p["drive_arm"], r), (up, r)], ext0=5, ext1=low, fill=WOOD, marks="rung")
    # つまみを押し上げる量の物差し。台のピンの先（下の短い側）に、travel だけ離した 2 本（下の側は 44mm あり、上限 40 が入る）。
    _travel_ticks(slat["part"], 5 + up + 2.5, p["travel"])
    peg = (P[0] - p["drive_arm"] * u[0], P[1] - p["drive_arm"] * u[1])
    floor = box(-500, floor_y, 500, floor_y + 500)
    mech = {"type": "push", "mover": slat, "pivot": P, "input": peg, "u": (math.sin(ang), -math.cos(ang)), "sign": 1, "obstacles": [floor],
            "slot": False, "out": "梯子の板"}
    return [st, slat], mech


def _yakko(p):
    r = pin_r(p)
    H = (30.0, 60.0)
    K = (H[0], H[1] + p["drive_arm"])
    G = (52.0, 96.0)
    body = unary_union([_disc((38, 12), 8), Polygon([(27, 18), (45, 18), (50, 60), (24, 64)]), box(50, 6, 80, 26), box(10, 15, 56, 19),
                        _limb([(44, 60), (48, 84), (46, 102)], 9), box(40, 98, 54, 106), box(46, 56, 58, 110), _disc(H, 7)])
    fig = _figure(1, "body", "奴の胴", body, MONKEY, [(box(50, 6, 80, 26), GREEN), (box(53, 9, 77, 12), WOOD), (box(10, 15, 56, 19), WOOD),
                  (box(28, 26, 48, 44), SKIN), (box(46, 56, 58, 110), WOOD), (_disc((38, 9), 8.2), HAIR)],
                  holes=[(H[0], H[1], r), (G[0], G[1], STRING_R)])
    leg_len = max(48.0, p["drive_arm"] + 8)
    leg_shape = unary_union([_limb([H, (H[0], H[1] + leg_len)], 11), _disc(H, 7), box(H[0] - 11, H[1] + leg_len - 5, H[0] + 5, H[1] + leg_len + 1)])
    leg = _figure(2, "leg", "蹴る足", leg_shape, MONKEY, [(_disc(H, 7.5), SKIN)], holes=[(H[0], H[1], r), (K[0], K[1], STRING_R)])
    mech = {"type": "pull", "mover": leg, "pivot": H, "input": K, "guide": G, "sign": -1, "obstacles": [], "slot": False, "out": "足"}
    return [fig, leg], mech


BUILD = {"sumo": _sumo, "saru_take": lambda p: _saru(p, True), "saru_sao": lambda p: _saru(p, False), "ebako": _ebako,
         "karakuri": _karakuri, "hashigo": _hashigo, "yakko": _yakko}


def assembly(p):
    """形ごとの組み図。Returns (部品の list, 仕掛けの dict)。"""
    return BUILD[p["kind"]](p)


# ---- 床 F5.link -------------------------------------------------------------------------------------------------------

def pin_margins(pieces):
    """ピンの穴・溝の縁から紙の端（外形・ほかの穴・溝・窓）までの最小の余白。Returns [(部品の名, 何, 余白 mm)]。"""
    out = []
    for pc in pieces:
        q = pc["part"]
        poly = Polygon(q.outline)
        feats = [("穴", Point(x, y).buffer(r, quad_segs=16)) for x, y, r in q.holes] + [("溝", box(x, y, x + w, y + h)) for x, y, w, h in pc["slots"]]
        others = [box(x, y, x + w, y + h) for x, y, w, h in pc["keepouts"]]
        for i, (what, g) in enumerate(feats):
            m = poly.exterior.distance(g) if poly.contains(g) else 0.0
            for j, (_, h) in enumerate(feats):
                if j != i:
                    m = min(m, g.distance(h))
            for h in others:
                m = min(m, g.distance(h))
            out.append((q.name, what, m))
    return out


def motion(p):
    """仕掛けの動く量を数える。Returns dict（形ごとの量）。前提は module の docstring。"""
    pieces, m = assembly(p)
    t = m["type"]
    res = {"type": t, "out": m["out"]}
    if t in ("push", "pull"):
        if t == "push":
            theta = push_angle(m["pivot"], m["input"], m["u"], p["travel"], m["sign"])
            res["dead"] = theta is None
            limited = False
        else:
            theta, limited = pull_angle(m["pivot"], m["input"], m["guide"], p["travel"], m["sign"])
            res["dead"] = False
        res["input_angle"] = theta
        res["string_limited"] = limited
        upto = theta if theta is not None else 170
        hit = swing_hit(asm_poly(m["mover"]), m["pivot"], m["sign"], upto, m["obstacles"])
        res["hit_angle"] = hit
        res["usable"] = min(x for x in (theta if theta is not None else 0.0, hit if hit is not None else 999.0))
    elif t == "crank":
        res["grashof"] = grashof(m["a"], m["b"], m["c"], m["d"])
        res["b"], res["d"] = m["b"], m["d"]
        fb = fourbar(m["A"], m["O"], m["a"], m["b"], m["c"], m["R0"])
        if fb is None:
            res.update(swing=None, transmission=None, hit_angle=None)
        else:
            angles, mu = fb
            psi0 = math.degrees(math.atan2(m["R0"][1] - m["O"][1], m["R0"][0] - m["O"][0]))
            rel = [((a - psi0 + 180) % 360) - 180 for a in angles]
            res["swing"], res["transmission"] = max(rel) - min(rel), mu
            poly = asm_poly(m["mover"])
            hits = [swing_hit(poly, m["O"], s, abs(lim), m["obstacles"]) for s, lim in ((1, max(rel)), (-1, min(rel)))]
            res["hit_angle"] = min((h for h in hits if h is not None), default=None)
    elif t == "clamp":
        res["lock"] = lock_angle(p["hole_d"], p["pole_d"], p["paper_thickness"])
        res["step"] = p["travel"]
    elif t == "slide":
        fw, fh = m["frame"]
        wx, wy, ww, wh = m["window"]
        cx, cy, cw, ch = m["card"]
        half = p["travel"] / 2
        res["cover"] = min(wy - (cy + half), (cy + ch - half) - (wy + wh))
        res["inside"] = min(cy - half, fh - (cy + ch + half))
        res["step"] = p["travel"]
    res["slot_free"] = p["slot_len"] - 2 * pin_r(p) if m["slot"] else None
    res["pins"] = pin_margins(pieces)
    return res


def check_physics(p):
    """F5.link: ピンの穴の余白・入力で出力が十分動く（止まる物に当たる前に）・四節の Grashof・溝が動く量より長い・板の噛み・札の覆い。"""
    out = []
    try:
        res = motion(p)
    except ValueError as e:  # 部品の形が分かれる寸法（範囲の中でも起きうる）は、作れない形として落とす
        return [Failure("F5.link", "形", str(e))]
    for name, what, m in res["pins"]:
        if m < PIN_MARGIN - 1e-9:
            out.append(Failure("F5.link", name, f"ピンの{what}から紙の端まで {m:.1f}mm で、回すと裂けやすい（{PIN_MARGIN}mm 以上）"))
    t, who = res["type"], res["out"]
    if t in ("push", "pull"):
        if res["dead"]:
            out.append(Failure("F5.link", who, f"押す量 {p['travel']:g}mm がピンからの腕 {p['drive_arm']:g}mm で届かず、死点を越える"))
        elif res["usable"] < MIN_ANGLE:
            why = "止まる物に当たる" if res["hit_angle"] is not None and res["hit_angle"] < (res["input_angle"] or 0) else \
                ("糸が張り切る" if res["string_limited"] else "入力が小さい")
            out.append(Failure("F5.link", who, f"{who}の振れが {res['usable']:.1f}° で小さい（{why}・{MIN_ANGLE}° 以上）"))
    elif t == "crank":
        if not res["grashof"] or res["swing"] is None:
            out.append(Failure("F5.link", "四節", f"水車の腕 {p['crank']:g}mm・連桿 {res['b']:.1f}mm・犬の腕 {p['drive_arm']:g}mm・軸の間 {res['d']:.1f}mm"
                               "で Grashof の条件を満たさず、手を 1 周回せない（最短が水車の腕で、最短 + 最長 ≦ 残りの和）"))
        else:
            if res["swing"] < MIN_ANGLE:
                out.append(Failure("F5.link", who, f"{who}の振れが {res['swing']:.1f}° で小さい（{MIN_ANGLE}° 以上）"))
            if res["transmission"] < MIN_TRANSMISSION:
                out.append(Failure("F5.link", "四節", f"伝達角が {res['transmission']:.1f}° まで下がり、きしんで回らない（{MIN_TRANSMISSION}° 以上）"))
            if res["hit_angle"] is not None and res["hit_angle"] < res["swing"]:
                out.append(Failure("F5.link", who, f"{who}が {res['hit_angle']:.1f}° で割ピンの頭に当たる"))
    elif t == "clamp":
        if res["lock"] < MIN_LOCK:
            out.append(Failure("F5.link", "板の穴", f"穴 {p['hole_d']:g}mm が竹串 {p['pole_d']:g}mm にきつく、水平でも滑らない（噛む角 {res['lock']:.1f}°・{MIN_LOCK}° 以上）"))
        elif res["lock"] > MAX_LOCK:
            out.append(Failure("F5.link", "板の穴", f"穴 {p['hole_d']:g}mm が竹串 {p['pole_d']:g}mm に緩く、{res['lock']:.1f}° 傾くまで噛まない（{MAX_LOCK}° まで）"))
        if res["step"] < MIN_DIST:
            out.append(Failure("F5.link", who, f"1 回に押し上げる量 {res['step']:g}mm が小さい（{MIN_DIST}mm 以上）"))
    elif t == "slide":
        if res["step"] < MIN_DIST:
            out.append(Failure("F5.link", who, f"札の動く量 {res['step']:g}mm が小さい（{MIN_DIST}mm 以上）"))
        if res["cover"] < COVER:
            out.append(Failure("F5.link", who, f"札が動くと窓の縁まで {res['cover']:.1f}mm になり、札の端が窓から見える（{COVER}mm 以上）"))
        if res["inside"] < 0:
            out.append(Failure("F5.link", who, f"札が枠の外へ {-res['inside']:.1f}mm 出る"))
    if res["slot_free"] is not None and res["slot_free"] < p["travel"]:
        out.append(Failure("F5.link", "溝", f"溝の中でピンが動ける長さ {res['slot_free']:.1f}mm が、動かす量 {p['travel']:g}mm より短い"))
    return out


# ---- 刷る部品・部品表・文 ---------------------------------------------------------------------------------------------

def parts(p):
    pieces, _ = assembly(p)
    return [pc["part"] for pc in pieces]


def place(by_key, page, top, gap):
    """部品を作った順に、入るいちばん上・その中でいちばん左の所へ置く（外接の矩形で見る）。
    段に詰めるだけだと、形ごとに部品の大きさが違うので、大きい部品の横や下の空きが無駄になり、寸法を変えると頁から溢れた。
    説明の列は部品の下に、頁の幅いっぱいで置く（物差し 100mm が入るように）。"""
    placed = []
    for q in by_key.values():
        xs = sorted({page.x0} | {x1 + gap for _, _, x1, _ in placed})
        ys = sorted({top} | {y1 + gap for _, _, _, y1 in placed})
        spot = None
        for y in ys:
            for x in xs:
                r = (x, y, x + q.width, y + q.height)
                if r[2] > page.x1 + 1e-9:
                    continue
                if all(r[2] + gap <= a[0] + 1e-9 or a[2] + gap <= r[0] + 1e-9 or r[3] + gap <= a[1] + 1e-9 or a[3] + gap <= r[1] + 1e-9
                       for a in placed):
                    spot = r
                    break
            if spot:
                break
        spot = spot or (page.x0, max(ys), page.x0 + q.width, max(ys) + q.height)  # 入らなければ下へ。印字域の検査が落とす
        q.x, q.y = spot[0], spot[1]
        placed.append(spot)
    return max(r[3] for r in placed) + gap, page.x1 - page.x0, page.x0


PAPER_WHY = "家庭のプリンタで刷って作るため"
PIN_ROW = "紙用の割ピン（足を開いて留める鋲・足の太さ {d:g}mm 前後）"


def _pin_count(kind):
    return {"sumo": 4, "saru_take": 2, "saru_sao": 1, "ebako": 2, "karakuri": 4, "hashigo": 1, "yakko": 1}[kind]


def bom(p):
    paper = f"紙（厚さ {p['paper_thickness']}mm 前後）"
    kind = p["kind"]
    rows = []
    origin = {"sumo": "木か紙（図の平たい人形と棒）", "saru_take": "紙か薄い木（図の平たい猿）", "saru_sao": "紙か薄い木（推定）",
              "ebako": "木の箱と紙の絵（推定）", "karakuri": "木（推定・図の柱と箱）", "hashigo": "木か竹（推定）", "yakko": "紙か木（推定）"}[kind]
    for q in parts(p):
        rows.append({"number": q.number, "key": q.key, "name": q.name, "qty": 1, "material": paper, "substituted": True,
                     "original_guess": f"不明（{origin}）", "reason": PAPER_WHY})
    n = 10
    rows.append({"number": n, "key": "pin", "name": "ピン", "qty": _pin_count(kind), "material": PIN_ROW.format(d=p["pin_d"]), "substituted": True,
                 "original_guess": "不明（図の継ぎ目の点からの推定。木の釘か竹の目釘）", "reason": "家にあり、紙を挟んで回る継ぎ目を作りやすいため"})
    if kind in ("saru_take", "saru_sao", "yakko"):
        rows.append({"number": n + 1, "key": "pole", "name": "竹の竿", "qty": 1, "material": f"竹串（太さ {p['pole_d']:g}mm・長さ {SKEWER_LEN}mm の見込み）",
                     "substituted": True, "original_guess": "竹（図の節のある竿）", "reason": "家にあり、太さがそろっているため"})
    if kind in ("karakuri", "hashigo"):
        rows.append({"number": n + 1, "key": "peg", "name": "つまみ", "qty": 1, "material": "竹串を 20mm に切った物", "substituted": True,
                     "original_guess": "木の棒（図の手・つまみ）", "reason": "家にあり、穴に差して糊で留めやすいため"})
    if kind in ("ebako", "yakko"):
        rows.append({"number": n + 2, "key": "cord", "name": "糸", "qty": 2 if kind == "ebako" else 1, "material": "木綿の糸（1 本 150mm に切る）",
                     "substituted": True, "original_guess": "糸（図の線と結び目）", "reason": "家にあるため"})
    if kind in ("saru_take", "saru_sao"):
        rows.append({"number": n + 3, "key": "weight", "name": "重り", "qty": 1, "material": "油粘土（2g ほど）", "substituted": True,
                     "original_guess": "無し（図に無い。紙の猿は軽く、板を傾ける重みが足りない見込み）", "reason": "板を傾けて竹串を噛ませるため"})
    return rows


def materials(p):
    by = {r["key"]: r for r in bom(p)}
    out = [f"{by[parts(p)[0].key]['material']}を 1 枚", "のり、はさみ、定規、穴をあける目打ちか竹串",
           f"{by['pin']['material']}を {by['pin']['qty']} 本"]
    for k in ("pole", "peg", "cord", "weight"):
        if k in by:
            out.append(f"{by[k]['material']}" + (f"を {by[k]['qty']} 本" if k == "cord" else ""))
    return out


def steps(p):
    k = p["kind"]
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。中の溝と窓も切り抜き、丸い穴は目打ちであける"]
    out += {
        "sumo": ["5 長い棒の丸い穴を 1 力士 A の肩に、溝を 2 力士 B の肩に重ね、割ピンで留める",
                 "3 B の足を B の腰に割ピンで留める", "4 細い棒の穴を足の膝に割ピンで留める",
                 f"A を持ち、細い棒を、棒の 2 本の朱の印の間（{p['travel']:g}mm）だけ横に押して、B の足が蹴り上がるか見る"],
        "saru_take": ["2 腕の板と 3 足の板の耳を破線で谷折りし、竹串を板の小さい穴に通す",
                      "耳を猿の胴の穴に合わせ、割ピンで留める。猿の背の朱の丸い印に油粘土を付ける",
                      f"竹串を立て、猿を下から {p['travel']:g}mm ほど押しては離し、登るか見る"],
        "saru_sao": ["2 手の板の耳を破線で谷折りし、竹串を板の小さい穴に通す",
                     "耳を人形の胴の穴に合わせ、割ピンで留める。人形の背の朱の丸い印に油粘土を付ける",
                     f"竹串を立て、人形を下から {p['travel']:g}mm ほど押しては離し、止まるか登るか見る"],
        "ebako": ["2 絵の札を 1 枠の後ろに置き、枠の溝から札の左右の穴へ割ピンを通して留める",
                  "札の上と下の小さい穴に糸を結び、枠の上と下へ出す",
                  f"上の糸と下の糸を交互に引き、ピンの頭の真ん中が溝の横の 2 本の朱の印の間（{p['travel']:g}mm）を動くか、窓の中の絵が動くか見る"],
        "karakuri": ["2 犬を梁の穴に、3 水車を箱の穴に割ピンで留める", "4 斜めの棒の両端を、犬の尾の穴と水車の小さい穴に割ピンで留める",
                     "水車の手のピンの頭に竹串のつまみを糊で付ける", "つまみを持って水車を回し、犬が首を振るか見る"],
        "hashigo": ["2 梯子の板の下の方の穴を 1 台の穴に重ね、割ピンで留める", "板の上の方の穴に竹串のつまみを差し、糊で留める",
                    f"つまみを、板の下の 2 本の朱の印の間の長さ（{p['travel']:g}mm）だけ板に直角に押し上げ、板が傾いて下の端が机に当たるか見る"],
        "yakko": ["2 蹴る足を胴の腰に割ピンで留める", "竹串を胴の下の帯の裏に糊で貼る（先を腰の下まで）",
                  "膝の小さい穴に糸を結び、胴の下の小さい穴に通して下へ垂らし、輪に結ぶ",
                  f"糸の、胴の下の穴から出た所にペンで印を付ける。竹串を持ち、印が {p['travel']:g}mm 下がるまで糸の輪を引いて、足が振れるか見る（糸は刷れないので印は自分で付ける）"],
    }[k]
    return out


def measures(p):
    """動くかの二択でなく、動かし方と出力の動きを言葉か絵で予想する（ほかの雛形と同じ形）。"""
    return {"predict": "棒（糸・手）をどう動かすと、人形はどう動くと思いますか（言葉か絵で）", "rows": [[("動かした量（mm か回数）", 40)]]}


def diagram(x, y, w, h, p):
    """組み上がりを正面から見た絵。部品の外形を組み図の位置に重ねるだけで、寸法の図ではない。"""
    pieces, _ = assembly(p)
    polys = [asm_poly(pc) for pc in pieces]
    minx = min(g.bounds[0] for g in polys)
    miny = min(g.bounds[1] for g in polys)
    maxx = max(g.bounds[2] for g in polys)
    maxy = max(g.bounds[3] for g in polys)
    s = min(w / (maxx - minx), h / (maxy - miny))
    return [{"kind": "poly", "pts": [(x + (a - minx) * s, y + (b - miny) * s) for a, b in list(g.exterior.coords)[:-1]], "fill": "none", "sw": 0.25}
            for g in polys]
