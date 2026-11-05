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
import datetime
import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter

from .compose import TEMPLATES

ROOT = pathlib.Path(__file__).resolve().parents[2]
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
           "problems", "reported_at", "reviewed_at"}  # reviewed_at は入口（omochae.intake）で人が受け入れた時刻
PROBLEM_KEYS = {"kind", "step", "note"}
# 出典の ID と時刻は決まった形だけを通す。自由な文を入れられる欄を、感想の 2 つと困り事の note に絞るため。
# 個人の情報の形の見方。式だけで全部の書き方は止められないので、これは補助で、受け入れの前に人が全文を読む（omochae.intake）。
# 見方の芯:
# - 番号は、区切りの文字の種類を決め打たず、2〜5 桁の数の固まりが 3 つ（国番号なら 4 つ）並ぶ所の桁の数で見る。
#   区切りの種類で決めると、/・_ ～ の などの区切りですり抜けた。
# - 小数（0.5 など）の数は固まりに数えない。寸法の小数の並びを電話と取り違えたため。
# - 範囲（200-1000円）は、後ろに単位が続けば郵便番号と見ない。
REPORTED_AT = re.compile(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:\d{2}|Z)?)?")
REPORTED_AT_MAX_DEPTH = 8  # 報告の入れ子の深さの上限。深い入れ子で再帰が止まらないように
KANJI_DIGITS = str.maketrans("〇一二三四五六七八九", "0123456789")
UNITS = ("mm", "cm", "m", "g", "kg", "円", "%", "rpm", "px", "度", "°", "枚", "本", "回", "gsm", "秒", "分", "個", "倍", "段")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[^\W\d_][\w-]*)+")
CONTACT = re.compile(r"(?i)\bline\s*(id)?\s*:|https?://|www\.|(?<![\w@])@[a-z_][a-z0-9_.]{2,}|\b(id|tel|mail)\s*:")
TOKEN = re.compile(r"\d+(\.\d+)?")


def _norm(text):
    """全角を半角に、漢数字を数字に、どのダッシュと波も - にそろえ、見えない文字を消す。メールの崩し（空白・(at)）もそろえる。"""
    t = unicodedata.normalize("NFKC", str(text)).translate(KANJI_DIGITS)
    t = "".join("-" if unicodedata.category(ch) == "Pd" or ch in "ー−~〜" else ch for ch in t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")
    t = re.sub(r"\s*[(\[]\s*at\s*[)\]]\s*", "@", t, flags=re.I)
    t = re.sub(r"\s*@\s*", "@", t)
    # 点が 2 つ以上続く数の並び（090.1234.5678）は小数でなく区切り。小数と取り違えて番号を見逃した
    t = re.sub(r"\d+(?:\.\d+){2,}", lambda m: m.group().replace(".", "-"), t)
    return re.sub(r"(?<=\w)\s*\.\s*(?=[^\W\d_])", ".", t)


def _groups(t):
    """整数の数の固まり（小数は除く）を、(始まり, 終わり, 桁の文字) で返す。"""
    return [(m.start(), m.end(), m.group()) for m in TOKEN.finditer(t) if not m.group(1)
            and not (m.start() > 0 and t[m.start() - 1] == "." and m.start() > 1 and t[m.start() - 2].isdigit())]


def _phone(gs, t):
    for i, (s0, e0, d0) in enumerate(gs):
        if (d0.startswith("0") and 10 <= len(d0) <= 11) or (d0.startswith("81") and 11 <= len(d0) <= 12):
            return True  # 区切りの無い番号
        for n in (3, 4):
            w = gs[i:i + n]
            if len(w) < n or any(w[j + 1][0] - w[j][1] > 2 for j in range(n - 1)):
                continue  # 固まりの間は 2 文字まで（区切りの文字の種類は問わない）
            digits = "".join(x[2] for x in w)
            if not all(2 <= len(x[2]) <= 5 for x in w[1:]):
                continue
            if (n == 3 and digits.startswith("0") and 10 <= len(digits) <= 11) or \
                    (n == 4 and digits.startswith("81") and 11 <= len(digits) <= 12):
                return True
    return False


def _postal(gs, t):
    if re.search(r"〒\D{0,2}\d{3}\D{0,2}\d{4}", t):
        return True
    for i, (s0, e0, d0) in enumerate(gs):
        if len(d0) == 7 and not t[e0:e0 + 1].isdigit():
            return True
        if len(d0) == 3 and i + 1 < len(gs):
            s1, e1, d1 = gs[i + 1]
            gap = t[e0:s1]
            if len(d1) == 4 and gap in ("-", " ", "- ", " -") and not t[e1:].lstrip().startswith(UNITS) \
                    and not t[e1:e1 + 1].isdigit():
                return True
    return False


def _has_pii(text):
    t = _norm(text)
    if EMAIL.search(t) or CONTACT.search(t):
        return True
    gs = _groups(t)
    return _phone(gs, t) or _postal(gs, t)


def _strings(v, depth=0):
    """入れ子の中の文字列を全部出す（欄の名も）。深すぎる入れ子は ValueError（再帰が止まらないように）。"""
    if depth > REPORTED_AT_MAX_DEPTH:
        raise ValueError("入れ子が深すぎる")
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield str(k)
            yield from _strings(x, depth + 1)
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from _strings(x, depth + 1)


def _iso_ok(at):
    """形だけでなく、日付として在るか（9999-99-99 を通さない）。"""
    try:
        datetime.datetime.fromisoformat(at)
        return True
    except ValueError:
        return False


def check(r):
    """報告 1 つを確かめる。Returns Failure の list（空なら通る）。
    知らせの文には、報告の値を入れない（落とした報告の中身を出し直さないため。欄の名も、決まりの外の物は出さない）。"""
    out = []
    if not isinstance(r, dict):
        return [Failure("F12.report", "報告", "JSON の物（辞書）でない")]
    # 個人の情報は、欄に関わらず全部の文字列で見る。決まった欄の中だけ見ると、params や source_id に書けばすり抜けた
    try:
        # source_id と時刻は、下で決まった形（在る出典・在る日付）だけを通すので、文の見方から外す。
        # 外さないと、出典の ID の 7 桁（1187053）を郵便番号と取り違えた
        texts = list(_strings({k: v for k, v in r.items() if k not in ("source_id", "reported_at", "reviewed_at")}))
    except ValueError:
        return [Failure("F12.report", "報告", "入れ子が深すぎる")]
    if any(_has_pii(t) for t in texts):
        out.append(Failure("F12.pii", "報告", "メールアドレス・電話番号・郵便番号・連絡先の形がある（個人の情報は書かない）"))
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
        # 寸法は数だけ。文字の値は、雛形が文字を既定に持つ寸法（形の名など）の、英小文字の短い名だけ
        def ok_param(k, v):
            if k not in tpl.DEFAULTS or isinstance(v, bool):
                return False
            if isinstance(v, (int, float)):
                return True
            return isinstance(v, str) and isinstance(tpl.DEFAULTS[k], str) and re.fullmatch(r"[a-z_]{1,20}", v) is not None
        if not isinstance(params, dict) or not all(ok_param(k, v) for k, v in params.items()):
            out.append(Failure("F12.report", "params", f"{tpl.ID} の寸法の名と、数か形の値だけ"))
    sid = r.get("source_id")
    # 出典の ID は、data/sources に在る記録だけ。形だけで見ると、末尾に好きな文字を足せた
    if sid is not None and not (isinstance(sid, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", sid)
                                and (ROOT / "data/sources" / f"{sid}.json").exists()):
        out.append(Failure("F12.report", "source_id", "data/sources に無い出典の ID"))
    for key in ("reported_at", "reviewed_at"):
        at = r.get(key)
        if at is not None and not (isinstance(at, str) and REPORTED_AT.fullmatch(at) and _iso_ok(at)):
            out.append(Failure("F12.report", key, "日付か ISO 8601 の時刻でない"))
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
