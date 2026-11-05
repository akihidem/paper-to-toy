"""作った人の報告（組み上がりの感想と、動いた様子）を確かめ、雛形・形ごとに集めて、直しの案の行き先を出す（Issue #21）。

本人の方針（2026-11-05）: 型紙は、組み上がった物の完成度と、動きの完成度を高めるように洗練させる。その材料は、作った人の報告。
エンジンの受け持ちは、報告の形・その検査・集計まで。報告の入口・確認・公開はサイト（提出物の側）が受け持つ。
判断の芯:
- 今の検査は式と配置だけを見て、実物で確かめた値が 1 つも無い。報告は、その見込みを確かめる唯一の材料になる。
- 直しは人が採る。この道具は型紙も寸法も書き換えず、困り事が「どの寸法・床・組み方の文」に当たるかの行き先だけを出す。
  案に新しい寸法の値を持たせないのは、少ない報告から値を決め打つと、仮説の違いと作り方の違いが混ざるため。
- 報告に名前や連絡先を入れない。提出物の持ち寄りの検査（F10.pii）と同じ見方で、全角や見えない文字をそろえてから落とす。
  落とした報告の中身は、集計にも知らせにも出し直さない。
終了: 0 = 通る / 3 = 落ちる / 4 = 確かめられない（置き場が無い等）。
"""
import argparse
import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter

from .compose import TEMPLATES
from .model import Failure

MOVED = ("moved", "partly", "not")  # 動いた・少し動いた・動かない
FINISH = range(1, 6)  # 仕上がりの点（1 悪い〜5 良い）。作った人の見た目の感じで、数えて比べるためだけの物
# 困り事の種類と、その直しの行き先。床の名は族ごと（下の FLOORS）に差し込む。
KINDS = {
    "cut": "切る線・組み方の文（切る順・大人がする所）",
    "fold": "折り線・凡例（谷と山の向き）",
    "glue": "糊代の大きさと位置",
    "fit": "寸法の隙間と、それを見る床（{floor}）",
    "motion": "動きの式と床（{floor}）・既定の寸法",
    "mark": "位置の印（貼る所・差す深さ）",
    "material": "部品表・用意する物",
    "finish": "描き直しの絵・部品の形（仕上がり・見た目）",
    "other": "人が読んで決める",
}
# 雛形ごとの動きの床。雛形を足したら、ここにも足す（test_feedback の 5 で漏れを見る）。
FLOORS = {
    "slider_fan": "F5.fan_clearance・F5.slide_clearance ほか", "pivot_counterweight": "F5.pivot",
    "spinner": "F5.spin", "whistle": "F5.sound", "popup_jar": "F5.popup・F5.jar_seat", "slide_box": "F5.slide",
    "wheel_cart": "F5.wheel", "balance": "F5.balance", "twist_drum": "F5.drum", "float": "F5.float",
    "pull_nod": "F5.pull_nod", "lever_link": "F5.link", "launcher": "F5.launch", "stand_figure": "F5.stand",
}
ALLOWED = {"template", "form", "params", "source_id", "built", "moved", "finish", "motion_notes", "finish_notes",
           "problems", "reported_at"}
PROBLEM_KEYS = {"kind", "step", "note"}
# 出典の ID と時刻は決まった形だけを通す。自由な文を入れられる欄を、感想の 2 つと困り事の note に絞るため。
SOURCE_ID = re.compile(r"NDL-\d+-R\d+-[LR](-[a-z_]+)?")
REPORTED_AT = re.compile(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:\d{2}|Z)?)?")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)*\.[A-Za-z]{2,}")
# 電話は、数字と区切り（-・空白・点・括弧・+）の並びから数字だけを数えて見る。区切りの形を決め打つと、区切りなし・空白・点・
# 括弧・国番号の書き方ですり抜けた（レビューの高）。\b を使わないのは、Python では漢字やかなも語の文字で、
# 「電話090-…」のように日本語に続く番号を見逃したため。数字の数で分けるので、寸法（03-12-150 mm）は落ちない。
PHONE_RUN = re.compile(r"\+?\(?\d[\d\s().-]{6,}\d")
# 郵便番号は 〒 付きか、3 桁-4 桁で後ろに長さ・重さの単位が続かない物。単位まで見ないと「100-1500 mm」を落とした。
POSTAL = re.compile(r"〒\s*\d{3}-?\d{4}|(?<!\d)\d{3}-\d{4}(?![\d.])(?!\s*(mm|cm|m|g|kg|度|°|枚|本|回))")


def _norm(text):
    """全角を半角にそろえ、見えない文字を消し、どのハイフンやダッシュも - にそろえる。
    そろえないと、全角の番号・間に挟んだ見えない文字・U+2010 や en dash の区切りですり抜けた。"""
    t = unicodedata.normalize("NFKC", str(text))
    t = "".join("-" if unicodedata.category(ch) == "Pd" or ch in "ー−" else ch for ch in t)
    return "".join(ch for ch in t if unicodedata.category(ch) != "Cf")


def _has_pii(text):
    t = _norm(text)
    if EMAIL.search(t) or POSTAL.search(t):
        return True
    for m in PHONE_RUN.finditer(t):
        digits = re.sub(r"\D", "", m.group())
        # 日本の電話は 0 から 10〜11 桁、国番号 81 なら 81 の後に 9〜10 桁
        if (digits.startswith("0") and 10 <= len(digits) <= 11) or (digits.startswith("81") and 11 <= len(digits) <= 12):
            return True
    return False


def _strings(v):
    """入れ子の中の文字列を全部出す（欄の名も）。決まった欄の外に書かれた個人の情報も見るため。"""
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield str(k)
            yield from _strings(x)
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from _strings(x)


def check(r):
    """報告 1 つを確かめる。Returns Failure の list（空なら通る）。
    知らせの文には、報告の値を入れない（落とした報告の中身を出し直さないため。欄の名も、決まりの外の物は出さない）。"""
    out = []
    if not isinstance(r, dict):
        return [Failure("F12.report", "報告", "JSON の物（辞書）でない")]
    # 個人の情報は、欄に関わらず全部の文字列で見る。決まった欄の中だけ見ると、params や source_id に書けばすり抜けた
    if any(_has_pii(t) for t in _strings(r)):
        out.append(Failure("F12.pii", "報告", "メールアドレス・電話番号・郵便番号の形がある（個人の情報は書かない）"))
    if set(r) - ALLOWED:
        out.append(Failure("F12.pii", "欄", f"決まりの外の欄が {len(set(r) - ALLOWED)} つある（名前や連絡先は書かない）"))
    t = r.get("template")
    tpl = TEMPLATES.get(t) if isinstance(t, str) else None
    if tpl is None:
        out.append(Failure("F12.report", "template", f"知らない雛形（{'・'.join(sorted(TEMPLATES))} のどれか）"))
    else:
        f = r.get("form")
        if not isinstance(f, str) or f not in tpl.FORMS:
            out.append(Failure("F12.report", "form", f"{tpl.ID} の形は {'・'.join(map(str, tpl.FORMS))}"))
        params = r.get("params", {})
        if not isinstance(params, dict) or any(k not in tpl.DEFAULTS for k in params) \
                or any(not isinstance(v, (int, float, str)) or isinstance(v, bool) for v in params.values()):
            out.append(Failure("F12.report", "params", f"{tpl.ID} の寸法の名と、数か形の値だけ"))
    sid = r.get("source_id")
    if sid is not None and not (isinstance(sid, str) and SOURCE_ID.fullmatch(sid)):
        out.append(Failure("F12.report", "source_id", "出典の ID の形（NDL-…）でない"))
    at = r.get("reported_at")
    if at is not None and not (isinstance(at, str) and REPORTED_AT.fullmatch(at)):
        out.append(Failure("F12.report", "reported_at", "日付か ISO 8601 の時刻でない"))
    if not isinstance(r.get("built"), bool):
        out.append(Failure("F12.report", "built", "組み上がったかを true か false で書く"))
    m = r.get("moved")
    if not isinstance(m, str) or m not in MOVED:
        out.append(Failure("F12.report", "moved", f"動いたかは {'・'.join(MOVED)} のどれか"))
    fin = r.get("finish")
    if not (isinstance(fin, int) and not isinstance(fin, bool) and fin in FINISH):
        out.append(Failure("F12.report", "finish", "仕上がりの点は 1〜5 の整数"))
    for key in ("motion_notes", "finish_notes"):
        if key in r and not isinstance(r[key], str):
            out.append(Failure("F12.report", key, "文で書く"))
    probs = r.get("problems", [])
    if not isinstance(probs, list):
        out.append(Failure("F12.report", "problems", "困り事は list"))
        probs = []
    for i, pr in enumerate(probs):
        if not isinstance(pr, dict) or not isinstance(pr.get("kind"), str) or pr["kind"] not in KINDS:
            out.append(Failure("F12.report", f"problems[{i}]", f"困り事の種類は {'・'.join(KINDS)} のどれか"))
            continue
        if set(pr) - PROBLEM_KEYS:
            out.append(Failure("F12.pii", f"problems[{i}]", "困り事に決まりの外の欄がある（kind・step・note だけ）"))
        if pr.get("step") is not None and not (isinstance(pr["step"], int) and not isinstance(pr["step"], bool) and pr["step"] >= 1):
            out.append(Failure("F12.report", f"problems[{i}].step", "手順の番号は 1 からの整数か null"))
        if "note" in pr and not isinstance(pr["note"], str):
            out.append(Failure("F12.report", f"problems[{i}].note", "文で書く"))
    return out


def summarize(reports):
    """通った報告を雛形・形ごとに集める。Returns {(template, form): 集計}。困り事は多い順で、行き先の文を付ける。"""
    out = {}
    for r in reports:
        if not isinstance(r, dict) or check(r):
            continue  # 通らない報告は数えない（CLI は先に check で除くが、道具として直に呼ばれても落ちないように）
        key = (r["template"], r["form"])
        g = out.setdefault(key, {"n": 0, "built": 0, "moved": Counter(), "finish": [], "kinds": {}})
        g["n"] += 1
        g["built"] += r["built"]
        g["moved"][r["moved"]] += 1
        g["finish"].append(r["finish"])
        for pr in r.get("problems") or []:
            k = g["kinds"].setdefault(pr["kind"], {"count": 0, "steps": Counter(), "notes": []})
            k["count"] += 1
            if pr.get("step") is not None:
                k["steps"][pr["step"]] += 1
            if pr.get("note"):
                k["notes"].append(pr["note"])
    for (tid, _), g in out.items():
        g["moved"] = {m: g["moved"][m] for m in MOVED}
        g["finish_mean"] = sum(g["finish"]) / len(g["finish"])
        del g["finish"]
        floor = FLOORS.get(tid, "族の床")
        g["problems"] = [{"kind": kind, "count": v["count"], "steps": dict(v["steps"].most_common()),
                          "target": KINDS[kind].format(floor=floor), "notes": v["notes"][:5]}
                         for kind, v in sorted(g.pop("kinds").items(), key=lambda kv: -kv[1]["count"])]
    return out


def _markdown(s):
    lines = ["# 作った人の報告の集計（直しの案の行き先。直しは人が採る）", ""]
    for (tid, form), g in sorted(s.items()):
        m = g["moved"]
        lines += [f"## {tid} / {form}（報告 {g['n']} 件・組み上がり {g['built']}）",
                  f"- 動いた {m['moved']}・少し {m['partly']}・動かない {m['not']}、仕上がりの点の平均 {g['finish_mean']:.1f}"]
        for p in g["problems"]:
            steps = "・".join(f"手順 {k}×{v}" for k, v in p["steps"].items()) or "手順の番号なし"
            lines.append(f"- {p['kind']} {p['count']} 件（{steps}）→ 行き先: {p['target']}")
            lines += [f"  - 「{n}」" for n in p["notes"]]
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.feedback", description="作った人の報告を確かめ（check）、雛形・形ごとに集める（summarize）。"
                                                                     "終了: 0 通る / 3 落ちる / 4 確かめられない")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="報告の JSON を 1 つ確かめる").add_argument("file")
    sm = sub.add_parser("summarize", help="置き場の *.json の報告を集め、Markdown で出す（落ちた報告は数えず、名前だけ知らせる）")
    sm.add_argument("dir")
    sm.add_argument("--json", action="store_true", help="Markdown でなく JSON で出す")
    args = ap.parse_args(argv)

    def load(path):
        try:
            return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError, RecursionError) as e:
            return e

    if args.cmd == "check":
        r = load(args.file)
        if isinstance(r, Exception):
            print(f"確かめられない: {r}", file=sys.stderr)
            return 4
        fails = check(r)
        for f in fails:
            print(f.line(), file=sys.stderr)
        return 3 if fails else 0
    d = pathlib.Path(args.dir)
    if not d.is_dir():
        print(f"確かめられない: 置き場が無い {d}", file=sys.stderr)
        return 4
    good = []
    for p in sorted(d.glob("*.json")):
        r = load(p)
        fails = [Failure("F12.report", "JSON", "読めない")] if isinstance(r, Exception) else check(r)
        if fails:
            # 落ちた報告は、ファイルの名と床の名だけを知らせる（個人の情報の形を含む中身を出し直さない）
            print(f"数えない: {p.name}（{'・'.join(sorted({f.floor for f in fails}))}）", file=sys.stderr)
        else:
            good.append(r)
    s = summarize(good)
    if args.json:
        print(json.dumps([{"template": t, "form": f, **g} for (t, f), g in sorted(s.items())], ensure_ascii=False, indent=1))
    else:
        print(_markdown(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
