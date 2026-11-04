"""雛形 twist_drum: 柄を指で回すと、鼓の左右に下げた玉が振れて面を打つ（でんでん太鼓・振り鼓）。

紙の部品は、面 2 枚・胴の帯（糊代の歯つき。丸めて胴にする）・柄の巻き紙。竹串・糸・玉は部品表に載せる。
面の絵は出典ごとに違うので、刷る形（face）で描き分ける。鳥の面（コマ 29）は図に幣（紙の房）が付くので、房の部品が 1 つ増える。
諫鼓（コマ 10、face=kanko）は柄の無い形で、台の上の柱に長い鼓を載せ、台の花車を回して玉を振る。仕組みは【解釈】（下の KANKO の注）。
寸法は手元の複写の図の比から出した見込みで、どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。

動きの見込み（F5.drum）の前提:
- 鼓の軸は横、柄（竹串）は胴を縦に貫く。糸は胴の帯の左右（柄から 90° の所）の帯の幅の真ん中に結ぶ。
- 柄を速く回すと、玉は結び目を中心に、結び目の高さの水平面をほぼ回ると見る（重力と糸のたるみは入れない）。
  その面で、玉が面（鼓の軸の向きに結び目から半分の奥行きの所）を打つ点が、面の中心から半径の半分の内に入る糸の長さを求める。
  玉は点でない。糸は玉の中心までの長さなので、玉の表が面に触れる時、中心は面より玉の半径だけ外にある
  （軸の向きの距離は 奥行きの半分＋玉の半径）。
  縁に近いと胴の帯が硬く、鳴りが鈍いと見込む（実物で確かめていない）。
- 玉が垂れた時に、胴の下に出た柄に届くと糸が柄に絡む。結び目から柄の一番近い点（胴の下の縁の柄）までは √2 × 半径。
  糸の長さ＋玉の半径がこれより短ければ（等しいと届くので落とす）絡まない（たるみ・玉の跳ね返りは入れない）。
"""
import math

from shapely.geometry import Polygon

from ..model import Failure, Part

ID = "twist_drum"
DEFAULTS = {
    "face": "kiku",
    # 面の半径と胴の奥行き。コマ 7 の図で、奥行きは面の直径の 3 割強に見える（斜めの図を目測）。
    "radius": 26, "depth": 18, "tab": 6, "seam_glue": 8,
    # 柄は竹串。太さ 3mm・長さ 180mm は家にある竹串の見込み。
    "stick_d": 3, "handle_length": 90, "wrap_glue": 3,
    "cord_length": 24, "bead_d": 8,
    # 0.15mm はふつうの厚めの紙の見込み。実物の紙を測ったら置き換える。
    "paper_thickness": 0.15,
    # 諫鼓（face=kanko）だけが使う寸法。鼓の形が違う（長い胴を横に寝かせる）ので、でんでん太鼓の寸法と名を分ける。
    # 比はコマ 10 の図の目測: 胴の長さは面の直径の 1.2 倍ほど、柱は面の半径ほど、花車は面の半径の半分ほど。
    "k_radius": 18, "k_length": 44, "k_cord": 9.5,
    "post_side": 8, "post_height": 20, "post_pos": 18,
    "base_length": 80, "base_width": 34, "base_height": 15,
    "wheel_r": 9, "peg_height": 38, "face_gap": 20,
}
RANGES = {
    # 半径の上限 28 は、胴の帯（円周＋糊代）が A4 の印字域の幅 190mm に 1 本で入るため。
    "radius": (15, 28), "depth": (8, 30), "tab": (3, 10), "seam_glue": (5, 12),
    "stick_d": (2, 5), "handle_length": (40, 130), "wrap_glue": (2, 6),
    "cord_length": (5, 60), "bead_d": (4, 14),
    "paper_thickness": (0.05, 0.5),
    "k_radius": (12, 24), "k_length": (20, 60), "k_cord": (3, 40),
    "post_side": (5, 14), "post_height": (8, 50), "post_pos": (5, 70),
    "base_length": (50, 100), "base_width": (24, 50), "base_height": (8, 25),
    "wheel_r": (8, 16), "peg_height": (10, 80), "face_gap": (8, 50),
}
FACES = ("kiku", "tori", "kanko")
# 刷る形を決める寸法（面の絵と、幣の房があるか）。どの面が「正しい」かは無いので、寸法を直に渡す入口では必ず書かせる。
FORM = "face"
FORMS = FACES
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000007-R-twist_drum"
# 刷る形ごとの出典。面の絵はコマごとに違うので、形と合わない出典の印を刷らない（compose が F1.source で落とす）。
SOURCES = {"kiku": SOURCE, "tori": "NDL-1187053-R0000029-L-twist_drum", "kanko": "NDL-1187053-R0000010-R-twist_drum"}
HOLE_MARGIN = 3  # 穴から紙の端（帯の縁・継ぎ目の糊代）までの見込み。これより狭いと串を回した時に裂けやすい
SKEWER_LEN = 180  # 家にある竹串の長さの見込み（実物を測ったら置き換える）
TOP_OUT = 5  # 柄の先を胴の上へ出す長さ。抜け止めに糸を巻くため（幣の房の無い形）


def stick_cut(p):
    """柄の竹串を切る長さ ＝ 胴の下の柄 ＋ 胴の直径 ＋ 胴の上へ出す長さ。部品表と組み方の文はこの 1 つの式から書く。
    切らずに 180mm のまま通すと、上を決めた分だけ下が余り、柄の巻き紙（柄より 2mm 短い）と合わなかった。"""
    return p["handle_length"] + 2 * p["radius"] + top_out(p)


def top_out(p):
    """竹串を胴の上へ出す長さ。鳥の面は幣の房の上の帯（STREAMER_TOP）をこの出た所に巻いて貼るので、帯の幅＋2mm 出す。
    5mm のままだと 8mm の帯を巻く所が無く、組めなかった。"""
    return STREAMER_TOP + 2 if p["face"] == "tori" else TOP_OUT
TAB_PITCH = 8  # 糊代の歯の目安の幅。細かいほど丸く貼れるが、切るのが手間になる
STRIKE_ZONE = 0.5  # 打つ点が面の中心から半径のこの割合の内に入れば、鳴ると見込む（縁は鳴りが鈍い）
FACE, INK, BAND, BAND_DARK, BAMBOO, CORD_MARK, PAPER = "#ddd0aa", "#3b3a34", "#9a5a35", "#6e4128", "#cdb98a", "#e8dfc6", "#ece6d6"
TITLES = {"kiku": "菊の面", "tori": "鳥の面と幣", "kanko": "諫鼓と花車【解釈】"}


def title(p):
    return TITLES[p["face"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "face": FACES}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "face":
            if v not in FACES:
                out.append(Failure("F5.range", k, f"{v} は {FACES} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


def drum_rd(p):
    """鼓の面の半径と胴の奥行き（帯の幅）。諫鼓は長い胴なので別の寸法の名から取る。"""
    if p["face"] == "kanko":
        return p["k_radius"], p["k_length"]
    return p["radius"], p["depth"]


def circumference(p):
    """胴の帯の長さ（糊代を除く）。面は内へ折った歯に外から貼り、面の縁と帯の外の面をそろえる見込み。
    帯の厚みの真ん中は面の縁から紙の厚みの半分だけ内にあるので、半径から厚みの半分を引いた円周にする。"""
    return 2 * math.pi * (drum_rd(p)[0] - p["paper_thickness"] / 2)


def band_length(p):
    """胴の帯の全長 ＝ 円周 ＋ 継ぎ目の糊代。帯を切り出す長さはこの 1 つの式から出す（型紙と試験が同じ値を使う）。"""
    return circumference(p) + p["seam_glue"]


def tab_teeth(p):
    """糊代の歯の数・間隔・肩の削り。歯を内へ折ると先は半径 (R − tab) の円に乗り、長さが (R − tab)/R に縮む。
    隣の歯と重ならないよう、先の幅を同じ割合に詰め、さらに両肩を 0.3mm ずつ空ける。"""
    n = max(1, round(circumference(p) / TAB_PITCH))
    pitch = circumference(p) / n
    inset = pitch * p["tab"] / (2 * drum_rd(p)[0]) + 0.3
    return n, pitch, inset


def stick_hole_r(p):
    return p["stick_d"] / 2 + 0.1  # 串が回らずに締まるよう、穴は串よりわずかに大きいだけにする


def hole_positions(p):
    """帯の上の穴の位置（継ぎ目から測った長さ）。柄の穴は向かい合う 2 つ、糸の穴はそこから 90° の 2 つ。
    継ぎ目の糊代（帯の頭の 0〜seam_glue）に穴が来ないよう、円周の 1/8 ずらして置く。"""
    c = circumference(p)
    return {"stick": (c / 8, 5 * c / 8), "cord": (3 * c / 8, 7 * c / 8)}


def cord_window(p):
    """糸の長さ（結び目から玉の中心まで）の下限と上限。前提は module の docstring。

    a = D/2 + 玉の半径（結び目から、面に触れた玉の中心までの軸の向きの距離）とする。
    下限: 打つ点 x = R − √(L² − a²) が面の中心から STRIKE_ZONE·R の内 → L ≧ √(((1 − k)R)² + a²)。
    上限: 反対側へ行き過ぎない L ≦ √(((1 + k)R)² + a²) と、柄に絡まない L + 玉の半径 < √2·R の小さい方。
    返す上限は 2 つの小さい方の値。柄の側は等号も落とす（check の側で厳密に見る）。
    """
    R, a, k = p["radius"], axial(p), STRIKE_ZONE
    low = math.hypot((1 - k) * R, a)
    high = min(far_limit(p), tangle_limit(p))
    return low, high


def axial(p):
    """結び目から、面に触れた玉の中心までの軸の向きの距離。玉の中心は面の外へ玉の半径だけ出る。"""
    return p["depth"] / 2 + p["bead_d"] / 2


def far_limit(p):
    """面の中心を越えて、反対の縁の近くを打つ手前の糸の長さ（この長さまでは通す）。"""
    return math.hypot((1 + STRIKE_ZONE) * p["radius"], axial(p))


def tangle_limit(p):
    """垂れた玉が柄に届く糸の長さ（この長さちょうどでも届くので、これより短い糸だけ通す）。"""
    return math.sqrt(2) * p["radius"] - p["bead_d"] / 2


def strike_offset(p):
    """玉が面を打つ点の、面の中心からの距離（正は結び目の側）。糸が axial に届かなければ None（面に届かない）。"""
    h = axial(p)
    if p["cord_length"] <= h:
        return None
    return p["radius"] - math.sqrt(p["cord_length"] ** 2 - h * h)


def check_physics(p):
    if p["face"] == "kanko":
        return check_kanko(p)
    return _check_hand(p)


def _check_hand(p):
    """F5.drum: 玉が面を打つ・柄に絡まない・串の穴が裂けない・帯の歯が貼れる・竹串が足りる、を見る。"""
    out = []
    low, high = cord_window(p)
    L = p["cord_length"]
    if L < low:
        x = strike_offset(p)
        where = "面に届かない" if x is None else f"面の中心から {x:.1f}mm の縁の近くを打つ"
        out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は短く、{where}（{low:.1f}mm 以上）"))
    if L >= tangle_limit(p):
        out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は長く、垂れた玉が柄に届いて絡む（{tangle_limit(p):.1f}mm より短く）"))
    elif L > far_limit(p):
        out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は長く、玉が面の中心を越えて反対の縁の近くを打つ（{far_limit(p):.1f}mm まで）"))
    r = stick_hole_r(p)
    edge = p["depth"] / 2 - r
    if edge < HOLE_MARGIN:
        out.append(Failure("F5.drum", "柄の穴", f"柄の穴から帯の縁まで {edge:.1f}mm で、回すと裂けやすい（{HOLE_MARGIN}mm 以上）"))
    seam = hole_positions(p)["stick"][0] - r - p["seam_glue"]
    if seam < HOLE_MARGIN:
        out.append(Failure("F5.drum", "柄の穴", f"柄の穴から継ぎ目の糊代まで {seam:.1f}mm で、継ぎ目が剥がれやすい（{HOLE_MARGIN}mm 以上）"))
    _, pitch, inset = tab_teeth(p)
    if pitch - 2 * inset < 1:
        out.append(Failure("F5.drum", "糊代の歯", f"歯の先が {pitch - 2 * inset:.1f}mm で、面を貼る所が無い（歯が深すぎる）"))
    need = stick_cut(p)
    if need > SKEWER_LEN:
        out.append(Failure("F5.drum", "柄", f"柄に竹串が {need:.0f}mm 要り、{SKEWER_LEN}mm の竹串で足りない"))
    return out


def _circle(cx, cy, r, n=72, a0=0.0):
    return [(cx + r * math.cos(a0 + 2 * math.pi * i / n), cy + r * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]


def _ring(cx, cy, r, sw):
    """細い輪は閉じた線で描く（絵の面は穴の無い多角形だけなので、輪を面にすると形が壊れる）。"""
    pts = _circle(cx, cy, r)
    return {"kind": "line", "pts": pts + [pts[0]], "stroke": INK, "sw": sw}


def _petal(cx, cy, r0, r1, a, w):
    """菊の花弁 1 枚。根元 r0 から先 r1 へ、幅 w の細い葉形。コマ 7 の図の 16 弁の形を手で取った。"""
    ca, sa = math.cos(a), math.sin(a)
    rm = r0 + (r1 - r0) * 0.7
    pts = [(r0, 0), (rm, w / 2), (r1, w * 0.18), (r1 + w * 0.15, 0), (r1, -w * 0.18), (rm, -w / 2)]
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]


# コマ 29 の鳥。面の図を 800 四方に拡大し、面の中心 (395, 385)・半径 295 の座標で手で取った点。画素は使っていない。
_BIRD = [(165, 365), (205, 325), (230, 290), (280, 275), (330, 290), (352, 300), (350, 240), (380, 200), (440, 178), (530, 170), (505, 195), (520, 212),
         (470, 228), (440, 290), (500, 298), (560, 265), (612, 245), (615, 275), (648, 285), (655, 322), (600, 332), (532, 362), (515, 405), (548, 462),
         (528, 478), (505, 452), (495, 495), (480, 545), (462, 568), (452, 520), (420, 560), (350, 612), (380, 565), (300, 562), (250, 532), (225, 482),
         (248, 445), (300, 420), (322, 405), (268, 392), (232, 362), (205, 385), (192, 378)]
_BIRD_EYE = (232, 318, 14)


def _bird(cx, cy, s):
    return [(cx + (x - 395) * s, cy + (y - 385) * s) for x, y in _BIRD]


def _face_art(p):
    R = drum_rd(p)[0]
    art = [{"kind": "poly", "pts": _circle(R, R, R - 0.3), "fill": FACE}]
    if p["face"] == "kanko":
        art += _tomoe_art(R)
    elif p["face"] == "kiku":
        # コマ 7: 面の中に 2 重の輪（半径の 0.66・0.60）、その内に 16 弁の菊と小さな芯。
        art += [_ring(R, R, 0.66 * R, 0.025 * R), _ring(R, R, 0.60 * R, 0.025 * R)]
        for i in range(16):
            art.append({"kind": "poly", "pts": _petal(R, R, 0.09 * R, 0.46 * R, 2 * math.pi * i / 16 - math.pi / 2, 0.11 * R), "fill": INK})
        art.append({"kind": "poly", "pts": _circle(R, R, 0.06 * R, 24), "fill": INK})
    else:
        # コマ 29: 面いっぱいの鳥。図では面の輪の内の半径 295 に描かれているので、面の半径の 0.9 に縮める。
        s = 0.9 * R / 295
        art.append({"kind": "poly", "pts": _bird(R, R, s), "fill": INK})
        ex, ey, er = _BIRD_EYE
        art.append({"kind": "poly", "pts": _circle(R + (ex - 395) * s, R + (ey - 385) * s, er * s, 16), "fill": FACE})
    return art


def _disc(number, key, name, p):
    R = drum_rd(p)[0]
    return Part(number, key, name, _circle(R, R, R), label_xy=(R - 1.5, 2 * R - 5), label=str(number), art=_face_art(p))


def _band(p):
    C, g, t, D = circumference(p), p["seam_glue"], p["tab"], drum_rd(p)[1]
    n, pitch, inset = tab_teeth(p)
    top, bot, H = t, t + D, D + 2 * t
    pts = [(0, top)]
    teeth = []
    for i in range(n):
        a, b = i * pitch, (i + 1) * pitch
        pts += [(a + inset, 0), (b - inset, 0), (b, top)]
        teeth.append([(a, top), (a + inset, 0), (b - inset, 0), (b, top)])
    pts += [(C + g, top), (C + g, bot), (C, bot)]
    for i in reversed(range(n)):
        a, b = i * pitch, (i + 1) * pitch
        pts += [(b - inset, H), (a + inset, H), (a, bot)]
        teeth.append([(b, bot), (b - inset, H), (a + inset, H), (a, bot)])
    band = Part(3, "band", "胴の帯", pts, label_xy=(2, top + 1.5), label="3 胴")
    band.valley = [((0, top), (C, top)), ((0, bot), (C, bot))]
    # 継ぎ目の糊代は帯の終わりに置き、帯の頭の下に入れて貼る（頭の側の絵が外に見える）。
    band.glue = teeth + [[(C, top), (C + g, top), (C + g, bot), (C, bot)]]
    band.art = [{"kind": "poly", "pts": [(0.2, top + 0.2), (C - 0.2, top + 0.2), (C - 0.2, bot - 0.2), (0.2, bot - 0.2)], "fill": KANKO_BODY if p["face"] == "kanko" else BAND}]
    # 帯の上下の縁の濃い筋（コマ 7 の胴の縁の影）。
    for y0 in (top + 0.2, bot - 1.4):
        band.art.append({"kind": "poly", "pts": [(0.2, y0), (C - 0.2, y0), (C - 0.2, y0 + 1.2), (0.2, y0 + 1.2)], "fill": BAND_DARK})
    mid = top + D / 2
    if p["face"] == "kanko":
        # 諫鼓は柄を通さず、柱の頭を帯の四角い穴に差す。穴は継ぎ目の向かい（円周の半分）に置き、糊代から一番遠くする。
        cs = p["post_side"] + POST_FIT
        band.cuts = [(C / 2 - cs / 2, mid - cs / 2, cs, cs)]
        return band
    pos = hole_positions(p)
    # コマ 7 の胴の白い菱形（糸の留め）を、糸の穴のまわりに描く。
    for s in pos["cord"]:
        d = min(3.0, D / 2 - 1.6)
        band.art.append({"kind": "poly", "pts": [(s, mid - d), (s + d, mid), (s, mid + d), (s - d, mid)], "fill": CORD_MARK})
    band.holes = [(s, mid, stick_hole_r(p)) for s in pos["stick"]] + [(s, mid, 0.6) for s in pos["cord"]]
    return band


def wrap_size(p):
    """柄の巻き紙の幅と長さ。幅は串の周りを紙の厚みの真ん中で 1 周＋糊代、長さは胴の下の柄から 2mm 短く（胴に当てない）。"""
    return math.pi * (p["stick_d"] + p["paper_thickness"]) + p["wrap_glue"], p["handle_length"] - 2


def _wrap(p):
    w, L = wrap_size(p)
    g = p["wrap_glue"]
    part = Part(4, "wrap", "柄の巻き紙", [(0, 0), (w, 0), (w, L), (0, L)], label_xy=(0.6, 1.5), label="4")
    part.glue = [[(w - g, 0), (w, 0), (w, L), (w - g, L)]]
    part.art = [{"kind": "poly", "pts": [(0.2, 0.2), (w - g - 0.2, 0.2), (w - g - 0.2, L - 0.2), (0.2, L - 0.2)], "fill": BAMBOO}]
    return part


# 幣の房（コマ 29）。上の帯を柄の先に巻いて貼り、下の 3 本の房を垂らす。房の幅と長さは図の比の目測。
STREAMER_TEETH, STREAMER_W, STREAMER_GAP, STREAMER_TOP, STREAMER_LEN = 3, 5, 2.5, 8, 50


def _streamer():
    W = STREAMER_TEETH * STREAMER_W + (STREAMER_TEETH - 1) * STREAMER_GAP
    pts = [(0, 0), (W, 0)]
    # 右の房から左へ、房の外形と房の間の切り込みを順に回る。
    for i in reversed(range(STREAMER_TEETH)):
        a = i * (STREAMER_W + STREAMER_GAP)
        pts += [(a + STREAMER_W, STREAMER_TOP + STREAMER_LEN), (a, STREAMER_TOP + STREAMER_LEN)]
        if i:
            pts += [(a, STREAMER_TOP), (a - STREAMER_GAP, STREAMER_TOP)]
    part = Part(5, "streamer", "幣の房", pts, label_xy=(0.6, STREAMER_TOP + 1.5), label="5")
    part.glue = [[(0, 0), (W, 0), (W, STREAMER_TOP), (0, STREAMER_TOP)]]
    part.art = [{"kind": "poly", "pts": [(a + 0.2, STREAMER_TOP + 0.2), (a + STREAMER_W - 0.2, STREAMER_TOP + 0.2),
                                         (a + STREAMER_W - 0.2, STREAMER_TOP + STREAMER_LEN - 0.2), (a + 0.2, STREAMER_TOP + STREAMER_LEN - 0.2)], "fill": PAPER}
                for a in (i * (STREAMER_W + STREAMER_GAP) for i in range(STREAMER_TEETH))]
    return part


def parts(p):
    if p["face"] == "kanko":
        return [_disc(1, "front", "表の面", p), _disc(2, "back", "裏の面", p), _band(p), _post(p), _base(p), _wheel(p), _rodtab(p), _gauge(p)]
    out = [_disc(1, "front", "表の面", p), _disc(2, "back", "裏の面", p), _band(p), _wrap(p)]
    if p["face"] == "tori":
        out.append(_streamer())
    return out


def place(by_key, page, top, gap):
    """1 段目に胴の帯（長い）、2 段目の左に面 2 枚を縦に、その右に巻き紙と房。
    説明の列は房の右から。物差し（100mm）が印字域に入るよう、列の左は 100mm より左に来るように並べる。"""
    band = by_key["band"]
    band.x, band.y = page.x0, top
    y = top + band.height + gap
    if "base" in by_key:
        return _place_kanko(by_key, page, y, gap)
    front, back, wrap = by_key["front"], by_key["back"], by_key["wrap"]
    front.x, front.y = page.x0, y
    back.x, back.y = page.x0, y + front.height + gap
    x = page.x0 + front.width + gap
    wrap.x, wrap.y = x, y
    right = x + wrap.width
    if "streamer" in by_key:
        st = by_key["streamer"]
        st.x, st.y = x, y + wrap.height + gap
        right = max(right, x + st.width)
    x = right + gap
    return y, page.x1 - x, x


def bom(p):
    if p["face"] == "kanko":
        return bom_kanko(p)
    paper = f"紙（厚さ {p['paper_thickness']}mm 前後）"
    why = "家庭のプリンタで刷って作るため"
    cord = p["cord_length"] + 15  # 結び目 2 つ分の余り
    rows = [
        {"number": 1, "key": "front", "name": "表の面", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（紙張りか革張りかは図から分からない）", "reason": why},
        {"number": 2, "key": "back", "name": "裏の面", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（同じ）", "reason": why},
        {"number": 3, "key": "band", "name": "胴の帯", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図では塗った胴）", "reason": why},
        {"number": 4, "key": "wrap", "name": "柄の巻き紙", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": "竹串の柄を持ちやすく、図の柄の色に近づけるため"},
        {"number": 7, "key": "stick", "name": "柄", "qty": 1, "material": f"竹串（太さ {p['stick_d']:g}mm・{SKEWER_LEN}mm の物を {stick_cut(p):g}mm に切る）", "substituted": True, "original_guess": "竹か木（図の柄の形からの推定）", "reason": "家にあり、胴に通しやすいため"},
        {"number": 8, "key": "cord", "name": "糸", "qty": 2, "material": f"木綿の糸（1 本 {cord:g}mm に切る）", "substituted": True, "original_guess": "糸か紐（図の線による）", "reason": "家にあるため"},
        {"number": 9, "key": "bead", "name": "玉", "qty": 2, "material": f"油粘土の玉（直径 {p['bead_d']:g}mm）かビーズ", "substituted": True, "original_guess": "不明", "reason": "大きさを変えて試しやすいため"},
    ]
    if p["face"] == "tori":
        rows.insert(4, {"number": 5, "key": "streamer", "name": "幣の房", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙（図の形からの推定）", "reason": why})
    return rows


def materials(p):
    # 行の位置でなく key で引く。形によって部品表の行が増えるので、位置で引くと別の行を刷る。
    by = {r["key"]: r for r in bom(p)}
    if p["face"] == "kanko":
        return [f"{by['band']['material']}を 1 枚", "のり、はさみ、定規", by["peg"]["material"], by["rod"]["material"],
                f"{by['cord']['material']}と{by['pull']['material']}", by["bead"]["material"]]
    return [f"{by['band']['material']}を 1 枚", "のり、はさみ、定規", by["stick"]["material"], f"{by['cord']['material']}を 2 本", f"{by['bead']['material']}を 2 つ"]


def steps(p):
    if p["face"] == "kanko":
        return steps_kanko(p)
    pos = hole_positions(p)
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。3 胴の帯の歯の間も切り込む。帯の穴は竹串の先であける",
           "3 胴の帯を丸め、終わりの糊代を頭の下に入れて貼る（絵が外）", "上下の歯を破線で内へ谷折りする",
           "1 表の面と 2 裏の面を、歯に外から貼る",
           f"竹串を {stick_cut(p):g}mm に切る（胴の下の柄 {p['handle_length']:g}mm・胴 {2 * p['radius']:g}mm・胴の上 {top_out(p):g}mm）",
           f"竹串を太い 2 つの穴（帯の頭から {pos['stick'][0]:.0f}mm と {pos['stick'][1]:.0f}mm）に通し、上へ {top_out(p):g}mm 出す。穴の所を糊で留める",
           f"糸の端に玉を付け、玉の中心から {p['cord_length']:g}mm の所で、菱形の小さい穴に結ぶ（左右 2 本）",
           "4 柄の巻き紙を胴の下の竹串に巻いて貼る"]
    if p["face"] == "tori":
        out.append("5 幣の房の上の帯を、胴の上に出た竹串に巻いて貼る")
    out.append("柄を両手で挟んで左右に回し、玉が面に当たるか見る")
    return out


RESULTS = ("鳴った", "鳴らない")


def measures(p):
    """鳴るかの二択でなく、回し方と玉の動きを言葉か絵で予想する（ほかの雛形と同じ形）。回し方は数でないので欄に残す。"""
    if p["face"] == "kanko":
        return {"predict": "棒をどう引くと、花車と玉はどう動くと思いますか（言葉か絵で）", "rows": [[("引き方（速さ・長さ）", 40)]]}
    return {"predict": "柄をどう回すと、玉はどう動くと思いますか（言葉か絵で）", "rows": [[("回し方（速さ・向き）", 40)]]}


def diagram(x, y, w, h, p):
    """組み上がりを正面から見た絵。寸法の図ではなく、面・柄・糸と玉の並びを見せるだけ。"""
    if p["face"] == "kanko":
        return _diagram_kanko(x, y, w, h, p)
    R, L = p["radius"], p["cord_length"]
    up = top_out(p)
    s = min(w / (2 * R + 2 * L + p["bead_d"]), h / (2 * R + p["handle_length"] + up))
    cx, cy = x + w / 2, y + (up + R) * s
    shapes = [{"kind": "poly", "pts": _circle(cx, cy, R * s, 48), "fill": "none", "sw": 0.25}]
    shapes.append({"kind": "line", "x1": cx, "y1": cy - (R + up) * s, "x2": cx, "y2": cy - R * s})
    shapes.append({"kind": "line", "x1": cx, "y1": cy + R * s, "x2": cx, "y2": cy + (R + p["handle_length"]) * s})
    br = p["bead_d"] / 2 * s
    for side in (-1, 1):
        ax = cx + side * R * s
        bx = ax + side * L * s  # 回して振れた時の玉。糸はほぼ水平に張る
        shapes.append({"kind": "line", "x1": ax, "y1": cy, "x2": bx, "y2": cy, "dash": "1,0.6"})
        shapes.append({"kind": "rect", "x": bx - br, "y": cy - br, "w": 2 * br, "h": 2 * br})
    return shapes


# ---- 諫鼓（コマ 10 右、face=kanko）----
# 図に見える物: 横に寝かせた長い鼓（面に三つ巴）、鼓を支える 1 本の柱、平たい台、台に立つ軸の上の花車（花弁 10 枚・先に糸と玉）、
# 台の端から差し込んだ 2 本並びの竹の棒（途中に切り欠き）。
# 【解釈】図に動かし方の説明は無い。この雛形では、棒を引くと台の中で軸に巻いた糸がほどけて軸が回り（独楽の紐と同じ）、
# 花車の先の玉が振れて、花車の側を向いた鼓の面を打つ、と読む。棒の切り欠きは糸を掛ける所と読む。どちらも図からの推定で、確かめていない。
# 鼓の軸の向き（面が花車を向く）も【解釈】。図では鼓が斜め奥を向き、花車は面の手前の下にある。
KANKO_BODY, WOOD, WOOD_DARK, PETAL = "#d8c58c", "#d6c38e", "#b49d62", "#e2cf95"
POST_FIT = 0.4  # 柱の頭を差す帯の四角い穴の遊び。きついと帯が裂け、緩いと鼓が回る
POST_INSERT, POST_TAB, POST_GLUE = 5, 5, 5  # 柱の頭を胴に差す長さ・足の糊代・継ぎ目の糊代
BASE_TAB = 6  # 台の角の糊代の幅（壁の高さより狭くする）
WHEEL_PETALS = 10  # 図の花車の花弁の数
PEG_TOP = 3  # 花車の軸の竹串を、花車の上へ出す長さ
ROD_NORTH_OUT = 10  # 引く棒を押し込んだ時に、北の壁から出しておく長さ（抜けないように）
ROD_GRIP = 40  # 引く棒の、南の壁から出して手で持つ長さ
TAB_W, TAB_FLAG = 5, 7  # 棒の留め具の帯の幅と、糸を結ぶ旗の長さ


def wheel_anchor(p):
    """花車で玉の糸を結ぶ穴の、軸からの距離。花弁の先から 1.5mm 内に穴をあける（先に寄せると裂ける）。"""
    return p["wheel_r"] - 1.5


def peg_cut(p):
    """花車の軸の竹串の長さ。下の端を床に着けて台の穴に立てるので、台の高さ＋花車の高さ（台の上の面から）＋上へ出す分。"""
    return p["base_height"] + p["peg_height"] + PEG_TOP


def rodtab_pos(p):
    """棒の留め具（巻く糸を結ぶ所）の、棒の北の端からの長さ。棒を押し込んだ時に留め具が軸の真横に来る所にする。
    図の棒の切り欠きの代わり【解釈】。位置を寸法から決めて刷るので、結ぶ所が作る人ごとにずれない。"""
    return ROD_NORTH_OUT + peg_pos(p)


def pull_travel(p):
    """棒を南へ引ける長さ。留め具が南の壁（の内側の余白 HOLE_MARGIN）に当たるまで。"""
    return p["base_length"] - peg_pos(p) - HOLE_MARGIN


def pull_turns(p):
    """引き切った時に軸が回る数。糸は竹串の太さの周りから解ける（糸の太さは入れない）。"""
    return pull_travel(p) / (math.pi * p["stick_d"])


def rod_perimeter(p):
    """竹串 2 本を縦に重ねて束ねた棒の周りの長さ（半円 2 つ＋まっすぐな所 2 つ）。"""
    return math.pi * p["stick_d"] + 2 * p["stick_d"]


def peg_pos(p):
    """台の北の端から軸（花車）までの長さ。柱の真上に鼓の真ん中を置き、鼓の前の面から face_gap 先に軸を立てる。"""
    return p["post_pos"] + p["k_length"] / 2 + p["face_gap"]


def rod_off(p):
    """棒の通り道を軸の線から横へずらす量。糸が軸に接して巻き取られるよう、棒の 2 本の幅の半分と軸の半径と 1mm をあける。"""
    return p["stick_d"] * 1.5 + 1


def rod_cut(p):
    """台の端の壁にあける棒の穴（幅・高さ）。竹串 2 本を縦に重ねて通す。"""
    return p["stick_d"] + 1, 2 * p["stick_d"] + 1


def kanko_window(p):
    """諫鼓の糸の長さ（花車の穴から玉の中心まで）の下限と上限。

    前提: 花車を速く回すと、玉は軸を中心に半径 ρ = 穴の距離 + 糸 の水平な円を、花車の高さで回る（重力・たるみは入れない）。
    面は軸から face_gap 先の縦の面で、玉の表が面に触れる時、玉の中心は面から玉の半径だけ手前（g = face_gap − 玉の半径）。
    打つ点の面の中心からのずれは、横 √(ρ² − g²) と縦 dz（花車の高さ − 鼓の中心の高さ）を合わせた長さ。
    でんでん太鼓と同じく、これが STRIKE_ZONE·R の内なら鳴ると見込む。
    下限: ρ ≧ g（面に届く）。上限: ρ² ≦ g² + (kR)² − dz²。dz が kR を越えると窓が無い（上限は None）。
    """
    R, k = p["k_radius"], STRIKE_ZONE
    g = p["face_gap"] - p["bead_d"] / 2
    dz = p["peg_height"] - (p["post_height"] + R)
    a = wheel_anchor(p)
    low = g - a
    room = g * g + (k * R) ** 2 - dz * dz
    high = math.sqrt(room) - a if room > g * g else None
    return low, high, dz


def check_kanko(p):
    """F5.drum（諫鼓）: 玉が面を打つ・花車が面に当たらない・柱の穴と台の穴が裂けない・柱と軸が台に載る、を見る。"""
    out = []
    low, high, dz = kanko_window(p)
    L, kR = p["k_cord"], STRIKE_ZONE * p["k_radius"]
    if high is None:
        out.append(Failure("F5.drum", "花車", f"花車の高さが鼓の中心から {dz:+.1f}mm ずれ、玉が面の真ん中（±{kR:.1f}mm）を通らない"))
    else:
        if L < low:
            out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は短く、玉が面に届かない（{low:.1f}mm 以上）"))
        if L > high:
            out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は長く、面の縁の近くを打つ（{high:.1f}mm まで）"))
    if p["wheel_r"] > p["face_gap"] - 2:
        out.append(Failure("F5.drum", "花車", f"花車の半径 {p['wheel_r']:g}mm が面までの {p['face_gap']:g}mm に近く、回すと面に当たる"))
    edge = (p["k_length"] - p["post_side"] - POST_FIT) / 2
    if edge < HOLE_MARGIN:
        out.append(Failure("F5.drum", "柱の穴", f"柱の穴から帯の縁まで {edge:.1f}mm で、裂けやすい（{HOLE_MARGIN}mm 以上）"))
    if p["post_pos"] - p["post_side"] / 2 < HOLE_MARGIN or p["post_side"] > p["base_width"] - 2 * HOLE_MARGIN:
        out.append(Failure("F5.drum", "柱", "柱の足が台の上に収まらない"))
    if peg_pos(p) > p["base_length"] - HOLE_MARGIN:
        out.append(Failure("F5.drum", "軸", f"花車の軸が台の端から {peg_pos(p):.0f}mm で、台（{p['base_length']:g}mm）の上に立たない"))
    cw, ch = rod_cut(p)
    if (p["base_height"] - ch) / 2 < HOLE_MARGIN:
        out.append(Failure("F5.drum", "棒の穴", f"台の壁 {p['base_height']:g}mm に棒の穴（高さ {ch:g}mm）の上下の余白が {HOLE_MARGIN}mm 取れない"))
    if p["base_width"] / 2 + rod_off(p) + cw / 2 > p["base_width"] - HOLE_MARGIN:
        out.append(Failure("F5.drum", "棒の穴", "棒の穴が台の壁の端に近すぎる"))
    _, pitch, inset = tab_teeth(p)
    if pitch - 2 * inset < 1:
        out.append(Failure("F5.drum", "糊代の歯", f"歯の先が {pitch - 2 * inset:.1f}mm で、面を貼る所が無い（歯が深すぎる）"))
    # 結ぶ所（留め具）を決めたので、引ける長さで軸が回る数も数えられる。1 回も回らないと玉が振れない。
    if pull_turns(p) < 1:
        out.append(Failure("F5.drum", "棒", f"棒を引ける長さ {pull_travel(p):.0f}mm では、軸が 1 回も回らない（{pull_turns(p):.1f} 回）"))
    return out


TOMOE_SWEEP = 110  # 巴の尾が外の円に沿う角度。3 つで 1 周を越えると尾が隣の頭に重なり、輪に見えるので 1/3 周より短くする


def _tomoe_art(R):
    """三つ巴。頭の丸と、外の円に沿って細くなる尾を 1 つの面にする。コマ 10 の面の巴の大きさ（面の半径の 0.75 の円の内）を目測した。"""
    ro, rh = 0.66 * R, 0.21 * R
    out = []
    for i in range(3):
        f0 = math.pi / 2 + 2 * math.pi * i / 3
        pts = []
        n = 24
        for j in range(n + 1):  # 外の縁: 頭から尾の先へ、外の円に沿って TOMOE_SWEEP° 戻る
            a = f0 - math.radians(TOMOE_SWEEP) * j / n
            pts.append((R + ro * math.cos(a), R + ro * math.sin(a)))
        for j in range(n, -1, -1):  # 内の縁: 尾の先から頭へ、半径を頭の幅だけ詰めていく
            a = f0 - math.radians(TOMOE_SWEEP) * j / n
            r = ro - 2 * rh * (1 - j / n) ** 2  # 2 乗で細らせ、尾を頭の近くで急に細くする（図の巴の尾は細い）
            pts.append((R + r * math.cos(a), R + r * math.sin(a)))
        hc = ro - rh
        for j in range(1, n):  # 頭の丸: 内の点（中心から見て内向き）から、進む向きの側を回って外の点へ
            a = math.pi - math.pi * j / n
            pts.append((R + hc * math.cos(f0) + rh * math.cos(f0 + a), R + hc * math.sin(f0) + rh * math.sin(f0 + a)))
        poly = Polygon(pts).buffer(0)
        if poly.geom_type == "MultiPolygon":
            poly = max(poly.geoms, key=lambda g: g.area)
        out.append({"kind": "poly", "pts": list(poly.exterior.coords)[:-1], "fill": INK})
    return out


def _post(p):
    """柱は四角い筒。面 4 つ＋継ぎ目の糊代、下に外へ折る足の糊代。上の POST_INSERT は胴の穴に差す分。"""
    s, L = p["post_side"], p["post_height"] + POST_INSERT
    W = 4 * s
    pts = [(0, 0), (W + POST_GLUE, 0), (W + POST_GLUE, L), (W, L)]
    tabs = []
    for i in reversed(range(4)):
        a, b = i * s, (i + 1) * s
        pts += [(b - 0.5, L + POST_TAB), (a + 0.5, L + POST_TAB), (a, L)]
        tabs.append([(a, L), (b, L), (b - 0.5, L + POST_TAB), (a + 0.5, L + POST_TAB)])
    part = Part(10, "post", "柱", pts, label_xy=(0.8, 1.5), label="10")
    part.valley = [((i * s, 0), (i * s, L)) for i in range(1, 5)] + [((0, L), (W, L))]
    part.glue = tabs + [[(W, 0), (W + POST_GLUE, 0), (W + POST_GLUE, L), (W, L)]]
    part.art = [{"kind": "poly", "pts": [(i * s + 0.2, POST_INSERT + 0.2), ((i + 1) * s - 0.2, POST_INSERT + 0.2), ((i + 1) * s - 0.2, L - 0.2), (i * s + 0.2, L - 0.2)],
                 "fill": WOOD if i % 2 == 0 else WOOD_DARK} for i in range(4)]
    return part


def _base(p):
    """台は底の無い箱（上の面と 4 つの壁）。北と南の壁の端に角の糊代。長さの向きは紙の縦（北が上）。
    北と南の壁に棒の穴、上の面に花車の軸の穴、柱の足を貼る所の印。"""
    W, L, H = p["base_width"], p["base_length"], p["base_height"]
    g = min(BASE_TAB, H - 1)
    pts = [(H, 0), (H + W, 0), (H + W + g, 1.5), (H + W + g, H - 0.5), (H + W, H), (2 * H + W, H), (2 * H + W, H + L), (H + W, H + L),
           (H + W + g, H + L + 0.5), (H + W + g, 2 * H + L - 1.5), (H + W, 2 * H + L), (H, 2 * H + L), (H - g, 2 * H + L - 1.5), (H - g, H + L + 0.5),
           (H, H + L), (0, H + L), (0, H), (H, H), (H - g, H - 0.5), (H - g, 1.5)]
    part = Part(11, "base", "台", pts, label_xy=(H + 1.5, H + 1.5), label="11 台")
    part.valley = [((H, H), (H + W, H)), ((H, H + L), (H + W, H + L)), ((H, H), (H, H + L)), ((H + W, H), (H + W, H + L)),
                   ((H, 0), (H, H)), ((H + W, 0), (H + W, H)), ((H, H + L), (H, 2 * H + L)), ((H + W, H + L), (H + W, 2 * H + L))]
    part.glue = [[(H, 0), (H, H), (H - g, H - 0.5), (H - g, 1.5)], [(H + W, 0), (H + W + g, 1.5), (H + W + g, H - 0.5), (H + W, H)],
                 [(H, H + L), (H, 2 * H + L), (H - g, 2 * H + L - 1.5), (H - g, H + L + 0.5)], [(H + W, H + L), (H + W + g, H + L + 0.5), (H + W + g, 2 * H + L - 1.5), (H + W, 2 * H + L)]]
    faces = [(H, H, H + W, H + L), (H, 0, H + W, H), (H, H + L, H + W, 2 * H + L), (0, H, H, H + L), (H + W, H, 2 * H + W, H + L)]
    part.art = [{"kind": "poly", "pts": [(a + 0.2, b + 0.2), (c - 0.2, b + 0.2), (c - 0.2, d - 0.2), (a + 0.2, d - 0.2)], "fill": WOOD if i == 0 else WOOD_DARK}
                for i, (a, b, c, d) in enumerate(faces)]
    cx = H + W / 2
    s = p["post_side"]
    py = H + p["post_pos"]
    sq = [(cx - s / 2, py - s / 2), (cx + s / 2, py - s / 2), (cx + s / 2, py + s / 2), (cx - s / 2, py + s / 2)]
    part.art.append({"kind": "line", "pts": sq + [sq[0]], "stroke": INK, "sw": 0.3})  # 柱の足を貼る所
    part.holes = [(cx, H + peg_pos(p), p["stick_d"] / 2 + 0.4)]  # 軸が回るよう、穴は串より 0.8mm 太い
    cw, ch = rod_cut(p)
    rx = cx + rod_off(p) - cw / 2
    # 北の壁は y=0 が床の縁、南の壁は y=2H+L が床の縁。棒は床から壁の高さの半分を通す。
    part.cuts = [(rx, H / 2 - ch / 2, cw, ch), (rx, H + L + H / 2 - ch / 2, cw, ch)]
    return part


def _wheel(p):
    """花車（花弁 10 枚）。真ん中に軸の穴、1 枚の花弁の先に玉の糸の穴。花弁の形はコマ 10 の図の目測。"""
    r, n = p["wheel_r"], WHEEL_PETALS
    ri = 0.6 * r  # 花弁の根元。番号の字を軸の穴の横に置けるだけの広さを残す
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        da = math.pi / n
        pts += [(r + ri * math.cos(a - da * 0.9), r + ri * math.sin(a - da * 0.9)),
                (r + r * math.cos(a - da * 0.45), r + r * math.sin(a - da * 0.45)),
                (r + r * math.cos(a + da * 0.45), r + r * math.sin(a + da * 0.45))]
    part = Part(12, "wheel", "花車", pts, label_xy=(r - 4.6, r - 1.75), label="12")
    a = wheel_anchor(p)
    part.holes = [(r, r, p["stick_d"] / 2 + 0.1), (r + a, r, 0.5)]
    part.art = [{"kind": "poly", "pts": _circle(r, r, ri * 0.9, 30), "fill": PETAL}]
    return part


def _rodtab(p):
    """棒の留め具。帯を棒に巻いて貼り、旗を軸に向けて立て、旗の穴に巻く糸を結ぶ。"""
    W = rod_perimeter(p) + 3
    pts = [(0, 0), (W, 0), (W, TAB_W), (7, TAB_W), (7, TAB_W + TAB_FLAG), (1, TAB_W + TAB_FLAG), (1, TAB_W), (0, TAB_W)]
    part = Part(16, "rodtab", "棒の留め具", pts, label_xy=(W - 6.5, 0.8), label="16")
    part.glue = [[(W - 3, 0), (W, 0), (W, TAB_W), (W - 3, TAB_W)]]
    part.valley = [((1, TAB_W), (7, TAB_W))]
    part.holes = [(4, TAB_W + TAB_FLAG - 2.5, 0.6)]
    return part


def _gauge(p):
    """花車の高さの物差しの紙。台の上の面に立て、上の端に花車の下の面を合わせる。長さは peg_height そのもの。"""
    h = p["peg_height"]
    part = Part(17, "gauge", "花車の高さの紙", [(0, 0), (6, 0), (6, h), (0, h)], label_xy=(1.4, 1.5), label="17")
    part.art = [{"kind": "poly", "pts": [(0.2, 0.2), (5.8, 0.2), (5.8, 1.0), (0.2, 1.0)], "fill": INK}]  # 上の端の印
    return part


def _place_kanko(by_key, page, y, gap):
    """2 段目に台・面 2 枚（縦）・柱・花車を並べ、説明は 2 段目の下に全幅で置く（台が広く、右に説明の列を取ると物差しが入らない）。"""
    x = page.x0
    base = by_key["base"]
    base.x, base.y = x, y
    x += base.width + gap
    front, back = by_key["front"], by_key["back"]
    front.x, front.y = x, y
    back.x, back.y = x, y + front.height + gap
    x += front.width + gap
    post, wheel = by_key["post"], by_key["wheel"]
    post.x, post.y = x, y
    wheel.x, wheel.y = x, y + post.height + gap
    tab, gauge = by_key["rodtab"], by_key["gauge"]
    tab.x, tab.y = x + wheel.width + gap, wheel.y
    gauge.x, gauge.y = tab.x + tab.width + gap, wheel.y
    bottom = max(base.y + base.height, back.y + back.height, wheel.y + wheel.height, tab.y + tab.height, gauge.y + gauge.height)
    return bottom + gap, page.x1 - page.x0, page.x0


def bom_kanko(p):
    paper = f"紙（厚さ {p['paper_thickness']}mm 前後）"
    why = "家庭のプリンタで刷って作るため"
    peg = peg_cut(p)
    rod = ROD_NORTH_OUT + p["base_length"] + ROD_GRIP  # 北の壁から出す分＋台の中＋手で持つ分
    return [
        {"number": 1, "key": "front", "name": "表の面", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（紙張りか革張りかは図から分からない）", "reason": why},
        {"number": 2, "key": "back", "name": "裏の面", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（同じ）", "reason": why},
        {"number": 3, "key": "band", "name": "胴の帯", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        {"number": 8, "key": "cord", "name": "糸", "qty": 1, "material": f"木綿の糸（{p['k_cord'] + 15:g}mm）", "substituted": True, "original_guess": "糸（図の線による）", "reason": "家にあるため"},
        {"number": 9, "key": "bead", "name": "玉", "qty": 1, "material": f"油粘土の玉（直径 {p['bead_d']:g}mm）かビーズを 1 つ", "substituted": True, "original_guess": "不明", "reason": "大きさを変えて試しやすいため"},
        {"number": 10, "key": "post", "name": "柱", "qty": 1, "material": paper, "substituted": True, "original_guess": "木か竹（図の形からの推定）", "reason": why},
        {"number": 11, "key": "base", "name": "台", "qty": 1, "material": paper, "substituted": True, "original_guess": "木の板（図の形からの推定）", "reason": why},
        {"number": 12, "key": "wheel", "name": "花車", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙（図の形からの推定）", "reason": why},
        {"number": 13, "key": "peg", "name": "花車の軸", "qty": 1, "material": f"竹串（長さ {peg:g}mm に切る）", "substituted": True, "original_guess": "竹か木（図の形からの推定）", "reason": "家にあり、台の穴で回しやすいため"},
        {"number": 14, "key": "rod", "name": "引く棒", "qty": 1, "material": f"竹串 2 本（長さ {rod:g}mm、テープで束ねる）", "substituted": True, "original_guess": "竹 2 本（図の形による。図の切り欠きは 16 棒の留め具に置き換えた）【解釈】", "reason": "図の 2 本並びの竹に近く、家にあるため"},
        {"number": 15, "key": "pull", "name": "巻く糸", "qty": 1, "material": "木綿の糸（200mm）", "substituted": True, "original_guess": "不明（図に見えない）【解釈】", "reason": "棒を引いて軸を回すため"},
        {"number": 16, "key": "rodtab", "name": "棒の留め具", "qty": 1, "material": paper, "substituted": True, "original_guess": "棒の切り欠き（図による）【解釈】", "reason": "竹串に切り欠きを彫るのは難しく、結ぶ所を刷って決めるため"},
        {"number": 17, "key": "gauge", "name": "花車の高さの紙", "qty": 1, "material": paper, "substituted": True, "original_guess": "無し（作るための道具）", "reason": "花車を台の上の面から決まった高さに貼るため"},
    ]


def steps_kanko(p):
    return ["刷った物差しに定規を当て、10cm か確かめる",
            "部品を実線で切る。胴の帯の歯の間・帯の四角い穴・台の壁の四角い穴も切る（カッターは大人がする）",
            "3 胴の帯を丸めて貼り、歯を内へ折って 1 表の面（巴）と 2 裏の面を貼る",
            "10 柱を四角い筒に貼り、足の糊代を外へ折る。頭を胴の四角い穴に差して貼る",
            "11 台を破線で折り、角の糊代で箱にする（底は無い）。印の四角に柱の足を貼る。表の面を花車の側に向ける",
            f"竹串 13（{peg_cut(p):g}mm）を台の丸い穴に通し、下の端を床に着ける",
            f"17 花車の高さの紙を軸の横の台の上の面に立て、12 花車を台の上の面から {p['peg_height']:g}mm の所（紙の上の端の印）に貼る。軸の上の端からは {PEG_TOP}mm 下",
            f"花車の小さい穴に糸を結び、玉の中心まで {p['k_cord']:g}mm にする",
            f"【解釈】14 引く棒を南の壁の穴から北の壁の穴へ通し、北の壁から {ROD_NORTH_OUT}mm 出す",
            f"【解釈】16 棒の留め具を、棒の北の端から {rodtab_pos(p):g}mm の所（軸の真横）に巻いて貼り、旗を軸に向ける",
            f"【解釈】巻く糸の端を旗の穴に結び、台の下から軸に {math.ceil(pull_turns(p))} 回巻く（棒を南へ {pull_travel(p):.0f}mm 引くと、約 {pull_turns(p):.1f} 回まわる）",
            "棒を引いて軸を回し、玉が面に当たるか見る"]


def _diagram_kanko(x, y, w, h, p):
    """横から見た絵。台・柱・鼓・軸・花車の並びと、振れた玉。"""
    R, Lk = p["k_radius"], p["k_length"]
    span = p["base_length"] + 10
    tall = p["base_height"] + max(p["post_height"] + 2 * R, p["peg_height"]) + 4
    s = min(w / span, h / tall)
    floor = y + h - 2
    top = floor - p["base_height"] * s
    shapes = [{"kind": "rect", "x": x, "y": top, "w": p["base_length"] * s, "h": p["base_height"] * s}]
    px = x + p["post_pos"] * s
    shapes.append({"kind": "rect", "x": px - p["post_side"] / 2 * s, "y": top - p["post_height"] * s, "w": p["post_side"] * s, "h": p["post_height"] * s})
    shapes.append({"kind": "rect", "x": px - Lk / 2 * s, "y": top - (p["post_height"] + 2 * R) * s, "w": Lk * s, "h": 2 * R * s})
    gx = x + peg_pos(p) * s
    wy = top - p["peg_height"] * s
    shapes.append({"kind": "line", "x1": gx, "y1": floor, "x2": gx, "y2": wy})
    shapes.append({"kind": "line", "x1": gx - p["wheel_r"] * s, "y1": wy, "x2": gx + p["wheel_r"] * s, "y2": wy})
    bx = gx - (wheel_anchor(p) + p["k_cord"]) * s
    shapes.append({"kind": "line", "x1": gx - wheel_anchor(p) * s, "y1": wy, "x2": bx, "y2": wy, "dash": "1,0.6"})
    br = p["bead_d"] / 2 * s
    shapes.append({"kind": "rect", "x": bx - br, "y": wy - br, "w": 2 * br, "h": 2 * br})
    return shapes
