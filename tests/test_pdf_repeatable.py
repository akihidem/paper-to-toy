"""同じ入力から同じ PDF ができる試験（#37）。

なぜ場面（tests/frozen）でなく試験にするか: 場面は 1 回ずつ刷って床を見るだけで、2 回刷った紙を比べる形を持たない。
別のプロセス・別の時間帯・秒の違う時刻で刷って比べないと、作った時刻の差が見えない。必須 2 種で見る。
必須 2 種の紙は、玩具のたたき台で刷る場面（御来迎 examples/goraigo_v12.json・首振り虎 pos_tiger_neck）。虎は本人の決定（2026-11-05）で
たたき台が neck（元の repo の H-A）になったので、hang の場面から替えた（hang の場面は凍結の正の場面として残る）。
御来迎は本人の決定（2026-11-06）でたたき台が rise（内筒を下から押し上げる形）になったので、pos_tab から替えた。rise には凍結の場面が
無いので、次の組の寸法の見本の場面で刷る（pos_tab は凍結の正の場面として残る）。
"""
import hashlib
import os
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}


def printed(scenario, d, name, tz):
    out = pathlib.Path(d) / name
    r = subprocess.run([sys.executable, "-m", "omochae", "--scenario", scenario, "--out", str(out)],
                       cwd=ROOT, env={**ENV, "TZ": tz}, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return out.with_suffix(".pdf").read_bytes()


# 必須 2 種の場面が、御来迎の rise と虎の neck を刷る物である事を先に見る（場面が別の形に書き替わっても、この試験が黙って通らないように）
import json  # noqa: E402
for scenario, want in (("examples/goraigo_v12.json", ("slider_fan", "push_part", "rise")),
                       ("tests/frozen/scenarios/pos_tiger_neck.json", ("pivot_counterweight", "mount", "neck"))):
    sc = json.loads((ROOT / scenario).read_text(encoding="utf-8"))
    assert sc["template"] == want[0] and sc["params"].get(want[1]) == want[2], (scenario, sc["template"], sc["params"])
# 時間帯と秒を変えて同じなら、作った機械の時計は PDF に入っていない
with tempfile.TemporaryDirectory() as d:
    for scenario in ("examples/goraigo_v12.json", "tests/frozen/scenarios/pos_tiger_neck.json"):
        name = pathlib.Path(scenario).stem
        first = printed(scenario, d, f"{name}_a", "Asia/Tokyo")
        time.sleep(1.1)  # 時刻の欄は秒まで。同じ秒に刷ると、時刻が入っていても同じになる
        second = printed(scenario, d, f"{name}_b", "UTC")
        assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest(), f"{scenario}: 2 回刷った PDF が違う"
print("ok")
