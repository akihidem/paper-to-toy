"""作り方の印（#53）。形ごとに「紙一枚」「折るだけ」「当時の材料」を出す。どれも優劣の印ではない。

本人の言葉（2026-11-05）「一枚の紙から作る選択肢もある」と、本人の決定 (c)「両方を別の印で持つ」による。
- one_sheet（紙一枚）: A4 1 枚に刷った紙だけで作れる。糊・はさみ・定規・カッター・下敷き・目打ちは道具なので使ってよい。
  ほかの材料（竹串・割ピン・粘土・糸・輪ゴム・テープ・厚紙など）は使わない。
- fold_only（折るだけ）: 1 枚の紙を切らずに折るだけで作る。部品が 1 つで、外形が長方形、中の切り込みも穴も無い。
- period（当時の材料）: 紙のほかの材料が、江戸の頃にもあった物（竹・糸・粘土・木・鈴・玉）だけ。
  本人の言葉「竹とか糸は江戸時代にもあったし使ったらよく再現できるということ」による、再現の良さの別の軸。
  紙一枚の印は優劣の印ではない。今の物で代えた材料（輪ゴム・テープ・割ピン・ストローなど）は modern_substitutes に出す。
判断の芯:
- 印は雛形に宣言させず、部品表（bom）・用意する物（materials）・部品（parts）から出す。宣言だと、部品を変えた時に印と食い違う。
- 材料は、部品表の素材と、用意する物の文の両方で見る。部品表に載らない物（割ピン・テープなど）が、用意する物にだけ書かれる雛形があるため。
"""
import argparse
import json
import re
import sys

from .compose import TEMPLATES
from .sheets import is_sheet, reading_of, source_of

# 紙一枚の印を外す材料の語。道具（糊・はさみ・定規・カッター・下敷き・目打ち・鉛筆・ニッパー・紙やすり、
# 硬さを測るのに下げる硬貨）は、玩具の材料でないので入れない。
OTHER = re.compile(r"竹串|割り?ピン|粘土|糸|輪ゴム|テープ|ビーズ|割り箸|厚紙|ストロー|水よけ|ろう|鈴|玉")


# 江戸の頃に無かった、今の物で代えた材料の語。竹串は竹、割り箸は木、粘土（油粘土）は当時の土や練り物に当たると見る（見立て）。
MODERN = re.compile(r"輪ゴム|テープ|割り?ピン|ビーズ|ストロー|厚紙|水よけ|ろう")


def _params(tpl, form):
    p = {**tpl.DEFAULTS, tpl.FORM: form}
    return tpl.filled(p) if hasattr(tpl, "filled") else p


def _is_paper(material):
    m = str(material)
    return "紙" in m and "厚紙" not in m and not OTHER.search(m.replace("紙", ""))


def fold_only(parts):
    """部品が 1 つで、外形が軸にそろった長方形、中の切り込み（cuts）も穴（holes）も無い。"""
    if len(parts) != 1:
        return False
    q = parts[0]
    xs = sorted({round(x, 6) for x, _ in q.outline})
    ys = sorted({round(y, 6) for _, y in q.outline})
    rect = len(q.outline) == 4 and len(xs) == 2 and len(ys) == 2
    return rect and not q.cuts and not q.holes


def details(template_id, form):
    tpl = TEMPLATES[template_id]
    p = _params(tpl, form)
    rows = tpl.bom(p)
    others = [r["name"] for r in rows if not _is_paper(r.get("material", ""))]
    for m in tpl.materials(p):
        for w in OTHER.findall(str(m)):
            if w not in others and not any(w in o for o in others):
                others.append(w)  # 同じ語を 2 度数えない
    text = " ".join([str(r.get("material", "")) for r in rows] + [str(m) for m in tpl.materials(p)])
    modern = sorted(set(MODERN.findall(text)))
    return {"one_sheet": not others, "fold_only": fold_only(tpl.parts(p)), "period": not modern,
            "other_materials": others, "modern_substitutes": modern}


def marks(template_id, form):
    d = details(template_id, form)
    return {"one_sheet": d["one_sheet"], "fold_only": d["fold_only"], "period": d["period"]}


def table():
    """全部の雛形の全部の形の印。サイトの絞り込みに使う。
    sheet は、その形が玩具の型紙の 1 枚か（本人の決定「玩具 1 つに型紙 1 枚」・omochae.sheets）。サイトは sheet の行だけを
    型紙として出す。別の読みの行（sheet が false）も消さずに残し、reading_of で型紙の形を指す（試行錯誤のヒントに使える）。
    行を消さないのは、今の一覧を読む側（サイト）の形を壊さず、足した欄で絞れるようにするため。"""
    return [{"template": tid, "form": str(f), "source_id": source_of(tid, f), "sheet": is_sheet(tid, f),
             "reading_of": reading_of(tid, f), **details(tid, f)}
            for tid, t in sorted(TEMPLATES.items()) for f in t.FORMS]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.ways", description="形ごとの作り方の印（紙一枚・折るだけ・当時の材料）を出す。どれも優劣の印ではない")
    ap.add_argument("--json", action="store_true", help="JSON で出す（サイトの絞り込みに使う）")
    args = ap.parse_args(argv)
    t = table()
    if args.json:
        print(json.dumps(t, ensure_ascii=False))
        return 0
    for r in t:
        mark = "・".join(n for n, k in (("紙一枚", "one_sheet"), ("折るだけ", "fold_only"), ("当時の材料", "period")) if r[k]) or "—"
        print(f"{r['template']:20s} {r['form']:12s} {mark:18s} 材料: {'・'.join(r['other_materials']) or '紙だけ'}"
              f"{'（今の物で代えた: ' + '・'.join(r['modern_substitutes']) + '）' if r['modern_substitutes'] else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
