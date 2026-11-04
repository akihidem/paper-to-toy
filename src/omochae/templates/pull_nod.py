"""雛形 pull_nod: 糸を引くと部品が軸で振れ、離すと粘土の重りで元に戻る。

形（kind）は玩具の違いなので描き分ける。
- bow: 米搗き人形（推定）。台の上の 2 本の柱に腰の軸を通し、体の前を糸で下へ引くと礼をして臼をつく。尾の粘土で起き上がる。
- jaw: 振り獅子（獅子頭）。棒の上の頭に下顎を軸で留め、顎の後ろの舌を糸で引くと口が閉じる。顎の先の粘土で口が開く。
どちらも図から読んだ仕掛けで【解釈】。寸法は手元の複写の図の比と A4 の紙面から出し、どの値も実物では未確認。
Claude が変えてよいのは RANGES の名前の値だけ。

動きの見込み（check_physics の式）の前提:
- 振れる部品は軸のまわりの天秤として見る。紙の曲がり・糸の伸び・空気は入れない。
- 戻る向きの力のモーメント（g·mm）は、重りと紙の質量 × 軸からの水平の距離。静かな時は止め（bow は尾の下の柱、jaw は舌の上のこぶ）に
  押し付けられている前提で、戻る向きのモーメントが軸の摩擦の SAFETY 倍を超える事を見る。振り切った所では cos(角度) 倍に減るので、そこでも見る。
- 軸の摩擦のモーメントは 摩擦係数 MU × 全質量 × 軸の半径。竹串と紙の MU は見込み（量っていない）。
- 振れる角度は、止めに当たるまでの幾何だけで出す（bow は頭が臼の上に当たるまで、jaw は舌がこぶに当たるまで）。
"""
import math

from shapely.geometry import LineString, Point, Polygon

from ..model import Failure, Part

ID = "pull_nod"
DEFAULTS = {
    "kind": "bow",
    # bow（米搗き人形）の寸法。torso_len は腰の軸から頭の先まで、tail_len は軸から尾の端まで。
    "plank_length": 110, "plank_width": 36, "post_height": 50, "post_width": 12,
    "torso_len": 50, "torso_w": 22, "tail_len": 20, "string_arm": 14,
    "stop_height": 18, "mortar_round": 56,
    # jaw（振り獅子）の寸法。jaw_len は軸から顎の先まで、tab_len は軸から舌の端まで。
    "head_w": 50, "head_h": 46, "jaw_len": 34, "jaw_h": 14, "tab_len": 14, "stop_gap": 6,
    "stick_len": 120, "stick_w": 10,
    "weight_g": 2.0, "glue": 8,
    # 紙の面密度は見込み。実物の紙を量ったら置き換える。
    "paper_gsm": 150,
}
RANGES = {
    "plank_length": (80, 180), "plank_width": (25, 60), "post_height": (30, 80), "post_width": (6, 20),
    "torso_len": (30, 80), "torso_w": (14, 36), "tail_len": (10, 40), "string_arm": (6, 40),
    "stop_height": (5, 60), "mortar_round": (40, 70),
    "head_w": (30, 70), "head_h": (30, 70), "jaw_len": (20, 60), "jaw_h": (8, 24), "tab_len": (6, 30), "stop_gap": (1, 20),
    "stick_len": (60, 160), "stick_w": (6, 16),
    "weight_g": (0.1, 15), "glue": (5, 12), "paper_gsm": (40, 400),
}
KINDS = ("bow", "jaw")
# 刷る形を決める寸法（玩具の形）。--params では既定に頼らず必ず書かせる（compose の決まり）。
FORM = "kind"
FORMS = KINDS
# 既定の出典。米搗き人形を既定にする（族の先頭の玩具）。獅子は場面で --source を R0000030-L に替える。
SOURCE = "NDL-1187053-R0000006-L-pull_nod"
HOLE_MARGIN = 4  # 穴の縁から紙の端・隣の穴の縁までの見込み。虎の雛形と同じ値（これより狭いと裂けやすい）
AXLE_R, STRING_R = 1.2, 1.0  # 竹串の穴と糸の穴の半径（mm）
MIN_SWING = 15  # 引いて動いたと目で分かる角度の見込み。虎の 10° より大きくするのは、礼・噛む動きが「振れ」より大きく見えないと遊びにならないため
MU = 0.4  # 竹串と紙の摩擦係数の見込み（量っていない）
SAFETY = 3  # 戻る力が摩擦の何倍あれば戻ると見るか。紙のたわみ・糸の擦れを入れていないので余裕を取る
POST_GAP = 6  # 2 本の柱の間。体の紙（2 枚重ね）が擦れずに入る幅の見込み
CLAY_IN = 3  # 粘土の中心を紙の端からこれだけ内側に付ける
WOOD, LINE, SKIN, CLOTH, ROUGE = "#c9b48a", "#3c3424", "#d9c2a0", "#6b4a2e", "#c9826b"
GOLD, FACE, MOUTH, STICK = "#c8a845", "#d4b49a", "#9a4a3a", "#cdb066"
TITLES = {"bow": "糸を引くと腰で礼をする", "jaw": "糸を引くと顎が閉じる"}


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


def paper_mass(area_mm2, gsm):
    return area_mm2 * 1e-6 * gsm


def lever(p):
    """振れる部品の質量の点 [(質量 g, 戻る向きに正の水平の距離 mm)] と、糸の腕（mm）。

    bow は体の紙（2 枚重ね）と尾の粘土。紙の重心は体の中央で、軸より前（礼の向き）に (torso_len - tail_len)/2。
    jaw は顎の紙（1 枚）と顎の先の粘土。戻る向き（口が開く向き）は前。
    """
    g = p["paper_gsm"]
    if p["kind"] == "bow":
        card = paper_mass(2 * p["torso_w"] * (p["torso_len"] + p["tail_len"]), g)
        pts = [(card, -(p["torso_len"] - p["tail_len"]) / 2), (p["weight_g"], p["tail_len"] - CLAY_IN)]
        return pts, p["string_arm"]
    card = paper_mass(p["jaw_h"] * (p["jaw_len"] + p["tab_len"]), g)
    pts = [(card, (p["jaw_len"] - p["tab_len"]) / 2), (p["weight_g"], p["jaw_len"] - CLAY_IN)]
    return pts, jaw_string_arm(p)


def jaw_string_arm(p):
    # 糸の穴は舌の端から HOLE_MARGIN + 糸の穴の半径 + 0.5 の所。端に寄せるほど腕が長く軽く引けるが、端が裂ける。
    return p["tab_len"] - (HOLE_MARGIN + STRING_R + 0.5)


def return_moment(p):
    """静かな時の戻る向きのモーメント（g·mm）と、軸の摩擦のモーメント（g·mm）。"""
    pts, _ = lever(p)
    m = sum(w * x for w, x in pts)
    friction = MU * sum(w for w, _ in pts) * AXLE_R
    return m, friction


def swing_deg(p):
    """引いて止めに当たるまでに振れる角度。

    bow: 静かな時は体が水平（尾が後ろの柱に載る）。頭の下の縁（軸の高さ − 体の幅の半分）が臼の上（stop_height）まで下がると止まる。
    下がれる量が体の長さ以上なら、臼に当たらず 90° まで振れる（それ以上は見ない）。
    jaw: 静かな時は舌がこぶに当たって口が開いている。引くと口が閉じるまで（顎が水平まで）振れる。振れる角度は舌の長さとこぶまでの隙間で決まる。
    """
    if p["kind"] == "bow":
        drop = p["post_height"] - p["torso_w"] / 2 - p["stop_height"]
        if drop <= 0:
            return 0.0
        return math.degrees(math.asin(min(1.0, drop / p["torso_len"])))
    return math.degrees(math.atan2(p["stop_gap"], p["tab_len"]))


def pull_gf(p):
    """引き切る時に糸に要る力（gf）。戻るモーメントと摩擦を糸の腕で割る。組み方の文に見当として書くだけで、床にはしない。"""
    m, friction = return_moment(p)
    _, arm = lever(p)
    return (m + friction) / arm if arm > 0 else math.inf


def hole_margins(parts):
    """穴ごとに、紙の端までと隣の穴までの縁の余白の最小（mm）。F5.hole は穴が紙の中にあるかだけを見るので、裂けにくさはここで見る。"""
    out = []
    for q in parts:
        edge = Polygon(q.outline).exterior
        for i, (x, y, r) in enumerate(q.holes):
            gaps = [edge.distance(Point(x, y)) - r]
            gaps += [math.hypot(x - x2, y - y2) - r - r2 for x2, y2, r2 in q.holes[i + 1:]]
            out.append((q.name, (x, y), min(gaps)))
    return out


def check_physics(p):
    out = []
    m, friction = return_moment(p)
    sw = swing_deg(p)
    what = "尾の粘土" if p["kind"] == "bow" else "顎の先の粘土"
    # 1. 戻る力が静かな時に勝つ。負なら止めから離れて倒れたまま、摩擦より小さければ引いた後に戻らない。
    if m <= SAFETY * friction:
        out.append(Failure("F5.pull_nod", what, f"戻るモーメント {m:.1f}g·mm が摩擦 {friction:.1f}g·mm の {SAFETY} 倍以下で、離しても戻らない"))
    elif m * math.cos(math.radians(sw)) <= SAFETY * friction:
        out.append(Failure("F5.pull_nod", what, f"{sw:.0f}° 振り切った所で戻るモーメントが摩擦の {SAFETY} 倍以下になる"))
    # 2. 引いた時に止めに当たるまで MIN_SWING 以上振れる。
    if sw < MIN_SWING:
        stop = "臼" if p["kind"] == "bow" else "こぶ"
        out.append(Failure("F5.pull_nod", stop, f"{stop}に当たるまで {sw:.1f}° しか振れない（{MIN_SWING}° 要る）"))
    # 3. 穴の縁の余白。
    for name, (x, y), gap in hole_margins(parts(p)):
        if gap < HOLE_MARGIN:
            out.append(Failure("F5.pull_nod", name, f"穴 ({x:.1f}, {y:.1f}) の縁から端か隣の穴まで {gap:.1f}mm で、{HOLE_MARGIN}mm 取れない"))
    if p["kind"] == "bow":
        # 軸の前に体の長さ、後ろに尾と止めの柱が載らないと、台からはみ出す。
        need = p["torso_len"] + p["tail_len"] + 10
        if p["plank_length"] < need:
            out.append(Failure("F5.pull_nod", "台", f"台が {p['plank_length']}mm で、体と尾の載る {need}mm に足りない"))
    else:
        # 舌の端が頭の右の縁を越えると、こぶを頭に貼れない（こぶの貼る所が無い）。
        if p["tab_len"] + 2 > p["head_w"] - 8:
            out.append(Failure("F5.pull_nod", "舌", "舌が頭の幅に収まらず、こぶを貼る所が無い"))
    return out


def _panel(x0, y0, x1, y1, fill):
    return {"kind": "poly", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "fill": fill}


def _box(x0, y0, x1, y1):
    """貼る所の目印の四角（線）。"""
    return {"kind": "line", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], "stroke": LINE, "sw": 0.25}


def _fit(pts, x0, y0, w0, h0, ox, oy, w, h):
    """図の上で取った点（図の画素の座標）を、部品の中の箱へ写す。縦横の比は箱に合わせて変わる。"""
    return [(ox + (x - x0) / w0 * w, oy + (y - y0) / h0 * h) for x, y in pts]


def _clip_lines(lines, shape, stroke, sw):
    out = []
    for line in lines:
        piece = LineString(line).intersection(shape)
        for g in getattr(piece, "geoms", [piece]):
            if not g.is_empty and g.geom_type == "LineString":
                out.append({"kind": "line", "pts": list(g.coords), "stroke": stroke, "sw": sw})
    return out


# 米搗き人形の体。R0000006 左頁を 1600 幅で見た図（表示の 1205 幅の座標）から手で取った点。原図の画素は使っていない。
# 図は前かがみの姿なので、型紙では水平に伸ばして写す（頭が左＝前、腰が右）。
_FIG = [(505, 1080), (520, 1050), (550, 1035), (580, 1040), (605, 1062), (650, 1048), (800, 1075), (880, 1110), (950, 1150), (960, 1185),
        (940, 1240), (900, 1260), (860, 1240), (760, 1200), (650, 1165), (600, 1172), (560, 1180), (520, 1160), (505, 1130)]
_CLOTH = [(865, 1100), (945, 1135), (962, 1200), (935, 1255), (905, 1258), (895, 1175), (860, 1150)]
_CHEEK = [(530, 1120), (548, 1112), (562, 1125), (550, 1142), (532, 1138)]
_FIG_LINES = [[(600, 1172), (612, 1100)]]  # 首の線だけ。腰の線は帯の絵と重なって読めなかった
FIG_BOX = (500, 1030, 460, 230)


def _figure_art(ox, oy, w, h, flip):
    """体の紙の半分 1 枚の絵。flip は折って裏になる半分（折り線で上下に写す）。"""
    fit = lambda ps: _fit(ps, *FIG_BOX, ox, oy, w, h)
    fix = (lambda ps: [(x, 2 * oy + h - y) for x, y in ps]) if flip else (lambda ps: ps)
    body = fix(fit(_FIG))
    shape = Polygon(body)
    art = [{"kind": "poly", "pts": body, "fill": SKIN, "stroke": LINE, "sw": 0.2}]
    for piece, fill in ((_CLOTH, CLOTH), (_CHEEK, ROUGE)):
        g = Polygon(fix(fit(piece))).intersection(shape.buffer(-0.15))
        for q in getattr(g, "geoms", [g]):
            if not q.is_empty and q.geom_type == "Polygon":
                art.append({"kind": "poly", "pts": list(q.exterior.coords)[:-1], "fill": fill})
    art += _clip_lines([fix(fit(ln)) for ln in _FIG_LINES], shape.buffer(-0.1), LINE, 0.35)
    return art


# 獅子頭。R0000030 左頁（表示の 1205 幅の座標）から手で取った点。鼻先が左、頭の後ろが右。顎は別の部品にする。
_HEAD = [(505, 1035), (540, 1005), (590, 975), (575, 935), (610, 900), (680, 885), (760, 900), (800, 940), (800, 1010), (790, 1080),
         (790, 1170), (640, 1170), (620, 1090), (530, 1075), (505, 1060)]
_MANE = [(575, 935), (610, 900), (680, 885), (760, 900), (800, 940), (790, 975), (700, 960), (620, 975)]
_EYES = [[(600, 1022), (622, 1015), (632, 1032), (610, 1040)], [(648, 1030), (670, 1024), (678, 1042), (655, 1048)]]
_HEAD_LINES = [[(590, 1000), (640, 990)], [(645, 1005), (690, 1000)], [(510, 1050), (600, 1062)], [(700, 990), (760, 1060)], [(730, 980), (780, 1040)]]
HEAD_BOX = (505, 885, 295, 285)
MANE_HUB = (690, 1000)


def _head_part(p):
    w, h = p["head_w"], p["head_h"]
    fit = lambda ps: _fit(ps, *HEAD_BOX, 0, 0, w, h)
    outline = fit(_HEAD)
    shape = Polygon(outline).buffer(-0.15)
    art = [{"kind": "poly", "pts": outline, "fill": FACE, "stroke": LINE, "sw": 0.2}]
    mane = Polygon(fit(_MANE)).intersection(shape)
    art.append({"kind": "poly", "pts": list(mane.exterior.coords)[:-1], "fill": GOLD})
    # たてがみの毛は、図の放射の線を中心から外へ引いて、たてがみの中だけ残す（図の金の毛の数を写すのでなく、向きを写す）。
    hub = fit([MANE_HUB])[0]
    rays = [[hub, (hub[0] + 60 * math.cos(math.radians(a)), hub[1] - 60 * math.sin(math.radians(a)))] for a in range(20, 165, 12)]
    art += _clip_lines(rays, mane.buffer(-0.2), LINE, 0.25)
    art += [{"kind": "poly", "pts": fit(e), "fill": "#ffffff", "stroke": LINE, "sw": 0.25} for e in _EYES]
    art += _clip_lines([fit(ln) for ln in _HEAD_LINES], shape, LINE, 0.35)
    px, py = jaw_pivot(p)
    return Part(1, "head", "頭", outline, label_xy=(w * 0.55, h * 0.58), label="1", art=art, holes=[(px, py, AXLE_R)])


def jaw_pivot(p):
    """頭の紙の上の顎の軸の穴。舌が頭の右の縁の 2mm 内側で終わり、閉じた顎が頭の下の縁に揃う所。"""
    return p["head_w"] - p["tab_len"] - 2, p["head_h"] - p["jaw_h"] / 2


def _bow_parts(p):
    L, W = p["plank_length"], p["plank_width"]
    T, t, TW = p["torso_len"], p["tail_len"], p["torso_w"]
    g, ph, pw = p["glue"], p["post_height"], p["post_width"]
    # 1 台: 2 枚重ねにして反らないようにする。糸の穴は軸の真下から string_arm だけ前。
    pivot_x = L - t - 5
    sx = pivot_x - p["string_arm"]
    plank = Part(1, "plank", "台", [(0, 0), (L, 0), (L, 2 * W), (0, 2 * W)], label_xy=(2, 2), label="1 台",
                 valley=[((0, W), (L, W))], holes=[(sx, W / 2, STRING_R), (sx, 1.5 * W, STRING_R)])
    plank.art = [_panel(0.3, 0.3, L - 0.3, W - 0.3, WOOD), _panel(0.3, W + 0.3, L - 0.3, 2 * W - 0.3, WOOD)]
    # 上の面に、柱・止めの柱・臼を貼る所の目印を描く。軸の位置と糸の穴の距離が式の前提なので、貼る所を目で合わせられるようにする。
    fx = pivot_x + t - CLAY_IN
    mx = pivot_x - (T - 5)
    r = p["mortar_round"] / (2 * math.pi)
    plank.art += [_box(pivot_x - pw / 2, W / 2 - POST_GAP / 2, pivot_x + pw / 2, W / 2 + POST_GAP / 2),
                  _box(fx - g / 2, W / 2 - pw / 2, fx + g / 2, W / 2 + pw / 2),
                  _box(mx - r, W / 2 - r, mx + r, W / 2 + r)]
    # 2 柱: 1 本の帯を U の字に折り、底を台に貼る。穴の中心が台から post_height の高さに来るよう、柱の長さは post_height + 幅の半分。
    side = ph + pw / 2
    posts = Part(2, "posts", "柱", [(0, 0), (2 * side + POST_GAP, 0), (2 * side + POST_GAP, pw), (0, pw)], label_xy=(pw, 1.5), label="2",
                 valley=[((side, 0), (side, pw)), ((side + POST_GAP, 0), (side + POST_GAP, pw))],
                 glue=[[(side, 0), (side + POST_GAP, 0), (side + POST_GAP, pw), (side, pw)]],
                 holes=[(pw / 2, pw / 2, AXLE_R), (2 * side + POST_GAP - pw / 2, pw / 2, AXLE_R)])
    posts.art = [_panel(pw + 6, 0.3, side - 0.3, pw - 0.3, WOOD), _panel(side + POST_GAP + 0.3, 0.3, 2 * side + POST_GAP - pw, pw - 0.3, WOOD)]
    # 3 体: 2 枚重ね。左が頭（前）、軸は前から torso_len、糸の穴は軸から string_arm 前。
    n = T + t
    torso = Part(3, "torso", "体", [(0, 0), (n, 0), (n, 2 * TW), (0, 2 * TW)], label_xy=(n - 6, 1), label="3",
                 valley=[((0, TW), (n, TW))],
                 holes=[(T, TW / 2, AXLE_R), (T, 1.5 * TW, AXLE_R), (T - p["string_arm"], TW / 2, STRING_R), (T - p["string_arm"], 1.5 * TW, STRING_R)])
    torso.art = _figure_art(0.6, 0.6, n * 0.92, TW - 1.2, False) + _figure_art(0.6, TW + 0.6, n * 0.92, TW - 1.2, True)
    # 4 止めの柱: 尾の下の縁が載る高さ（軸の高さ − 体の幅の半分）。下を糊代で折って台に貼る。
    sh = ph - TW / 2
    stop = Part(4, "stop", "止めの柱", [(0, 0), (sh + g, 0), (sh + g, pw), (0, pw)], label_xy=(1, 1.5), label="4",
                valley=[((sh, 0), (sh, pw))], glue=[[(sh, 0), (sh + g, 0), (sh + g, pw), (sh, pw)]])
    stop.art = [_panel(6, 0.3, sh - 0.3, pw - 0.3, WOOD)]
    # 5 臼: 丸めて筒にする。高さが頭の止め（stop_height）。杵は描かない（臼に当たって止まる所だけを作る）。
    c, hh = p["mortar_round"], p["stop_height"]
    mortar = Part(5, "mortar", "臼", [(0, 0), (c + g, 0), (c + g, hh), (0, hh)], label_xy=(1, 1), label="5",
                  valley=[((c, 0), (c, hh))], glue=[[(c, 0), (c + g, 0), (c + g, hh), (c, hh)]])
    mortar.art = [_panel(6, 0.3, c - 0.3, hh - 0.3, WOOD)] + [{"kind": "line", "pts": [(6.5, y), (c - 0.8, y)], "stroke": LINE, "sw": 0.3} for y in (2.5, hh - 2.5)]
    return [plank, posts, torso, stop, mortar]


def _jaw_parts(p):
    head = _head_part(p)
    jl, jh, tl = p["jaw_len"], p["jaw_h"], p["tab_len"]
    n = jl + tl
    # 2 顎: 左が顎の先、軸は先から jaw_len、舌の端に糸の穴。
    jaw = Part(2, "jaw", "下顎", [(3, 0), (n, 0), (n, jh), (0, jh), (0, 3)], label_xy=(jl + 1.5, jh - 4.5), label="2",
               holes=[(jl, jh / 2, AXLE_R), (n - (HOLE_MARGIN + STRING_R + 0.5), jh / 2, STRING_R)])
    jaw.art = [{"kind": "poly", "pts": [(3.3, 0.4), (jl - 2, 0.4), (jl - 2, jh * 0.45), (0.6, jh * 0.45), (0.6, 3.2)], "fill": MOUTH},
               {"kind": "poly", "pts": [(0.6, jh * 0.55), (jl - 2, jh * 0.55), (jl - 2, jh - 0.4), (0.6, jh - 0.4)], "fill": FACE}]
    jaw.art += [{"kind": "line", "pts": [(x, 0.8), (x + 1.2, jh * 0.4), (x + 2.4, 0.8)], "stroke": "#ffffff", "sw": 0.3} for x in range(4, int(jl) - 5, 3)]
    # 3 棒: 2 枚重ね。頭を上の端に貼り、糸は裏に沿わせて下の端から出す。
    sl, s = p["stick_len"], p["stick_w"]
    stick = Part(3, "stick", "棒", [(0, 0), (sl, 0), (sl, 2 * s), (0, 2 * s)], label_xy=(2, 1), label="3",
                 valley=[((0, s), (sl, s))], art=[_panel(6, 0.3, sl - 0.3, s - 0.3, STICK), _panel(0.3, s + 0.3, sl - 0.3, 2 * s - 0.3, STICK)])
    # 4 こぶ: 三角の柱に折り、1 面を頭に貼る。舌がここに当たって口の開きが止まる。
    bump = Part(4, "bump", "こぶ", [(0, 0), (24, 0), (24, 8), (0, 8)], label_xy=(1, 1), label="4",
                valley=[((8, 0), (8, 8)), ((16, 0), (16, 8))], glue=[[(16, 0), (24, 0), (24, 8), (16, 8)]])
    return [head, jaw, stick, bump]


def parts(p):
    return _bow_parts(p) if p["kind"] == "bow" else _jaw_parts(p)


def place(by_key, page, top, gap):
    x0 = page.x0
    if "plank" in by_key:
        plank, torso, mortar, posts, stop = (by_key[k] for k in ("plank", "torso", "mortar", "posts", "stop"))
        plank.x, plank.y = x0, top
        torso.x, torso.y = x0 + plank.width + gap, top
        mortar.x, mortar.y = torso.x, top + torso.height + gap
        y = top + max(plank.height, torso.height + gap + mortar.height) + gap
        posts.x, posts.y = x0, y
        stop.x, stop.y = x0 + posts.width + gap, y
        y += max(posts.height, stop.height) + gap
        # 文字の列は部品の下に頁の幅いっぱいで置く（10cm の物差しが入る幅が要る）。
        return y, page.x1 - x0, x0
    stick, jaw, head, bump = (by_key[k] for k in ("stick", "jaw", "head", "bump"))
    stick.x, stick.y = x0, top
    jaw.x, jaw.y = x0 + stick.width + gap, top
    y = top + max(stick.height, jaw.height) + gap
    head.x, head.y = x0, y
    bump.x, bump.y = x0 + head.width + gap, y
    x = bump.x + bump.width + gap
    return y, page.x1 - x, x


def bom(p):
    paper = f"紙（厚さ 0.15mm 前後・{p['paper_gsm']}g/m² の見込み）"
    why = "家庭のプリンタで刷って作るため"
    if p["kind"] == "bow":
        rows = [
            {"number": 1, "key": "plank", "name": "台", "qty": 1, "material": paper, "substituted": True, "original_guess": "木の板（図の色と形による推定）", "reason": why},
            {"number": 2, "key": "posts", "name": "柱", "qty": 1, "material": paper, "substituted": True, "original_guess": "木（同じ）", "reason": why},
            {"number": 3, "key": "torso", "name": "体", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
            {"number": 4, "key": "stop", "name": "止めの柱", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図に無い。戻りを止める所として足した）", "reason": why},
            {"number": 5, "key": "mortar", "name": "臼", "qty": 1, "material": paper, "substituted": True, "original_guess": "木（図の色と形による推定）", "reason": why},
        ]
        axle_len = 2 * p["post_width"] + POST_GAP + 14
        thread = p["post_height"] + 150
    else:
        rows = [
            {"number": 1, "key": "head", "name": "頭", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子か木（不明）", "reason": why},
            {"number": 2, "key": "jaw", "name": "下顎", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
            {"number": 3, "key": "stick", "name": "棒", "qty": 1, "material": paper, "substituted": True, "original_guess": "竹か木の棒（図の色による推定）", "reason": why},
            {"number": 4, "key": "bump", "name": "こぶ", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図に無い。口の開きを止める所として足した）", "reason": why},
        ]
        axle_len = 10
        thread = p["stick_len"] + 80
    rows += [
        {"number": 7, "key": "axle", "name": "軸", "qty": 1, "material": f"竹串（長さ約 {axle_len}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明", "reason": "家にあり、穴に通しやすいため"},
        {"number": 8, "key": "weight", "name": "重り", "qty": 1, "material": f"油粘土 {p['weight_g']:g}g", "substituted": True, "original_guess": "不明", "reason": "量を変えて戻り方を試しやすいため"},
        {"number": 9, "key": "string", "name": "糸", "qty": 1, "material": f"木綿の糸（長さ約 {thread}mm）", "substituted": True, "original_guess": "糸（図に描かれている）", "reason": "家にあるため"},
    ]
    return rows


def materials(p):
    by = {r["key"]: r for r in bom(p)}
    return [f"{by['plank' if p['kind'] == 'bow' else 'head']['material']}を 1 枚", "のり、はさみ、定規", by["axle"]["material"], by["weight"]["material"], by["string"]["material"]]


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。穴は竹串の先であける"]
    if p["kind"] == "bow":
        out += ["1 台を破線で谷折りして 2 枚に貼り合わせる。穴は重ねたまま通す",
                "3 体を破線で谷折りして貼り合わせる。軸の穴と糸の穴は重ねたまま通す",
                f"2 柱を U の字に折り、糊代を台の上の面の小さい四角（糸の穴から {p['string_arm']}mm 後ろ）に貼る",
                "体を柱の間に入れ、竹串を柱の穴と体の軸の穴に通す",
                f"4 止めの柱の糊代を、台の後ろの細い四角（軸から {p['tail_len'] - CLAY_IN}mm 後ろ）に貼る",
                f"5 臼を丸めて筒にし、台の前の大きい四角（軸から {p['torso_len'] - 5}mm 前）に立てて貼る",
                "尾の端に粘土を付ける。体が水平で止めの柱に載るか見る",
                f"糸を体の糸の穴に結び、台の穴から下へ通す。引くと約 {pull_gf(p):.0f}gf（見込み）で礼をして臼に当たる"]
    else:
        out += ["3 棒を破線で谷折りして貼り合わせる",
                "1 頭の裏の下を 3 棒の上の端に貼る",
                "2 下顎を頭の口に重ね、短く切った竹串を両方の穴に通し、竹串の両端に粘土を少し付けて抜けないようにする",
                f"4 こぶを三角に折り、舌の上の端から {p['stop_gap']}mm 上の頭に貼る",
                "顎の先の裏に粘土を付ける。口が開いて舌がこぶに当たるか見る",
                f"糸を舌の穴に結び、棒の裏に沿わせて下の端から出す。引くと約 {pull_gf(p):.0f}gf（見込み）で口が閉じる"]
    return out


RESULTS = ("動いた", "動かない")


def measures(p):
    """動くかの二択でなく、動き方を言葉か絵で予想する（虎の雛形と同じ形）。粘土の量は戻り方を分ける量なので書かせる。"""
    return {"predict": "糸を引いて離すと、どう動くと思いますか（言葉か絵で）", "rows": [[("付けた粘土の量", 40)]]}


def diagram(x, y, w, h, p):
    """横から見た仕組みの図。軸・振れる部品・止め・糸の向きを線で描く。"""
    if p["kind"] == "bow":
        span = p["plank_length"]
        s = min(w / span, h / (p["post_height"] + p["torso_w"] + 6))
        base = y + h - 2
        px = x + (span - p["tail_len"] - 5) * s
        py = base - p["post_height"] * s
        shapes = [{"kind": "line", "x1": x, "y1": base, "x2": x + span * s, "y2": base},
                  {"kind": "line", "x1": px, "y1": base, "x2": px, "y2": py},
                  {"kind": "rect", "x": px - p["torso_len"] * s, "y": py - p["torso_w"] * s / 2, "w": (p["torso_len"] + p["tail_len"]) * s, "h": p["torso_w"] * s},
                  {"kind": "rect", "x": px - p["torso_len"] * s, "y": base - p["stop_height"] * s, "w": 10 * s, "h": p["stop_height"] * s},
                  {"kind": "line", "x1": px - p["string_arm"] * s, "y1": py, "x2": px - p["string_arm"] * s, "y2": base + 2, "dash": "1,0.6"}]
        return shapes
    s = min(w / (p["head_w"] + 4), h / (p["head_h"] + 20))
    px, py = x + jaw_pivot(p)[0] * s, y + jaw_pivot(p)[1] * s
    return [{"kind": "rect", "x": x, "y": y, "w": p["head_w"] * s, "h": p["head_h"] * s},
            {"kind": "line", "x1": px - p["jaw_len"] * s, "y1": py, "x2": px + p["tab_len"] * s, "y2": py},
            {"kind": "line", "x1": px + p["tab_len"] * s, "y1": py, "x2": px + p["tab_len"] * s, "y2": y + h, "dash": "1,0.6"}]
