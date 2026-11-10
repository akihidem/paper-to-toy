"""改善の輪（omochae.engine_loop）の束の欄の型違いを確かめる（セキュリティの点検 2026-11-07）。
束の欄（TOP_KEYS・GROUP_KEYS・TEXT_KEYS の全部）に、決まりと違う型（null・真偽・整数・小数・字・list・辞書）を入れても、
決まった誤り（F13.bundle。CLI は 3）で断り、トレースバックで落ちない事を見る。群の雛形・刷った組・紙に list や辞書が来ると、
重なりを見る集合に当ててハッシュできずに落ちていた。
置き場に手で置いた束（take を通らない）・深すぎる入れ子・型の違う台帳と案の記録でも、案作り（propose）と並べ（compare）は
トレースバックで落ちず、CLI は 0・3・4 のどれかで終わる（1 と 2 は使わない決まり）。ふだんの束の結果は変わらない。"""
import contextlib
import copy
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import engine_loop as el  # noqa: E402

SAMPLE = json.loads((ROOT / "examples/bundles/sample_made_up.json").read_text(encoding="utf-8"))
tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local")
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")
os.environ["OMOCHAE_REPORTS"] = str(tmp / "reports")
# 型の見本: null・真偽・整数・小数・字・list・辞書。list と辞書は、中身のある物（ハッシュできない物を含む）にする
TYPES = {"null": None, "bool": True, "int": 7, "float": 1.5, "str": "x", "list": ["a"], "dict": {"a": 1}}


def reset():
    shutil.rmtree(tmp / "local", ignore_errors=True)
    shutil.rmtree(tmp / "reports", ignore_errors=True)
    (tmp / "versions.json").unlink(missing_ok=True)


def run_main(*argv):
    """CLI の main を、同じ process の中で回す（例外が出たら、そのまま試験が落ちる）。Returns (rc, stderr)。"""
    err = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
        rc = el.main(list(argv))
    return rc, err.getvalue()


def place(b):
    """take を通さずに、置き場へ束を置く（置いた後に手で書き換えられた束の形）。"""
    d = tmp / "local" / "bundles"
    d.mkdir(parents=True, exist_ok=True)
    (d / "B-20261105-1500-aaaaaaaa.json").write_text(b if isinstance(b, str) else json.dumps(b, ensure_ascii=False), encoding="utf-8")


def variants():
    """欄の全部 × 型の全部。群の欄は、紙の名の無い群（0）と、紙の名のある群（2）の両方で見る。"""
    for k in sorted(el.TOP_KEYS):
        for name, v in TYPES.items():
            b = copy.deepcopy(SAMPLE)
            b[k] = v
            yield f"{k}={name}", b
    for gi in (0, 2):
        for k in sorted(el.GROUP_KEYS):
            for name, v in TYPES.items():
                b = copy.deepcopy(SAMPLE)
                b["groups"][gi][k] = copy.deepcopy(v)
                yield f"groups[{gi}].{k}={name}", b
    for k in sorted(el.TEXT_KEYS):
        for name, v in TYPES.items():
            b = copy.deepcopy(SAMPLE)
            b["groups"][0]["texts"][0][k] = copy.deepcopy(v)
            yield f"texts.{k}={name}", b


# 1. どの欄のどの型でも、check_bundle は Failure の list を返し、take は (path か None, list, 数) を返す（例外で落ちない）。
# 形の誤りがあれば何も置かない。CLI の check と take は 0 か 3、案作りと並べは 0 で終わる
seen = 0
for where, b in variants():
    reset()
    try:
        fails = el.check_bundle(b)
        path, take_fails, _ = el.take(b)
        place(b)
        el.propose()
        el.compare(el.groups(el.sources()), el.ledger())
    except Exception as e:
        raise AssertionError(f"{where}: 決まった誤りでなく {type(e).__name__} で落ちた") from e
    assert all(isinstance(f, el.Failure) and f.floor in ("F13.bundle", "F13.pii") for f in fails), where
    if any(f.floor == "F13.bundle" for f in fails):
        assert path is None and take_fails, where
    reset()
    f = tmp / "b.json"
    f.write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
    for argv in (("check", str(f)), ("take", str(f))):
        rc, err = run_main(*argv)
        assert rc in (0, 3) and "Traceback" not in err, (where, argv, rc, err[-200:])
    place(b)
    for argv in (("propose",), ("compare",)):
        rc, err = run_main(*argv)
        assert rc == 0, (where, argv, rc, err[-200:])
    seen += 1
assert seen == len(TYPES) * (len(el.TOP_KEYS) + 2 * len(el.GROUP_KEYS) + len(el.TEXT_KEYS)), seen

# 2. 前に落ちていた所: 群の雛形・刷った組・紙が list や辞書。その欄を名指しした F13.bundle で断り、CLI は 3（トレースバックの 1 でない）。
# 知らせの文に、束の値を出さない
for gi in (0, 2):
    for k in ("template", "sheet_set", "paper"):
        for v in (["山田"], {"山田": 1}, []):
            b = copy.deepcopy(SAMPLE)
            b["groups"][gi][k] = v
            fails = el.check_bundle(b)
            assert f"groups[{gi}].{k}" in [f.where for f in fails] and all(f.floor == "F13.bundle" for f in fails), (gi, k, v)
            assert not any("山田" in f.line() for f in fails)
f = tmp / "b.json"
f.write_text(json.dumps({**SAMPLE, "groups": [{**SAMPLE["groups"][0], "paper": ["a"]}]}, ensure_ascii=False), encoding="utf-8")
env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
r = subprocess.run([sys.executable, "-m", "omochae.engine_loop", "check", str(f)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
assert r.returncode == 3 and "F13.bundle" in r.stderr and "Traceback" not in r.stderr, (r.returncode, r.stderr[-300:])

# 3. ふだんの束は今までどおり: 見本は通り、同じ雛形・刷った組・紙の群が 2 つあれば断る
assert el.check_bundle(SAMPLE) == []
dup = copy.deepcopy(SAMPLE)
dup["groups"].append(copy.deepcopy(dup["groups"][2]))
assert [f.message for f in el.check_bundle(dup)] == ["同じ雛形・刷った組・紙の群が 2 つある"]

# 4. 深すぎる入れ子: CLI の check は 4（読めない）。置き場の束と受け入れた報告にあっても、読めない物として数えず、案作りは 0
deep = "[" * 100000 + "]" * 100000
reset()
(tmp / "deep.json").write_text(deep, encoding="utf-8")
rc, err = run_main("check", str(tmp / "deep.json"))
assert rc == 4 and "RecursionError" in err, (rc, err)
reset()
place(deep)
(tmp / "reports" / "accepted").mkdir(parents=True)
(tmp / "reports" / "accepted" / "r.json").write_text(deep, encoding="utf-8")
assert el.bundles() == [] and el.report_source() is None
for argv in (("propose",), ("compare",)):
    rc, err = run_main(*argv)
    assert rc == 0, (argv, rc, err[-200:])

# 5. 手で書き換えた台帳（git の中）と案の記録（git の外）の型違いは、CLI では 4（できない）。トレースバックの 1 にしない。
# 知らせは型の名だけで、例外の文（台帳の値が入りうる）を出さない
for led in ([], 1, None, {"versions": [1], "next": []}, {"versions": [], "next": [1]}, {"versions": [{"version": 1, "proposals": ["山田"]}], "next": []},
            {"versions": [], "next": [{"id": ["山田"]}]}):
    reset()
    (tmp / "versions.json").write_text(json.dumps(led, ensure_ascii=False), encoding="utf-8")
    for argv in (("version",), ("compare",), ("propose",)):
        rc, err = run_main(*argv)
        assert rc == 4 and err.startswith("できない: ") and "山田" not in err, (led, argv, rc, err[-200:])
for rec in ([], 1, {"key": ["山田"]}):
    reset()
    d = tmp / "local" / "proposals"
    d.mkdir(parents=True)
    (d / "EP-0001.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    for argv in (("list",), ("show", "EP-0001"), ("propose",), ("adopt", "EP-0001", "--by", "作る人")):
        rc, err = run_main(*argv)
        assert rc == 4 and "山田" not in err, (rec, argv, rc, err[-200:])
reset()
(tmp / "versions.json").write_text("[1]", encoding="utf-8")
r = subprocess.run([sys.executable, "-m", "omochae.engine_loop", "version"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
assert r.returncode == 4 and "Traceback" not in r.stderr, (r.returncode, r.stderr[-300:])

print("OK test_engine_loop_types")
