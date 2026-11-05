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
# 提出物の F10.pii と同じ形。数字の並び（寸法や日付）まで落とさないよう、電話と郵便は区切りの形に限る。
PII = [re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), re.compile(r"\b0\d{1,4}-\d{1,4}-\d{3,4}\b"), re.compile(r"〒?\s*\b\d{3}-\d{4}\b")]


def _norm(text):
    """全角を半角にそろえ、見えない文字を消す。そろえないと、全角の電話番号や間に挟んだ見えない文字ですり抜けた。"""
    t = unicodedata.normalize("NFKC", str(text))
    t = t.replace("－", "-").replace("ー", "-").replace("−", "-")
    return "".join(ch for ch in t if unicodedata.category(ch) != "Cf")


def _texts(r):
    yield r.get("motion_notes", ""), "motion_notes"
    yield r.get("finish_notes", ""), "finish_notes"
    for i, pr in enumerate(r.get("problems") or []):
        if isinstance(pr, dict):
            yield pr.get("note", ""), f"problems[{i}].note"


def check(r):
    """報告 1 つを確かめる。Returns Failure の list（空なら通る）。"""
    out = []
    if not isinstance(r, dict):
        return [Failure("F12.report", "報告", "JSON の物（辞書）でない")]
    extra = set(r) - ALLOWED
    if extra:
        # 名前・連絡先の欄は、決まりの外の欄として落とす。欄の名を知らせるだけで、値は出さない。
        out.append(Failure("F12.pii", "欄", f"決まりの外の欄 {'・'.join(sorted(extra))}（名前や連絡先は書かない）"))
    tpl = TEMPLATES.get(r.get("template"))
    if tpl is None:
        out.append(Failure("F12.report", "template", f"知らない雛形 {r.get('template')!r}"))
    elif r.get("form") not in tpl.FORMS:
        out.append(Failure("F12.report", "form", f"{tpl.ID} の形は {'・'.join(map(str, tpl.FORMS))}"))
    if not isinstance(r.get("built"), bool):
        out.append(Failure("F12.report", "built", "組み上がったかを true か false で書く"))
    if r.get("moved") not in MOVED:
        out.append(Failure("F12.report", "moved", f"動いたかは {'・'.join(MOVED)} のどれか"))
    if not (isinstance(r.get("finish"), int) and not isinstance(r.get("finish"), bool) and r.get("finish") in FINISH):
        out.append(Failure("F12.report", "finish", "仕上がりの点は 1〜5 の整数"))
    probs = r.get("problems", [])
    if not isinstance(probs, list):
        out.append(Failure("F12.report", "problems", "困り事は list"))
        probs = []
    for i, pr in enumerate(probs):
        if not isinstance(pr, dict) or pr.get("kind") not in KINDS:
            out.append(Failure("F12.report", f"problems[{i}]", f"困り事の種類は {'・'.join(KINDS)} のどれか"))
        elif pr.get("step") is not None and not (isinstance(pr["step"], int) and not isinstance(pr["step"], bool) and pr["step"] >= 1):
            out.append(Failure("F12.report", f"problems[{i}].step", "手順の番号は 1 からの整数か null"))
    for text, where in _texts(r):
        if any(p.search(_norm(text)) for p in PII):
            out.append(Failure("F12.pii", where, "メールアドレス・電話番号・郵便番号の形がある（個人の情報は書かない）"))
    return out


def summarize(reports):
    """通った報告を雛形・形ごとに集める。Returns {(template, form): 集計}。困り事は多い順で、行き先の文を付ける。"""
    out = {}
    for r in reports:
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
        except (OSError, ValueError) as e:
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
