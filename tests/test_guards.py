"""検査と出力の守りの試験。全体の見直し（2026-11-04）で見つかった穴を、1 つずつ負の場面で押さえる。

なぜ場面（tests/frozen）でなく試験にするか: 前の回の出力が残るか・部品表と部品の対応など、1 回の生成の rc と床の名前だけでは見えない物を見るため。
"""
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


def scenario(d, name, params):
    f = pathlib.Path(d) / f"{name}.json"
    f.write_text(json.dumps({"template": "slider_fan", "source_id": SRC_ID, "params": params, "inject": {}}), encoding="utf-8")
    return f


def gen(sc, out):
    return subprocess.run([PY, "-m", "omochae", "--scenario", str(sc), "--out", str(out)], cwd=ROOT, env=ENV, capture_output=True, text=True)


# 1. 描く前の検査に落ちた時、同じ名前の前の回の紙を残さない
with tempfile.TemporaryDirectory() as d:
    out = pathlib.Path(d) / "x"
    assert gen(scenario(d, "ok", {"push_part": "tab"}), out).returncode == 0
    r = gen(scenario(d, "bad", {"push_part": "tab", "fold_height": 50}), out)
    assert r.returncode == 3 and "F5.fan_height" in r.stderr, r.stderr
    left = sorted(p.name for p in pathlib.Path(d).glob("x.*"))
    assert left == [], f"落ちた後に前の紙が残った: {left}"

print("ok")
