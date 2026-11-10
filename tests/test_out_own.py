"""型紙の入口（python -m omochae）が検査に落ちた時、--out の所の物を消すのは、この入口が書いたと確かめた紙だけ、という試験
（セキュリティの点検 2026-11-07。3D の入口の同じ種類の守りは tests/test_security.py の 1 が見る）。

なぜ場面（tests/frozen）でなく試験にするか: 場面は空の置き場に 1 回ずつ刷るだけで、--out の所に前から在る物の扱いを見る形を持たない。
落ちる場面は凍結の負の対照を使う（刷った後の検査に落ちる neg_marks_all・neg_image_count。読むだけで変えない）。次を見る:
1. 自分の紙は前と同じに消える（描く前の検査・刷った後の検査のどちらで落ちても。退けた紙の名の前の自分の物は上書きする）
2. 別の物（同じ名の写真・絵の道具で保存し直した SVG・ほかの道具の PDF・PDF の頭だけの物）は消えず、「消さない」の行で言う。
   同じ名の PDF が別の物なら、自分の SVG と PNG も消さない（3 つは同じ名の PDF で確かめる）。作り手だけ合う・時刻だけ合う・
   Info の指さない所に欄を置いた・題で欄を偽った PDF も、この入口の物と読まない
3. 確かめは pdftotext に頼らない（作った時刻をいつも空で出す古い poppler の形の pdftotext を置いても、自分の紙は消える）。
   確かめられない時（大きすぎる・圧縮の爆弾の stream・普通のファイルでない）は消さず、爆弾でも開く大きさは上限で止まる。
   圧縮していない Info の辞書（object stream を使わない cairo の形）も読む
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
import tracemalloc
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
ENV = {**{k: v for k, v in os.environ.items() if k != "OMOCHAE_INJECT"}, "PYTHONPATH": str(ROOT / "src")}
# 刷った後の検査に落ちる負の対照（場面の inject）は、試験の印を立てた子でだけ回る（compose.INJECT_MARK と同じ名。印の無い道では 4 で断る）。
# 印はその場面の子にだけ渡し、ほかの子は印の無い道（使う人と同じ道）で回す
INJECT_ENV = {**ENV, "OMOCHAE_INJECT": "1"}
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


def hand_pdf(path, objs, info):
    """手で書く PDF。頁は持たず、Info の辞書の読み方だけを試す。objs は {番号: 辞書の中身}、info は trailer の /Info の番号。"""
    body = b"".join(b"%d 0 obj\n<< %s >>\nendobj\n" % (n, d) for n, d in objs.items())
    path.write_bytes(b"%PDF-1.4\n" + body + b"trailer\n<< /Size 9 /Info %d 0 R >>\n%%%%EOF\n" % info)


CAIRO, EPOCH = b"/Producer (cairo 1.18.0 (https://cairographics.org))", b"/CreationDate (19700101000000Z)"
NOW = b"/CreationDate (D:20261110120000+09'00)"


def bomb(path):
    """圧縮の爆弾の object stream を持つ PDF（0.3 MB ほどの塊が 256 MB に開く）。/Info はその中を指す。"""
    z = zlib.compressobj(9)
    blob = b"".join(z.compress(b"0" * (1 << 20)) for _ in range(256)) + z.flush()
    head = b"%%PDF-1.7\n1 0 obj\n<< /Type /ObjStm /N 1 /First 4 /Filter /FlateDecode /Length %d >>\nstream\n" % len(blob)
    path.write_bytes(head + blob + b"\nendstream\nendobj\ntrailer\n<< /Info 2 0 R >>\n%%EOF\n")


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
    r = gen(marks, d / "x", INJECT_ENV)
    assert r.returncode == 3 and "F1.marks" in r.stderr and f"退けた: {d / 'x.rejected.pdf'}" in r.stderr and KEEP not in r.stderr, r.stderr
    assert sorted(files(d)) == ["x.rejected.pdf"], sorted(files(d))
    first = (d / "x.rejected.pdf").read_bytes()
    r = gen(images, d / "x", INJECT_ENV)
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
    # 2c. 同じ名の PDF が別の物なら、自分の SVG と PNG も消さない。作り手だけ合う（ほかの cairo の道具・手で書いた物）・時刻だけ合う・
    # Info の指さない所に欄を置いた・題で欄を偽った・PDF の頭だけの物
    fake_title = 'x" /Producer (cairo 1) /CreationDate (19700101000000Z) >> <<'
    others = (("other_pdf", other_pdf), ("forged_title", lambda p: other_pdf(p, fake_title)),
              ("maker_only", lambda p: hand_pdf(p, {1: CAIRO + b" " + NOW}, 1)),
              ("time_only", lambda p: hand_pdf(p, {1: b"/Producer (other 1.0) " + EPOCH}, 1)),
              ("misplaced", lambda p: hand_pdf(p, {1: CAIRO + b" " + NOW, 2: CAIRO + b" " + EPOCH}, 1)),
              ("pdf_head_only", lambda p: p.write_bytes(b"%PDF-1.7\n%%EOF\n")))
    for name, how in others:
        d = case(name, _pdf=how)
        before = files(d)
        r = gen(bad, d / "x")
        assert r.returncode == 3 and all(keep_line(d / f"x{x}") in r.stderr for x in KINDS), (name, r.stderr)
        assert files(d) == before, f"{name}: 別の PDF の名で、紙が消えた"

    # 3. 確かめは pdftotext に頼らない。22.04 より前の poppler の pdftotext は、-htmlmeta の作った時刻をいつも空で出した。
    # その形を出す pdftotext を前に置いても自分の紙は消え、pdftotext は呼ばれない
    fake = base / "bin"
    fake.mkdir()
    called = base / "pdftotext.log"
    (fake / "pdftotext").write_text(f'#!/bin/sh\necho "$*" >> "{called}"\necho \'<meta name="CreationDate" content=""/>\'\n')
    (fake / "pdftotext").chmod(0o755)
    d = case("old_poppler")
    r = gen(bad, d / "x", {**ENV, "PATH": f"{fake}:{os.environ['PATH']}"})
    assert r.returncode == 3 and KEEP not in r.stderr and files(d) == {}, (r.stderr, sorted(files(d)))
    assert not called.exists(), called.read_text(encoding="utf-8")
    # 確かめられない時は消さない: 上限より大きい PDF（自分の紙の後ろを伸ばした物）・圧縮の爆弾
    import omochae.__main__ as entry  # noqa: E402
    big = lambda p: p.write_bytes(OURS["x.pdf"] + b"\n" * entry.PDF_READ_MAX)
    for name, how in (("too_big", big), ("bomb", bomb)):
        d = case(name, _pdf=how)
        before = files(d)
        r = gen(bad, d / "x")
        assert r.returncode == 3 and all(keep_line(d / f"x{x}") in r.stderr for x in KINDS), (name, r.stderr)
        assert files(d) == before, f"{name}: 確かめられない PDF の名で、紙が消えた"
    # 爆弾を開く大きさは上限で止まる（時間でなく、開いた物の大きさで見る。上限の 1 MB に、読んだ塊などの分の余裕を見る）。
    # 先に 1 度呼んで、確かめが読み込む render などの分を測る物から外す
    assert entry._ours_pdf(made / "x.pdf") is True  # 今の cairo（object stream の中）の形
    tracemalloc.start()
    assert entry._ours_pdf(base / "bomb" / "x.pdf") is False
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert peak < 8 * entry.INFLATE_MAX, f"爆弾を {peak} バイトまで開いた（256 MB に開く塊）"
    # 圧縮していない Info の辞書も読む（object stream を使わない cairo の形）。Info の指す辞書の作り手と時刻が合えば、この入口の物と読む
    hand_pdf(base / "plain.pdf", {1: b"/Type /Catalog", 2: CAIRO + b"\n   " + EPOCH}, 2)
    assert entry._ours_pdf(base / "plain.pdf") is True
    # 普通のファイルでない物（PDF の名の所・PNG の名の FIFO）。開かずに言うので止まらない。前は所を消そうとして exit 4 だった
    d = case("not_file", _pdf=lambda p: p.mkdir(), _png=lambda p: os.mkfifo(p))
    r = gen(bad, d / "x")
    assert r.returncode == 3 and all(keep_line(d / f"x{x}") in r.stderr for x in KINDS), r.stderr
    assert (d / "x.pdf").is_dir() and (d / "x.png").exists() and files(d) == {"x.svg": OURS["x.svg"]}, sorted(files(d))

    # 4. 刷った後の検査に落ちた時、退けた紙の名に在る別の物を上書きしない（今回の退けた紙は残さない）。自分の紙は消す
    for name, how in (("rejected_other", other_pdf), ("rejected_text", lambda p: p.write_text("大事なメモ", encoding="utf-8"))):
        d = case(name, _rejected_pdf=how)
        keep = (d / "x.rejected.pdf").read_bytes()
        r = gen(marks, d / "x", INJECT_ENV)
        assert r.returncode == 3 and "F1.marks" in r.stderr and keep_line(d / "x.rejected.pdf") in r.stderr and "退けた: " not in r.stderr, r.stderr
        assert files(d) == {"x.rejected.pdf": keep}, (name, sorted(files(d)))
        assert not [p for p in d.iterdir() if p.name.startswith(".omochae-")], "仮の置き場が残った"

    # 5. 落ちない回の書き出しは今と同じ。同じ名の別の物が在っても、同じバイトの 3 つで置き換え、PDF の名だけを出す
    d = case("success_over_other", _svg=lambda p: p.write_text(EDITED_SVG, encoding="utf-8"), _pdf=other_pdf, _png=photo)
    r = gen(ok, d / "x")
    assert r.returncode == 0 and r.stdout.strip() == str(d / "x.pdf") and r.stderr == "", (r.returncode, r.stderr)
    assert files(d) == OURS, "落ちない回の書き出しが変わった"
