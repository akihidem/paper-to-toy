"""型紙の折りのある部品を、Origami Simulator（Ghassaei ほか、origamisimulator.org）が読める SVG に書き出す。

元の repo（utsushi）の foldsim から、部品を SVG にする所（part_svg）と色の約束をそのまま写した。入口だけを変えた:
元は仮説の記録から寸法を読んだが、この repo には仮説が無いので、型紙と同じ雛形と寸法（--template と --params、
または場面の JSON）から部品を作る。
判断の芯:
- 書き出す前に型紙と同じ検査（描く前の検査）を通す。落ちる寸法の部品を「折れる形」として渡さないため。落ちれば 3
- Origami Simulator の色の約束: 外形（切る線）は黒、山折りは赤、谷折りは青。紙の厚みと摩擦は模擬しないので、実物と動きは違う
- 色の境で折る部品（hide_folds）も、折り線のデータは持っているので書き出す（型紙に線を刷らないだけ）
終了: 0 = 書き出した / 3 = 検査に落ちた / 4 = 書き出せない。
"""
import argparse
import pathlib
import shutil
import sys
import tempfile

from .__main__ import Parser, load_source, scenario_from_args
from .compose import TEMPLATES, compose
from .model import ToolMissing

COLORS = {"outline": "#000000", "mountain": "#ff0000", "valley": "#0000ff"}


def part_svg(part):
    """1 つの部品を SVG の文字列にする。座標は mm のまま。穴と糊代は折りに関わらないので書かない。"""
    xs = [x for x, _ in part.outline]
    ys = [y for _, y in part.outline]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0, max(ys) - y0
    lines = []
    pts = part.outline + part.outline[:1]
    for (a, b), (c, d) in zip(pts, pts[1:]):
        lines.append((a, b, c, d, COLORS["outline"]))
    # 中を切り抜く穴（cuts の矩形）も黒の外形の線で書く。Origami Simulator は黒を「外形と中の穴」と読む（2026-11-04 に
    # origamisimulator.org の説明で確かめた。緑は細い切れ目なので穴には使わない）。書かないと、穴の無い紙として折れて形も硬さも違う。
    for x, y, cw, ch in part.cuts:
        corners = [(x, y), (x + cw, y), (x + cw, y + ch), (x, y + ch), (x, y)]
        for (a, b), (c, d) in zip(corners, corners[1:]):
            lines.append((a, b, c, d, COLORS["outline"]))
    for kind in ("mountain", "valley"):
        for (a, b), (c, d) in getattr(part, kind):
            lines.append((a, b, c, d, COLORS[kind]))
    body = "".join(f'<line x1="{a - x0:.3f}" y1="{b - y0:.3f}" x2="{c - x0:.3f}" y2="{d - y0:.3f}" stroke="{col}" stroke-width="0.3"/>'
                   for a, b, c, d, col in lines)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{h:.3f}mm" viewBox="0 0 {w:.3f} {h:.3f}">'
            f"{body}</svg>\n")


def export(template_id, params, source, out_dir, name=None, parts=None, title=None, inject=None):
    """雛形と寸法から部品を作り、検査を通ったら、折りのある部品を 1 つずつ SVG にする。Returns (書いたファイル, 検査の失敗)。

    parts は書き出す部品の key の組（None なら折りのある部品を全部。知らない key は ValueError）。name はファイル名の頭
    （既定は雛形の名前）。title と inject は場面の物で、python -m omochae と同じ検査にするために compose へ渡す。
    前の回の同じ頭の SVG（<頭>_*_foldsim.svg）は、検査に落ちた時も書き出した時も残さない（部品を減らした回と混ざらないように）。
    書き出しは仮の置き場で作り、全部書けてから移す。途中で止まった時は前の回の物に触らない。
    """
    _, layout, failures = compose(template_id, params, source, title=title, inject=inject or {})
    out = pathlib.Path(out_dir)
    head = name or template_id
    old = lambda: list(out.glob(f"{head}_*_foldsim.svg")) if out.exists() else []
    if failures:
        for f in old():
            f.unlink()
        return [], failures
    keys = {q.key for q in layout["parts"]}
    if parts is not None and not set(parts) <= keys:
        raise ValueError(f"知らない部品: {'・'.join(sorted(set(parts) - keys))}（この雛形の部品は {'・'.join(sorted(keys))}）")
    out.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix=".foldsim-", dir=out))
    try:
        made = []
        # 検査を通った配置の部品を使う（型紙に刷る物と同じ部品）。部品の座標は部品の左上が原点なので、頁の上の置き場は関わらない。
        for q in layout["parts"]:
            if (parts is None or q.key in parts) and (q.valley or q.mountain):
                f = work / f"{head}_{q.key}_foldsim.svg"
                f.write_text(part_svg(q), encoding="utf-8")
                made.append(f)
        for f in old():
            f.unlink()
        written = [f.replace(out / f.name) for f in made]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return written, []


def main(argv=None):
    ap = Parser(prog="omochae.foldsim", description="型紙の折りのある部品を、Origami Simulator が読める SVG（外形 黒・山折り 赤・谷折り 青）に書き出す。"
                                                  "書き出す前に型紙と同じ検査を通す。終了: 0 書き出した / 3 検査に落ちた / 4 書き出せない")
    ap.add_argument("--scenario", help="場面の JSON（python -m omochae と同じ形）。渡すと --template・--source・--params は使わない")
    ap.add_argument("--template", default="slider_fan", help="雛形（" + "・".join(sorted(TEMPLATES)) + "。既定 slider_fan）")
    ap.add_argument("--source", help="data/sources/ の出典の記録の名前（既定は雛形ごと）")
    ap.add_argument("--params", help="寸法の JSON。雛形の刷る形の寸法（slider_fan は push_part、pivot_counterweight は mount）が要る")
    ap.add_argument("--parts", help="書き出す部品の key をカンマで（例 fan,tube）。既定は折りのある部品を全部")
    ap.add_argument("--out", default="out/foldsim", help="書き出す所（既定 out/foldsim）")
    ap.add_argument("--name", help="ファイル名の頭（既定は雛形の名前）。<頭>_<部品>_foldsim.svg")
    args = ap.parse_args(argv)
    try:
        sc = scenario_from_args(args)
        if sc["template"] not in TEMPLATES:
            raise ToolMissing(f"知らない雛形: {sc['template']}")
        parts = set(args.parts.split(",")) if args.parts else None
        written, failures = export(sc["template"], sc["params"], load_source(sc["source_id"]), args.out, args.name, parts,
                                   sc.get("title"), sc.get("inject"))
    except (ToolMissing, ValueError) as e:
        print(f"書き出せない: {e}", file=sys.stderr)
        return 4
    except Exception as e:  # 想定外は「書き出した」にも「落ちた」にも数えない。
        print(f"書き出せない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    if failures:
        for f in failures:
            print(f.line(), file=sys.stderr)
        return 3
    if not written:
        print("書き出せない: 折りのある部品が無い（--parts を確かめる）", file=sys.stderr)
        return 4
    for f in written:
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
