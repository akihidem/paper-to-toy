"""型紙の生成の入口: 寸法 → 配置 → 描く前の検査 → SVG/PDF → 刷った後の検査 → PNG。

終了: 0 = 通る / 3 = 落ちる / 4 = 検査できない。1 と 2 は使わない（検査の結果と道具の故障を読み分けるため）。
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import sys
import zlib

# 読み込みは main の囲いより前に走るので、ここで落ちるとトレースバックの 1 になる（#25）。omochae.foldsim もここを通る。
try:
    from .compose import TEMPLATES, compose
    from .marks import check_image_count, check_pdf
    from .model import ToolMissing, check_name
    from .tools import work_dir
except Exception as e:
    print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(4)

ROOT = pathlib.Path(__file__).resolve().parents[2]


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"omochae: {message}", file=sys.stderr)
        sys.exit(4)


def _named(stem, ext):
    """出力の名前の後ろに拡張子を足す。with_suffix は最後の点から後ろを置き換えるので、tiger_v1.5 が tiger_v1 の紙を指してしまう（#28）。"""
    return stem.with_name(stem.name + ext)


# この入口が書く 3 つの紙の頭。SVG は render.to_svg が drawsvg で書く頭（drawsvg は requirements.txt で版を固定）。型紙の SVG を
# 絵の道具で開いて同じ名で保存し直すと、頭が道具の物に変わるので、手を入れた SVG を前の回の紙と読まない。PNG は PNG の決まった頭だけ
# （pdftoppm の PNG には、この入口が決まった値を書く所が無い）。
HEADS = {".svg": b'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg"', ".pdf": b"%PDF-",
         ".png": b"\x89PNG\r\n\x1a\n"}


def _head_is(path, head):
    """普通のファイルで、頭が head か。FIFO などは開くと止まりうるので、開かない。"""
    try:
        if not path.is_file():
            return False
        with path.open("rb") as f:
            return f.read(len(head)) == head
    except OSError:
        return False


# PDF を読む時の上限。型紙の PDF は、手元で刷った 3688 枚で 0.10〜0.51 MB（2026-11-10）。30 倍ほどの余裕を持たせ、これより大きい物は
# この入口の物と言わない（全部を読む前に止める）。開いた後の上限は、object stream を全部合わせた大きさ（1 つずつの max_length は残り）。
# 同じ 3688 枚では Info の辞書まで 0.5 KB も開かずに届く。圧縮の爆弾（小さな塊が大きく開く物）でも、ここで止まる
PDF_READ_MAX = 16 * 1024 * 1024
INFLATE_MAX = 1024 * 1024


def _pdf_info(data):
    """PDF の Info の辞書（作り手・作った時刻などの欄）の中身のバイト。見つからない・読めない時は None。

    末尾の trailer（cairo 1.18 では XRef の stream の辞書。どちらも圧縮しない）の /Info が指す物を読む。ほかの所に同じ字を置いた PDF を、
    この入口の物と読まないため。Info は、圧縮しない「N 0 obj << … >>」（object stream を使わない cairo 1.16 などの形。その版の実物では
    確かめていない）か、/FlateDecode の object stream の中（cairo 1.18 の形）に在る。object stream のほかの stream（頁の線など）は、
    辞書が入らないので開かない。開けない stream と、形の読めない stream は飛ばす。"""
    refs = re.findall(rb"/Info\s+(\d+)\s+0\s+R", data)
    if not refs:
        return None
    num = int(refs[-1])  # 後から書き足した PDF では、新しい trailer が後ろに来る
    plain = re.search(rb"(?<![0-9])%d\s+0\s+obj\s*<<(.*?)>>" % num, data, re.S)
    if plain:
        return plain.group(1)
    budget = INFLATE_MAX
    for s in re.finditer(rb"<<([^<>]*/Type\s*/ObjStm\b[^<>]*)>>\s*stream\r?\n", data):
        first = re.search(rb"/First\s+(\d+)", s.group(1))
        if not first or not re.search(rb"/Filter\s*/FlateDecode\b", s.group(1)):
            continue
        try:
            body = zlib.decompressobj().decompress(memoryview(data)[s.end():], budget)  # 写さずに渡す（stream ごとに後ろを全部写さない）
        except zlib.error:
            continue
        budget -= len(body)
        first = int(first.group(1))
        try:
            nums = [int(x) for x in body[:first].split()]  # 頭は「番号 位置」の並び
        except ValueError:
            nums = []
        pairs = list(zip(nums[0::2], nums[1::2]))
        for i, (n, at) in enumerate(pairs):
            if n == num:
                stop = first + pairs[i + 1][1] if i + 1 < len(pairs) else len(body)
                found = re.match(rb"\s*<<(.*?)>>", body[first + at:stop], re.S)
                return found.group(1) if found else None
        if budget <= 0:
            return None
    return None


def _ours_pdf(path):
    """この入口（render.write_all）が書いた PDF か。検査に落ちた時に、--out の所の別の物（同じ名の写真や書類）を消さない・
    上書きしないため（セキュリティの点検 2026-11-07）。落ちない回は今までどおり置き換える。3D の入口の _ours（作り方の 3D の JSON か）と
    同じ種類の直し。

    なぜ作った時刻の欄で見るか: write_all は cairo で書き、作った時刻の欄を決まった値 PDF_DATE にする。ほかの道具や人の PDF は
    本当の時刻を持つ（cairo も、時刻を決めないと今の時刻を D:2026… の形で書く）ので、Info の作り手が cairo で、作った時刻が PDF_DATE の
    PDF は、この入口の紙と読める。紙に新しい印を足さずに済む（刷る紙を変えない）。
    なぜ道具を呼ばずに Python で読むか: poppler の pdftotext -htmlmeta は、22.04 より前の版（Ubuntu 22.04 は 22.02）では作った時刻を
    いつも空で出すので、それで見ると、この入口の紙を自分の物と読めない。pdfinfo は init.sh が見ていない。poppler の版の下限を要る物にしない。
    cairo は時刻を「(19700101000000Z)」の形で書く（PDF_DATE から - と T と : を除いた形。頭の D: を付けない。cairo 1.18.0 の実物で確かめた）。
    確かめられない時（読めない・大きすぎる・普通のファイルでない・Info が見つからない・render が読み込めない）は、この入口の物と
    言わない（消さない側）。"""
    if not _head_is(path, HEADS[".pdf"]):
        return False
    try:
        from .render import PDF_DATE  # 描く前の検査だけの時は、消す候補が在る時にだけ重い読み込みをする
        with path.open("rb") as f:
            # 大きさを先に見る（read に上限の大きさを渡すと、小さな物でも上限の分の置き場を取る）
            size = os.fstat(f.fileno()).st_size
            data = f.read(size + 1) if size <= PDF_READ_MAX else b""
    except (ImportError, OSError):
        return False
    info = _pdf_info(data) if 0 < len(data) <= PDF_READ_MAX else None
    if info is None:
        return False
    when = re.escape(PDF_DATE.translate(str.maketrans("", "", "-T:")).encode("ascii"))
    return bool(re.search(rb"/Producer\s*\(cairo \d", info) and re.search(rb"/CreationDate\s*\((?:D:)?" + when + rb"\)", info))


def _keep(path):
    # 3D の入口と同じ言い方にする。確かめられない物も同じ行で言う（どちらも、この入口の物としては扱わない）。
    print(f"--out の所の物は型紙の {path.suffix[1:].upper()} でないので、消さない: {path}", file=sys.stderr)


def _drop(stem):
    """前の回の紙（--out の名の SVG・PDF・PNG）を消す。消すのは、この入口が書いたと確かめた物だけで、ほかは消さずに行で言う。

    SVG と PNG を同じ名の PDF で確かめるのは、SVG と PNG には、PDF の作った時刻の欄のような、この入口が決まった値を書く所が無いため。
    3 つは通った回にだけ、同じ回に同じ名へ置くので、同じ名の PDF がこの入口の物なら、SVG と PNG も同じ回の物と読む。そのうえで、
    それぞれの頭が、この入口の書く形かも見る（HEADS）。PDF が無い・この入口の物と確かめられない時は、SVG と PNG も消さない。
    前の回の紙が正しい名で残りうるが、消さない事は行で分かる。確かめは消す前に済ませる（PDF を先に消すと、SVG と PNG の確かめの
    拠り所が無くなる）。
    限り: この入口の PDF を残したまま、横の SVG・PNG だけを頭の同じ別の物（PNG の写真など）に替えると、それは消える（ファイルの時刻で
    同じ回の物かを見る形は、混んだ機械では書く間の時間の幅が読めず誤りうるので採らない）。"""
    ours = _ours_pdf(_named(stem, ".pdf"))
    for ext, head in HEADS.items():
        old = _named(stem, ext)
        if not (old.exists() or old.is_symlink()):
            continue
        if ours and _head_is(old, head):
            old.unlink()
        else:
            _keep(old)


def load_source(source_id):
    """data/sources の出典の記録を読む。型紙の書き出し（omochae.foldsim）と同じ物を使う。"""
    src = ROOT / "data/sources" / f"{check_name(source_id, 'source_id')}.json"
    if not src.exists():
        # 出典の記録を作る道具（元の repo の omochae.ingest）はこの repo に無いので、置き場だけを言う。
        # 機械の絶対のパスは出さない（受付の画面などへ、そのまま返る文なので）。
        raise ToolMissing(f"出典の記録が無い: {source_id}（data/sources に出典の記録の JSON を置く）")
    return json.loads(src.read_text(encoding="utf-8"))


def scenario_from_args(args):
    """--scenario か、--template・--source・--params から場面を作る。型紙の書き出し（omochae.foldsim）も同じ入口を使う。"""
    if args.scenario:
        return json.loads(pathlib.Path(args.scenario).read_text(encoding="utf-8"))
    # 寸法を直に渡す入口。刷る形を決める寸法（雛形の FORM）は必ず書かせる（どの形を刷ったかを、呼んだ側の JSON に残すため）。
    # 玩具の型紙の 1 枚（たたき台）がどの形かは omochae.sheets が持つ（制作者の決定 2026-11-05「玩具 1 つに型紙 1 枚」）。
    if args.template not in TEMPLATES:
        raise ToolMissing(f"知らない雛形: {args.template}（{'・'.join(TEMPLATES)} のどれか）")
    tpl = TEMPLATES[args.template]
    params = json.loads(pathlib.Path(args.params).read_text(encoding="utf-8")) if args.params else {}
    if tpl.FORM not in params:
        raise ToolMissing(f"寸法の JSON に {tpl.FORM} が要る（雛形 {args.template} の刷る形。{tpl.FORM} の値は README の「雛形」の表）")
    # 刷る形ごとに出典が違う雛形（SOURCES）は、形から既定の出典を選ぶ。1 つの SOURCE に決め打ちすると、別の形の絵に別の玩具の出典を刷った。
    default = getattr(tpl, "SOURCES", {}).get(params[tpl.FORM], tpl.SOURCE)
    return {"template": args.template, "source_id": args.source or default, "params": params, "inject": {}}


def generate(template, params, source_id, out, page="A4", version=1, title=None, inject=None):
    """型紙を 1 枚作る共通の流れ。検査に落ちれば 3 を返す。"""
    source = load_source(source_id)
    stem = pathlib.Path(out)
    _, layout, failures = compose(template, params, source, page, version, title, inject or {})
    if failures:
        # 検査に落ちた時だけ前の回の紙を消す。前に通った紙が正しい名前で残ると、今回の物と取り違える。
        # 検査できない（例外・exit 4）時は消さない。今回は何も分かっていないので、前の結果を壊す理由が無い。
        # 消すのは、この入口が書いたと確かめた紙だけ（_drop）。消さない物の行は、検査の行の後に出す（3D の入口と同じ順）。
        for f in failures:
            print(f.line(), file=sys.stderr)
        _drop(stem)
        return 3
    from .render import to_png, write_all  # 描く前の検査だけの時に重い読み込みをしない
    # 描く・刷った後の検査・PNG は、その回だけの仮の置き場で作り、全部済んでから正しい名前へ移す。途中で検査できなくなった
    # （例外・exit 4）時に、前の回の紙と今回の紙が混ざって残らないようにするため（前の回の紙には触らない）。
    # 置き場は出力と同じ所に毎回別の名前で作る。決まった仮の名前だと、点のある --out や、たまたま同じ名前の別の出力と重なった。
    # 同じ所に置くのは、移す（replace）が同じ機械の中の名前の付け替えで済むようにするため。
    # 限り: 3 つの紙は 1 つずつ移すので、移す途中で止まると新旧が混ざりうる（全部を一度に替える手段が無い。移すのは名前の付け替えだけ）。
    stem.parent.mkdir(parents=True, exist_ok=True)
    work = work_dir(stem.parent, ".omochae-")
    tmp = work / "page"
    try:
        pdf = write_all(layout, tmp)
        failures = check_pdf(pdf, source) + check_image_count(pdf)
        if failures:
            rejected = _named(stem, ".rejected.pdf")
            for f in failures:
                print(f.line(), file=sys.stderr)
            # 退けた紙の名に別の物が在る時は上書きしない（上書きは消すのと同じ。確かめは _drop と同じ _ours_pdf）。
            # その時は今回の退けた紙を残さない（別の名で置くと、使う人の知らない名の物が増える）。
            if not (rejected.exists() or rejected.is_symlink()) or _ours_pdf(rejected):
                pdf.replace(rejected)  # 印の無い紙を正しい名前で残さない。
                print(f"退けた: {rejected}", file=sys.stderr)
            else:
                _keep(rejected)
            _drop(stem)  # 前の回の紙も正しい名前で残さない（今回の物と取り違えるため）。
            return 3
        to_png(pdf, tmp)
        for x in (".svg", ".pdf", ".png"):
            tmp.with_suffix(x).replace(_named(stem, x))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(_named(stem, ".pdf"))
    return 0


def sheet_version(args, sc):
    """題に刷る型紙の版の番号。--version が先、無ければ場面の version（見本の型紙の版。虎 v7 は 7・御来迎 v14 は 14）、どちらも無ければ 1。
    決める側の決定（2026-11-07）「紙の題の版も見本に番号を持たせる形で」。前は見本から版を渡さず、どの版の紙の題も「版 1」だった
    （サイトで v7 と出しても紙は「版 1」）。撮影中の虎 v6 の見本には番号を持たせない（刷った紙を変えない）。
    版は 1 以上の整数に限り、ほかは呼び方の誤り（4）にする（見直しの指摘: 場面の null・字・負の数が、そのまま「版 None」などと刷られた）。
    場面の title は題の全体を置き換えるので、その時は版も title に書く（凍結の場面 pos_long_title のように、題を丸ごと試す場面のため）。"""
    v = args.version if args.version is not None else sc.get("version", 1)
    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
        raise ToolMissing(f"型紙の版（version）は 1 以上の整数にする（{v!r}）")
    return v


def run(args):
    sc = scenario_from_args(args)
    version = sheet_version(args, sc)
    out = args.out or f"out/templates/{sc['template']}_v{version}"
    return generate(sc["template"], sc["params"], sc["source_id"], out, args.page, version, sc.get("title"), sc["inject"])


def main():
    ap = Parser(prog="omochae", description="寸法から型紙の SVG・PDF・PNG を作り、描く前と刷った後に検査する。終了: 0 通る / 3 落ちる / 4 検査できない")
    ap.add_argument("--scenario", help="場面の JSON（template・source_id・params・inject と、あれば version・title）。examples/ と tests/frozen/scenarios/ の形。渡すと --template・--source・--params は使わない")
    # choices で縛らない。--scenario の時は --template を使わないので、併記された値で止めない（知らない名前は run が --params の時だけ落とす）。
    ap.add_argument("--template", default="slider_fan", help="雛形（" + "・".join(sorted(TEMPLATES)) + "。既定 slider_fan）")
    ap.add_argument("--source", help="data/sources/ の出典の記録の名前（既定は雛形ごと: slider_fan は御来迎、pivot_counterweight は張子の首振り虎）")
    ap.add_argument("--params", help="寸法の JSON。雛形の刷る形の寸法（slider_fan は push_part、pivot_counterweight は mount）が要る。書かない寸法は雛形の既定値")
    ap.add_argument("--page", default="A4", choices=["A4", "B4"], help="紙の大きさ（既定 A4）")
    ap.add_argument("--version", type=int, default=None, help="題に刷る版の番号（既定は場面の version、無ければ 1）")
    ap.add_argument("--out", help="出力の名前（拡張子なし）。既定は out/templates/<雛形>_v<版>")
    args = ap.parse_args()
    try:
        return run(args)
    except ToolMissing as e:
        print(f"検査できない: {e}", file=sys.stderr)
        return 4
    except Exception as e:  # 想定外は「通った」にも「落ちた」にも数えない。
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
