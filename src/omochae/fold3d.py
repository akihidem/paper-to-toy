"""型紙の部品を 3D の中で折って組み、刷る部品の形が組み方と合うかを確かめる（最小の 1 本: 御来迎 つまみの形）。

本人の考え（2026-11-05「手順をAIが3Dで組み立てて、その過程を手順書にする」）の最初の 1 本。本人の決定で、提出の前は 2 つだけを見る:
- 3D.close: 外筒を、型紙の折り線で 90° ずつ谷折りすると角筒に閉じ、糊代が帯の反対の端の面（1 面目）に重なる。内筒も同じく見る
  （竹串の線の前提なので）。糊代 1 つが 1 面である事、折り線が面を分けていない・長さ 0・つながらない面・自分と交わる外形も、
  同じ床で落とす（式と絵のずれそのものなので）
- 3D.skewer: 折った内筒が外筒の中に入り、内筒の 2 つの穴が向かい合い（高さも横もずれない）、穴を通す竹串が水平で、
  内筒を外筒に入れて静かな時から押し上げ切るまで、外筒の溝の中を通る
判断の芯:
- 寸法の式（check_physics・slot_span）でなく、刷る部品（外形・折り線・糊代・穴・溝の切り込み）から形を組む。式と絵がずれた時に見つけるため
- 面は硬い板、折り線は蝶番と見る。紙の厚み・たわみ・摩擦は入れないので、通っても紙で動く保証ではない
- 刷る紙・手順の文・凍結の床は変えない。入口は python -m omochae.fold3d だけで、型紙の検査（compose）には繋がない。
  3D.close・3D.skewer は凍結の基準（tests/frozen/criteria.md）の床ではない（足すかは本人が決める）
前提と限り:
- 外筒は折り線を刷らず、絵の色の境で折る（hide_folds）。ここで折るのは型紙の折り線のデータで、色の境がその上にある事は見ない
  （型紙の絵は、折り線と同じ位置から面ごとに塗っている）
- 内筒は外筒の真ん中に、同じ面の並び（1 面目と 1 面目を向かい合わせ）で入れる。すき間の分だけ横にずれる遊びは見ない
- 竹串の太さは、溝の式（slot_span）と同じ knob_width と見る。刷った穴の丸（半径 1.2mm）は竹串の先であける所の印で、竹串の太さではない
- 行程は、内筒の上の端が口より押し上げる量だけ下にある時（静かな時）から、口に届く時（押し上げ切る）まで。
  押し上げる量は寸法から、筒の高さは折った形から取る
- 溝の無い側の竹串の端の長さは見ない
終了: 0 = 確かめて通った / 3 = 落ちた / 4 = 確かめられない（まだ組めない形・読めない）。
"""
import math
import sys
from dataclasses import dataclass

# 読み込みの囲い（壊れた雛形で 4 にする所）を先に通す。
from .__main__ import Parser, load_source, scenario_from_args
from .compose import TEMPLATES, compose
from .model import Failure, ToolMissing

# ここだけが使う shapely の部分も、読めなければ 4 にする。読み込みは main の囲いより前に走るので、
# 囲わないとトレースバックの 1 になる（__main__ の囲いと同じ考え。レビューの指摘）。
try:
    from shapely.geometry import LineString, MultiPoint, Point, Polygon
    from shapely.ops import nearest_points, split
except Exception as e:
    print(f"確かめられない: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(4)

# 折る手の誤差の見込み（実物で未確認）。継ぎ目のずれ・糊代の浮き・2 つの穴の高さの差をこれで見る。
TOL = 0.5
# 竹串が溝の縁に触れるだけ（余り 0）は通す。溝の上の端は、押し上げ切った時の竹串の上の端そのもの（slot_span）なので、
# 押し上げ切った所の余りは作りとして 0 になる。浮動小数の誤差だけを見逃す幅。
EPS = 1e-6
# 糊代が相手の面に重なる割合の下限。角を落とした糊代は面の中に収まるので、ほぼ全部が重なる。
GLUE_COVER = 0.95
FOLD_DEG = 90  # 角筒は 4 面なので、折り線ごとに 90°
OUTER, INNER = "tube", "pusher"


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(a):
    return _mul(a, 1 / math.sqrt(_dot(a, a)))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


IDENTITY = (((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), (0.0, 0.0, 0.0))


def _apply(T, p):
    R, t = T
    return tuple(_dot(R[i], p) + t[i] for i in range(3))


def _back(T, q):
    """_apply の逆。R は回転なので、転置で戻す。"""
    R, t = T
    d = _sub(q, t)
    return tuple(R[0][i] * d[0] + R[1][i] * d[1] + R[2][i] * d[2] for i in range(3))


def _turn(T, o, d, ang):
    """変換 T の後に、点 o を通る向き d（単位）の線のまわりに ang（ラジアン）回す変換。"""
    x, y, z = d
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    M = ((c + x * x * C, x * y * C - z * s, x * z * C + y * s),
         (y * x * C + z * s, c + y * y * C, y * z * C - x * s),
         (z * x * C - y * s, z * y * C + x * s, c + z * z * C))
    R, t = T
    cols = list(zip(*R))
    return (tuple(tuple(_dot(M[i], cols[j]) for j in range(3)) for i in range(3)),
            _add(tuple(_dot(M[i], _sub(t, o)) for i in range(3)), o))


def _lift(pt):
    """頁の点（mm、y は下向き）を、折る前の紙の 3D の点にする。刷った面が z の正を向き、筒の上（頁の上）が y の正。"""
    return (pt[0], -pt[1], 0.0)


@dataclass
class Face:
    """折った後の面 1 枚。poly は頁の上の平らな形、T は頁の点を 3D へ写す変換、hinge は親の面とつなぐ折り線。"""
    poly: Polygon
    T: tuple
    hinge: tuple = None
    parent: int = None

    def at(self, pt):
        return _apply(self.T, _lift(pt))

    def flat(self, q):
        """3D の点を、この面の頁の上の点と、面から浮く量にする。"""
        X, Y, Z = _back(self.T, q)
        return (X, -Y), Z

    @property
    def normal(self):
        """刷った面の向き（折る前の z の正を、今の向きへ写した物）。"""
        R, _ = self.T
        return (R[0][2], R[1][2], R[2][2])


def _long(a, b, ext=1.0):
    """折り線を両端で ext mm 伸ばす。外形の縁でちょうど終わる線は、縁に触れるだけで面を分けないことがあるため（伸ばした分は外形の外で捨てる）。"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    ux, uy = dx / n * ext, dy / n * ext
    return LineString([(a[0] - ux, a[1] - uy), (b[0] + ux, b[1] + uy)])


class FoldError(Exception):
    """型紙の折り線と外形が合わず、折れない（3D.close で落とす。確かめられない 4 にはしない。式と絵のずれそのものなので）。"""


def fold(part, deg=FOLD_DEG):
    """部品を折り線で面に分け、外形の始めの点を持つ面を動かさずに、折り線ごとに deg° 折る。谷は刷った面の側へ、山は裏へ折る。

    Returns 面の並び（list of Face）。親の面を子より先に並べる。最初の面が動かない面（筒なら 1 面目）。
    外形が自分と交わる・長さ 0 の折り線がある・折り線が面をちょうど 2 つに分けていない・折り線でつながらない面がある時は
    FoldError（黙って飛ばしたり、例外の 4 にしたりすると、崩れた型紙が「確かめられない」に紛れる）。
    """
    lines = [(ln, 1) for ln in part.valley] + [(ln, -1) for ln in part.mountain]
    outline = Polygon(part.outline)
    if not outline.is_valid:
        raise FoldError("外形が自分と交わり、面に分けられない")
    for n, ((a, b), _) in enumerate(lines, 1):
        if math.dist(a, b) <= EPS:
            raise FoldError(f"{n} 本目の折り線の長さが 0")
    polys = [outline]
    for (a, b), _ in lines:
        polys = [g for f in polys for g in split(f, _long(a, b)).geoms]
    # 折り線に沿って縁を持つ 2 面を、その折り線でつなぐ。縁が線に沿う長さで見る（真ん中の点で見ると、溝や穴を通る折り線で外れる）
    adj = {}
    for n, ((a, b), sign) in enumerate(lines, 1):
        seg = LineString([a, b])
        touch = [i for i, f in enumerate(polys) if f.boundary.intersection(seg).length > EPS]
        if len(touch) != 2:
            raise FoldError(f"{n} 本目の折り線が面を 2 つに分けていない（外形と合わない）")
        i, j = touch
        adj.setdefault(i, []).append((j, (a, b), sign))
        adj.setdefault(j, []).append((i, (a, b), sign))
    start = Point(part.outline[0])
    root = next(i for i, f in enumerate(polys) if f.boundary.distance(start) < EPS)
    faces, index = [Face(polys[root], IDENTITY)], {root: 0}
    for k in range(len(polys)):  # 広さ優先。faces が伸びる間だけ回る
        if k >= len(faces):
            break
        i = next(n for n, m in index.items() if m == k)
        parent = faces[k]
        for j, (a, b), sign in adj.get(i, []):
            if j in index:
                continue
            o, e = parent.at(a), parent.at(b)
            d = _unit(_sub(e, o))
            ang = math.radians(deg)
            c = polys[j].centroid.coords[0]
            c0 = parent.at(c)
            # 回す向きは、子の面の真ん中が親の刷った面の側（谷）か裏（山）へ動く方。線の向きで符号が変わるので、動きで決める
            T = _turn(parent.T, o, d, ang)
            if _dot(_sub(_apply(T, _lift(c)), c0), parent.normal) * sign < 0:
                T = _turn(parent.T, o, d, -ang)
            index[j] = len(faces)
            faces.append(Face(polys[j], T, (a, b), k))
    if len(faces) < len(polys):
        raise FoldError(f"折り線でつながらない面が {len(polys) - len(faces)} つある（外形と折り線が合わない）")
    return faces


def _glue_faces(part, faces):
    gs = [Polygon(g) for g in part.glue]
    return [f for f in faces if any(f.poly.intersection(g).area >= 0.99 * f.poly.area for g in gs)]


def _seam(part, face, ends):
    """糊代の折り線の 2 つの端（3D）が、相手の面の 1 本の切る縁（折り線の上でない外形の辺）にどれだけ近いか。2 つの端の遠い方で測る。

    縁のどこかまでの距離にすると、1 面目だけが広い時に、2 つの端が上と下の縁に乗って 0 になり、閉じない筒を見逃した。
    1 本の辺に 2 つの端がそろって乗る事を見る。並んだ辺の途中の点は除いてから見る（同じ線の上で切れた辺を 1 本にするため）。
    """
    folds = [LineString(ln) for ln in part.valley + part.mountain]
    pts = [face.flat(e) for e in ends]
    coords = list(face.poly.simplify(0).exterior.coords)
    gaps = [max(math.hypot(LineString([a, b]).distance(Point(pt)), z) for pt, z in pts)
            for a, b in zip(coords, coords[1:])
            if not any(ln.distance(Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)) < EPS for ln in folds)]
    return min(gaps, default=math.inf)


def _far_end(faces, g):
    """折り線でつながる面の木の上で、面 g から一番遠い面（帯の反対の端）。筒の糊代の面なら、帯の始めの 1 面目。"""
    def up(k):
        out = [k]
        while faces[out[-1]].parent is not None:
            out.append(faces[out[-1]].parent)
        return out
    pg = up(g)

    def dist(k):
        pk = up(k)
        common = next(x for x in pk if x in pg)
        return pk.index(common) + pg.index(common)
    return max(range(len(faces)), key=dist)


def _close(part, faces):
    """糊代の面が、継ぎ目を合わせて帯の反対の端の面に重なるか。Returns (所見の文, 失敗)。どちらか片方だけ。

    相手は帯の反対の端の面に限る。どの面でもよいとすると、折り線の崩れで糊代が別の面に貼り付く形を通しうる（レビューの指摘）。
    継ぎ目を先に見る。折り線が 1 本ずれた時に、継ぎ目と糊代の重なりの 2 行が出ると、1 つの崩れが 2 つに見えるため。
    """
    where = part.label
    if not part.glue:
        return None, Failure("3D.close", where, "糊代の印が無く、角筒の継ぎ目を貼れない")
    glued = _glue_faces(part, faces)
    # 糊代 1 つに面 1 つ。余計な折り線で糊代が分かれると、片方だけを見て、もう片方を見落とす（レビューの指摘）
    if len(glued) != len(part.glue):
        return None, Failure("3D.close", where, f"糊代が折り線で区切られた 1 面になっておらず（糊代 {len(part.glue)} つに面 {len(glued)} つ）、折って貼れない")
    gi = next(i for i, f in enumerate(faces) if f is glued[0])
    g, k = faces[gi], _far_end(faces, gi)
    # 糊代の面の折り線。外形の始めの点が糊代の面にあると、その面が動かない面になり、折り線は子の面の側が持つ
    hinge = g.hinge or next((f.hinge for f in faces if f.parent == gi), None)
    if k == gi or hinge is None:
        return None, Failure("3D.close", where, "糊代を折って貼る相手の面が無い")
    gap = _seam(part, faces[k], [g.at(pt) for pt in hinge])
    if gap > TOL:
        return None, Failure("3D.close", where, f"型紙の折り線で 90° ずつ谷折りすると、継ぎ目が {gap:.1f}mm ずれ、角筒に閉じない")
    f = faces[k]
    mapped = [f.flat(g.at(pt)) for pt in g.poly.exterior.coords]
    lift = max(abs(z) for _, z in mapped)
    cover = Polygon([pt for pt, _ in mapped]).intersection(f.poly).area / g.poly.area
    if lift > TOL or cover < GLUE_COVER:
        return None, Failure("3D.close", where, f"糊代が貼る相手の面に重ならない（浮き {lift:.1f}mm・重なり {cover:.0%}）")
    target = "1 面目" if k == 0 else "帯の反対の端の面"
    folds = len(part.valley) + len(part.mountain)
    return f"閉じる {where}: 折り線 {folds} 本を 90° ずつ谷折りすると角筒に閉じる（継ぎ目のずれ {gap:.2f}mm・糊代は{target}に {cover:.0%} 重なる）", None


def tube_axis(faces):
    """角筒の軸の上向きの向き・断面の中心の点・その点から測った底と上の端の高さ。

    中心は折り線（蝶番）の位置の平均から取る。面の頂点の平均にすると、溝のある面の点が多いぶん溝の側へ寄る。
    """
    hinged = [f for f in faces if f.hinge]
    a, b = hinged[0].hinge
    top, bottom = (a, b) if a[1] < b[1] else (b, a)  # 頁の y の小さい方が筒の上
    up = _unit(_sub(hinged[0].at(top), hinged[0].at(bottom)))
    mids = [f.at(((f.hinge[0][0] + f.hinge[1][0]) / 2, (f.hinge[0][1] + f.hinge[1][1]) / 2)) for f in hinged]
    c = _mul(tuple(sum(m[i] for m in mids) for i in range(3)), 1 / len(mids))
    hs = [_dot(_sub(f.at(pt), c), up) for f in faces for pt in f.poly.exterior.coords]
    return up, c, min(hs), max(hs)


def _section(faces, up, c):
    """角筒の断面。折り線（角）の位置を、軸に垂直な面へ写した多角形（軸の中心 c が原点）。"""
    e1 = _cross(up, (0.0, 0.0, 1.0))
    e1 = _unit(e1 if _dot(e1, e1) > EPS else _cross(up, (1.0, 0.0, 0.0)))
    e2 = _cross(up, e1)
    mids = [_sub(f.at(((f.hinge[0][0] + f.hinge[1][0]) / 2, (f.hinge[0][1] + f.hinge[1][1]) / 2)), c) for f in faces if f.hinge]
    return MultiPoint([(_dot(m, e1), _dot(m, e2)) for m in mids]).convex_hull


def _skewer(outer_part, outer, inner_part, inner, p):
    """竹串の線が水平で、行程の全部で外筒の溝の中を通るか。Returns (所見の文, 失敗)。"""
    holes = inner_part.holes
    if len(holes) != 2:
        return None, Failure("3D.skewer", "竹串", f"竹串を通す穴が 2 つでない（{len(holes)} 個）")
    centers, walls_of = [], []
    for x, y, _ in holes:
        f = next((f for f in inner if f.poly.contains(Point(x, y))), None)
        if f is None:
            return None, Failure("3D.skewer", "竹串", "竹串を通す穴が面の中に無い（折り線の上か外形の外）")
        centers.append(f.at((x, y)))
        walls_of.append(f)
    up_o, c_o, bot_o, top_o = tube_axis(outer)
    up_i, c_i, bot_i, top_i = tube_axis(inner)
    # 折った内筒が外筒の中に入るか。寸法の式（F5.slide_clearance）でなく、折った形の断面で見る（絵の内筒が式より大きくずれた時に
    # 見つけるため。レビューの指摘）。紙の厚みを入れないので、すき間が 0 より大きいかだけを見る（厚みの分の余りは式の床が見る）
    sec_o, sec_i = _section(outer, up_o, c_o), _section(inner, up_i, c_i)
    if sec_i.within(sec_o):
        fit = sec_o.exterior.distance(sec_i)
    else:
        fit = -max(sec_o.distance(Point(pt)) for pt in sec_i.exterior.coords)
    if fit <= EPS:
        return None, Failure("3D.skewer", inner_part.label, f"内筒の断面が外筒の断面に収まらず（すき間 {fit:.1f}mm）、外筒に入らない")
    d = _sub(centers[1], centers[0])
    tilt = abs(_dot(d, up_i))
    if tilt > TOL:
        return None, Failure("3D.skewer", "竹串", f"2 つの穴の高さが {tilt:.1f}mm 違い、竹串が傾く（溝の中で引っかかる）")
    # 横のずれも同じく見る。高さだけがそろい、穴が向かい合わずに横へずれると、竹串が面へ斜めに交わる（レビューの指摘）。
    # 穴のある面に垂直な向きと、軸の向きのどちらでもない向きの長さ
    n1 = walls_of[0].normal
    side = math.sqrt(max(0.0, _dot(d, d) - _dot(d, n1) ** 2 - _dot(d, up_i) ** 2))
    if side > TOL:
        return None, Failure("3D.skewer", "竹串", f"2 つの穴が向かい合っておらず（横に {side:.1f}mm ずれ）、竹串が斜めになる（溝の中で引っかかる）")
    H, L, s, r = top_o - bot_o, top_i - bot_i, p["push_amount"], p["knob_width"] / 2
    rest, push = H - s - L, H - L  # 内筒の底の、外筒の底からの高さ

    def placed(q, t):
        """内筒の点を、外筒の真ん中で、内筒の底を外筒の底から t の高さに置いた所へ写す（両方とも 1 面目を動かさずに折ったので、向きはそろう）。"""
        return _add(_add(_sub(q, c_i), c_o), _mul(up_o, bot_o + t - bot_i))

    u = _unit(_sub(centers[1], centers[0]))
    glue = _glue_faces(outer_part, outer)
    best = None
    for f in (f for f in outer if f not in glue):
        n = f.normal
        if abs(_dot(u, n)) < EPS:
            continue  # 竹串と平らな面は通らない
        o = f.at(f.poly.exterior.coords[0])
        q = []
        for t in (rest, push):
            a = placed(centers[0], t)
            q.append(f.flat(_add(a, _mul(u, _dot(_sub(o, a), n) / _dot(u, n))))[0])
        hull = f.poly.convex_hull
        if not all(hull.covers(Point(pt)) for pt in q):
            continue  # 行程の端で面の外（筒の上か下）を通る面は、竹串が出る所ではない
        # 竹串が面へ斜めに交わると、面の上の切り口は楕円になり、長い方の半径は r / cos。安全側に、その半径の円で見る
        # （上の横のずれの床を通った後は、斜めは 1° ほどまでなので、円にした分の差は小さい）
        rf = r / abs(_dot(u, n))
        clear = f.poly.distance(LineString(q)) - rf
        if best is None or clear > best[0]:
            best = (clear, f, q, rf)
    if best is None:
        return None, Failure("3D.skewer", "竹串", "竹串の線が、行程の間ずっと外筒の面を横切る所が無い（筒の外を通る）")
    clear, f, (q0, q1), rf = best  # rf はその面の上の竹串の切り口の半径（文に出す太さは r のまま）
    rest_h, push_h = (_dot(_sub(placed(centers[0], t), c_o), up_o) - bot_o for t in (rest, push))
    if clear < -EPS:
        at_rest = f.poly.distance(Point(q0)) - rf
        if at_rest < -EPS:
            return None, Failure("3D.skewer", "竹串", f"静かな時から、竹串（太さ {2 * r:g}mm）が外筒の紙に {-at_rest:.1f}mm 掛かり、溝を通らない")
        # 動きは真っ直ぐなので、紙に当たる所は行程の途中の 1 か所。二分で探す
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            end = (q0[0] + (q1[0] - q0[0]) * mid, q0[1] + (q1[1] - q0[1]) * mid)
            lo, hi = (mid, hi) if f.poly.distance(LineString([q0, end])) - rf >= -EPS else (lo, mid)
        short = (1 - lo) * (push - rest)
        return None, Failure("3D.skewer", "竹串", f"押し上げ切る {short:.1f}mm 手前で、竹串が外筒の紙に当たり、溝を通り切らない")
    c_rest, c_push = (f.poly.distance(Point(pt)) - rf for pt in (q0, q1))
    stop = ""
    if c_push < TOL and nearest_points(f.poly, Point(q1))[0].y < q1[1] - EPS:
        stop = "。押し上げ切ると溝の上の端に届いて止まる"
    return (f"並ぶ 竹串: 内筒は外筒の中に入る（断面のすき間 {fit:.2f}mm）。2 つの穴は向かい合い（高さの差 {tilt:.2f}mm・横のずれ {side:.2f}mm）、竹串は水平。"
            f"内筒を外筒の真ん中に入れ、竹串（太さ {2 * r:g}mm）の中心が底から "
            f"{rest_h:.1f}mm（静かな時）から {push_h:.1f}mm（押し上げ切る）まで、溝の中を通る（紙までの余り 静かな時 {c_rest:.2f}mm・"
            f"押し上げ切った時 {c_push:.2f}mm{stop}）"), None


def check(parts, p):
    """刷る部品（compose の配置の部品）と寸法から、外筒と内筒を折って組み、確かめる。Returns (所見の文の並び, 失敗の並び)。"""
    by = {q.key: q for q in parts}
    if OUTER not in by or INNER not in by:
        raise ToolMissing("外筒と内筒が無い（最小の 1 本は、御来迎 つまみの形だけを組む）")
    notes, failures, folded = [], [], {}
    for q in (by[OUTER], by[INNER]):
        try:
            folded[q.key] = fold(q)
        except FoldError as e:
            failures.append(Failure("3D.close", q.label, str(e)))
            continue
        note, fail = _close(q, folded[q.key])
        if fail:
            failures.append(fail)
        else:
            notes.append(note)
    if failures:
        # 筒が閉じなければ、竹串の線の形が決まらない。続けて見ると、1 つの崩れに別の行が続いて狙いが読めなくなる（compose と同じ考え）
        return notes, failures
    note, fail = _skewer(by[OUTER], folded[OUTER], by[INNER], folded[INNER], p)
    return (notes + [note], []) if note else (notes, [fail])


def run(template_id, params, source, title=None, inject=None):
    """型紙と同じ検査（compose）を通ってから、3D で組んで確かめる。Returns (所見, 失敗)。

    型紙の検査に落ちる寸法は、組む前にその失敗を返す（落ちる寸法の部品を「組める形」として確かめないため。omochae.foldsim と同じ）。
    まだ組めない形かは、型紙の検査の後で見る。先に見ると、形の値の打ち間違いも F5.range（3）でなく「まだ組めない」（4）になった（レビューの指摘）。
    """
    p, layout, failures = compose(template_id, params, source, title=title, inject=inject or {})
    if failures:
        return [], failures
    if template_id != "slider_fan" or p.get(TEMPLATES[template_id].FORM) != "tab":
        raise ToolMissing("まだ 3D で組めない形（最小の 1 本は、御来迎 つまみの形の外筒と竹串だけ）")
    return check(layout["parts"], p)


def main(argv=None):
    ap = Parser(prog="omochae.fold3d", description="型紙の部品を 3D の中で折って組み、外筒が閉じるか・溝と竹串が並ぶかを確かめる（最小の 1 本: 御来迎 "
                                                 "つまみの形）。先に型紙と同じ検査を通す。終了: 0 通った / 3 落ちた / 4 確かめられない")
    ap.add_argument("--scenario", help="場面の JSON（python -m omochae と同じ形）。渡すと --template・--source・--params は使わない")
    ap.add_argument("--template", default="slider_fan", help="雛形（今は slider_fan だけ組める。既定 slider_fan）")
    ap.add_argument("--source", help="data/sources/ の出典の記録の名前（既定は雛形ごと）")
    ap.add_argument("--params", help="寸法の JSON。push_part（今は tab だけ組める）が要る")
    args = ap.parse_args(argv)
    try:
        sc = scenario_from_args(args)
        if sc["template"] not in TEMPLATES:
            raise ToolMissing(f"知らない雛形: {sc['template']}")
        notes, failures = run(sc["template"], sc["params"], load_source(sc["source_id"]), sc.get("title"), sc.get("inject"))
    except (ToolMissing, ValueError) as e:
        print(f"確かめられない: {e}", file=sys.stderr)
        return 4
    except Exception as e:  # 想定外は「通った」にも「落ちた」にも数えない。
        print(f"確かめられない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    for n in notes:
        print(n)
    if failures:
        for f in failures:
            print(f.line(), file=sys.stderr)
        return 3
    print("紙の厚み・たわみ・摩擦は入れていない。通っても、紙で動く保証ではない")
    return 0


if __name__ == "__main__":
    sys.exit(main())
