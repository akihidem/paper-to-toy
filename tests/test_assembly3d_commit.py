"""作り方の 3D の入口（python -m omochae.assembly3d）が、出所の commit を git から読む所の試験（セキュリティの点検 2026-11-07）。

--commit を渡さない時は git の HEAD を読む。git が無い・返らない機械でも、トレースバック（決まりの外の 1）で落ちず、
固まりもせず、出所の commit を無し（null）にして JSON を書く。時間の上限は外の命令と同じ OMOCHAE_TOOL_TIMEOUT で、
値が読めない時は「検査できない」（4）。偽の git は眠るだけ。PATH は、今の PATH の道具から名を挙げた物だけを除いた所にする
（本物の git を隠す。字の道具 fc-match などは要るので残す）。字の道具が無い時も、トレースバックでなく 4 にする。
"""
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCENARIO = str(ROOT / "examples/tora_v7.json")  # 3D の組み立て検品を通る見本（0 で JSON を書く）
OUTER = 120  # 偽の git は 600 秒眠るので、これより長くかかれば時間の上限は効いていない


def path_without(where, *names, extra=None):
    """今の PATH の道具を where に symlink で並べ、names の物だけを除く。extra（名 → 中身）は偽の道具として置く。"""
    where.mkdir()
    for part in os.environ.get("PATH", "").split(os.pathsep):
        for tool in (pathlib.Path(part).iterdir() if part and pathlib.Path(part).is_dir() else []):
            if tool.name not in names and not (where / tool.name).exists() and os.access(tool, os.X_OK):
                (where / tool.name).symlink_to(tool)
    for name, body in (extra or {}).items():
        (where / name).write_text(body, encoding="utf-8")
        (where / name).chmod((where / name).stat().st_mode | stat.S_IEXEC)
    return where


def run(out, path, **env):
    # python は絶対のパスで起こす（PATH は道具を探すためだけ）
    e = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PATH": str(path), **env}
    return subprocess.run([sys.executable, "-m", "omochae.assembly3d", "--scenario", SCENARIO, "--out", str(out)],
                          cwd=ROOT, env=e, capture_output=True, text=True, timeout=OUTER)


with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)

    # 1 git が無い機械: 0 で JSON を書き、出所の commit は null
    r = run(d / "a.json", path_without(d / "no-git", "git"))
    assert r.returncode == 0, ("git が無いと落ちた", r.returncode, r.stderr[-400:])
    assert "Traceback" not in r.stderr, r.stderr[-400:]
    assert json.loads((d / "a.json").read_text(encoding="utf-8"))["engine"]["commit"] is None
    print("ok no git")

    # 2 git が返らない機械: 決めた秒数で諦め、0 で JSON を書く（出所の commit は null）
    hang = path_without(d / "hang-git", "git", extra={"git": f"#!/bin/sh\nexec {shutil.which('sleep')} 600\n"})
    t0 = time.monotonic()
    r = run(d / "b.json", hang, OMOCHAE_TOOL_TIMEOUT="2")
    assert r.returncode == 0, ("git が返らないと落ちた", r.returncode, r.stderr[-400:])
    assert time.monotonic() - t0 < OUTER / 2, "時間の上限が効いていない"
    assert json.loads((d / "b.json").read_text(encoding="utf-8"))["engine"]["commit"] is None
    print("ok hung git")

    # 3 時間の上限の値が読めない: 黙って上限無しにせず、検査できない（4）。JSON は書かない
    r = run(d / "c.json", hang, OMOCHAE_TOOL_TIMEOUT="abc")
    assert r.returncode == 4 and "検査できない" in r.stderr and "OMOCHAE_TOOL_TIMEOUT" in r.stderr, (r.returncode, r.stderr[-400:])
    assert not (d / "c.json").exists()
    print("ok bad timeout")

    # 4 ふだん（git が在る repo の中）: 出所は今の HEAD のまま
    real = shutil.which("git")
    if real and subprocess.run([real, "rev-parse", "HEAD"], cwd=ROOT, capture_output=True).returncode == 0:
        head = subprocess.run([real, "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        r = run(d / "d.json", os.environ.get("PATH", ""))
        assert r.returncode == 0, (r.returncode, r.stderr[-400:])
        assert json.loads((d / "d.json").read_text(encoding="utf-8"))["engine"]["commit"] == head
        print("ok head")

    # 5 字の道具（fc-match）が無い: トレースバックの 1 でなく、検査できない（4）。JSON は書かない
    r = run(d / "e.json", path_without(d / "no-fc", "fc-match"))
    assert r.returncode == 4 and "検査できない" in r.stderr and "Traceback" not in r.stderr, (r.returncode, r.stderr[-400:])
    assert not (d / "e.json").exists()
    print("ok no fc-match")

print("ok")
