"""作った人の報告（omochae.feedback）の形と、集めて直しの案を出す所を確かめる（Issue #21）。"""
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import feedback as fb  # noqa: E402

OK = {"template": "spinner", "form": "pinwheel", "built": True, "moved": "partly", "finish": 3,
      "motion_notes": "息では回るが、風では止まる", "finish_notes": "羽の角がよれた",
      "problems": [{"kind": "fit", "step": 4, "note": "柄と羽の間が狭く、羽が柄に擦れた"}]}

# 1. 形の誤りを落とす。知らない雛形・その雛形に無い形・決まりの外の値・知らない困り事の種類
assert fb.check(OK) == [], [f.line() for f in fb.check(OK)]
for bad in ({**OK, "template": "no_such"}, {**OK, "form": "jaw"}, {**OK, "moved": "yes"}, {**OK, "finish": 6},
            {**OK, "built": "はい"}, {**OK, "problems": [{"kind": "smell", "step": 1, "note": ""}]}):
    assert any(f.floor == "F12.report" for f in fb.check(bad)), bad

# 2. 個人の情報（メールアドレス・電話番号・郵便番号・名前や連絡先の欄）を落とす。全角はそろえてから見る
for pii in ({**OK, "motion_notes": "a.b@example.com まで"}, {**OK, "finish_notes": "０９０－１２３４－５６７８"},
            {**OK, "problems": [{"kind": "other", "step": None, "note": "〒123-4567 に住む"}]}, {**OK, "name": "山田"}):
    assert any(f.floor == "F12.pii" for f in fb.check(pii)), pii

# 2b. 日本語に続く番号・区切りの違う番号・どの欄（params・source_id・reported_at・困り事の余分な欄）にあっても落とす
for pii in ({**OK, "motion_notes": "電話090-1234-5678"}, {**OK, "motion_notes": "住所123-4567"}, {**OK, "motion_notes": "09012345678"},
            {**OK, "motion_notes": "090 1234 5678"}, {**OK, "motion_notes": "090.1234.5678"}, {**OK, "motion_notes": "(090)1234-5678"},
            {**OK, "motion_notes": "+81-90-1234-5678"}, {**OK, "motion_notes": "〒1234567"}, {**OK, "motion_notes": "090\u20101234\u20105678"},
            {**OK, "motion_notes": "090\u20131234\u20135678"}, {**OK, "motion_notes": "a\u200b@b.jp"},
            {**OK, "source_id": "山田太郎 090-1234-5678"}, {**OK, "params": {"name": "山田", "tel": "090-1234-5678"}},
            {**OK, "reported_at": "a@b.jp"}, {**OK, "problems": [{"kind": "fit", "step": 1, "note": "", "tel": "090-1234-5678"}]}):
    assert any(f.floor in ("F12.pii", "F12.report") for f in fb.check(pii)), pii
# 2b2. 区切りの違う番号・漢数字・前に数が付く番号・空白の郵便番号・崩したメール・連絡先の印も、文の欄で F12.pii で落とす
for t in ("090/1234/5678", "090・1234・5678", "090_1234_5678", "090,1234,5678", "090～1234～5678", "090の1234の5678",
          "〇九〇-一二三四-五六七八", "2.5 090 1234 5678", "手順3 03 1234 5678", "〒123 4567", "〒 123 4567", "1234567",
          "郵便123-4567.", "a @ b.jp", "a@b . jp", "a(at)b.jp", "山田@例え.日本", "LINE: yamada_taro", "@yamada_taro",
          "https://x.com/yamada"):
    assert any(f.floor == "F12.pii" for f in fb.check({**OK, "motion_notes": t})), t
# 2b3. 決まった形の欄も、値を絞る（自由な文を入れさせない）。深い入れ子は落ちずに F12.report
for bad in ({**OK, "params": {"kind": "山田太郎 横浜市"}}, {**OK, "source_id": "NDL-1-R1-L-yamada_taro"},
            {**OK, "reported_at": "9999-99-99"}):
    assert any(f.floor == "F12.report" for f in fb.check(bad)), bad
deep = []
for _ in range(3000):
    deep = [deep]
assert any(f.floor == "F12.report" for f in fb.check({**OK, "params": {"radius": deep}}))
# 2c. 普通の寸法・日付・記号・小数の並び・範囲は落とさない
for fine in ("12-34mm", "2026-11-05", "糊代@3.0mm", "長さ 100-1500 mm", "03-12-150 mm", "羽 8 枚・半径 46mm",
             "2026-11-05 10:30", "0.1 0.2 0.3 0.4 0.5", "厚さ 0.3 0.5 0.8 1.0 1.2", "200-1000円", "120-1500 rpm", "100-2000%"):
    assert not [f for f in fb.check({**OK, "motion_notes": fine}) if f.floor == "F12.pii"], fine
# 2d. 型の崩れた入力でも落ちずに F12.report を返す。落とした報告の値は知らせに出さない
for broken in ({**OK, "template": ["spinner"]}, {**OK, "problems": [{"kind": ["fit"]}]}, {**OK, "template": "a@b.jp"},
               {**OK, "params": "x"}, {**OK, "motion_notes": 3}):
    fl = fb.check(broken)
    assert fl and "a@b.jp" not in " ".join(f.line() for f in fl), broken

# 3. 集めると、雛形・形ごとに動いた割合・仕上がりの点・多い困り事（手順つき）・直しの行き先が出る
reports = [OK, {**OK, "moved": "moved", "finish": 5, "problems": []},
           {**OK, "moved": "not", "finish": 2, "problems": [{"kind": "fit", "step": 4, "note": "擦れて回らない"},
                                                            {"kind": "glue", "step": 2, "note": "糊代が小さい"}]},
           {"template": "balance", "form": "okiagari", "built": True, "moved": "moved", "finish": 4}]
s = fb.summarize(reports)
pw = s[("spinner", "pinwheel")]
assert pw["n"] == 3 and pw["moved"] == {"moved": 1, "partly": 1, "not": 1}, pw
assert abs(pw["finish_mean"] - 10 / 3) < 1e-9
assert pw["problems"][0]["kind"] == "fit" and pw["problems"][0]["count"] == 2 and pw["problems"][0]["steps"] == {4: 2}
assert "F5.spin" in pw["problems"][0]["target"], pw["problems"][0]["target"]
assert s[("balance", "okiagari")]["n"] == 1
# 直しは人が採る。案は型紙や寸法を書き換えない（案の中に寸法の新しい値を持たない）
assert all("new_value" not in p for p in pw["problems"])

# 4. 入口: check は 0 / 3、summarize は形の誤りや個人の情報のある報告を数えずに知らせる
with tempfile.TemporaryDirectory() as d:
    good, bad = pathlib.Path(d, "r1.json"), pathlib.Path(d, "r2.json")
    good.write_text(json.dumps(OK, ensure_ascii=False), encoding="utf-8")
    bad.write_text(json.dumps({**OK, "motion_notes": "x@y.jp"}, ensure_ascii=False), encoding="utf-8")
    run = lambda *a: subprocess.run([sys.executable, "-m", "omochae.feedback", *a], cwd=ROOT, capture_output=True, text=True,
                                    env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
    assert run("check", str(good)).returncode == 0
    r = run("check", str(bad))
    assert r.returncode == 3 and "F12.pii" in r.stderr, r.stderr
    r = run("summarize", d)
    assert r.returncode == 0 and "spinner" in r.stdout and "r2.json" in r.stderr, (r.stdout, r.stderr)
    assert "x@y.jp" not in r.stdout + r.stderr  # 落とした報告の中身を出し直さない
    leak = pathlib.Path(d, "r3.json")
    leak.write_text(json.dumps({**OK, "template": "z@w.jp"}), encoding="utf-8")
    r = run("check", str(leak))
    assert r.returncode == 3 and "z@w.jp" not in r.stderr, r.stderr  # check も値を出し直さない
    pathlib.Path(d, "r4.json").write_text(json.dumps({**OK, "template": ["x"]}), encoding="utf-8")
    r = run("summarize", d)
    assert r.returncode == 0 and "spinner" in r.stdout, r.stderr  # 型の崩れた 1 つで集計が止まらない

# 5. 雛形を足したら、直しの行き先の床（FLOORS）にも足す。漏れると、その雛形の案が「族の床」としか言えない
from omochae.compose import TEMPLATES
assert set(TEMPLATES) <= set(fb.FLOORS), sorted(set(TEMPLATES) - set(fb.FLOORS))
# 例の報告（examples/reports/spinner_pinwheel.json）は通る
assert fb.check(json.loads((ROOT / "examples/reports/spinner_pinwheel.json").read_text(encoding="utf-8"))) == []

print("ok")
