"""型紙の入口（python -m omochae）が検査に落ちた時、--out の所の物を消すのは、この入口が書いたと確かめた紙だけ、という試験
（セキュリティの点検 2026-11-07。3D の入口の同じ種類の守りは tests/test_security.py の 1 が見る）。

なぜ場面（tests/frozen）でなく試験にするか: 場面は空の置き場に 1 回ずつ刷るだけで、--out の所に前から在る物の扱いを見る形を持たない。
落ちる場面は凍結の負の対照を使う（刷った後の検査に落ちる neg_marks_all・neg_image_count。読むだけで変えない）。次を見る:
1. 自分の紙は前と同じに消える（描く前の検査・刷った後の検査のどちらで落ちても。退けた紙の名の前の自分の物は上書きする）
2. 別の物（同じ名の写真・絵の道具で保存し直した SVG・ほかの道具の PDF・PDF の頭だけの物）は消えず、「消さない」の行で言う。
   同じ名の PDF が別の物なら、自分の SVG と PNG も消さない（3 つは同じ名の PDF で確かめる）
3. 確かめられない時（pdftotext が落ちる・返らない、普通のファイルでない）は消さない
4. 刷った後の検査に落ちた時、退けた紙の名に在る別の物を上書きしない
5. 落ちない回の書き出しは今と同じ（3 つを書き、同じ名の別の物は同じバイトの紙で置き換え、PDF の名を出す）
"""
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
SRC_ID = "NDL-1187053-R0000005-L"
FROZEN = ROOT / "tests/frozen/scenarios"
KINDS = (".svg", ".pdf", ".png")
KEEP = "でないので、消さない: "


def scenario(d, name, params):
    f = pathlib.Path(d) / f"{name}.json"
    f.write_text(json.dumps({"template": "slider_fan", "source_id": SRC_ID, "params": params, "inject": {}}), encoding="utf-8")
    return f


def gen(sc, out, env=ENV):
    return subprocess.run([PY, "-m", "omochae", "--scenario", str(sc), "--out", str(out)], cwd=ROOT, env=env, capture_output=True,
                          text=True, timeout=600)


def files(d):
    return {p.name: p.read_bytes() for p in pathlib.Path(d).iterdir() if p.is_file() and p.suffix != ".json"}


def keep_line(path):
    return f"--out の所の物は型紙の {path.suffix[1:].upper()} {KEEP}{path}"


sys.path.insert(0, str(ROOT / "src"))
import cairocffi  # noqa: E402
from PIL import Image  # noqa: E402


def other_pdf(path, title="書類"):
    """ほかの道具の PDF。作り手は同じ cairo でも、作った時刻の欄は本当の時刻（この入口の決まった値でない）。"""
    s = cairocffi.PDFSurface(str(path), 100, 100)
    s.set_metadata(cairocffi.PDF_METADATA_TITLE, title)
    cairocffi.Context(s).show_page()
    s.finish()


def photo(path):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "green").save(buf, format="PNG")
    path.write_bytes(buf.getvalue())


EDITED_SVG = ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!-- 絵の道具で保存し直した型紙 -->\n'
              '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm"></svg>\n')

with tempfile.TemporaryDirectory() as base:
    base = pathlib.Path(base)
    ok, bad = scenario(base, "ok", {"push_part": "tab"}), scenario(base, "bad", {"push_part": "tab", "fold_height": 50})
    marks, images = FROZEN / "neg_marks_all.json", FROZEN / "neg_image_count.json"
    made = base / "made"
    made.mkdir()
    r = gen(ok, made / "x")
    assert r.returncode == 0 and r.stdout.strip() == str(made / "x.pdf") and r.stderr == "", (r.returncode, r.stderr)
    OURS = files(made)
    assert sorted(OURS) == ["x.pdf", "x.png", "x.svg"], sorted(OURS)

    def case(name, **put):
        """自分の紙の写しを置いた所を作る。put の値が None の物は置かない・関数は、その名の物を作る。"""
        d = base / name
        d.mkdir()
        for n, b in OURS.items():
            (d / n).write_bytes(b)
        for ext, how in put.items():
            p = d / f"x{ext.replace('_', '.')}"
            p.unlink(missing_ok=True)
            if how is not None:
                how(p)
        return d

    # 1. 自分の紙は前と同じに消える。描く前の検査に落ちた時
    d = case("own_pre")
    r = gen(bad, d / "x")
    assert r.returncode == 3 and "F5.fan_height" in r.stderr and KEEP not in r.stderr, r.stderr
    assert files(d) == {}, f"自分の紙が残った: {sorted(files(d))}"
    # 刷った後の検査に落ちた時も消え、退けた紙だけが残る。退けた紙の名の前の自分の物は上書きする
    d = case("own_post")
    r = gen(marks, d / "x")
    assert r.returncode == 3 and "F1.marks" in r.stderr and f"退けた: {d / 'x.rejected.pdf'}" in r.stderr and KEEP not in r.stderr, r.stderr
    assert sorted(files(d)) == ["x.rejected.pdf"], sorted(files(d))
    first = (d / "x.rejected.pdf").read_bytes()
    r = gen(images, d / "x")
    assert r.returncode == 3 and "F5.image_count" in r.stderr and "退けた: " in r.stderr and KEEP not in r.stderr, r.stderr
    assert sorted(files(d)) == ["x.rejected.pdf"] and (d / "x.rejected.pdf").read_bytes() != first, "自分の前の退けた紙を上書きしない"

    # 2. 別の物は消えず、行で言う
    # 2a. 同じ名の写真だけ（PDF が無い）: 写真は消さない
    d = case("photo", _svg=None, _pdf=None, _png=photo)
    before = files(d)
    r = gen(bad, d / "x")
    assert r.returncode == 3 and "F5.fan_height" in r.stderr and keep_line(d / "x.png") in r.stderr, r.stderr
    assert files(d) == before, "同じ名の写真が消えた"
    # 2b. PDF は自分の物でも、絵の道具で保存し直した SVG は消さない（頭がこの入口の形でない）。PDF と PNG は消す
    d = case("edited_svg", _svg=lambda p: p.write_text(EDITED_SVG, encoding="utf-8"))
    r = gen(bad, d / "x")
    assert r.returncode == 3 and keep_line(d / "x.svg") in r.stderr and r.stderr.count(KEEP) == 1, r.stderr
    assert files(d) == {"x.svg": EDITED_SVG.encode("utf-8")}, sorted(files(d))
    # 2c. 同じ名の PDF が別の物（作った時刻が本当の時刻・題で行の形を偽る・PDF の頭だけ）なら、自分の SVG と PNG も消さない
    fake_title = 'x"/>\n<meta name="Producer" content="cairo 1"/>\n<meta name="CreationDate" content="1970-01-01T00:00:00Z"/>'
    for name, how in (("other_pdf", other_pdf), ("forged_title", lambda p: other_pdf(p, fake_title)),
                      ("pdf_head_only", lambda p: p.write_bytes(b"%PDF-1.7\n%%EOF\n"))):
        d = case(name, _pdf=how)
        before = files(d)
        r = gen(bad, d / "x")
        assert r.returncode == 3 and all(keep_line(d / f"x{x}") in r.stderr for x in KINDS), (name, r.stderr)
        assert files(d) == before, f"{name}: 別の PDF の名で、紙が消えた"

    # 3. 確かめられない時は消さない
    fake = base / "bin"
    fake.mkdir()
    for tool, body in (("fail", "exit 1"), ("slow", "exec sleep 30")):
        (fake / tool).mkdir()
        (fake / tool / "pdftotext").write_text(f"#!/bin/sh\n{body}\n")
        (fake / tool / "pdftotext").chmod(0o755)
    for tool, extra in (("fail", {}), ("slow", {"OMOCHAE_TOOL_TIMEOUT": "1"})):
        d = case(f"tool_{tool}")
        r = gen(bad, d / "x", {**ENV, **extra, "PATH": f"{fake / tool}:{os.environ['PATH']}"})
        assert r.returncode == 3 and all(keep_line(d / f"x{x}") in r.stderr for x in KINDS), (tool, r.stderr)
        assert files(d) == OURS, f"pdftotext が {tool} の時に紙が消えた"
    # 普通のファイルでない物（PDF の名の所・PNG の名の FIFO）。開かずに言うので止まらない。前は所を消そうとして exit 4 だった
    d = case("not_file", _pdf=lambda p: p.mkdir(), _png=lambda p: os.mkfifo(p))
    r = gen(bad, d / "x")
    assert r.returncode == 3 and all(keep_line(d / f"x{x}") in r.stderr for x in KINDS), r.stderr
    assert (d / "x.pdf").is_dir() and (d / "x.png").exists() and files(d) == {"x.svg": OURS["x.svg"]}, sorted(files(d))

    # 4. 刷った後の検査に落ちた時、退けた紙の名に在る別の物を上書きしない（今回の退けた紙は残さない）。自分の紙は消す
    for name, how in (("rejected_other", other_pdf), ("rejected_text", lambda p: p.write_text("大事なメモ", encoding="utf-8"))):
        d = case(name, _rejected_pdf=how)
        keep = (d / "x.rejected.pdf").read_bytes()
        r = gen(marks, d / "x")
        assert r.returncode == 3 and "F1.marks" in r.stderr and keep_line(d / "x.rejected.pdf") in r.stderr and "退けた: " not in r.stderr, r.stderr
        assert files(d) == {"x.rejected.pdf": keep}, (name, sorted(files(d)))
        assert not [p for p in d.iterdir() if p.name.startswith(".omochae-")], "仮の置き場が残った"

    # 5. 落ちない回の書き出しは今と同じ。同じ名の別の物が在っても、同じバイトの 3 つで置き換え、PDF の名だけを出す
    d = case("success_over_other", _svg=lambda p: p.write_text(EDITED_SVG, encoding="utf-8"), _pdf=other_pdf, _png=photo)
    r = gen(ok, d / "x")
    assert r.returncode == 0 and r.stdout.strip() == str(d / "x.pdf") and r.stderr == "", (r.returncode, r.stderr)
    assert files(d) == OURS, "落ちない回の書き出しが変わった"
