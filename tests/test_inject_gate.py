"""場面の inject（負の対照の差し込み）は、試験だけで使える（セキュリティの点検 2026-11-07）。

なぜ要るか: inject は印を抜く・図を貼る・部品を動かすなど、検査が落とす事を確かめるための差し込みで、試験の外では要らない。
前はどの場面からでも渡せた。印（環境の値）の無い道では、空でない inject を、紙を作らずに断る（4）。空の inject は今のまま通す。
印は tests/run_floors.py が inject を持つ凍結の場面の子にだけ渡し、試験の子には渡さない（この試験が印の無い道を確かめられるように）。
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_floors  # noqa: E402
from omochae import compose as compose_mod  # noqa: E402
from omochae.__main__ import load_source  # noqa: E402
from omochae.model import ToolMissing  # noqa: E402

ROOT = run_floors.ROOT
SCENARIOS = ROOT / "tests/frozen/scenarios"
MARK = "OMOCHAE_INJECT"
os.environ.pop(MARK, None)  # 呼ぶ側の印に頼らない（ここで見たいのは印の無い道）
PLAIN = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
NEG = json.loads((SCENARIOS / "neg_overlap.json").read_text(encoding="utf-8"))
SRC = load_source(NEG["source_id"])


def run(module, *args, cwd, env=PLAIN):
    return subprocess.run([sys.executable, "-m", module, *args], cwd=cwd, env=env, capture_output=True, text=True)


# 1. compose（入口がみな通る 1 か所）: 印が無ければ、空でない inject を断る。知らない名前だけの inject も断る。
#    印の値が 1 でない時も断る（消し忘れの 0 や空の値で許さない）。断る文に、渡された差し込みの名前を返さない
for env, inject in (({}, NEG["inject"]), ({}, {"no_such": 1}), ({MARK: "0"}, NEG["inject"]), ({MARK: ""}, NEG["inject"])):
    with mock.patch.dict(os.environ, env):
        try:
            compose_mod.compose(NEG["template"], NEG["params"], SRC, inject=inject)
            raise AssertionError(("印の無い道で inject を通した", env, inject))
        except ToolMissing as e:
            assert "inject" in str(e) and "no_such" not in str(e) and "move_part" not in str(e), e

# 空の inject（{} と None）は、渡さない時と同じに通る
base = compose_mod.compose(NEG["template"], NEG["params"], SRC)[2]
assert base == [], [f.line() for f in base]
for empty in ({}, None):
    assert compose_mod.compose(NEG["template"], NEG["params"], SRC, inject=empty)[2] == [], empty

# 印のある間は、今までどおり差し込み、狙った床で落ちる
with mock.patch.dict(os.environ, {MARK: "1"}):
    fl = compose_mod.compose(NEG["template"], NEG["params"], SRC, inject=NEG["inject"])[2]
assert sorted({f.floor for f in fl}) == NEG["expect"]["floors"], [f.line() for f in fl]

# 2. 入口（python -m omochae）: 印が無ければ、凍結の負の対照の場面を全部、作らずに 4 で断る。前の回の紙も消さない
#    （落ちた 3 にすると、前の回の紙を消す流れに入る）。仮の置き場も残さない
negs = [p for p in sorted(SCENARIOS.glob("*.json")) if json.loads(p.read_text(encoding="utf-8")).get("inject")]
assert len(negs) >= 9, [p.stem for p in negs]
with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    for p in negs:
        old = [d / f"{p.stem}{x}" for x in (".svg", ".pdf", ".png")]
        for f in old:
            f.write_text("前の回", encoding="utf-8")
        r = run("omochae", "--scenario", str(p), "--out", str(d / p.stem), cwd=d)
        assert r.returncode == 4 and r.stderr.startswith("検査できない: ") and "inject" in r.stderr and "FAIL" not in r.stderr, (p.stem, r.returncode, r.stderr)
        assert all(f.read_text(encoding="utf-8") == "前の回" for f in old), (p.stem, "前の回の紙を消した")
    assert sorted(f.name for f in d.iterdir()) == sorted(f"{p.stem}{x}" for p in negs for x in (".svg", ".pdf", ".png")), "紙か仮の置き場を作った"

    # 型紙の書き出し（omochae.foldsim）と 3D の確かめ（omochae.fold3d）も、場面の inject を読むので同じに断る。前の回の SVG も消さない
    fs = d / "fs"
    fs.mkdir()
    (fs / "slider_fan_fan_foldsim.svg").write_text("<svg/>", encoding="utf-8")
    r = run("omochae.foldsim", "--scenario", str(SCENARIOS / "neg_overlap.json"), "--out", str(fs), cwd=d)
    assert r.returncode == 4 and r.stderr.startswith("書き出せない: ") and "inject" in r.stderr, (r.returncode, r.stderr)
    assert [f.name for f in fs.iterdir()] == ["slider_fan_fan_foldsim.svg"], "前の回の SVG を消したか、書き出した"
    r = run("omochae.fold3d", "--scenario", str(SCENARIOS / "neg_overlap.json"), cwd=d)
    assert r.returncode == 4 and r.stderr.startswith("確かめられない: ") and "inject" in r.stderr, (r.returncode, r.stderr)

# 3. 空の inject は、印の無い道で今のまま通る。見本の場面（inject は {}）と、inject を書かない場面（omochae.foldsim は無いのを空と読む）
with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    r = run("omochae", "--scenario", str(ROOT / "examples/fan_tab.json"), "--out", str(d / "fan_tab"), cwd=d)
    assert r.returncode == 0 and (d / "fan_tab.pdf").exists(), (r.returncode, r.stderr)
    plain = d / "plain.json"
    plain.write_text(json.dumps({"template": "slider_fan", "source_id": NEG["source_id"], "params": {"push_part": "tab"}}), encoding="utf-8")
    r = run("omochae.foldsim", "--scenario", str(plain), "--out", str(d / "fs"), cwd=d)
    assert r.returncode == 0 and "_foldsim.svg" in r.stdout, (r.returncode, r.stderr)

# 4. 試験の道（tests/run_floors.py と同じ渡し方）: 試験の子には印を渡さず、inject を持つ場面の子にだけ印を足す
env = run_floors.child_env({**os.environ, MARK: "1", "PYTHONOPTIMIZE": "1"})
assert MARK not in env and "PYTHONOPTIMIZE" not in env, "呼ぶ側の印を試験の子へ渡した"
assert MARK not in run_floors.scenario_env(env, SCENARIOS / "neg_base_size.json"), "inject の無い場面にも印を渡した"
# 前の流れで落ちる所の違う 3 本: 描く前（部品を動かす）・刷った後の画像（図を貼る）・刷った後の字（印を抜く）。rc 3 と狙った床
for name in ("neg_overlap", "neg_image_count", "neg_marks_source_id"):
    p = SCENARIOS / f"{name}.json"
    expect = json.loads(p.read_text(encoding="utf-8"))["expect"]
    with tempfile.TemporaryDirectory() as d:
        r = run("omochae", "--scenario", str(p), "--out", str(pathlib.Path(d) / name), cwd=ROOT, env=run_floors.scenario_env(env, p))
    assert r.returncode == 3 and run_floors.scenario_ok({**expect, "floors": sorted(expect["floors"])}, r.returncode, r.stderr)[0], (name, r.returncode, r.stderr[-300:])

# 結果の表の命令は、inject を持つ場面では印まで含み、repo の頭でそのまま打って同じ結果になる。inject の無い場面の命令は前のまま
cmd = run_floors.scenario_command(SCENARIOS / "neg_overlap.json")
assert cmd.startswith(f"{MARK}=1 PYTHONPATH=src "), cmd
r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"})
assert run_floors.scenario_ok(NEG["expect"], r.returncode, r.stderr)[0], (cmd, r.returncode, r.stderr[-300:])
assert run_floors.scenario_command(SCENARIOS / "neg_base_size.json").startswith("PYTHONPATH=src "), "inject の無い場面の命令を変えた"

# 印の名前は compose と run_floors で同じ（run_floors は src を読まずに回る写しの tree のため、名前を写して持つ）
assert compose_mod.INJECT_MARK == run_floors.INJECT_MARK == MARK
print(f"ok 印の無い道で断った凍結の場面 {len(negs)} 本")
