"""外の命令や試験が返らない時、決めた秒数で「検査できない（4）」になる。止められた回の一時の置き場は、次の回に残さない（#29）。

偽の命令は眠るだけ。時間切れは環境の変数で短くする（既定は混んだ機械でも越えない長さなので、そのままでは試験が長くなる）。
親の時間切れ（OUTER）は、直す前の命令が固まっても試験だけは戻るためのもの。
"""
import os
import pathlib
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
SCENARIO = str(ROOT / "examples/fan_tab.json")
OUTER = 60  # 偽の命令は 600 秒眠るので、これより長くかかれば時間切れは効いていない


def write_exec(path, body):
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def env_with(fake=None, **extra):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), **extra}
    if fake:
        env["PATH"] = f"{fake}{os.pathsep}{env['PATH']}"
    return env


def generate(out, env, timeout=OUTER):
    try:
        return subprocess.run([PY, "-m", "omochae", "--scenario", SCENARIO, "--out", str(out)], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise SystemExit(f"命令が {timeout} 秒で戻らない（時間切れが効いていない）")


with tempfile.TemporaryDirectory() as tmp:
    base = pathlib.Path(tmp).resolve()

    # 1 どの外の命令が止まっても、決めた秒数で 4。止まった命令の名前を言い、一時の置き場を残さない
    for tool in ("pdftotext", "pdfimages", "pdftoppm", "fc-match"):
        fake = base / f"fake-{tool}"
        fake.mkdir()
        write_exec(fake / tool, "#!/bin/sh\nexec sleep 600\n")
        out = base / f"o-{tool}" / "sc"
        t = time.monotonic()
        r = generate(out, env_with(fake, OMOCHAE_TOOL_TIMEOUT="2"))
        took = time.monotonic() - t
        assert r.returncode == 4, (tool, r.returncode, r.stderr)
        assert tool in r.stderr and "秒" in r.stderr, (tool, r.stderr)
        assert took < OUTER, (tool, took)
        left = [p.name for p in out.parent.glob(".omochae-*")] if out.parent.exists() else []
        assert not left, (tool, left)
        print(f"ok {tool}")

    # 2 外から止められた回の一時の置き場は、次の回が片づける
    fake = base / "fake-kill"
    fake.mkdir()
    write_exec(fake / "pdftotext", f'#!/bin/sh\necho $$ > "{base}/pdftotext.pid"\nexec sleep 600\n')
    out = base / "killed" / "sc"
    proc = subprocess.Popen([PY, "-m", "omochae", "--scenario", SCENARIO, "--out", str(out)], cwd=ROOT,
                            env=env_with(fake), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pid_file = base / "pdftotext.pid"
    end = time.monotonic() + OUTER
    while not pid_file.exists() or not pid_file.read_text(encoding="utf-8").strip():
        assert time.monotonic() < end and proc.poll() is None, "偽の命令まで届かない"
        time.sleep(0.1)
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait()
    os.kill(int(pid_file.read_text(encoding="utf-8")), signal.SIGKILL)
    stale = list(out.parent.glob(".omochae-*"))
    assert len(stale) == 1, ("止められた回の置き場が残るはず（試験の前提）", stale)

    # 動いている回の置き場は消さない（同じ所へ別の回が同時に書く）。名前で作った主は、この試験の子ではなくこの試験そのもの。
    # 名前は work_dir（mkdtemp）が作る形（頭の字・pid・- ・8 字）にそろえる。形の違う名は、そもそも消す物に入らないため
    alive = out.parent / f".omochae-{os.getpid()}-alive000"
    alive.mkdir()
    # pid の無い前の形の古い置き場（頭の字・8 字。時刻で見る）: 古い物だけ消す
    old = out.parent / ".omochae-old00000"
    old.mkdir()
    os.utime(old, (time.time() - 7200, time.time() - 7200))
    fresh = out.parent / ".omochae-fresh000"
    fresh.mkdir()
    # 頭の字は同じでも、work_dir の作る形でない物は、古くても主が死んでいても消さない（--out の親の所は人の置き場でもある）
    dead = subprocess.Popen([PY, "-c", "pass"])
    dead.wait()
    others = [out.parent / ".omochae-old", out.parent / f".omochae-{dead.pid}-keep", out.parent / ".omochae-backup-20261107"]
    for o in others:
        o.mkdir()
        (o / "keep.txt").write_text("x", encoding="utf-8")
        os.utime(o, (time.time() - 7200, time.time() - 7200))

    r = generate(out, env_with())
    assert r.returncode == 0, (r.returncode, r.stderr)
    assert not any(p.exists() for p in stale), "止められた回の置き場が残った"
    assert not old.exists(), "古い置き場が残った"
    assert alive.exists() and fresh.exists(), "動いている回の置き場まで消した"
    assert all((o / "keep.txt").exists() for o in others), ("work_dir の作る形でない物まで消した", [o.name for o in others if not o.exists()])
    assert out.with_suffix(".pdf").exists()
    print("ok stale work dir")

    # 3 折りの絵の一時の置き場も同じ
    fold = base / "fold"
    fold.mkdir()
    dead = subprocess.Popen([PY, "-c", "pass"])
    dead.wait()
    stale_fold = fold / f".foldsim-{dead.pid}-xxxxxxxx"
    stale_fold.mkdir()
    other_fold = fold / f".foldsim-{dead.pid}-x"  # 主は死んでいるが、work_dir の作る形でない名なので残す
    other_fold.mkdir()
    r = subprocess.run([PY, "-m", "omochae.foldsim", "--scenario", SCENARIO, "--out", str(fold)], cwd=ROOT, env=env_with(),
                       capture_output=True, text=True, timeout=OUTER)
    assert r.returncode == 0, (r.returncode, r.stderr)
    assert not stale_fold.exists(), "折りの絵の古い置き場が残った"
    assert other_fold.exists(), "折りの絵の置き場で、work_dir の作る形でない物まで消した"
    print("ok foldsim work dir")

    # 4 床の入口: 返らない子は決めた秒数で打ち切り、4 で名指しする（ほかの子は回し切る）
    root = base / "floors"
    (root / "tests/frozen/scenarios").mkdir(parents=True)
    shutil.copy(ROOT / "tests/run_floors.py", root / "tests/run_floors.py")
    (root / "tests/test_hang.py").write_text("import time\ntime.sleep(600)\n", encoding="utf-8")
    (root / "tests/test_fine.py").write_text("print('ok')\n", encoding="utf-8")
    (root / ".venv/bin").mkdir(parents=True)
    write_exec(root / ".venv/bin/python", f'#!/bin/sh\nexec "{PY}" "$@"\n')
    # 照合の表は今の木から書く。見たいのは表と合った後の回す所（表の見張りは test_frozen_manifest が見る）
    subprocess.run([PY, str(root / "tests/run_floors.py"), "--write-manifest"], capture_output=True, check=True)
    env = {k: v for k, v in env_with(OMOCHAE_CHILD_TIMEOUT="2").items() if k != "PYTHONPATH"}
    try:
        r = subprocess.run([PY, str(root / "tests/run_floors.py")], env=env, capture_output=True, text=True, timeout=OUTER)
    except subprocess.TimeoutExpired:
        raise SystemExit(f"床の入口が {OUTER} 秒で戻らない（時間切れが効いていない）")
    assert r.returncode == 4, (r.returncode, r.stderr)
    assert "test_hang" in r.stderr and "秒" in r.stderr, r.stderr
    table = (root / "out/RESULT.md").read_text(encoding="utf-8")
    assert "test_fine" in table and "test_hang" in table, table
    print("ok floors")

    # 5 秒数の値が読めない時は、黙って時間切れ無しにしない
    r = generate(base / "bad-value" / "sc", env_with(OMOCHAE_TOOL_TIMEOUT="abc"))
    assert r.returncode == 4 and "OMOCHAE_TOOL_TIMEOUT" in r.stderr, (r.returncode, r.stderr)
    print("ok bad value")

print("ok")
