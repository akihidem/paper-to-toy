"""型紙に刷る印（所蔵・改変・出典 ID・仮説）と、刷った後の検査。

なぜ PDF から読み直すか: 「描く命令を出した」ではなく「刷られた紙に載っている」ことを保証するため。
字が画像化された・隠れた・別の字に落ちた場合も、ここで落ちる。
"""

from .model import Failure
from .tools import run_tool

HOLDER = "国立国会図書館デジタルコレクション"
# 制作者の言葉（2026-11-05）「型紙が正解ではなくて、とりあえずAIが考えた仮説であるということを明示する」による。
# 文言は制作者に出して決める（#57）。刷った後の検査（F1.marks）は、この文がそのまま PDF から読める事を見る。
HYPOTHESIS = "仮説: AI が考えた、試すための 1 つの翻案です。正解ではありません。作って、動きを確かめて、直していきます"


def mark_lines(source, omit=None):
    if omit == "all":
        return []
    # 史料でない作例（江戸の玩具でなく、物理などの原理から寸法を出した試作の型紙）の出典は、所蔵の代わりに、その原理の文を
    # 「原理: …」と刷る（holding_label。無ければ今までどおり「所蔵」）。所蔵の無い物に所蔵と刷らないため
    label = source.get("holding_label", "所蔵")
    lines = [f"{label}: {source['holding']}", source["modification_note"], HYPOTHESIS]
    if omit != "source_id":
        lines.insert(2, f"出典ID: {source['source_id']}")
    return lines


def check_image_count(pdf_path, expected=0):
    """PDF に貼られた画像の数を見る。原図を貼らず描き直す決まりを、できた紙で確かめる。"""
    out = run_tool(["pdfimages", "-list", str(pdf_path)], "pdfimages で読めない", text=True).stdout
    # 透明度の smask は別の行に出るので、image の行だけを数える。
    found = sum(1 for line in out.splitlines()[2:] if line.split()[2] == "image")
    return [] if found == expected else [Failure("F5.image_count", "PDF", f"貼られた画像の数 {found} が見込み {expected} と違う")]


def check_pdf(pdf_path, source):
    out = run_tool(["pdftotext", str(pdf_path), "-"], "pdftotext で読めない", text=True).stdout
    # 印が折り返されても読めるよう、空白と改行を全部取ってから探す。
    flat = "".join(out.split())
    # 短い語だけを探すと、本文が欠けても化けても別の所に同じ語が残れば通ってしまう。刷った文をそのまま探す。
    need = {
        "所蔵": HOLDER,
        "所蔵の文": source["holding"],
        "永続ID": source.get("persistent_id"),
        "改変": source["modification_note"],
        "出典ID": source["source_id"],
        "仮説": HYPOTHESIS,
    }
    # 史料の出典（国立国会図書館の図）は、所蔵の名と永続 ID も探す。原理の作例（holding_label を持つ出典）は所蔵も永続 ID も
    # 持たないので探さず、原理の文（所蔵の文の欄）・改変・出典 ID・仮説を探す（史料の出典の見方と並びは変えない）
    if "holding_label" in source:
        del need["所蔵"], need["永続ID"]
    return [Failure("F1.marks", name, f"PDF から「{text}」を取り出せない") for name, text in need.items() if "".join(text.split()) not in flat]
