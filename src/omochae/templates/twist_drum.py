"""雛形 twist_drum: 柄を指で回すと、鼓の左右に下げた玉が振れて面を打つ（でんでん太鼓・振り鼓）。

紙の部品は、面 2 枚・胴の帯（糊代の歯つき。丸めて胴にする）・柄の巻き紙。竹串・糸・玉は部品表に載せる。
面の絵は出典ごとに違うので、刷る形（face）で描き分ける。鳥の面（コマ 29）は図に幣（紙の房）が付くので、房の部品が 1 つ増える。
寸法は手元の複写の図の比から出した見込みで、どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。

動きの見込み（F5.drum）の前提:
- 鼓の軸は横、柄（竹串）は胴を縦に貫く。糸は胴の帯の左右（柄から 90° の所）の帯の幅の真ん中に結ぶ。
- 柄を速く回すと、玉は結び目を中心に、結び目の高さの水平面をほぼ回ると見る（重力と糸のたるみは入れない）。
  その面で、面（鼓の軸の向きに結び目から半分の奥行きの所）を打つ点が、面の中心から半径の半分の内に入る糸の長さを求める。
  縁に近いと胴の帯が硬く、鳴りが鈍いと見込む（実物で確かめていない）。
- 玉が垂れた時に、胴の下に出た柄に届くと糸が柄に絡む。結び目から柄の一番近い点（胴の下の縁の柄）までは √2 × 半径。
  糸の長さ＋玉の半径がこれより短ければ絡まない（たるみ・玉の跳ね返りは入れない）。
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
}
RANGES = {
    # 半径の上限 28 は、胴の帯（円周＋糊代）が A4 の印字域の幅 190mm に 1 本で入るため。
    "radius": (15, 28), "depth": (8, 30), "tab": (3, 10), "seam_glue": (5, 12),
    "stick_d": (2, 5), "handle_length": (40, 130), "wrap_glue": (2, 6),
    "cord_length": (5, 60), "bead_d": (4, 14),
    "paper_thickness": (0.05, 0.5),
}
FACES = ("kiku", "tori")
# 刷る形を決める寸法（面の絵と、幣の房があるか）。どの面が「正しい」かは無いので、寸法を直に渡す入口では必ず書かせる。
FORM = "face"
FORMS = FACES
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000007-R-twist_drum"
HOLE_MARGIN = 3  # 穴から紙の端（帯の縁・継ぎ目の糊代）までの見込み。これより狭いと串を回した時に裂けやすい
SKEWER_LEN = 180  # 家にある竹串の長さの見込み（実物を測ったら置き換える）
TOP_OUT = 5  # 柄の先を胴の上へ出す長さ。抜け止めに糸を巻くため
TAB_PITCH = 8  # 糊代の歯の目安の幅。細かいほど丸く貼れるが、切るのが手間になる
STRIKE_ZONE = 0.5  # 打つ点が面の中心から半径のこの割合の内に入れば、鳴ると見込む（縁は鳴りが鈍い）
FACE, INK, BAND, BAND_DARK, BAMBOO, CORD_MARK, PAPER = "#ddd0aa", "#3b3a34", "#9a5a35", "#6e4128", "#cdb98a", "#e8dfc6", "#ece6d6"
TITLES = {"kiku": "菊の面", "tori": "鳥の面と幣"}


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


def circumference(p):
    """胴の帯の長さ（糊代を除く）。面は内へ折った歯に外から貼り、面の縁と帯の外の面をそろえる見込み。
    帯の厚みの真ん中は面の縁から紙の厚みの半分だけ内にあるので、半径から厚みの半分を引いた円周にする。"""
    return 2 * math.pi * (p["radius"] - p["paper_thickness"] / 2)


def band_length(p):
    """胴の帯の全長 ＝ 円周 ＋ 継ぎ目の糊代。帯を切り出す長さはこの 1 つの式から出す（型紙と試験が同じ値を使う）。"""
    return circumference(p) + p["seam_glue"]


def tab_teeth(p):
    """糊代の歯の数・間隔・肩の削り。歯を内へ折ると先は半径 (R − tab) の円に乗り、長さが (R − tab)/R に縮む。
    隣の歯と重ならないよう、先の幅を同じ割合に詰め、さらに両肩を 0.3mm ずつ空ける。"""
    n = max(1, round(circumference(p) / TAB_PITCH))
    pitch = circumference(p) / n
    inset = pitch * p["tab"] / (2 * p["radius"]) + 0.3
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

    下限: 打つ点 x = R − √(L² − (D/2)²) が面の中心から STRIKE_ZONE·R の内 → L ≧ √(((1 − k)R)² + (D/2)²)。
    上限: 反対側へ行き過ぎない L ≦ √(((1 + k)R)² + (D/2)²) と、柄に絡まない L + 玉の半径 < √2·R の小さい方。
    """
    R, h, k = p["radius"], p["depth"] / 2, STRIKE_ZONE
    low = math.hypot((1 - k) * R, h)
    high = min(math.hypot((1 + k) * R, h), math.sqrt(2) * R - p["bead_d"] / 2)
    return low, high


def strike_offset(p):
    """玉が面を打つ点の、面の中心からの距離（正は結び目の側）。糸が奥行きの半分に届かなければ None（面に届かない）。"""
    h = p["depth"] / 2
    if p["cord_length"] <= h:
        return None
    return p["radius"] - math.sqrt(p["cord_length"] ** 2 - h * h)


def check_physics(p):
    """F5.drum: 玉が面を打つ・柄に絡まない・串の穴が裂けない・帯の歯が貼れる・竹串が足りる、を見る。"""
    out = []
    low, high = cord_window(p)
    L = p["cord_length"]
    if L < low:
        x = strike_offset(p)
        where = "面に届かない" if x is None else f"面の中心から {x:.1f}mm の縁の近くを打つ"
        out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は短く、{where}（{low:.1f}mm 以上）"))
    if L > high:
        out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は長く、玉が柄に絡むか面を越える（{high:.1f}mm まで）"))
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
    need = p["handle_length"] + 2 * p["radius"] + TOP_OUT
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
    R = p["radius"]
    art = [{"kind": "poly", "pts": _circle(R, R, R - 0.3), "fill": FACE}]
    if p["face"] == "kiku":
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
    R = p["radius"]
    return Part(number, key, name, _circle(R, R, R), label_xy=(R - 1.5, 2 * R - 5), label=str(number), art=_face_art(p))


def _band(p):
    C, g, t, D = circumference(p), p["seam_glue"], p["tab"], p["depth"]
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
    band.art = [{"kind": "poly", "pts": [(0.2, top + 0.2), (C - 0.2, top + 0.2), (C - 0.2, bot - 0.2), (0.2, bot - 0.2)], "fill": BAND}]
    # 帯の上下の縁の濃い筋（コマ 7 の胴の縁の影）。
    for y0 in (top + 0.2, bot - 1.4):
        band.art.append({"kind": "poly", "pts": [(0.2, y0), (C - 0.2, y0), (C - 0.2, y0 + 1.2), (0.2, y0 + 1.2)], "fill": BAND_DARK})
    mid = top + D / 2
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
    paper = f"紙（厚さ {p['paper_thickness']}mm 前後）"
    why = "家庭のプリンタで刷って作るため"
    cord = p["cord_length"] + 15  # 結び目 2 つ分の余り
    rows = [
        {"number": 1, "key": "front", "name": "表の面", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（紙張りか革張りかは図から分からない）", "reason": why},
        {"number": 2, "key": "back", "name": "裏の面", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（同じ）", "reason": why},
        {"number": 3, "key": "band", "name": "胴の帯", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図では塗った胴）", "reason": why},
        {"number": 4, "key": "wrap", "name": "柄の巻き紙", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": "竹串の柄を持ちやすく、図の柄の色に近づけるため"},
        {"number": 7, "key": "stick", "name": "柄", "qty": 1, "material": f"竹串（太さ {p['stick_d']:g}mm・長さ {SKEWER_LEN}mm の見込み）", "substituted": True, "original_guess": "竹か木（図の柄の形からの推定）", "reason": "家にあり、胴に通しやすいため"},
        {"number": 8, "key": "cord", "name": "糸", "qty": 2, "material": f"木綿の糸（1 本 {cord:g}mm に切る）", "substituted": True, "original_guess": "糸か紐（図の線による）", "reason": "家にあるため"},
        {"number": 9, "key": "bead", "name": "玉", "qty": 2, "material": f"油粘土の玉（直径 {p['bead_d']:g}mm）かビーズ", "substituted": True, "original_guess": "不明", "reason": "大きさを変えて試しやすいため"},
    ]
    if p["face"] == "tori":
        rows.insert(4, {"number": 5, "key": "streamer", "name": "幣の房", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙（図の形からの推定）", "reason": why})
    return rows


def materials(p):
    # 行の位置でなく key で引く。形によって部品表の行が増えるので、位置で引くと別の行を刷る。
    by = {r["key"]: r for r in bom(p)}
    return [f"{by['band']['material']}を 1 枚", "のり、はさみ、定規", by["stick"]["material"], f"{by['cord']['material']}を 2 本", f"{by['bead']['material']}を 2 つ"]


def steps(p):
    pos = hole_positions(p)
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。3 胴の帯の歯の間も切り込む。帯の穴は竹串の先であける",
           "3 胴の帯を丸め、終わりの糊代を頭の下に入れて貼る（絵が外）", "上下の歯を破線で内へ谷折りする",
           "1 表の面と 2 裏の面を、歯に外から貼る",
           f"竹串を太い 2 つの穴（帯の頭から {pos['stick'][0]:.0f}mm と {pos['stick'][1]:.0f}mm）に通し、上へ {TOP_OUT}mm 出す。穴の所を糊で留める",
           f"糸の端に玉を付け、玉の中心から {p['cord_length']:g}mm の所で、菱形の小さい穴に結ぶ（左右 2 本）",
           "4 柄の巻き紙を胴の下の竹串に巻いて貼る"]
    if p["face"] == "tori":
        out.append("5 幣の房の上の帯を、胴の上に出た竹串に巻いて貼る")
    out.append("柄を両手で挟んで左右に回し、玉が面に当たるか見る")
    return out


RESULTS = ("鳴った", "鳴らない")


def measures(p):
    """鳴るかの二択でなく、回し方と玉の動きを言葉か絵で予想する（ほかの雛形と同じ形）。回し方は数でないので欄に残す。"""
    return {"predict": "柄をどう回すと、玉はどう動くと思いますか（言葉か絵で）", "rows": [[("回し方（速さ・向き）", 40)]]}


def diagram(x, y, w, h, p):
    """組み上がりを正面から見た絵。寸法の図ではなく、面・柄・糸と玉の並びを見せるだけ。"""
    R, L = p["radius"], p["cord_length"]
    s = min(w / (2 * R + 2 * L + p["bead_d"]), h / (2 * R + p["handle_length"] + TOP_OUT))
    cx, cy = x + w / 2, y + (TOP_OUT + R) * s
    shapes = [{"kind": "poly", "pts": _circle(cx, cy, R * s, 48), "fill": "none", "sw": 0.25}]
    shapes.append({"kind": "line", "x1": cx, "y1": cy - (R + TOP_OUT) * s, "x2": cx, "y2": cy - R * s})
    shapes.append({"kind": "line", "x1": cx, "y1": cy + R * s, "x2": cx, "y2": cy + (R + p["handle_length"]) * s})
    br = p["bead_d"] / 2 * s
    for side in (-1, 1):
        ax = cx + side * R * s
        bx = ax + side * L * s  # 回して振れた時の玉。糸はほぼ水平に張る
        shapes.append({"kind": "line", "x1": ax, "y1": cy, "x2": bx, "y2": cy, "dash": "1,0.6"})
        shapes.append({"kind": "rect", "x": bx - br, "y": cy - br, "w": 2 * br, "h": 2 * br})
    return shapes
