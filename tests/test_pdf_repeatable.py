"""同じ入力から同じ PDF ができる試験（#37）。

なぜ場面（tests/frozen）でなく試験にするか: 場面は 1 回ずつ刷って床を見るだけで、2 回刷った紙を比べる形を持たない。
別のプロセス・別の時間帯・秒の違う時刻で刷って比べないと、作った時刻の差が見えない。必須 2 種で見る。
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
    r = subprocess.run([sys.executable, "-m", "omochae", "--scenario", f"tests/frozen/scenarios/{scenario}.json", "--out", str(out)],
                       cwd=ROOT, env={**ENV, "TZ": tz}, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return out.with_suffix(".pdf").read_bytes()


# 時間帯と秒を変えて同じなら、作った機械の時計は PDF に入っていない
with tempfile.TemporaryDirectory() as d:
    for scenario in ("pos_tab", "pos_tiger_hang"):
        first = printed(scenario, d, f"{scenario}_a", "Asia/Tokyo")
        time.sleep(1.1)  # 時刻の欄は秒まで。同じ秒に刷ると、時刻が入っていても同じになる
        second = printed(scenario, d, f"{scenario}_b", "UTC")
        assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest(), f"{scenario}: 2 回刷った PDF が違う"
print("ok")
