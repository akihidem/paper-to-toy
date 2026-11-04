"""雛形 spinner: 軸のまわりに回る部品。『江都二色』の風車と独楽を試す。

刷る形（kind）は 3 つ。形が違えば部品も回り方の見込みも違うので、FORM の値で描き分ける。
- pinwheel: 正方形の紙を角から中心へ切り、1 つおきの角を軸へ寄せる紙の風車（コマ 14 左の風車を、家で作れる 1 枚の風車にした翻案）
- square: 中心から 8 本の腕が出て、先に四角い羽が付く風車（コマ 20 右）
- top: 紙の円盤を何枚か重ね、竹串か爪楊枝を通した独楽（コマ 26 左）

寸法は図の比を目測して出した。どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。

回り方の見込み（式の前提。どれも実物で確かめていない）:
- 風車の羽と柄（ストロー）の間: 羽は軸の 2 か所（風車は中心の紙と 4 つの角の束、四角の羽は 1 の中心と 2 の座金）で軸に載る。
  穴と軸の隙間 s、2 か所の間 b なら、羽は軸に対して atan(s/b) まで傾く。羽の先（半径 R）は柄の側へ R・sin(傾き) 寄る。
  四角の羽は風を受けるよう腕をねじる（TWIST_DEG）ので、羽の半分の幅 × sin(ねじれ) だけ後ろへ出る。
  柄との間（spacer）がこの和に MIN_CLEAR を足した長さより短いと、羽が柄に当たる。紙のたわみは入れていない。
- 穴の余白: 穴の縁から紙の端（切り込みの終わり・羽の角の辺）まで HOLE_MARGIN（虎の雛形と同じ 4mm）。狭いと回すうちに裂ける見込み。
- 穴の隙間: 穴の径 − 軸の径 が MIN_SLACK より小さいと、紙が軸を締めて回らない見込み。
- 柄を持つ手: 柄の長さから軸の位置と羽の半径を引いた残りが GRIP より短いと、羽が手に当たる。
- 独楽は速く回る対称な独楽が倒れない条件（Klein–Sommerfeld の「眠る独楽」）を使う: ω² > 4·M·g·l·I1 / I3²。
  M は全質量、l は先から重心までの高さ、I1 は先を通る横の軸のまわり、I3 は回る軸のまわりの慣性モーメント。
  円盤は一様な紙（面密度 paper_gsm、厚さ paper_gsm/800 mm＝密度 0.8g/cm³ の見込み）、軸は一様な木の棒（WOOD_DENSITY）。
  指でひねって回す速さを OMEGA_HAND と見込み、その SLEEP_RATIO 倍で倒れない事を求める（回り続ける時間の余裕）。
  円盤が軽いと軸の重さで重心が上がり、I3 も小さいので倒れやすい。1 枚で足りなければ layers 枚を重ねて貼る（部品表に枚数を書く）。
  軸が重心を通る事: 刷った円盤の輪郭と穴から重心を数え、穴の中心から COM_TOL より離れれば落とす（ぶれて跳ねる見込み）。
  先が短いと、少し傾いただけで円盤の縁が床に付く。MIN_TILT_DEG 傾くまで縁が床に付かない事を求める。持つ所は MIN_GRIP_TOP。
- 空気の抵抗・先の摩擦・紙の反りは入れていない。どれも回る時間を縮める側に効く。
"""
import math

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from ..model import Failure, Part

ID = "spinner"
DEFAULTS = {
    "kind": "pinwheel",
    # 軸と柄（風車の 2 つの形で同じ）。竹串 3mm・ストローはふつうの物の見込み。
    "axle_d": 3.0, "hole_d": 3.6, "spacer": 24, "bearing": 10, "stick_length": 200,
    # 紙の風車
    "square": 120, "uncut": 12,
    # 四角の羽の風車。コマ 20 右の図で、中心から羽の中心まで ≈ 羽の一辺 × 2.6
    "vane": 24, "vane_radius": 62, "spoke_w": 4, "hub_r": 12,
    # 独楽。コマ 26 左の図で、円盤の径に対して下の軸は短く、上の軸は径の 4 割ほど
    "disc_r": 30, "layers": 3, "tip": 8, "grip": 25, "hole_offset": 0,
    # 紙の面密度は見込み（厚めの紙）。実物の紙を量ったら置き換える。
    "paper_gsm": 180,
}
RANGES = {
    "axle_d": (1.8, 4.0), "hole_d": (1.0, 8.0), "spacer": (0, 40), "bearing": (2, 30), "stick_length": (100, 210),
    "square": (60, 180), "uncut": (4, 40),
    "vane": (10, 40), "vane_radius": (25, 80), "spoke_w": (2, 10), "hub_r": (5, 25),
    "disc_r": (10, 40), "layers": (1, 6), "tip": (1, 40), "grip": (5, 60), "hole_offset": (0, 10),
    "paper_gsm": (40, 400),
}
KINDS = ("pinwheel", "square", "top")
# 刷る形を決める寸法。形が違えば部品が違うので、寸法を直に渡す入口では既定に頼らず必ず書かせる。
FORM = "kind"
FORMS = KINDS
# 既定の出典。紙の風車（既定の形）の元にしたコマ 14 左。四角の羽と独楽は場面の --source で出典を替える。
SOURCE = "NDL-1187053-R0000014-L-spinner"

HOLE_MARGIN = 4
MIN_SLACK = 0.3
MIN_CLEAR = 3
TWIST_DEG = 45
# 腕を 45° ねじっても折れ目が付かない長さの見込み（腕の幅の倍数）。
TWIST_LEN = 3
VANE_GAP = 2
GRIP = 60
# 柄の上の端から軸までの長さ。ストローの端に近いと串の穴が裂ける。
AXLE_FROM_TOP = 10
# 柄のストローの径と、軸の前の止め（テープを巻く分）。軸の長さを部品表に書くため。
STRAW_D = 6
FRONT_STOP = 8
G = 9800.0  # mm/s²
WOOD_DENSITY = 0.65e-3  # g/mm³。竹・木の串の見込み
OMEGA_HAND = 60.0  # rad/s（約 10 回/秒）。指でひねって回す速さの見込み
SLEEP_RATIO = 0.5
MIN_TILT_DEG = 8
MIN_GRIP_TOP = 15
COM_TOL = 0.5
SIN_HALF = math.sin(math.radians(22.5))  # 風車の角の尖り（45°）の半分
NOTCH = 0.5  # 切り込みの口の幅。幅 0 の線は輪郭にできないので、細い V にして刷る
GOLD, CREAM, ORANGE, INK = "#cdb57e", "#e9dfc3", "#c8724e", "#4a3f2c"
LAYER_KEYS = "abcdef"
TITLES = {"pinwheel": "紙の角を軸へ寄せる", "square": "八枚の四角い羽", "top": "円盤に串を通す"}


def title(p):
    return TITLES[p["kind"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "kind": KINDS}


def check_range(p):
    out = []
    if isinstance(p.get("layers"), float) and not p["layers"].is_integer():
        out.append(Failure("F5.range", "layers", "重ねる枚数は整数"))
    for k, v in p.items():
        if k == "kind":
            if v not in KINDS:
                out.append(Failure("F5.range", k, f"{v} は {KINDS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


# ---- 回り方の見込みの式 ----

def thickness(p):
    return p["paper_gsm"] / 800


def wheel_radius(p):
    if p["kind"] == "pinwheel":
        return p["square"] / math.sqrt(2)
    return p["vane_radius"] + p["vane"] / math.sqrt(2)


def wobble_deg(p):
    """羽が軸に対して傾ける角度。2 か所の穴の隙間と間の長さから。"""
    return math.degrees(math.atan2(max(p["hole_d"] - p["axle_d"], 0), p["bearing"]))


def need_spacer(p):
    """羽が柄に当たらないのに要る、羽の面と柄の間の長さ。"""
    back = wheel_radius(p) * math.sin(math.radians(wobble_deg(p)))
    if p["kind"] == "square":
        back += p["vane"] / math.sqrt(2) * math.sin(math.radians(TWIST_DEG))
    return back + MIN_CLEAR


def tip_hole_dist(p):
    """風車の角の穴を、角の先から尖りの二等分線に沿ってどれだけ入れるか。両側の辺まで穴の縁から HOLE_MARGIN 取れる所。"""
    return (HOLE_MARGIN + p["hole_d"] / 2) / SIN_HALF


def axle_length(p):
    stack = 5 * thickness(p) if p["kind"] == "pinwheel" else 2 * thickness(p)
    return STRAW_D + p["spacer"] + p["bearing"] + stack + FRONT_STOP


def top_stick_length(p):
    return p["tip"] + p["layers"] * thickness(p) + p["grip"]


def top_masses(p):
    """独楽の質量（g）: 円盤 1 枚・円盤全部・軸。"""
    r = p["disc_r"]
    layer = (math.pi * r * r - math.pi * (p["axle_d"] / 2) ** 2) * 1e-6 * p["paper_gsm"]
    stick = WOOD_DENSITY * math.pi * (p["axle_d"] / 2) ** 2 * top_stick_length(p)
    return layer, layer * p["layers"], stick


def top_omega_min(p):
    """眠る独楽の下限の角速度（rad/s）と、先から重心までの高さ l（mm）。座標は軸の先を原点に上を正にする。"""
    r, d = p["disc_r"], p["axle_d"]
    h = p["layers"] * thickness(p)
    L = top_stick_length(p)
    _, md, ms = top_masses(p)
    zd, zs = p["tip"] + h / 2, L / 2
    M = md + ms
    l = (md * zd + ms * zs) / M
    i3 = md * r * r / 2 + ms * d * d / 8
    i1 = md * (r * r / 4 + h * h / 12 + zd * zd) + ms * L * L / 3
    return 2 * math.sqrt(M * G * l * i1) / i3, l


def disc_com_offset(p):
    """刷る円盤（輪郭と穴）の重心と、穴の中心の距離（mm）。穴が中心からずれると重心が軸から外れる。"""
    q = _disc_part(p, 0)
    x, y, r = q.holes[0]
    shape = Polygon(q.outline, [Point(x, y).buffer(r, 32).exterior.coords])
    c = shape.centroid
    return math.hypot(c.x - x, c.y - y)


def _wheel_floors(p):
    out = []
    R = wheel_radius(p)
    slack = p["hole_d"] - p["axle_d"]
    if slack < MIN_SLACK:
        out.append(Failure("F5.spin", "軸の穴", f"穴 {p['hole_d']}mm と軸 {p['axle_d']}mm の隙間が {MIN_SLACK}mm 無く、紙が軸を締めて回らない"))
    need = need_spacer(p)
    if p["spacer"] < need:
        out.append(Failure("F5.spin", "羽", f"羽と柄の間 {p['spacer']}mm が、羽の傾き {wobble_deg(p):.1f}° で柄に寄る分を見た {need:.1f}mm に足りず、羽が柄に当たる"))
    if p["stick_length"] - AXLE_FROM_TOP - R < GRIP:
        out.append(Failure("F5.spin", "柄", f"軸から下の柄 {p['stick_length'] - AXLE_FROM_TOP}mm が羽の半径 {R:.0f}＋持つ所 {GRIP} に足りず、羽が手に当たる"))
    if p["kind"] == "pinwheel":
        if p["uncut"] - p["hole_d"] / 2 < HOLE_MARGIN:
            out.append(Failure("F5.spin", "中心の穴", f"切り込みの終わりから中心の穴まで {p['uncut'] - p['hole_d'] / 2:.1f}mm で、{HOLE_MARGIN}mm 無く裂けやすい"))
        flap = R - p["uncut"]
        if flap < tip_hole_dist(p) + p["hole_d"] / 2 + HOLE_MARGIN:
            out.append(Failure("F5.spin", "角の穴", f"切り込み {flap:.1f}mm が短く、角の穴を辺から {HOLE_MARGIN}mm 離して置けない"))
    else:
        if p["hub_r"] - p["hole_d"] / 2 < HOLE_MARGIN:
            out.append(Failure("F5.spin", "中心の穴", f"中心の円の縁まで {p['hub_r'] - p['hole_d'] / 2:.1f}mm で、{HOLE_MARGIN}mm 無く裂けやすい"))
        half = p["vane"] / math.sqrt(2)
        chord = 2 * p["vane_radius"] * SIN_HALF
        if chord < 2 * half + VANE_GAP:
            out.append(Failure("F5.spin", "羽", f"隣の羽の中心の間 {chord:.1f}mm に羽の幅 {2 * half:.1f}＋{VANE_GAP} が入らず、羽が重なる"))
        free = p["vane_radius"] - half - p["hub_r"]
        if free < TWIST_LEN * p["spoke_w"]:
            out.append(Failure("F5.spin", "腕", f"腕の長さ {free:.1f}mm が幅の {TWIST_LEN} 倍に足りず、羽をねじると折れ目が付く"))
    return out


def _top_floors(p):
    out = []
    off = disc_com_offset(p)
    if off > COM_TOL:
        out.append(Failure("F5.spin", "円盤", f"円盤の重心が軸から {off:.1f}mm 外れ（{COM_TOL}mm まで）、ぶれて跳ねる"))
    w, l = top_omega_min(p)
    if w > OMEGA_HAND * SLEEP_RATIO:
        _, md, ms = top_masses(p)
        out.append(Failure("F5.spin", "独楽", f"倒れずに回るのに {w:.0f}rad/s 要り、指で回す見込み {OMEGA_HAND:.0f} の {SLEEP_RATIO} 倍を超える"
                                          f"（重心の高さ {l:.1f}mm・円盤 {md:.2f}g・軸 {ms:.2f}g）"))
    tilt = math.degrees(math.atan2(p["tip"], p["disc_r"]))
    if tilt < MIN_TILT_DEG:
        out.append(Failure("F5.spin", "下の軸", f"下の軸 {p['tip']}mm では {tilt:.1f}° 傾くと円盤の縁が床に付く（{MIN_TILT_DEG}° まで要る）"))
    if p["grip"] < MIN_GRIP_TOP:
        out.append(Failure("F5.spin", "上の軸", f"上の軸 {p['grip']}mm が {MIN_GRIP_TOP}mm 無く、指でひねれない"))
    if p["disc_r"] - p["hole_offset"] - p["axle_d"] / 2 < HOLE_MARGIN:
        out.append(Failure("F5.spin", "円盤の穴", "穴が円盤の縁に近すぎる"))
    return out


def check_physics(p):
    return _top_floors(p) if p["kind"] == "top" else _wheel_floors(p)


# ---- 部品 ----

def _circle(cx, cy, r, n=64):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _poly_art(geom, fill, stroke=None, sw=0):
    """shapely の面を絵の面にする。切れて 2 つ以上になった時は全部描く。"""
    out = []
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty or g.geom_type != "Polygon":
            continue
        item = {"kind": "poly", "pts": [(round(x, 3), round(y, 3)) for x, y in g.exterior.coords[:-1]], "fill": fill}
        if stroke:
            item.update(stroke=stroke, sw=sw)
        out.append(item)
    return out


def _pinwheel_part(p):
    S, u = p["square"], p["uncut"]
    c = S / 2
    k = u / math.sqrt(2)
    # 角ごとに、辺から切り込みの終わりへ入って戻る細い V。角の順は (0,0)→(S,0)→(S,S)→(0,S)。
    ends = {(0, 0): (c - k, c - k), (S, 0): (c + k, c - k), (S, S): (c + k, c + k), (0, S): (c - k, c + k)}
    w = NOTCH
    pts = [(0, w), ends[(0, 0)], (w, 0),
           (S - w, 0), ends[(S, 0)], (S, w),
           (S, S - w), ends[(S, S)], (S - w, S),
           (w, S), ends[(0, S)], (0, S - w)]
    body = Polygon(pts)
    # 1 つおきの角に穴。どの三角も同じ回りの向きの角を選ぶ（向きがそろわないと風を受けても打ち消し合う）。
    a = tip_hole_dist(p)
    tips = [((S, 0), (-1, 0)), ((S, S), (0, -1)), ((0, S), (1, 0)), ((0, 0), (0, 1))]
    holes = [(c, c, p["hole_d"] / 2)]
    for (x, y), (ex, ey) in tips:
        dx, dy = (c - x) / math.hypot(c - x, c - y), (c - y) / math.hypot(c - x, c - y)
        bx, by = ex + dx, ey + dy
        n = math.hypot(bx, by)
        holes.append((x + a * bx / n, y + a * by / n, p["hole_d"] / 2))
    # 絵: 4 つの三角を辺の真ん中で 2 つに分けた 8 枚を、金と白で交互に塗る。コマ 14 左の 8 枚の羽の先が橙なので、外の辺の帯を橙にする。
    inner = body.buffer(-0.4, join_style=2)
    corners = [(0, 0), (S, 0), (S, S), (0, S)]
    art = []
    for i in range(4):
        (x0, y0), (x1, y1) = corners[i], corners[(i + 1) % 4]
        mid = ((x0 + x1) / 2, (y0 + y1) / 2)
        for j, half in enumerate(([(x0, y0), mid, (c, c)], [mid, (x1, y1), (c, c)])):
            tri = Polygon(half).intersection(inner)
            art += _poly_art(tri, GOLD if j == 0 else CREAM)
            if j == 0:
                continue
            # 橙は軸へ寄せる角（穴のある半分）の外の帯だけ。図の羽の先の橙は羽の長さの 3 割ほど（目測）。
            # 寄せる角が色で分かるので、組む時に 1 つおきを数え間違えにくい。
            band = Polygon([(x0, y0), (x1, y1), (x1 + (c - x1) * 0.24, y1 + (c - y1) * 0.24), (x0 + (c - x0) * 0.24, y0 + (c - y0) * 0.24)])
            art += _poly_art(tri.intersection(band), ORANGE)
    # 中心の飾りの丸。図の羽の中心の点を写した。穴より外。
    art += _poly_art(Point(c, c).buffer(p["hole_d"] / 2 + 2.2, 24).difference(Point(c, c).buffer(p["hole_d"] / 2 + 1.2, 24)).intersection(inner), INK)
    return Part(1, "vanes", "羽", pts, label_xy=(c - 3, 3), label="1 羽", holes=holes, art=art)


def _star_outline(p):
    R = wheel_radius(p)
    a, rv, sw, hr = p["vane"], p["vane_radius"], p["spoke_w"], p["hub_r"]
    half = a / math.sqrt(2)
    shapes = [Point(R, R).buffer(hr, 32)]
    vanes = []
    for i in range(8):
        t = 2 * math.pi * i / 8 - math.pi / 2
        ux, uy, vx, vy = math.cos(t), math.sin(t), -math.sin(t), math.cos(t)
        cx, cy = R + rv * ux, R + rv * uy
        # 図の羽は菱形（対角線が腕の向き）。
        dia = Polygon([(cx + half * ux, cy + half * uy), (cx + half * vx, cy + half * vy), (cx - half * ux, cy - half * uy), (cx - half * vx, cy - half * vy)])
        r0 = hr - 1
        spoke = Polygon([(R + r0 * ux + sw / 2 * vx, R + r0 * uy + sw / 2 * vy), (cx + sw / 2 * vx, cy + sw / 2 * vy),
                         (cx - sw / 2 * vx, cy - sw / 2 * vy), (R + r0 * ux - sw / 2 * vx, R + r0 * uy - sw / 2 * vy)])
        shapes += [dia, spoke]
        vanes.append(dia)
    return unary_union(shapes), vanes, R


def _square_part(p):
    shape, vanes, R = _star_outline(p)
    if shape.geom_type != "Polygon":
        # 羽が重なると 1 つの輪郭にならない。床（F5.spin）が羽の重なりで落とすので、ここでは外の殻で描くだけにする。
        shape = shape.convex_hull
    pts = [(round(x, 3), round(y, 3)) for x, y in shape.exterior.coords[:-1]]
    inner = Polygon(pts).buffer(-0.35, join_style=2)
    art = _poly_art(Point(R, R).buffer(p["hub_r"] - 0.4, 32).intersection(inner), GOLD)
    for i, v in enumerate(vanes):
        # 図の羽は薄茶と薄紅が混じる。交互に塗る。
        art += _poly_art(v.buffer(-0.4, join_style=2).intersection(inner), GOLD if i % 2 else "#d9a58c", INK, 0.25)
    top = vanes[0].centroid
    return Part(1, "star", "羽", pts, label_xy=(top.x - 1, top.y - 1.7), label="1", holes=[(R, R, p["hole_d"] / 2)], art=art)


HUB_DISC = 8  # 四角の羽の前の座金の半径。穴の余白 HOLE_MARGIN を取れる大きさ


def _washer_part(p):
    r = HUB_DISC
    return Part(2, "washer", "座金", _circle(r, r, r, 32), label_xy=(r - 1, 0.8), label="2", holes=[(r, r, p["hole_d"] / 2)],
                art=_poly_art(Polygon(_circle(r, r, r - 0.4, 32)), GOLD))


def _disc_part(p, i):
    r = p["disc_r"]
    hole = (r + p["hole_offset"], r, p["axle_d"] / 2)
    art = []
    if i in (0, p["layers"] - 1):
        # 表と裏に見える 1 枚目と最後の 1 枚だけ塗る。コマ 26 左の円盤は黄土の地に、縁寄りと中ほどに橙の輪（目測で半径の 0.72〜0.62 と 0.4〜0.3）。
        for rr, col in ((r - 0.4, GOLD), (0.72 * r, ORANGE), (0.62 * r, GOLD), (0.40 * r, ORANGE), (0.30 * r, GOLD)):
            art += _poly_art(Polygon(_circle(r, r, rr, 64)), col)
    n = i + 1
    return Part(n, f"disc{LAYER_KEYS[i]}", f"円盤 {n} 枚目", _circle(r, r, r, 96), label_xy=(r - 1.2, 1.5), label=str(n), holes=[hole], art=art)


def parts(p):
    k = p["kind"]
    if k == "pinwheel":
        return [_pinwheel_part(p)]
    if k == "square":
        return [_square_part(p), _washer_part(p)]
    return [_disc_part(p, i) for i in range(int(p["layers"]))]


def place(by_key, page, top, gap):
    """部品を左から並べ、入らなければ次の行へ送る。文字は部品の下に全幅で置く。"""
    x, y, row = page.x0, top, 0.0
    for q in by_key.values():
        if x > page.x0 and x + q.width > page.x1:
            x, y, row = page.x0, y + row + gap, 0.0
        q.x, q.y = x, y
        x += q.width + gap
        row = max(row, q.height)
    return y + row + gap, page.x1 - page.x0, page.x0


# ---- 部品表・組み方 ----

def bom(p):
    paper = f"紙（厚さ {thickness(p):.2f}mm 前後・{p['paper_gsm']}g/m² の見込み）"
    why = "家庭のプリンタで刷って作るため"
    k = p["kind"]
    if k == "top":
        n = int(p["layers"])
        rows = [{"number": i + 1, "key": f"disc{LAYER_KEYS[i]}", "name": f"円盤 {i + 1} 枚目（{n} 枚重ねる）", "qty": 1, "material": paper,
                 "substituted": True, "original_guess": "木（推定。図の円盤の輪は木地の塗りに見える）", "reason": f"{why}。1 枚では軽いので {n} 枚を重ねて貼る"}
                for i in range(n)]
        L = top_stick_length(p)
        stick = f"爪楊枝（長さ約 {L:.0f}mm）" if p["axle_d"] <= 2.2 and L <= 60 else f"竹串（太さ {p['axle_d']:g}mm・長さ約 {L:.0f}mm に切る）"
        rows.append({"number": 7, "key": "axle", "name": "軸", "qty": 1, "material": stick, "substituted": True,
                     "original_guess": "不明（図の細い棒の素材は読めない）", "reason": "家にあり、まっすぐで円盤の穴に固く通るため"})
        return rows
    if k == "pinwheel":
        rows = [{"number": 1, "key": "vanes", "name": "羽", "qty": 1, "material": paper, "substituted": True,
                 "original_guess": "紙（推定。図の羽の色は紙の色に見える）", "reason": why}]
    else:
        rows = [{"number": 1, "key": "star", "name": "羽", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙（推定。同じ）", "reason": why},
                {"number": 2, "key": "washer", "name": "座金", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図の中心の筒）",
                 "reason": "羽が軸に対して傾かないよう、2 か所で軸に載せるため"}]
    rows += [
        {"number": 7, "key": "axle", "name": "軸", "qty": 1, "material": f"竹串（太さ {p['axle_d']:g}mm・長さ約 {axle_length(p):.0f}mm に切り、先を落とす）",
         "substituted": True, "original_guess": "不明（図の細い棒の素材は読めない）", "reason": "家にあり、まっすぐで穴に通しやすいため"},
        {"number": 8, "key": "stick", "name": "柄", "qty": 1, "material": f"ストロー（長さ約 {p['stick_length']}mm）", "substituted": True,
         "original_guess": "竹（推定。図の長い棒の節の無い色から）", "reason": "竹串を横に刺して通せるため"},
        {"number": 9, "key": "spacer", "name": "間の筒", "qty": 2, "material": f"ストローの切れ端（{p['spacer']}mm と {p['bearing']}mm）", "substituted": True,
         "original_guess": "不明", "reason": "羽を柄から離し、2 か所の穴の間を保つため"},
        {"number": 10, "key": "stop", "name": "止め", "qty": 1, "material": "セロハンテープ（軸の先に巻く）", "substituted": True, "original_guess": "不明", "reason": "家にあり、羽が抜けないようにするため"},
    ]
    return rows


def materials(p):
    by = {r["key"]: r for r in bom(p)}
    first = by.get("vanes") or by.get("star") or by["disca"]
    out = [f"{first['material']}を 1 枚", "のり、はさみ、定規", by["axle"]["material"]]
    if p["kind"] != "top":
        out += [by["stick"]["material"], by["spacer"]["material"], by["stop"]["material"]]
    return out


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる"]
    k = p["kind"]
    if k == "top":
        n = int(p["layers"])
        out += [f"円盤を {n} 枚とも実線で切る", "1 枚目の穴に竹串の先で穴をあけ、残りの円盤も穴を重ねてあける",
                f"{n} 枚を穴をそろえて重ねて貼り、乾くまで本などで押さえる（反ると回らない）",
                f"軸を通し、円盤の下に {p['tip']}mm、上に {p['grip']}mm 出して、穴の所をのりで止める",
                "円盤が軸に直角か、横から見て確かめる", "上の軸を指でひねって回す"]
        return out
    if k == "pinwheel":
        out += ["1 羽を外の線で切る。角の切り込みは V の線を中心の手前まで切る", "穴を 5 つ竹串の先であける"]
    else:
        out += ["1 羽と 2 座金を切る。腕は細いので、はさみをゆっくり進める", "穴を竹串の先であける",
                f"8 本の腕を、根元から同じ向きに約 {TWIST_DEG}° ねじる"]
    out += [f"柄のストローの上の端から {AXLE_FROM_TOP}mm の所に竹串を横に刺し通す", f"竹串に {p['spacer']}mm のストローを通す"]
    if k == "pinwheel":
        out += ["羽の中心の穴を竹串に通す", f"{p['bearing']}mm のストローを通す", "印の穴のある 4 つの角を順に中心へ曲げ、穴を竹串に通す（折り目を付けない）"]
    else:
        out += ["1 羽の中心の穴を竹串に通す", f"{p['bearing']}mm のストローを通し、2 座金を通す"]
    out += ["竹串の先にテープを巻いて止める。羽が軽く回るか確かめる", "息を吹きかけるか、持って走る"]
    return out


RESULTS = ("回った", "回らない")


def measures(p):
    """回るかの二択でなく、回り方を言葉か絵で予想する（ほかの雛形と同じ）。"""
    if p["kind"] == "top":
        return {"predict": "独楽はどう回ると思いますか（言葉か絵で）", "rows": [[("回した手（指・両手）", 40)]]}
    return {"predict": "羽はどう回ると思いますか（言葉か絵で）", "rows": [[("風にした物（息・団扇・走る）", 40)]]}


def diagram(x, y, w, h, p):
    """横から見た組み上がりの並び。寸法の図ではなく、部品の並びを見せるだけの絵。"""
    if p["kind"] == "top":
        r, tip, grip = p["disc_r"], p["tip"], p["grip"]
        s = min(w / (2 * r + 4), h / (tip + grip + 4))
        cx, base = x + w / 2, y + h - 2
        dh = max(p["layers"] * thickness(p) * s, 0.6)
        disc_y = base - tip * s - dh
        return [{"kind": "line", "x1": cx, "y1": base, "x2": cx, "y2": disc_y - grip * s},
                {"kind": "rect", "x": cx - r * s, "y": disc_y, "w": 2 * r * s, "h": dh}]
    R = wheel_radius(p)
    s = min(w / (STRAW_D + p["spacer"] + p["bearing"] + 12), h / (2 * R + 4))
    stick_x, cy = x + 4 * s, y + h / 2
    face = stick_x + (STRAW_D + p["spacer"]) * s
    return [{"kind": "rect", "x": stick_x, "y": cy - AXLE_FROM_TOP * s, "w": STRAW_D * s, "h": y + h - (cy - AXLE_FROM_TOP * s)},
            {"kind": "line", "x1": stick_x, "y1": cy, "x2": face + (p["bearing"] + FRONT_STOP) * s, "y2": cy},
            {"kind": "line", "x1": face, "y1": cy - R * s, "x2": face, "y2": cy + R * s},
            {"kind": "line", "x1": face + p["bearing"] * s, "y1": cy - 2, "x2": face + p["bearing"] * s, "y2": cy + 2, "dash": "1,0.6"}]
